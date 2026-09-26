#!/usr/bin/env python3
"""Render a matrix file (the translator's JSON output) as Markdown, CSV, XLSX and HTML.

    python3 tools/write_matrix.py outputs/some-rfp.matrix.json

Writes, beside the JSON:  some-rfp.matrix.md   .csv   .xlsx   .html

The JSON is the contract (reference/schema.md). This script adds nothing to it: every cell
in every rendering is a field from the JSON, and every sourced cell carries its citation.
Run tools/check_matrix.py first; this script also refuses a file the checker rejects.
"""
import csv
import html as htmllib
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from check_matrix import COLUMNS, check, coverage_stats, load_source, reconciles, stated_label  # noqa: E402

EMPTY = "not in source"
HUMAN_KEYS = ("input_source", "owner", "human_check", "claude_does")
HDR = ["#", "RFP section", "RFP criterion (their words)", "Points", "Input needed",
       "Input data source", "Evaluation criteria (what the scorer looks for)",
       "Proposal section that answers it", "Owner", "Claude does", "Human check", "Status"]


def cell(v):
    """A sourced field renders as its text plus [cite]; a multi-part list joins with ' · ';
    a human field renders empty."""
    if v is None or v == "":
        return ""
    if isinstance(v, list):
        return " · ".join(cell(part) for part in v)
    if isinstance(v, dict):
        t = v.get("text", v.get("value", ""))
        c = v.get("cite", "")
        return f"{t} [{c}]" if c else str(t)
    return str(v)


def row_cells(i, r):
    return [str(i)] + [cell(r.get(k, "")) for k in COLUMNS[1:]]


def stage_sums(m):
    sums = {}
    for r in m["rows"]:
        if "stage" not in r:
            continue
        p = r.get("points")
        if isinstance(p, dict) and isinstance(p.get("value"), (int, float)):
            sums[r["stage"]] = sums.get(r["stage"], 0) + p["value"]
    return sums


def stage_reconcile_line(m):
    st = m["stated_total"]
    if not (isinstance(st, dict) and "stages" in st):
        return None
    sums = stage_sums(m)
    parts = []
    for s in st["stages"]:
        got = sums.get(s["name"], 0)
        got = int(got) if got == int(got) else got
        parts.append(f"{s['name']}: {s['value']} stated, {got} summed")
    return " · ".join(parts)


def coverage_line(cov):
    n_hits, counts = cov
    return (f"Coverage: {n_hits} trigger line(s) in source, all accounted for "
            f"(rows {counts['rows']}, disqualifiers {counts['disqualifiers']}, "
            f"could-not-map {counts['could_not_map']}, reviewed {counts['reviewed']})")


def to_markdown(m, cov):
    out = []
    out.append(f"# Evaluation matrix: {cell(m['rfp'])}")
    out.append("")
    out.append(f"Source text: `{m['source']}` (page:line citations point into it).")
    st = m["stated_total"]
    if isinstance(st, dict) and "stages" in st:
        out.append("RFP's stated totals, by stage: " + "; ".join(
            f"**{s['name']} {s['value']}** [{s['cite']}]" for s in st["stages"]))
        if st.get("combined"):
            out.append(f"Combined: {cell(st['combined'])}")
        line = stage_reconcile_line(m)
        if line:
            out.append(f"Per-stage reconcile: {line}")
    else:
        out.append(f"RFP's stated total: **{cell(st)}**")
    out.append(f"Sum of the Points column: **{m['_sum']}** — reconciles: **{'yes' if m['_reconciles'] else 'NO'}**")
    out.append(coverage_line(cov))
    if m.get("stop"):
        out.append("")
        out.append(f"## STOP: {m['stop']}")
    out.append("")
    out.append("## Part 1: Scored criteria")
    out.append("")
    out.append("| " + " | ".join(HDR) + " |")
    out.append("|" + "---|" * len(HDR))
    for i, r in enumerate(m["rows"], start=1):
        out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in row_cells(i, r)) + " |")
    out.append("")
    out.append("**TOTAL** points: " + str(m["_sum"]))
    out.append("")
    out.append(f"## Part 2: Disqualifiers — what gets a proposal thrown out before scoring "
               f"({len(m['disqualifiers'])})")
    if m["disqualifiers"]:
        for d in m["disqualifiers"]:
            out.append(f"- {d['text']} [{d['cite']}] — {d['kind']}")
    else:
        out.append("- nothing: the source states no disqualifying conditions")
    out.append("")
    out.append("## Part 3: Could not map")
    if m.get("could_not_map"):
        for c in m["could_not_map"]:
            out.append(f"- {c['text']} [{c['cite']}] — {c['why']}")
    else:
        out.append("- nothing: every scoring sentence found in the source is in a row above")
    out.append("")
    out.append("## Human columns still empty")
    out.append("Input data source, Owner, Human check and Claude does are never filled by the translator. "
               f"{len(m['rows'])} row(s) need a person.")
    return "\n".join(out) + "\n"


