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


def chip_html(cite):
    if not cite:
        return ""
    return f'<button type="button" class="chip" data-cite="{esc(cite)}">[{esc(cite)}]</button>'


def sourced_html(v):
    if v is None or v == "" or v == EMPTY:
        return '<span class="empty">not in source</span>'
    parts = v if isinstance(v, list) else [v]
    chunks = []
    for part in parts:
        if isinstance(part, dict):
            t = part.get("text", part.get("value", ""))
            c = part.get("cite", "")
            chunks.append(f'<div class="part"><span class="ftext">{esc(t)}</span> {chip_html(c)}</div>')
        else:
            chunks.append(f'<div class="part">{esc(part)}</div>')
    return "".join(chunks)


def row_html(i, r):
    tds = [f'<td class="num">{i}</td>']
    for k in COLUMNS[1:]:
        if k in HUMAN_KEYS:
            tds.append('<td class="human"></td>')
        elif k == "status":
            tds.append(f"<td>{esc(r.get(k, ''))}</td>")
        else:
            tds.append(f"<td>{sourced_html(r.get(k))}</td>")
    return "<tr>" + "".join(tds) + "</tr>"


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Evaluation matrix — @@TITLE@@</title>
<style>
  :root {
    --bg: #ffffff; --fg: #1a1a1a; --muted: #5a5a5a; --border: #d8d8d8;
    --head-bg: #1f3a5f; --head-fg: #ffffff; --chip-bg: #eef3fa; --chip-fg: #1f3a5f;
    --hl-bg: #fff2a8; --ok: #1a7f37; --bad: #b42318; --sidebar-bg: #f7f7f8;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14161a; --fg: #e8e8e8; --muted: #a0a0a0; --border: #34373d;
      --head-bg: #2a4266; --head-fg: #ffffff; --chip-bg: #223047; --chip-fg: #cfe0ff;
      --hl-bg: #4a3f0d; --ok: #4fbf67; --bad: #e5695b; --sidebar-bg: #1c1e23;
    }
  }
  * { box-sizing: border-box; }
  body { background: var(--bg); color: var(--fg); font: 15px/1.5 -apple-system, BlinkMacSystemFont,
         "Segoe UI", Helvetica, Arial, sans-serif; margin: 0; padding: 24px; }
  header { margin-bottom: 24px; }
  h1 { font-size: 1.3rem; margin: 0 0 8px; }
  h2 { font-size: 1.05rem; margin: 28px 0 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
  h3 { font-size: 0.95rem; margin: 0 0 10px; }
  p { margin: 4px 0; color: var(--muted); }
  code { background: var(--chip-bg); padding: 1px 5px; border-radius: 4px; color: var(--fg); }
  .ok { color: var(--ok); }
  .bad { color: var(--bad); }
  .stop { color: var(--bad); font-weight: 600; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid var(--border); padding: 6px 8px; vertical-align: top; text-align: left; }
  th { background: var(--head-bg); color: var(--head-fg); position: sticky; top: 0; }
  td.num { text-align: center; width: 2.5em; }
  td.human { background: repeating-linear-gradient(45deg, transparent, transparent 6px,
             var(--chip-bg) 6px, var(--chip-bg) 7px); }
  .part + .part { margin-top: 6px; }
  .empty { color: var(--muted); font-style: italic; }
  .chip { background: var(--chip-bg); color: var(--chip-fg); border: 1px solid var(--border);
          border-radius: 999px; padding: 1px 8px; font: 12px/1.6 monospace; cursor: pointer; }
  .chip:hover { filter: brightness(1.08); }
  ul.disq, ul.cnm { padding-left: 20px; }
  ul.disq li, ul.cnm li { margin: 6px 0; }
  .total { font-weight: 600; }
  .footer { margin-top: 18px; font-style: italic; }
  #scrim { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: none; z-index: 40; }
  #scrim.open { display: block; }
  #sidebar { position: fixed; top: 0; right: 0; height: 100%; width: min(480px, 92vw);
             background: var(--sidebar-bg); border-left: 1px solid var(--border);
             transform: translateX(100%); transition: transform .18s ease-out;
             z-index: 50; overflow-y: auto; padding: 18px; }
  #sidebar.open { transform: translateX(0); }
  #closeSidebar { position: sticky; top: 0; float: right; background: none; border: none;
                  font-size: 22px; line-height: 1; cursor: pointer; color: var(--fg); }
  .srcline { font: 12px/1.6 ui-monospace, SFMono-Regular, monospace; white-space: pre-wrap;
             padding: 1px 4px; border-radius: 3px; }
  .srcline.hl { background: var(--hl-bg); }
  @media (max-width: 700px) {
    #sidebar { top: auto; bottom: 0; right: 0; left: 0; width: 100%; height: min(70vh, 520px);
               border-left: none; border-top: 1px solid var(--border);
               transform: translateY(100%); border-radius: 12px 12px 0 0; }
    #sidebar.open { transform: translateY(0); }
    table { font-size: 12px; }
  }
