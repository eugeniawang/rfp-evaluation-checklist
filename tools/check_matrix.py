#!/usr/bin/env python3
"""The gate. Re-checks a matrix file against the RFP source text it cites, and fails on any miss.

    python3 tools/check_matrix.py outputs/some-rfp.matrix.json

What it proves (reference/schema.md is the contract it enforces):

  1. Every sourced field carries a citation p<page>:<line> or p<page>:<line>-p<page>:<line>,
     on ONE page, spanning at most 12 lines, and that place exists in the source.
  2. The field's text is a whole-word, verbatim run of the cited lines (whitespace collapsed,
     nothing else changed). A paraphrase fails. A respelling fails. A fragment that starts or
     ends mid-word fails.
  3. A points value is a number printed on its cited line(s), and a points citation spans at
     most 2 lines, so the number is the one beside the criterion and not one from nearby text.
  4. Rows are in the RFP's order: each criterion is cited later in the source than the last.
  5. The Points column sums to the stated total (per stage when staged), or `stop` names why.
  6. Every key is a known key. The human columns (input_source, owner, human_check) are present
     and empty. `claude_does`, `status`, `stop` and every `could_not_map[].why` come from closed
     vocabularies, so no free text exists anywhere in the matrix that is not a cited quotation.
  7. A field with nothing to cite says exactly "not in source".

Exit 0 = every claim in the matrix was found in the input. Exit 1 = at least one was not, and
each one is named.

Standard library only.
"""
import json
import pathlib
import re
import sys

COLUMNS = ["#", "section", "criterion", "points", "input_needed", "input_source",
           "evaluation_criteria", "answering_section", "owner", "claude_does",
           "human_check", "status"]
SOURCED = ["section", "criterion", "points", "input_needed", "evaluation_criteria", "answering_section"]
HUMAN = ["input_source", "owner", "human_check"]
ROW_KEYS = set(COLUMNS[1:]) | {"stage"}
TOP_KEYS = {"rfp", "source", "stated_total", "rows", "could_not_map", "stop"}
EMPTY = "not in source"
MAX_SPAN = 12          # lines one citation may cover, on one page
MAX_POINTS_SPAN = 2    # lines a points citation may cover
CLAUDE_DOES = {
    "draft: write the response to this criterion from the inputs in Input needed, citing each one",
    "assemble: fill the RFP's own form from figures a person supplies; no prose",
    "prepare: build the interview or presentation material from the submitted proposal; scored live, not in writing",
}
WHY = {
    "applies to every row; no points of its own",
    "scoring method that applies to every row; no points of its own",
    "pass/fail gate that removes a proposal from scoring; not a scored criterion",
    "later stage whose criteria and points are not in this document",
    "submittal item the RFP does not tie to a scored criterion",
    "sits inside a scored criterion with no points of its own",
}
STOP = {
    "points do not reconcile to the stated total",
    "no scoring table published",
}
CITE = re.compile(r"^p(\d+):(\d+)(?:-p(\d+):(\d+))?$")
NUMBER = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def load_source(path: pathlib.Path) -> dict:
    lines, order = {}, []
    for raw in path.read_text().splitlines():
        tag, _, text = raw.partition("|")
        m = re.match(r"p(\d+):(\d+)$", tag)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        lines[key] = text
        order.append(key)
    return {"lines": lines, "order": order, "pos": {k: i for i, k in enumerate(order)}}


def cited_text(src: dict, cite: str, max_span: int = MAX_SPAN):
    m = CITE.match(cite or "")
    if not m:
        return None, f"bad citation format {cite!r}"
    a = (int(m.group(1)), int(m.group(2)))
    b = (int(m.group(3)), int(m.group(4))) if m.group(3) else a
    if a not in src["lines"] or b not in src["lines"]:
        return None, f"citation {cite} is not in the source"
    if a[0] != b[0]:
        return None, f"citation {cite} crosses a page; cite the lines on one page"
    i, j = src["pos"][a], src["pos"][b]
    if j < i:
        return None, f"citation {cite} runs backwards"
    if j - i + 1 > max_span:
        return None, f"citation {cite} spans {j - i + 1} lines; the limit is {max_span}"
    return " ".join(src["lines"][k] for k in src["order"][i:j + 1]), None