def to_csv(m, path):
    hdr = ["#"] + COLUMNS[1:]
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(hdr)
        for i, r in enumerate(m["rows"], start=1):
            w.writerow(row_cells(i, r))
        w.writerow(["", "", "TOTAL", m["_sum"]] + [""] * 8)


def to_xlsx(m, path):
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Font, PatternFill
    except ImportError:
        print("openpyxl not installed; XLSX skipped (pip install openpyxl)")
        return
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Evaluation Matrix"
    ws["A1"] = f"Evaluation matrix — {cell(m['rfp'])} — stated total {stated_label(m['stated_total'])} — sum {m['_sum']}"
    ws["A1"].font = Font(bold=True, size=12)
    ws.merge_cells("A1:L1")
    for c, h in enumerate(HDR, start=1):
        x = ws.cell(row=2, column=c, value=h)
        x.font = Font(bold=True, color="FFFFFF")
        x.fill = PatternFill("solid", fgColor="1F3A5F")
        x.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for i, r in enumerate(m["rows"], start=1):
        vals = row_cells(i, r)
        for c, v in enumerate(vals, start=1):
            if c == 4 and isinstance(r.get("points"), dict) and isinstance(r["points"].get("value"), (int, float)):
                v = r["points"]["value"]
            x = ws.cell(row=i + 2, column=c, value=v)
            x.alignment = Alignment(wrap_text=True, vertical="top",
                                    horizontal="center" if c in (1, 4, 12) else "left")
    tr = len(m["rows"]) + 3
    ws.cell(row=tr, column=3, value="TOTAL").font = Font(bold=True)
    ws.cell(row=tr, column=4, value=f"=SUM(D3:D{tr - 1})").font = Font(bold=True)
    widths = {"A": 5, "B": 24, "C": 44, "D": 9, "E": 52, "F": 20, "G": 52, "H": 34, "I": 14, "J": 36, "K": 20, "L": 10}
    for col, w in widths.items():
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "C3"
    ws.auto_filter.ref = f"A2:L{tr - 1}"
    wb.save(path)


# ---------------------------------------------------------------------------------------
# HTML: one self-contained file, inline CSS/JS, a Part 1/2/3 layout, and a citation
# sidebar. Built with a plain-text template and token replacement (not an f-string) so the
# embedded CSS/JS braces never collide with Python's own string formatting.
# ---------------------------------------------------------------------------------------

def esc(s) -> str:
    return htmllib.escape(str(s), quote=True)


# ---- HTML rendering (design worker). Markup/CSS/JS live in tools/matrix_template.html. ----
# Every word on the page is a field from the JSON, a line of the source, or one of the fixed
# labels below / in the template. Nothing here summarises or rates the RFP.

import re  # noqa: E402

