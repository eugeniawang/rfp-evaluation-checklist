#!/usr/bin/env python3
"""The gate. Re-checks a matrix file against the RFP source text it cites, and fails on any miss.

    python3 tools/check_matrix.py outputs/some-rfp.matrix.json

What it proves (reference/schema.md is the contract it enforces):

  1. Every sourced field carries a citation p<page>:<line> or p<page>:<line>-p<page>:<line>,
     on ONE page, spanning at most 12 lines, and that place exists in the source. A sourced
     text field (not `criterion` or `points`) may instead be a list of 1-10 such objects, for
     an ask spread across several passages; each part is checked independently.
  2. The field's text is a whole-word, verbatim run of the cited lines (whitespace collapsed,
     nothing else changed). A paraphrase fails. A respelling fails. A fragment that starts or
     ends mid-word fails.
  3. A points value is a number printed on its cited line(s), and a points citation spans at
     most 2 lines, so the number is the one beside the criterion and not one from nearby text.
  4. Rows are in the RFP's order: each criterion is cited later in the source than the last.
  5. The Points column sums to the stated total (per stage when staged), or `stop` names why.
  6. Every key is a known key. The four human columns (status, input_source, lead, reviewer)
     are present and always empty on hand-over. Every `kind` and `could_not_map[].why` come
     from closed vocabularies, so no free text exists anywhere in the matrix that is not a
     cited quotation.
  7. A field with nothing to cite says exactly "not in source".
  8. `answering_section` never holds an instruction: a part beginning with an imperative verb
     (Provide, Describe, Identify, ...) is refused. Name a section/item/form, or say
     "not in source".
  9. Part 2 `disqualifiers`: every entry is verbatim and cited, and its `kind` is one of the
     nine fixed phrases.
  10. Coverage: every source line that matches a scoring or gating trigger pattern is cited
      somewhere in the matrix (a row, a disqualifier, a could_not_map entry, or a `reviewed`
      entry) — nothing that looks like scoring or a gate is silently dropped.
  11. `issuer`, `title` and `due` (Ruling 18:49: who, what, when) are required top-level sourced
      fields, checked like `rfp` — verbatim, cited, or "not in source".

Exit 0 = every claim in the matrix was found in the input, and every line that looked like it
mattered was accounted for. Exit 1 = at least one was not, and each one is named.

Standard library only.
"""
import json
import pathlib
import re
import sys

# The nine real columns (Ruling 18:25). `section` is a tenth per-row field — still sourced
# and cited — but it is not a table column: it renders as a group heading above the rows that
# share it. `#` is a render-time row index, folded into the criterion cell; it is not a key.
COLUMNS = ["status", "criterion", "points", "input_needed", "input_source",
           "evaluation_criteria", "answering_section", "lead", "reviewer"]
ROW_FIELDS = ["section"] + COLUMNS  # every real key a row dict may carry (plus optional "stage")
SOURCED = ["section", "criterion", "points", "input_needed", "evaluation_criteria", "answering_section"]
MULTI_OK = {"section", "input_needed", "evaluation_criteria", "answering_section"}  # not criterion, not points
HUMAN = ["status", "input_source", "lead", "reviewer"]  # always "" on hand-over
ROW_KEYS = set(ROW_FIELDS) | {"stage"}
TOP_KEYS = {"rfp", "issuer", "title", "due", "source", "stated_total", "rows",
            "disqualifiers", "could_not_map", "reviewed", "stop"}
REQUIRED_TOP = ("rfp", "issuer", "title", "due", "source", "stated_total", "rows",
                "disqualifiers", "could_not_map", "reviewed")
