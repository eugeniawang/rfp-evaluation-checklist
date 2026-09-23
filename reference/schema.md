---
title: The contract: the evaluation matrix, field by field
created: 2026-09-23 00:36
last_updated: 2026-09-23 01:05
owner: Gina Wang
status: active
---

# The contract: the evaluation matrix, field by field

This is the output schema. A reader checks the translator against this file; `tools/check_matrix.py` checks it by machine. The matrix is one JSON file, `outputs/<rfp>.matrix.json`, rendered to `.md`, `.csv` and `.xlsx` by `tools/write_matrix.py`. Nothing exists in a rendering that is not in the JSON.

## Citations

Every fact taken from the RFP carries a citation into the numbered source text that `tools/extract.py` writes:

- `p11:14` means page 11, line 14 of `<rfp>.source.txt`.
- `p13:14-p13:17` means lines 14 through 17 of page 13, joined with single spaces.
- A range stays on one page and covers at most 12 lines. A points citation covers at most 2.
- The quoted text must occur in the cited lines as whole words: starting and ending at a space or at the edge, whitespace collapsed, nothing else changed.

A **sourced field** is an object `{"text": "<verbatim>", "cite": "<citation>"}` (or `{"value": <number>, "cite": ...}` for points), or the exact string `"not in source"`.

A **human field** is the empty string `""`. Always.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `rfp` | sourced | The RFP's title or number, as printed |
| `source` | string | Path to the `.source.txt` the citations point into, relative to the matrix file |
| `stated_total` | sourced number, **or** `{"stages": [{"name", "value", "cite"}...], "combined": sourced?}`, or `"not in source"` | The total the RFP says it scores out of. Staged scoring lists each stage's total with its own citation; `combined` is the sentence that says the stages are added, if the RFP has one |
| `rows` | list | One object per scored item, in the RFP's order (fields below) |
| `could_not_map` | list of `{"text", "cite", "why"}` | Scoring sentences that did not become a row, each verbatim, cited, with `why` from the six fixed reasons below. The list is required; empty is fine |
| `stop` | enum, optional | `points do not reconcile to the stated total` or `no scoring table published`. Its presence is the stop state |

No other key may exist at the top level or in a row. The checker rejects unknown keys, so there is nowhere in the file for free text that is not a cited quotation or a fixed phrase.

## The twelve columns (each row)

| # | Key | Type | What it holds |
|---|---|---|---|
| 1 | `#` | rendered only | Row number, assigned at render time |
| 2 | `section` | sourced | The RFP's own heading for the section that holds the scoring table |
| 3 | `criterion` | sourced | The criterion in the RFP's exact words |
| 4 | `points` | sourced number | The points printed beside the criterion. Must appear as a number on the cited line(s) |
| 5 | `input_needed` | sourced | What the RFP tells the proposer to supply for this criterion |
| 6 | `input_source` | human | Where the firm keeps that input. Empty |
| 7 | `evaluation_criteria` | sourced | What the RFP says the scorer looks for |
| 8 | `answering_section` | sourced | The submittal item, section, or form the RFP says carries the response |
| 9 | `owner` | human | The person who supplies or confirms the input. Empty |
| 10 | `claude_does` | enum | One of the three fixed phrases below |
| 11 | `human_check` | human | What passing looks like and who says so. Empty |
| 12 | `status` | enum | Always `open` on hand-over. Downstream: `input received` → `drafted` → `checked` |

Rows in a staged RFP also carry `stage`, whose value must be one of the `stated_total.stages` names.

### `claude_does`, the three fixed phrases

The column names the kind of downstream job, not a fact about the RFP, so it is a closed vocabulary rather than a citation:

- `draft: write the response to this criterion from the inputs in Input needed, citing each one`
- `assemble: fill the RFP's own form from figures a person supplies; no prose`
- `prepare: build the interview or presentation material from the submitted proposal; scored live, not in writing`

Any other string fails the check.

### `could_not_map[].why`, the six fixed reasons

- `applies to every row; no points of its own`
- `scoring method that applies to every row; no points of its own`
- `pass/fail gate that removes a proposal from scoring; not a scored criterion`
- `later stage whose criteria and points are not in this document`
- `submittal item the RFP does not tie to a scored criterion`
- `sits inside a scored criterion with no points of its own`

## Row order

Rows follow the RFP's order: each row's `criterion` citation must come later in the source than the previous row's. The checker enforces it.

## The stop state

The matrix is complete and valid when `stop` is set, even with zero rows. The checker does not demand reconciliation when `stop` is `points do not reconcile to the stated total`; it demands that phrase whenever the sum and the stated total disagree, and `no scoring table published` whenever `stated_total` is `not in source`. The renderer prints the stated total and the sum beside the stop, so the reader sees the gap without anyone typing a number.

## Rendered forms

- **Markdown** (`.matrix.md`): header with the RFP, stated total, sum and reconcile verdict; the twelve-column table with `[citation]` after every sourced cell; a TOTAL line; the "Could not map" list; a count of rows waiting on a person.
- **CSV** (`.matrix.csv`): the same twelve columns, citations inline, a TOTAL row.
- **XLSX** (`.matrix.xlsx`): one sheet, header row frozen and filterable, Points as numbers, a live `=SUM` TOTAL row. A fresh workbook; no firm's template.

## What the checker proves (exit 0)

1. Every citation parses, exists in the source, stays on one page, and covers at most 12 lines (2 for points).
2. Every sourced text is a whole-word, whitespace-normalized run of its cited lines.
3. Every points value appears as a number on its cited line(s).
4. Every key is a contract key. Every human column is present and empty; `claude_does` is one of the three phrases; `status` is `open`; `stop` and every `why` are fixed phrases.
5. Rows are in the RFP's order.
6. The Points column reconciles to the stated total (per stage if staged), or `stop` says which stop state applies.
7. Every `could_not_map` entry is cited and verbatim.

Exit 1 names every failure. One failure is enough to refuse the matrix.