TEMPLATE_PATH = pathlib.Path(__file__).parent / "matrix_template.html"
N_COLORS = 8  # categorical swatches --c0..--c7 in the template; colour marks identity only
HUMAN_FIELDS = ("status", "input_source", "lead", "reviewer")  # always "" on hand-over
# The nine columns (owner ruling 18:25), in order, with their plain headers.
HTML_COLS = [
    ("status", "Status"),
    ("criterion", "What the RFP will score (their exact words)"),
    ("points", "Points for this item"),
    ("input_needed", "What the RFP asks you to provide"),
    ("input_source", "Where your team will get it"),
    ("evaluation_criteria", "What the scorer will look for"),
    ("answering_section", "Where it goes in your proposal"),
    ("lead", "Lead for this section"),
    ("reviewer", "Reviewer for this section"),
]
HEAD = dict(HTML_COLS)
NIS_LABEL = "The RFP doesn't say"
# Plain names for the closed vocabularies. Unknown values show as written in the JSON.
KIND_LABEL = {
    "late submittal": "Turned in late",
    "incomplete submittal or missing required item": "Missing something required",
    "missing or incorrect required form": "Missing or wrong required form",
    "prequalification, license, or registration required": "Must be prequalified, licensed, or registered",
    "page, format, or delivery rule": "Broke a formatting or delivery rule (like a page limit)",
    "non-responsive or non-responsible determination": "Doesn't meet the agency's requirements",
    "explicit disqualification": "The RFP says this specifically disqualifies a proposal",
    "owner reserves the right to reject": "The agency keeps the right to reject proposals",
    "other gate stated in the source": "Another rule in the RFP that can remove a proposal",
}
WHY_LABEL = {
    "applies to every row; no points of its own": "Applies to everything above, but isn't worth its own points",
    "scoring method that applies to every row; no points of its own":
        "Explains how scoring works overall, not a separate scored item",
    "later stage whose criteria and points are not in this document":
        "Happens later in the process; its scoring is not in this RFP document",
    "submittal item the RFP does not tie to a scored criterion":
        "The RFP asks for this, but doesn't say it's worth points",
    "sits inside a scored criterion with no points of its own":
        "Mentioned inside a scored item above, but doesn't carry its own points",
    "named criterion with no points printed": "The RFP names this as a criterion but prints no points for it",
}
CITE_RE = re.compile(r"^p(\d+):(\d+)(?:-p(\d+):(\d+))?$")


def cite_label(cite):
    """p14:15 -> 'Page 14, line 15'; p10:18-p10:20 -> 'Page 10, lines 18-20'."""
    mo = CITE_RE.match(cite or "")
    if not mo:
        return str(cite)
    page, a, b = mo.group(1), mo.group(2), mo.group(4)
    if b and b != a:
        return f"Page {page}, lines {a}–{b}"
    return f"Page {page}, line {a}"


def chip_html(cite):
    """A clickable citation. Shows 'Page N, line N'; the raw cite stays in data-cite."""
    if not cite:
        return ""
    return (f'<button type="button" class="chip" data-cite="{esc(cite)}" '
            f'title="{esc(cite)}">{esc(cite_label(cite))}</button>')


def nis_html():
    return f'<span class="nis">{esc(NIS_LABEL)}</span>'


def parts_of(v):
    if v is None or v == "" or v == EMPTY:
        return []
    return v if isinstance(v, list) else [v]


def part_text(part):
    if isinstance(part, dict):
        return part.get("text", part.get("value", "")), part.get("cite", "")
    return part, ""


def sourced_html(v):
    """Table cell / inline: each part is its text followed by its chip, one per line."""
    ps = parts_of(v)
    if not ps:
        return nis_html()
    out = []
    for part in ps:
        t, c = part_text(part)
        out.append(f'<div class="p"><span class="quote">{esc(t)}</span> {chip_html(c)}</div>')
    return "".join(out)