TOP_SOURCED = ("rfp", "issuer", "title", "due")  # who/what/when at the top; each may be multi-part
EMPTY = "not in source"
MAX_SPAN = 12          # lines one citation may cover, on one page
MAX_POINTS_SPAN = 2    # lines a points citation may cover
WHY = {
    "applies to every row; no points of its own",
    "scoring method that applies to every row; no points of its own",
    "later stage whose criteria and points are not in this document",
    "submittal item the RFP does not tie to a scored criterion",
    "sits inside a scored criterion with no points of its own",
    "named criterion with no points printed",
}
KIND = {
    "late submittal",
    "incomplete submittal or missing required item",
    "missing or incorrect required form",
    "prequalification, license, or registration required",
    "page, format, or delivery rule",
    "non-responsive or non-responsible determination",
    "explicit disqualification",
    "owner reserves the right to reject",
    "other gate stated in the source",
}
REVIEWED_WHY = {
    "not about how proposals are evaluated or rejected",
    "repeats a sentence already cited",
    "table of contents or index entry",
    "scoring of a different procurement or contract phase",
}
IMPERATIVE_VERBS = {
    "Provide", "Describe", "Identify", "Define", "Summarize", "Include", "List", "Explain",
    "Submit", "Discuss", "Demonstrate", "Outline", "Detail", "Present", "Show", "Indicate",
}
STOP = {
    "points do not reconcile to the stated total",
    "no scoring table published",
    "no total stated; rows are the RFP's own maximums",
}
CITE = re.compile(r"^p(\d+):(\d+)(?:-p(\d+):(\d+))?$")
NUMBER = re.compile(r"(?<![\d.])\d+(?:\.\d+)?(?![\d.])")

TRIGGER_PATTERNS = [
    # scoring
    r"\b\d+\s*(points?|pts\.?)\b",
    r"\b\d+\s*%",
    r"\bpoints possible\b",
    r"\bweight(ed|ing)?\b",
    r"\bscor(e|ed|es|ing)\b",
    r"\bevaluation criteria\b",
    r"\bpass/fail\b",
    r"\bnot scored\b",
    r"\bmaximum\b",
    r"\bmax\.?\s*\d",
    # gates
    r"non-?responsive",
    r"non-?responsib",
    r"disqualif",
    r"\breject",
    r"will not be (considered|evaluated|scored|accepted|opened|reviewed)",
    r"shall not be (considered|evaluated|scored|accepted|opened|reviewed)",
    r"\bmandatory\b",
    r"\blate (proposals?|submittals?|bids?|responses?)\b",
    r"\bprequalif",
]
TRIGGER_RE = re.compile("|".join(TRIGGER_PATTERNS), re.IGNORECASE)

# The coverage scan only: some sources set headings/emphasis with Unicode hyphen variants
# (e.g. U+2011 non-breaking hyphen) instead of ASCII "-", which silently defeats `non-?responsive`
# and friends. Normalize to ASCII "-" before matching triggers. Never used for verbatim/whole-word
# text matching — a citation's quoted text still must match the source's actual characters.
HYPHEN_VARIANTS = str.maketrans({chr(c): "-" for c in range(0x2010, 0x2016)} | {0x2212: "-"})


def normalize_hyphens(s: str) -> str:
    return s.translate(HYPHEN_VARIANTS)


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


def citation_lines(src: dict, cite):
    """The (page, line) keys a valid citation covers, or None if it doesn't parse/exist."""
    if not isinstance(cite, str):
        return None
    m = CITE.match(cite)
    if not m:
        return None
    a = (int(m.group(1)), int(m.group(2)))
    b = (int(m.group(3)), int(m.group(4))) if m.group(3) else a
    if a not in src["lines"] or b not in src["lines"] or a[0] != b[0]:
        return None
    i, j = src["pos"][a], src["pos"][b]
    if j < i:
        return None
    return src["order"][i:j + 1]


def collect_cites(node):
    """Every 'cite' string anywhere under node, walked generically (dicts and lists)."""
    out = []
    if isinstance(node, dict):
        c = node.get("cite")
        if isinstance(c, str):
            out.append(c)
        for v in node.values():
            out.extend(collect_cites(v))
    elif isinstance(node, list):
        for item in node:
            out.extend(collect_cites(item))
    return out


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