def whole_word_in(needle: str, hay: str) -> bool:
    """needle occurs in hay starting and ending at word boundaries (whitespace or edge)."""
    n, h = norm(needle), norm(hay)
    if not n:
        return False
    start = 0
    while True:
        k = h.find(n, start)
        if k < 0:
            return False
        end = k + len(n)
        before_ok = k == 0 or h[k - 1] == " "
        after_ok = end == len(h) or h[end] == " "
        if before_ok and after_ok:
            return True
        start = k + 1


def check_field(src, where, v, problems, numeric=False):
    if v == EMPTY:
        return
    if not isinstance(v, dict) or "cite" not in v or set(v) - {"text", "value", "cite"}:
        problems.append(f"{where}: must be {{text|value, cite}} or the phrase {EMPTY!r}")
        return
    text, err = cited_text(src, v.get("cite"), MAX_POINTS_SPAN if numeric else MAX_SPAN)
    if err:
        problems.append(f"{where}: {err}")
        return
    if numeric:
        val = v.get("value")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            problems.append(f"{where}: value must be a number, got {val!r}")
            return
        if float(val) not in [float(n) for n in NUMBER.findall(text)]:
            problems.append(f"{where}: {val} does not appear as a number at {v['cite']} ({norm(text)[:80]!r})")
        return
    t = v.get("text", "")
    if not isinstance(t, str) or not t.strip():
        problems.append(f"{where}: empty text; use {EMPTY!r} if the RFP has nothing")
        return
    if not whole_word_in(t, text):
        problems.append(f"{where}: text is not verbatim (whole words) at {v['cite']}: {norm(t)[:90]!r}")


def cite_pos(src, v):
    m = CITE.match(v.get("cite", "")) if isinstance(v, dict) else None
    return src["pos"].get((int(m.group(1)), int(m.group(2)))) if m else None


