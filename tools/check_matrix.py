#!/usr/bin/env python3
"""The gate. Re-checks a matrix file against the RFP source text it cites, and fails on any miss.

    python3 tools/check_matrix.py outputs/some-rfp.matrix.json

What it proves (see reference/schema.md for the contract it enforces):

  1. Every sourced field (section, criterion, points, input needed, evaluation criteria,
     answering section, stated total, could-not-map entries) carries a citation of the form
     p<page>:<line> or p<page>:<line>-p<page>:<line>, and that place exists in the source.
  2. The field's text is a verbatim substring of the cited lines (whitespace collapsed,
     nothing else changed). A paraphrase fails. A criterion spelled "the usual way" fails.
  3. A points value is a number that appears, as a number, on its cited line(s).
  4. The Points column sums to the RFP's stated total, or the file says why it does not.
  5. The human columns (input_source, owner, human_check) are empty. The translator never
     fills them. `claude_does` is one of the fixed phrases; `status` is "open".
  6. A field with nothing to cite says exactly "not in source".

Exit 0 = every claim in the matrix was found in the input. Exit 1 = at least one was not,
and each one is named.

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
EMPTY = "not in source"
CLAUDE_DOES = {
    "draft: write the response to this criterion from the inputs in Input needed, citing each one",
    "assemble: fill the RFP's own form from figures a person supplies; no prose",
    "prepare: build the interview or presentation material from the submitted proposal; scored live, not in writing",
}
CITE = re.compile(r"^p(\d+):(\d+)(?:-p(\d+):(\d+))?$")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def load_source(path: pathlib.Path) -> dict:
    lines = {}
    order = []
    for raw in path.read_text().splitlines():
        tag, _, text = raw.partition("|")
        m = re.match(r"p(\d+):(\d+)$", tag)
        if not m:
            continue
        key = (int(m.group(1)), int(m.group(2)))
        lines[key] = text
        order.append(key)
    return {"lines": lines, "order": order}


def cited_text(src: dict, cite: str):
    m = CITE.match(cite or "")
    if not m:
        return None, f"bad citation format {cite!r}"
    a = (int(m.group(1)), int(m.group(2)))
    b = (int(m.group(3)), int(m.group(4))) if m.group(3) else a
    if a not in src["lines"] or b not in src["lines"]:
        return None, f"citation {cite} is not in the source"
    order = src["order"]
    i, j = order.index(a), order.index(b)
    if j < i:
        return None, f"citation {cite} runs backwards"
    if j - i > 60:
        return None, f"citation {cite} spans more than 60 lines; cite the lines that carry the words"
    return " ".join(src["lines"][k] for k in order[i:j + 1]), None


def check_field(src, where, v, problems, numeric=False):
    if v == EMPTY:
        return
    if not isinstance(v, dict) or "cite" not in v:
        problems.append(f"{where}: must be {{text|value, cite}} or the phrase {EMPTY!r}")
        return
    text, err = cited_text(src, v.get("cite"))
    if err:
        problems.append(f"{where}: {err}")
        return
    if numeric:
        val = v.get("value")
        if not isinstance(val, (int, float)):
            problems.append(f"{where}: value must be a number, got {val!r}")
            return
        nums = [float(n) for n in re.findall(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])", text)]
        if float(val) not in nums:
            problems.append(f"{where}: {val} does not appear as a number at {v['cite']} ({norm(text)[:80]!r})")
        return
    t = v.get("text", "")
    if not t or not t.strip():
        problems.append(f"{where}: empty text; use {EMPTY!r} if the RFP has nothing")
        return
    if norm(t) not in norm(text):
        problems.append(f"{where}: text is not verbatim at {v['cite']}: {norm(t)[:90]!r}")


def check(m: dict, base: pathlib.Path):
    problems = []
    src_path = (base / m["source"]) if not pathlib.Path(m["source"]).is_absolute() else pathlib.Path(m["source"])
    if not src_path.exists():
        src_path = pathlib.Path(m["source"])
    if not src_path.exists():
        return [f"source text not found: {m['source']}"], 0
    src = load_source(src_path)
    check_field(src, "rfp", m.get("rfp"), problems)
    st = m.get("stated_total")
    stages = None
    if isinstance(st, dict) and "stages" in st:
        # An RFP that scores in stages (e.g. 60 for the proposal, 40 for the interview) and
        # never writes one grand total. Each stage total is cited and reconciled on its own.
        stages = {}
        for s in st["stages"]:
            check_field(src, f"stated_total stage {s.get('name')}", s, problems, numeric=True)
            stages[s.get("name")] = s.get("value")
        if st.get("combined"):
            check_field(src, "stated_total combined", st["combined"], problems)
    else:
        check_field(src, "stated_total", st, problems, numeric=True)
    total = 0.0
    stage_sum = {}
    for i, r in enumerate(m.get("rows", []), start=1):
        if stages is not None:
            if r.get("stage") not in stages:
                problems.append(f"row {i} stage: {r.get('stage')!r} is not a stated stage")
            elif isinstance(r.get("points"), dict) and isinstance(r["points"].get("value"), (int, float)):
                stage_sum[r["stage"]] = stage_sum.get(r["stage"], 0) + r["points"]["value"]
        for k in SOURCED:
            if k not in r:
                problems.append(f"row {i}: missing field {k}")
                continue
            check_field(src, f"row {i} {k}", r[k], problems, numeric=(k == "points"))
        if isinstance(r.get("points"), dict) and isinstance(r["points"].get("value"), (int, float)):
            total += r["points"]["value"]
        for k in HUMAN:
            if r.get(k, "") != "":
                problems.append(f"row {i} {k}: human column must be empty, translator wrote {r[k]!r}")
        if r.get("claude_does") not in CLAUDE_DOES:
            problems.append(f"row {i} claude_does: not one of the fixed phrases")
        if r.get("status") != "open":
            problems.append(f"row {i} status: must be 'open'")
    for i, c in enumerate(m.get("could_not_map", []), start=1):
        check_field(src, f"could_not_map {i}", {"text": c.get("text"), "cite": c.get("cite")}, problems)
        if not c.get("why"):
            problems.append(f"could_not_map {i}: needs a why")
    if stages is not None:
        for name, want in stages.items():
            got = stage_sum.get(name, 0)
            if got != want and not m.get("stop"):
                problems.append(f"stage {name!r}: rows sum to {got:g} but the RFP states {want}; set 'stop'")
    elif isinstance(st, dict):
        if st.get("value") != total and not m.get("stop"):
            problems.append(f"points sum to {total:g} but the RFP states {st.get('value')}; "
                            f"set 'stop' to say so rather than adjusting a row")
    elif st == EMPTY:
        if m.get("rows") and not m.get("stop"):
            problems.append("no stated total in source but rows carry points; set 'stop'")
    total = int(total) if total == int(total) else total
    return problems, total


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
          f"({'reconciles' if reconciles(m, total) else 'STOP state recorded: ' + str(m.get('stop'))})")


def stated_label(st):
    if isinstance(st, dict) and "stages" in st:
        return " + ".join(f"{s['name']} {s['value']}" for s in st["stages"])
    return str(st["value"]) if isinstance(st, dict) else str(st)


def reconciles(m, total):
    st = m["stated_total"]
    if isinstance(st, dict) and "stages" in st:
        return total == sum(s["value"] for s in st["stages"]) and not m.get("stop")
    return isinstance(st, dict) and st.get("value") == total


if __name__ == "__main__":
    main()