def check_one(src, where, v, problems, numeric=False):
    if not isinstance(v, dict) or "cite" not in v or set(v) - {"text", "value", "cite"}:
        problems.append(f"{where}: must be {{text|value, cite}} or the phrase {EMPTY!r}")
        return None
    text, err = cited_text(src, v.get("cite"), MAX_POINTS_SPAN if numeric else MAX_SPAN)
    if err:
        problems.append(f"{where}: {err}")
        return None
    if numeric:
        val = v.get("value")
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            problems.append(f"{where}: value must be a number, got {val!r}")
            return None
        if float(val) not in [float(n) for n in NUMBER.findall(text)]:
            problems.append(f"{where}: {val} does not appear as a number at {v['cite']} ({norm(text)[:80]!r})")
        return None
    t = v.get("text", "")
    if not isinstance(t, str) or not t.strip():
        problems.append(f"{where}: empty text; use {EMPTY!r} if the RFP has nothing")
        return None
    if not whole_word_in(t, text):
        problems.append(f"{where}: text is not verbatim (whole words) at {v['cite']}: {norm(t)[:90]!r}")
        return None
    return t


def check_field(src, where, v, problems, numeric=False, multi=False):
    """Returns the list of verified text part(s), or None (EMPTY / invalid)."""
    if v == EMPTY:
        return None
    if multi and isinstance(v, list):
        if not (1 <= len(v) <= 10):
            problems.append(f"{where}: multi-part list must have 1 to 10 parts")
            return None
        out = []
        for idx, part in enumerate(v, start=1):
            t = check_one(src, f"{where} part {idx}", part, problems, numeric=numeric)
            if t is not None:
                out.append(t)
        return out or None
    t = check_one(src, where, v, problems, numeric=numeric)
    return [t] if t is not None else None


def cite_pos(src, v):
    m = CITE.match(v.get("cite", "")) if isinstance(v, dict) else None
    return src["pos"].get((int(m.group(1)), int(m.group(2)))) if m else None


def imperative_violation(text: str):
    m = re.match(r"([A-Za-z]+)", text.strip())
    return m and m.group(1) in IMPERATIVE_VERBS


def check_answering_section(where, v, problems):
    parts = v if isinstance(v, list) else ([v] if v != EMPTY else [])
    for idx, part in enumerate(parts, start=1):
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            if imperative_violation(part["text"]):
                label = where + (f" part {idx}" if isinstance(v, list) else "")
                first = part["text"].strip().split()[0] if part["text"].strip() else ""
                problems.append(f"{label}: begins with an imperative verb ({first!r}); "
                                f"name a section/item/form, or use {EMPTY!r}")


def check_coverage(m: dict, src: dict, problems: list):
    hits = [key for key in src["order"] if TRIGGER_RE.search(normalize_hyphens(src["lines"][key]))]
    buckets = {
        "rows": collect_cites(m.get("rfp")) + collect_cites(m.get("issuer")) + collect_cites(m.get("title"))
                + collect_cites(m.get("due")) + collect_cites(m.get("stated_total"))
                + collect_cites(m.get("rows", [])),
        "disqualifiers": collect_cites(m.get("disqualifiers", [])),
        "could_not_map": collect_cites(m.get("could_not_map", [])),
        "reviewed": collect_cites(m.get("reviewed", [])),
    }
    covered_by = {name: set() for name in buckets}
    for name, cites in buckets.items():
        for c in cites:
            lines = citation_lines(src, c)
            if lines:
                covered_by[name].update(lines)
    covered_all = set()
    for s in covered_by.values():
        covered_all |= s
    for (page, line) in hits:
        if (page, line) not in covered_all:
            problems.append(f"COVERAGE: p{page}:{line} not cited or reviewed: {src['lines'][(page, line)]}")
    counts = {name: sum(1 for h in hits if h in covered_by[name]) for name in buckets}
    return hits, counts


def coverage_stats(m: dict, base: pathlib.Path):
    """Recomputes coverage for rendering. Only meaningful once check() reports no problems."""
    src_path = pathlib.Path(m["source"])
    if not src_path.is_absolute():
        src_path = base / src_path
    src = load_source(src_path)
    problems = []
    hits, counts = check_coverage(m, src, problems)
    return len(hits), counts