</style>
</head>
<body>
<header>
  <h1>Evaluation matrix: @@TITLE@@</h1>
  <p>Source: <code>@@SOURCE@@</code></p>
  <p>Stated total: @@STATED_LINE@@</p>
  @@STAGE_LINE@@
  <p>Sum of Points: <strong>@@SUM@@</strong> — reconciles: <strong class="@@RECONCILE_CLASS@@">@@RECONCILE_TEXT@@</strong></p>
  <p>@@COVERAGE_LINE@@</p>
  @@STOP_LINE@@
</header>
<main>
  <h2>Part 1: Scored criteria</h2>
  <table>
    <thead><tr>@@HDR_CELLS@@</tr></thead>
    <tbody>@@BODY_ROWS@@</tbody>
  </table>
  <p class="total">TOTAL points: @@SUM@@</p>

  <h2>Part 2: Disqualifiers — what gets a proposal thrown out before scoring (@@DISQ_COUNT@@)</h2>
  <ul class="disq">@@DISQ_ROWS@@</ul>

  <h2>Part 3: Could not map</h2>
  <ul class="cnm">@@CNM_ROWS@@</ul>

  <p class="footer">@@ROW_COUNT@@ row(s) waiting on a person (Input data source, Owner, Human check, Claude does).</p>
</main>

<div id="scrim"></div>
<aside id="sidebar" aria-hidden="true">
  <button id="closeSidebar" type="button" aria-label="Close">&times;</button>
  <div id="sidebarContent"></div>
</aside>