def block_html(label, v):
    """Card block: a label, then the parts as a list (one item per cited part)."""
    ps = parts_of(v)
    if not ps:
        return f'<div class="block single"><h5>{esc(label)}</h5><ul><li>{nis_html()}</li></ul></div>'
    items = []
    for part in ps:
        t, c = part_text(part)
        items.append(f'<li><span class="quote">{esc(t)}</span> {chip_html(c)}</li>')
    cls = "block" + (" single" if len(ps) == 1 else "")
    return f'<div class="{cls}"><h5>{esc(label)}</h5><ul>{"".join(items)}</ul></div>'


def points_value(r):
    p = r.get("points")
    if isinstance(p, dict) and isinstance(p.get("value"), (int, float)):
        return p["value"]
    return None


def num(x):
    return int(x) if isinstance(x, float) and x == int(x) else x


def pct(part, whole):
    if not whole:
        return None
    v = 100.0 * part / whole
    return f"{v:.0f}" if abs(v - round(v)) < 0.05 else f"{v:.1f}"


def groups_for_share(m):
    """Rows grouped for percent-of-sum arithmetic: by stage when staged, else one group."""
    st = m["stated_total"]
    if isinstance(st, dict) and "stages" in st:
        names = [s["name"] for s in st["stages"]]
        groups = [(n, [(i, r) for i, r in enumerate(m["rows"], 1) if r.get("stage") == n]) for n in names]
        return [(n, g) for n, g in groups if g]
    return [(None, list(enumerate(m["rows"], 1)))]


def group_sum(g):
    return sum(points_value(r) or 0 for _, r in g)


def ruler_html(name, g):
    total = group_sum(g)
    if not total:
        return ""
    step = 10 if total >= 50 else 5
    ticks, t = [], 0
    while t <= total:
        major = t % (step * 2) == 0
        cls = "tick" + (" major" if major else "") + (" first" if t == 0 else "")
        near_end = total - t < step and t != total
        label = f"<span>{num(t)}</span>" if major and not near_end else ""
        ticks.append(f'<i class="{cls}" style="left:{100.0 * t / total:.4f}%">{label}</i>')
        t += step
    if total % step == 0:
        ticks[-1] = f'<i class="tick major last" style="left:100%"><span>{num(total)}</span></i>'
    else:
        ticks.append(f'<i class="tick major last" style="left:100%"><span>{num(total)}</span></i>')
    segs, legend = [], []
    for i, r in g:
        v = points_value(r) or 0
        color = f"var(--c{(i - 1) % N_COLORS})"
        crit, _ = part_text(r.get("criterion", ""))
        share = pct(v, total)
        segs.append(f'<a class="seg" href="#row-{i}" style="--w:{v};--c:{color}" '
                    f'title="{esc(crit)}: {esc(num(v))} points">{esc(num(v))}</a>')
        legend.append(f'<li style="--c:{color}"><span class="sw"></span><a href="#row-{i}">{esc(crit)}</a>'
                      f'<span class="pts">{esc(num(v))} <span class="pct">({share}%)</span></span></li>')
    head = (f"<h2>{esc(name)}: {esc(num(total))} points in all</h2>" if name
            else f"<h2>How the {esc(num(total))} points are split</h2>")
    return (f'<div class="ruler">{head}'
            f'<div class="scale" aria-hidden="true">{"".join(ticks)}</div>'
            f'<div class="bar">{"".join(segs)}</div><ul class="legend">{"".join(legend)}</ul></div>')


def slots_html(r):
    out = []
    for key in HUMAN_FIELDS:
        val = r.get(key, "")
        out.append(f'<div class="slot"><b>{esc(HEAD[key])}</b>{esc(val)}</div>')
    return "".join(out)


def section_key(r):
    return json.dumps(r.get("section", ""), sort_keys=True)


def section_heading_html(r, tag="h3"):
    ps = parts_of(r.get("section"))
    inner = " ".join(f'{esc(part_text(p)[0])} {chip_html(part_text(p)[1])}' for p in ps) or nis_html()
    return f'<{tag} class="group-head">From the RFP section: {inner}</{tag}>'