def check(m: dict, base: pathlib.Path):
    problems = []
    if not isinstance(m, dict):
        return ["matrix must be a JSON object"], 0
    extra = set(m) - TOP_KEYS
    if extra:
        problems.append(f"unknown top-level key(s) {sorted(extra)}; nothing may exist outside the contract")
    for k in REQUIRED_TOP:
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

    for k in TOP_SOURCED:
        check_field(src, k, m[k], problems, multi=True)
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
            problems.append(f"row {i}: unknown key(s) {sorted(extra)}; nothing may exist outside the nine "
                            f"columns plus section and stage")
        for k in ROW_FIELDS:
            if k not in r:
                problems.append(f"row {i}: missing field {k}")
        if stages is not None:
            if r.get("stage") not in stages:
                problems.append(f"row {i} stage: {r.get('stage')!r} is not a stated stage")
        elif "stage" in r:
            problems.append(f"row {i}: 'stage' is only allowed when stated_total is staged")
        for k in SOURCED:
            if k in r:
                check_field(src, f"row {i} {k}", r[k], problems, numeric=(k == "points"), multi=(k in MULTI_OK))
        if "answering_section" in r:
            check_answering_section(f"row {i} answering_section", r["answering_section"], problems)
        p = r.get("points")
        if isinstance(p, dict) and isinstance(p.get("value"), (int, float)):
            total += p["value"]
            if stages is not None and r.get("stage") in stages:
                stage_sum[r["stage"]] = stage_sum.get(r["stage"], 0) + p["value"]
        for k in HUMAN:
            if k in r and r[k] != "":
                problems.append(f"row {i} {k}: human column must be empty, translator wrote {r[k]!r}")
        pos = cite_pos(src, r.get("criterion"))
        if pos is not None:
            if pos <= last_pos:
                problems.append(f"row {i}: criterion cited at {r['criterion']['cite']} comes before the previous row; "
                                f"rows follow the RFP's order")
            last_pos = pos

    if not isinstance(m["disqualifiers"], list):
        problems.append("disqualifiers must be a list (empty is fine)")
    else:
        for i, d in enumerate(m["disqualifiers"], start=1):
            if not isinstance(d, dict) or set(d) != {"text", "cite", "kind"}:
                problems.append(f"disqualifiers {i}: exactly text, cite, kind")
                continue
            check_field(src, f"disqualifiers {i}", {"text": d["text"], "cite": d["cite"]}, problems)
            if d["kind"] not in KIND:
                problems.append(f"disqualifiers {i} kind: not one of the fixed phrases")

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

    if not isinstance(m["reviewed"], list):
        problems.append("reviewed must be a list (empty is fine)")
    else:
        for i, rv in enumerate(m["reviewed"], start=1):
            if not isinstance(rv, dict) or set(rv) != {"cite", "why"}:
                problems.append(f"reviewed {i}: exactly cite, why")
                continue
            lines = citation_lines(src, rv.get("cite"))
            if lines is None:
                problems.append(f"reviewed {i}: citation {rv.get('cite')!r} is invalid, not in source, "
                                f"or crosses a page")
            elif len(lines) > MAX_SPAN:
                problems.append(f"reviewed {i}: citation spans {len(lines)} lines; the limit is {MAX_SPAN}")
            if rv.get("why") not in REVIEWED_WHY:
                problems.append(f"reviewed {i} why: not one of the fixed reasons")

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
        if stop == "no total stated; rows are the RFP's own maximums":
            if not m["rows"]:
                problems.append("stop 'no total stated; rows are the RFP's own maximums' is set but the "
                                f"matrix has no rows")
        elif stop == "no scoring table published":
            if m["rows"]:
                problems.append("no stated total in source but the matrix has rows with points")
        else:
            problems.append("stated_total is not in source; stop must be 'no scoring table published' "
                            "(no rows) or \"no total stated; rows are the RFP's own maximums\" (rows carry "
                            "their own printed maximums)")

    # Coverage runs last, over the whole (already-parsed-enough) matrix and the loaded source.
    check_coverage(m, src, problems)

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
    n_hits, counts = coverage_stats(m, p.parent)
    print(f"PASS {p}: {len(m['rows'])} rows, every cited claim found in {m['source']}; "
          f"points {total} vs stated {stated_label(m['stated_total'])} "
          f"({'reconciles' if reconciles(m, total) else 'STOP: ' + str(m.get('stop'))}); "
          f"coverage {n_hits} trigger line(s) accounted for "
          f"(rows {counts['rows']}, disqualifiers {counts['disqualifiers']}, "
          f"could-not-map {counts['could_not_map']}, reviewed {counts['reviewed']})")


if __name__ == "__main__":
    main()