<script>
const SOURCE = @@SOURCE_JSON@@;
function escapeHtml(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
function openSidebar(cite) {
  const m = /^p(\\d+):(\\d+)(?:-p(\\d+):(\\d+))?$/.exec(cite);
  if (!m) return;
  const page = m[1];
  const startLine = parseInt(m[2], 10);
  const endLine = m[4] ? parseInt(m[4], 10) : startLine;
  const lines = SOURCE[page] || [];
  const rows = lines.map(function (pair) {
    const ln = pair[0], text = pair[1];
    const hl = (ln >= startLine && ln <= endLine) ? ' hl' : '';
    return '<div class="srcline' + hl + '" id="ln-' + ln + '">p' + page + ':' + ln + '| ' + escapeHtml(text) + '</div>';
  }).join('');
  document.getElementById('sidebarContent').innerHTML = '<h3>Page ' + page + '</h3>' + rows;
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.add('open');
  sidebar.setAttribute('aria-hidden', 'false');
  document.getElementById('scrim').classList.add('open');
  const target = document.getElementById('ln-' + startLine);
  if (target) target.scrollIntoView({ block: 'center' });
}
function closeSidebar() {
  const sidebar = document.getElementById('sidebar');
  sidebar.classList.remove('open');
  sidebar.setAttribute('aria-hidden', 'true');
  document.getElementById('scrim').classList.remove('open');
}
document.addEventListener('click', function (e) {
  const chip = e.target.closest('.chip');
  if (chip) { openSidebar(chip.dataset.cite); return; }
  if (e.target.id === 'closeSidebar' || e.target.id === 'scrim') closeSidebar();
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') closeSidebar();
});
</script>
</body>
</html>
"""


def to_html(m, cov, src):
    st = m["stated_total"]
    if isinstance(st, dict) and "stages" in st:
        stated_line = "; ".join(f"{esc(s['name'])} {esc(s['value'])} {chip_html(s['cite'])}" for s in st["stages"])
        if st.get("combined"):
            stated_line += f" — combined: {sourced_html(st['combined'])}"
        line = stage_reconcile_line(m)
        stage_line_html = f"<p>Per-stage reconcile: {esc(line)}</p>" if line else ""
    else:
        stated_line = sourced_html(st)
        stage_line_html = ""

    body_rows = "".join(row_html(i, r) for i, r in enumerate(m["rows"], start=1))
    hdr_cells = "".join(f"<th>{esc(h)}</th>" for h in HDR)

    disq_rows = "".join(
        f"<li>{esc(d['text'])} {chip_html(d['cite'])} — <em>{esc(d['kind'])}</em></li>" for d in m["disqualifiers"]
    ) or "<li class='empty'>nothing: the source states no disqualifying conditions</li>"

    cnm_rows = "".join(
        f"<li>{esc(c['text'])} {chip_html(c['cite'])} — <em>{esc(c['why'])}</em></li>" for c in m["could_not_map"]
    ) or "<li class='empty'>nothing: every scoring sentence found in the source is in a row above</li>"

    pages = {}
    for (page, line) in src["order"]:
        pages.setdefault(page, []).append([line, src["lines"][(page, line)]])
    source_json = json.dumps({str(k): v for k, v in pages.items()}).replace("</", "<\\/")

    title = m["rfp"]["text"] if isinstance(m["rfp"], dict) else (
        m["rfp"][0]["text"] if isinstance(m["rfp"], list) else str(m["rfp"]))

    stop_line = f'<p class="stop">STOP: {esc(m["stop"])}</p>' if m.get("stop") else ""

    out = HTML_TEMPLATE
    out = out.replace("@@TITLE@@", esc(title))
    out = out.replace("@@SOURCE@@", esc(m["source"]))
    out = out.replace("@@STATED_LINE@@", stated_line)
    out = out.replace("@@STAGE_LINE@@", stage_line_html)
    out = out.replace("@@SUM@@", esc(m["_sum"]))
    out = out.replace("@@RECONCILE_CLASS@@", "ok" if m["_reconciles"] else "bad")
    out = out.replace("@@RECONCILE_TEXT@@", "yes" if m["_reconciles"] else "NO")
    out = out.replace("@@COVERAGE_LINE@@", esc(coverage_line(cov)))
    out = out.replace("@@STOP_LINE@@", stop_line)
    out = out.replace("@@HDR_CELLS@@", hdr_cells)
    out = out.replace("@@BODY_ROWS@@", body_rows)
    out = out.replace("@@DISQ_COUNT@@", str(len(m["disqualifiers"])))
    out = out.replace("@@DISQ_ROWS@@", disq_rows)
    out = out.replace("@@CNM_ROWS@@", cnm_rows)
    out = out.replace("@@ROW_COUNT@@", str(len(m["rows"])))
    out = out.replace("@@SOURCE_JSON@@", source_json)
    return out


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
    pathlib.Path(base + ".html").write_text(to_html(m, cov, src))
    print(f"wrote {base}.md .csv .xlsx .html — {len(m['rows'])} rows, {total} points, "
          f"reconciles={'yes' if m['_reconciles'] else 'NO'}, "
          f"{len(m['disqualifiers'])} disqualifier(s)")


if __name__ == "__main__":
    main()