def card_html(i, n_rows, r, share, stage_name):
    color = f"var(--c{(i - 1) % N_COLORS})"
    crit, crit_cite = part_text(r.get("criterion", ""))
    p = r.get("points")
    v = points_value(r)
    p_cite = p.get("cite", "") if isinstance(p, dict) else ""
    pct_line = ""
    if share is not None:
        of = f"of the {esc(stage_name)} points" if stage_name else "of all the points"
        pct_line = f'<span class="pct">{share}% {of}</span>'
    stage_html = f'<div class="rowmeta">Scoring stage: {esc(r["stage"])}</div>' if r.get("stage") else ""
    return (
        f'<article class="card" id="row-{i}" style="--c:{color}">'
        f'<div class="card-points"><span class="bignum">{esc(num(v)) if v is not None else ""}</span>'
        f'<span class="bignum-unit">points</span>{pct_line}{chip_html(p_cite)}</div>'
        f'<div class="card-body"><span class="rowno">Item {i} of {n_rows}</span>'
        f'<h4 class="crit">{esc(crit)} {chip_html(crit_cite)}</h4>{stage_html}'
        f'{block_html(HEAD["input_needed"], r.get("input_needed"))}'
        f'{block_html(HEAD["evaluation_criteria"], r.get("evaluation_criteria"))}'
        f'{block_html(HEAD["answering_section"], r.get("answering_section"))}'
        f'<div class="people"><div class="slots">{slots_html(r)}</div></div>'
        f'</div></article>')


def row_html(i, r):
    tds = []
    for k, _ in HTML_COLS:
        if k in HUMAN_FIELDS:
            tds.append(f'<td class="human">{esc(r.get(k, ""))}</td>')
        elif k == "criterion":
            crit, c = part_text(r.get("criterion", ""))
            tds.append(f'<td><span class="idx">{i}</span> <span class="quote">{esc(crit)}</span> {chip_html(c)}</td>')
        elif k == "points":
            v = points_value(r)
            c = r["points"].get("cite", "") if isinstance(r.get("points"), dict) else ""
            tds.append(f'<td class="pts">{esc(num(v)) if v is not None else nis_html()}<br>{chip_html(c)}</td>')
        else:
            tds.append(f"<td>{sourced_html(r.get(k))}</td>")
    return "<tr>" + "".join(tds) + "</tr>"


def grouped(rows):
    """Consecutive rows that share an RFP section, in RFP order: [(first_row, [(i, r), ...]), ...]."""
    out = []
    for i, r in enumerate(rows, start=1):
        if out and section_key(out[-1][0]) == section_key(r):
            out[-1][1].append((i, r))
        else:
            out.append((r, [(i, r)]))
    return out


def disq_groups_html(disq):
    if not disq:
        return '<p class="empty-note">The RFP states no rules that throw a proposal out before scoring.</p>'
    order, groups = [], {}
    for d in disq:
        if d["kind"] not in groups:
            order.append(d["kind"])
            groups[d["kind"]] = []
        groups[d["kind"]].append(d)
    out = []
    for k in order:
        items = "".join(f'<li><span class="quote">{esc(d["text"])}</span> {chip_html(d["cite"])}</li>'
                        for d in groups[k])
        out.append(f'<div class="gate-group"><h3>{esc(KIND_LABEL.get(k, k))}<span class="n">{len(groups[k])}</span></h3>'
                   f'<ol>{items}</ol></div>')
    return "".join(out)


def pdf_name(m, src_path):
    """The PDF the source text was extracted from, when it sits beside it; else the text file."""
    p = pathlib.Path(src_path)
    stem = p.name[:-len(".source.txt")] if p.name.endswith(".source.txt") else p.stem
    pdf = p.with_name(stem + ".pdf")
    return pdf.name if pdf.exists() else p.name


