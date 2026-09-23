---
title: The contract: the evaluation matrix, field by field
created: 2026-09-23 00:36
last_updated: 2026-09-23 00:36
owner: Gina Wang
status: active
---

# The contract: the evaluation matrix, field by field

This is the output schema. A reader checks the translator against this file; `tools/check_matrix.py` checks it by machine. The matrix is one JSON file, `outputs/<rfp>.matrix.json`, rendered to `.md`, `.csv` and `.xlsx` by `tools/write_matrix.py`. Nothing exists in a rendering that is not in the JSON.

## Citations

Every fact taken from the RFP carries a citation into the numbered source text that `tools/extract.py` writes:

- `p11:14` means page 11, line 14 of `<rfp>.source.txt`.
- `p13:14-p13:17` means lines 14 through 17 of page 13, joined with single spaces.
- A range may not exceed 60 lines.

A **sourced field** is an object `{"text": "<verbatim>", "cite": "<citation>"}` (or `{"value": <number>, "cite": ...}` for points), or the exact string `"not in source"`.

A **human field** is the empty string `""`. Always.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `rfp` | sourced | The RFP's title or number, as printed |
| `source` | string | Path to the `.source.txt` the citations point into, relative to the matrix file |
| `stated_total` | sourced number, **or** `{"stages": [{"name", "value", "cite"}...], "combined": sourced?}`, or `"not in source"` | The total the RFP says it scores out of. Staged scoring lists each stage's total with its own citation; `combined` is the sentence that says the stages are added, if the RFP has one |
| `rows` | list | One object per scored item, in the RFP's order (fields below) |
| `could_not_map` | list of `{"text", "cite", "why"}` | Scoring-related sentences that did not become a row, each verbatim, cited, and explained |
| `stop` | string, optional | Present only when the matrix cannot reconcile or the RFP publishes no scoring. One sentence. Its presence is the stop state |

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

## The stop state

The matrix is complete and valid when `stop` is set, even with zero rows. The checker does not demand reconciliation when `stop` is present; it demands that `stop` be present whenever the sum and the stated total disagree. A reader opens `stop`, reads one sentence, and knows the translator refused to guess.

## Rendered forms

- **Markdown** (`.matrix.md`): header with the RFP, stated total, sum and reconcile verdict; the twelve-column table with `[citation]` after every sourced cell; a TOTAL line; the "Could not map" list; a count of rows waiting on a person.
- **CSV** (`.matrix.csv`): the same twelve columns, citations inline, a TOTAL row.
- **XLSX** (`.matrix.xlsx`): one sheet, header row frozen and filterable, Points as numbers, a live `=SUM` TOTAL row. A fresh workbook; no firm's template.

## What the checker proves (exit 0)

1. Every citation parses and exists in the source.
2. Every sourced text is a whitespace-normalized substring of its cited lines.
3. Every points value appears as a number at its citation.
4. Every human column is empty; `claude_does` is one of the three phrases; `status` is `open`.
5. The Points column reconciles to the stated total (per stage if staged), or `stop` is set.
6. Every `could_not_map` entry is cited, verbatim, and has a `why`.

Exit 1 names every failure. One failure is enough to refuse the matrix.