def check(m: dict, base: pathlib.Path):
    problems = []
    if not isinstance(m, dict):
        return ["matrix must be a JSON object"], 0
    extra = set(m) - TOP_KEYS
    if extra:
        problems.append(f"unknown top-level key(s) {sorted(extra)}; nothing may exist outside the contract")
    for k in ("rfp", "source", "stated_total", "rows", "could_not_map"):
        if k not in m:
            problems.append(f"missing top-level key {k}")
    if problems:
        return problems, 0
    src_path = pathlib.Path(m["source"])
    if not src_path.is_absolute():
        src_path = base / src_path
    if not src_path.exists():
        return [f"source text not found: {m['source']}"], 0
    src = load_source(src_path)

    check_field(src, "rfp", m["rfp"], problems)
    st = m["stated_total"]
    stages = None
    if isinstance(st, dict) and "stages" in st:
        if set(st) - {"stages", "combined"}:
            problems.append("stated_total: staged form allows only 'stages' and 'combined'")
        stages = {}
        for s in st["stages"]:
            if set(s) - {"name", "value", "cite"}:
                problems.append(f"stated_total stage {s.get('name')}: only name, value, cite")
            check_field(src, f"stated_total stage {s.get('name')}", {"value": s.get("value"), "cite": s.get("cite")},
                        problems, numeric=True)
            stages[s.get("name")] = s.get("value")
        if st.get("combined"):
            check_field(src, "stated_total combined", st["combined"], problems)
    else:
        check_field(src, "stated_total", st, problems, numeric=True)

    total, stage_sum, last_pos = 0.0, {}, -1
    for i, r in enumerate(m["rows"], start=1):
        if not isinstance(r, dict):
            problems.append(f"row {i}: must be an object")
            continue
        extra = set(r) - ROW_KEYS
        if extra:
            problems.append(f"row {i}: unknown key(s) {sorted(extra)}; nothing may exist outside the twelve columns")
        for k in COLUMNS[1:]:
            if k not in r:
                problems.append(f"row {i}: missing field {k}")
        if stages is not None:
            if r.get("stage") not in stages:
                problems.append(f"row {i} stage: {r.get('stage')!r} is not a stated stage")
        elif "stage" in r:
            problems.append(f"row {i}: 'stage' is only allowed when stated_total is staged")
        for k in SOURCED:
            if k in r:
                check_field(src, f"row {i} {k}", r[k], problems, numeric=(k == "points"))
        p = r.get("points")
        if isinstance(p, dict) and isinstance(p.get("value"), (int, float)):
            total += p["value"]
            if stages is not None and r.get("stage") in stages:
                stage_sum[r["stage"]] = stage_sum.get(r["stage"], 0) + p["value"]
        for k in HUMAN:
            if k in r and r[k] != "":
                problems.append(f"row {i} {k}: human column must be empty, translator wrote {r[k]!r}")
        if r.get("claude_does") not in CLAUDE_DOES:
            problems.append(f"row {i} claude_does: not one of the fixed phrases")
        if r.get("status") != "open":
            problems.append(f"row {i} status: must be 'open'")
        pos = cite_pos(src, r.get("criterion"))
        if pos is not None:
            if pos <= last_pos:
                problems.append(f"row {i}: criterion cited at {r['criterion']['cite']} comes before the previous row; "
                                f"rows follow the RFP's order")
            last_pos = pos

    if not isinstance(m["could_not_map"], list):
        problems.append("could_not_map must be a list (empty is fine)")
    else:
        for i, c in enumerate(m["could_not_map"], start=1):
            if not isinstance(c, dict) or set(c) != {"text", "cite", "why"}:
                problems.append(f"could_not_map {i}: exactly text, cite, why")
                continue
            check_field(src, f"could_not_map {i}", {"text": c["text"], "cite": c["cite"]}, problems)
            if c["why"] not in WHY:
                problems.append(f"could_not_map {i} why: not one of the fixed reasons")

    stop = m.get("stop")
    if stop is not None and stop not in STOP:
        problems.append(f"stop: not one of the fixed states {sorted(STOP)}")
    if stages is not None:
        for name, want in stages.items():
            got = stage_sum.get(name, 0)
            if got != want and stop != "points do not reconcile to the stated total":
                problems.append(f"stage {name!r}: rows sum to {got:g} but the RFP states {want}; "
                                f"set stop to 'points do not reconcile to the stated total'")
    elif isinstance(st, dict):
        if st.get("value") != total and stop != "points do not reconcile to the stated total":
            problems.append(f"points sum to {total:g} but the RFP states {st.get('value')}; "
                            f"set stop to 'points do not reconcile to the stated total' rather than adjusting a row")
    elif st == EMPTY:
        if stop != "no scoring table published":
            problems.append("stated_total is not in source; stop must be 'no scoring table published'")
        if m["rows"]:
            problems.append("no stated total in source but the matrix has rows with points")
    total = int(total) if total == int(total) else total
    return problems, total


def stated_label(st):
    if isinstance(st, dict) and "stages" in st:
        return " + ".join(f"{s['name']} {s['value']}" for s in st["stages"])
    return str(st["value"]) if isinstance(st, dict) else str(st)


def reconciles(m, total):
    if m.get("stop"):
        return False
    st = m["stated_total"]
    if isinstance(st, dict) and "stages" in st:
        return total == sum(s["value"] for s in st["stages"])
    return isinstance(st, dict) and st.get("value") == total


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_matrix.py <matrix.json>")
    p = pathlib.Path(sys.argv[1])
    m = json.loads(p.read_text())
    problems, total = check(m, p.parent)
    if problems:
        print(f"FAIL {p}: {len(problems)} problem(s)")
        for x in problems:
            print("  -", x)
        sys.exit(1)
    print(f"PASS {p}: {len(m['rows'])} rows, every cited claim found in {m['source']}; "
          f"points {total} vs stated {stated_label(m['stated_total'])} "
          f"({'reconciles' if reconciles(m, total) else 'STOP: ' + str(m.get('stop'))})")


if __name__ == "__main__":
    main()