def to_html(m, cov, src, src_path=None):
    n_hits, counts = cov
    st = m["stated_total"]
    total_s = esc(num(m["_sum"]))
    staged = isinstance(st, dict) and "stages" in st
    stage_line = ""
    if staged:
        stated_html = " ".join(
            f'<span class="stagefact">{esc(s["name"])} {esc(s["value"])}</span>{chip_html(s["cite"])}'
            for s in st["stages"])
        sums = stage_sums(m)
        stage_line = "<p>" + "; ".join(
            f'{esc(s["name"])}: the RFP says {esc(s["value"])} points, the items add up to '
            f'{esc(num(sums.get(s["name"], 0)))}' for s in st["stages"]) + ".</p>"
        if st.get("combined"):
            stage_line += f"<p>How the stages combine: {sourced_html(st['combined'])}</p>"
        stated_words = " + ".join(f'{esc(s["value"])} ({esc(s["name"])})' for s in st["stages"])
    elif isinstance(st, dict):
        t, c = part_text(st)
        stated_html = f"{esc(t)} {chip_html(c)}"
        stated_words = esc(t)
    else:
        stated_html = nis_html()
        stated_words = None

    if stated_words is None:
        total_sentence = f"The RFP doesn't state a total. The items below add up to <strong>{total_s}</strong>."
    elif m["_reconciles"]:
        total_sentence = (f"The RFP says proposals are scored out of <strong>{stated_words}</strong> points, "
                          f"and the items below add up to <strong>{total_s}</strong>.")
    else:
        total_sentence = (f"The RFP says proposals are scored out of <strong>{stated_words}</strong> points, but the "
                          f"items below only add up to <strong>{total_s}</strong>. Something doesn't add up here: "
                          f"check this before you rely on this page.")
    if staged:
        total_sentence += " This RFP scores in stages. Each stage's own total is shown next to that stage's items below."

    shares, stage_of, rulers = {}, {}, []
    for name, g in groups_for_share(m):
        total = group_sum(g)
        for i, r in g:
            v = points_value(r)
            shares[i] = pct(v, total) if v is not None else None
            stage_of[i] = name
        rulers.append(ruler_html(name, g))
    rulers_html = "".join(rulers)
    if rulers_html:
        rulers_html += '<p class="arith">Bar sizes and percentages are simple math on the points the RFP prints.</p>'

    rows = m["rows"]
    n_rows = len(rows)
    cards, body_rows = [], []
    for first, g in grouped(rows):
        cards.append('<div class="group">' + section_heading_html(first) +
                     "".join(card_html(i, n_rows, r, shares.get(i), stage_of.get(i)) for i, r in g) + "</div>")
        body_rows.append(f'<tr class="grouprow"><td colspan="{len(HTML_COLS)}">'
                         f'{section_heading_html(first, "span")}</td></tr>')
        body_rows.extend(row_html(i, r) for i, r in g)
    cards_html = "".join(cards) or '<p class="empty-note">No scored items: see the note at the top of the page.</p>'
    hdr_cells = "".join(f"<th>{esc(h)}</th>" for _, h in HTML_COLS)

    disq_flat = "".join(
        f'<li><span class="quote">{esc(d["text"])}</span> {chip_html(d["cite"])} '
        f'<span class="kind">{esc(KIND_LABEL.get(d["kind"], d["kind"]))}</span></li>' for d in m["disqualifiers"]
    ) or '<li class="empty-note">The RFP states no rules that throw a proposal out before scoring.</li>'

    if m["could_not_map"]:
        cnm = '<ul class="cnm">' + "".join(
            f'<li>{esc(c["text"])} {chip_html(c["cite"])}'
            f'<span class="why">{esc(WHY_LABEL.get(c["why"], c["why"]))}</span></li>'
            for c in m["could_not_map"]) + "</ul>"
    else:
        cnm = '<p class="empty-note">Nothing: every line about scoring is in one of the two parts above.</p>'

    pages = {}
    for (page, line) in src["order"]:
        pages.setdefault(page, []).append([line, src["lines"][(page, line)]])
    source_json = json.dumps({str(k): v for k, v in pages.items()}).replace("</", "<\\/")

    rfp_parts = parts_of(m["rfp"])
    title = part_text(rfp_parts[0])[0] if rfp_parts else str(m["rfp"])
    title_html = " ".join(f'{esc(part_text(p)[0])} {chip_html(part_text(p)[1])}' for p in rfp_parts) or esc(title)

    stop_line = (f'<p class="stop">This checklist stopped early. The reason: {esc(m["stop"])}.</p>'
                 if m.get("stop") else "")
    coverage = (f"We checked {n_hits} lines in the RFP that talk about scoring or rejection. Every one of them is "
                f"accounted for: {counts['rows']} in How you'll be scored, {counts['disqualifiers']} in What gets you "
                f"thrown out, {counts['could_not_map']} in Things we found but couldn't place, and "
                f"{counts['reviewed']} read and set aside, each with its reason recorded in the matrix file.")
    empty_boxes = sum(1 for r in rows for k in HUMAN_FIELDS if not r.get(k))

    fills = {
        "TITLE": esc(title),
        "TITLE_HTML": title_html,
        "PDF": esc(pdf_name(m, src_path or m["source"])),
        "SOURCE": esc(m["source"]),
        "STATED_HTML": stated_html,
        "TOTAL_SENTENCE": total_sentence,
        "STAGE_LINE": stage_line,
        "SUM": total_s,
        "RECONCILE_CLASS": "na" if stated_words is None else "ok" if m["_reconciles"] else "bad",
        "RECONCILE_TEXT": ("No total to compare" if stated_words is None
                           else "Yes" if m["_reconciles"] else "No"),
        "COVERAGE_LINE": esc(coverage),
        "STOP_LINE": stop_line,
        "RULERS": rulers_html,
        "CARDS": cards_html,
        "HDR_CELLS": hdr_cells,
        "BODY_ROWS": "".join(body_rows),
        "NCOLS_REST": str(len(HTML_COLS) - 3),
        "DISQ_COUNT": str(len(m["disqualifiers"])),
        "DISQ_GROUPS": disq_groups_html(m["disqualifiers"]),
        "DISQ_FLAT": disq_flat,
        "CNM_COUNT": str(len(m["could_not_map"])),
        "CNM": cnm,
        "ROW_COUNT": str(n_rows),
        "EMPTY_BOXES": str(empty_boxes),
        "SOURCE_JSON": source_json,
    }
    # One pass, so text from the JSON can never be re-read as a placeholder.
    return re.sub(r"@@([A-Z_]+)@@", lambda mo: fills[mo.group(1)], TEMPLATE_PATH.read_text())


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: write_matrix.py <matrix.json>")
    p = pathlib.Path(sys.argv[1])
    m = json.loads(p.read_text())
    problems, total = check(m, p.parent)
    if problems:
        sys.exit("refusing to render; check_matrix.py reports:\n  " + "\n  ".join(problems))
    m["_sum"] = total
    m["_reconciles"] = reconciles(m, total)
    cov = coverage_stats(m, p.parent)
    src_path = pathlib.Path(m["source"])
    if not src_path.is_absolute():
        src_path = p.parent / src_path
    src = load_source(src_path)
    base = str(p)[:-len(".json")] if p.name.endswith(".json") else str(p)
    pathlib.Path(base + ".md").write_text(to_markdown(m, cov))
    to_csv(m, base + ".csv")
    to_xlsx(m, base + ".xlsx")
    pathlib.Path(base + ".html").write_text(to_html(m, cov, src, src_path))
    print(f"wrote {base}.md .csv .xlsx .html — {len(m['rows'])} rows, {total} points, "
          f"reconciles={'yes' if m['_reconciles'] else 'NO'}, "
          f"{len(m['disqualifiers'])} disqualifier(s)")


if __name__ == "__main__":
    main()
