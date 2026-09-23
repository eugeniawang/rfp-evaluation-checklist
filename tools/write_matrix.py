#!/usr/bin/env python3
"""Render a matrix file (the translator's JSON output) as Markdown, CSV and XLSX.

    python3 tools/write_matrix.py outputs/some-rfp.matrix.json

Writes, beside the JSON:  some-rfp.matrix.md   some-rfp.matrix.csv   some-rfp.matrix.xlsx

The JSON is the contract (reference/schema.md). This script adds nothing to it: every cell
in every rendering is a field from the JSON, and every sourced cell carries its citation.
Run tools/check_matrix.py first; this script also refuses a file the checker rejects.
"""
import csv
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from check_matrix import COLUMNS, check, reconciles, stated_label  # noqa: E402

EMPTY = "not in source"


def cell(v):
    """A sourced field renders as its text plus [cite]; a human field renders empty."""
    if v is None or v == "":
        return ""
    if isinstance(v, dict):
        t = v.get("text", v.get("value", ""))
        c = v.get("cite", "")
        return f"{t} [{c}]" if c else str(t)
    return str(v)


def row_cells(i, r):
    return [str(i)] + [cell(r.get(k, "")) for k in COLUMNS[1:]]


def to_markdown(m):
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
    else:
        out.append(f"RFP's stated total: **{cell(st)}**")
    out.append(f"Sum of the Points column: **{m['_sum']}** — reconciles: **{'yes' if m['_reconciles'] else 'NO'}**")
    if m.get("stop"):
        out.append("")
        out.append(f"## STOP: {m['stop']}")
    out.append("")
    hdr = ["#", "RFP section", "RFP criterion (their words)", "Points", "Input needed",
           "Input data source", "Evaluation criteria (what the scorer looks for)",
           "Proposal section that answers it", "Owner", "Claude does", "Human check", "Status"]
    out.append("| " + " | ".join(hdr) + " |")
    out.append("|" + "---|" * len(hdr))
    for i, r in enumerate(m["rows"], start=1):
        out.append("| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in row_cells(i, r)) + " |")
    out.append("")
    out.append("**TOTAL** points: " + str(m["_sum"]))
    out.append("")
    out.append("## Could not map")
    if m.get("could_not_map"):
        for c in m["could_not_map"]:
            out.append(f"- {c['text']} [{c['cite']}] — {c['why']}")
    else:
        out.append("- nothing: every scoring sentence found in the source is in a row above")
    out.append("")
    out.append("## Human columns still empty")
    out.append("Input data source, Owner and Human check are never filled by the translator. "
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
    hdr = ["#", "RFP section", "RFP criterion (their words)", "Points", "Input needed",
           "Input data source", "Evaluation criteria (what the scorer looks for)",
           "Proposal section that answers it", "Owner", "Claude does", "Human check", "Status"]
    for c, h in enumerate(hdr, start=1):
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
    base = str(p)[:-len(".json")] if p.name.endswith(".json") else str(p)
    pathlib.Path(base + ".md").write_text(to_markdown(m))
    to_csv(m, base + ".csv")
    to_xlsx(m, base + ".xlsx")
    print(f"wrote {base}.md .csv .xlsx — {len(m['rows'])} rows, {total} points, "
          f"reconciles={'yes' if m['_reconciles'] else 'NO'}")


if __name__ == "__main__":
    main()
