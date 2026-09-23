#!/usr/bin/env python3
"""Turn an RFP (PDF or plain text) into the numbered source text the translator reads.

    python3 tools/extract.py fixtures/some-rfp.pdf            # writes fixtures/some-rfp.source.txt
    python3 tools/extract.py fixtures/some-rfp.txt -o out.txt

Every line of the output is prefixed  p<page>:<line>|  so a matrix row can cite the exact
place a criterion came from, and check_matrix.py can open that place and confirm the words.

PDFs are read with poppler's `pdftotext -layout` (the only non-stdlib dependency; on a Mac,
`brew install poppler`). A PDF with no text layer (a scan) produces an empty file, and the
script says so and exits non-zero: a translator cannot cite what it cannot read.
"""
import argparse
import pathlib
import shutil
import subprocess
import sys


def pdf_pages(path: pathlib.Path) -> list[str]:
    if not shutil.which("pdftotext"):
        sys.exit("pdftotext not found; install poppler (brew install poppler)")
    out = subprocess.run(["pdftotext", "-layout", str(path), "-"],
                         capture_output=True, text=True, check=True).stdout
    return out.split("\f")


def number(pages: list[str]) -> list[str]:
    lines = []
    for p, page in enumerate(pages, start=1):
        page_lines = page.split("\n")
        if page_lines and page_lines[-1] == "":
            page_lines.pop()  # the trailing newline is not a line
        for n, line in enumerate(page_lines, start=1):
            lines.append(f"p{p}:{n}|{line.rstrip()}")
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("-o", "--out")
    a = ap.parse_args()
    src = pathlib.Path(a.source)
    if src.suffix.lower() == ".pdf":
        pages = pdf_pages(src)
    else:
        pages = [src.read_text(errors="replace")]
    lines = number(pages)
    if not any(l.split("|", 1)[1].strip() for l in lines):
        sys.exit(f"{src}: no text found (scanned PDF?). Nothing to cite, nothing written.")
    out = pathlib.Path(a.out) if a.out else src.with_suffix(".source.txt")
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}: {len(pages)} page(s), {len(lines)} lines")


if __name__ == "__main__":
    main()
