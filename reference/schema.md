---
title: The contract: the evaluation matrix, field by field
created: 2026-09-23 00:36
last_updated: 2026-09-25 18:31
owner: Gina Wang
status: active
---

# The contract: the evaluation matrix, field by field

This is the output schema. A reader checks the translator against this file; `tools/check_matrix.py` checks it by machine. The matrix is one JSON file, `outputs/<rfp>.matrix.json`, rendered to `.md`, `.csv`, `.xlsx` and `.html` by `tools/write_matrix.py`. Nothing exists in a rendering that is not in the JSON.

## Citations

Every fact taken from the RFP carries a citation into the numbered source text that `tools/extract.py` writes:

- `p11:14` means page 11, line 14 of `<rfp>.source.txt`.
- `p13:14-p13:17` means lines 14 through 17 of page 13, joined with single spaces.
- A range stays on one page and covers at most 12 lines. A points citation covers at most 2.
- The quoted text must occur in the cited lines as whole words: starting and ending at a space or at the edge, whitespace collapsed, nothing else changed.

A **sourced field** is an object `{"text": "<verbatim>", "cite": "<citation>"}` (or `{"value": <number>, "cite": ...}` for points), the exact string `"not in source"`, **or a JSON list of 1 to 10 such objects** when the ask is spread across several passages of the source (a bullet list longer than 12 lines, or one that crosses a page). Each element of the list is checked independently against the same rules. `criterion` and `points` are always a single object — never a list.

A **human field** is the empty string `""`. Always.

## Top level

| Key | Type | Meaning |
|---|---|---|
| `rfp` | sourced | The RFP's title or number, as printed |
| `source` | string | Path to the `.source.txt` the citations point into, relative to the matrix file |
| `stated_total` | sourced number, **or** `{"stages": [{"name", "value", "cite"}...], "combined": sourced?}`, or `"not in source"` | The total the RFP says it scores out of. Staged scoring lists each stage's total with its own citation; `combined` is the sentence that says the stages are added, if the RFP has one |
| `rows` | list | One object per scored item, in the RFP's order (fields below) |
| `disqualifiers` | list of `{"text", "cite", "kind"}` | Part 2. Every sentence that removes, rejects, disqualifies, or refuses to evaluate/score/consider a proposal or proposer, or makes something mandatory on pain of rejection — cited, verbatim, one object per sentence (a sentence that crosses a page becomes two entries with the same `kind`). `kind` is from the nine fixed phrases below. The list is required; empty is fine |
| `could_not_map` | list of `{"text", "cite", "why"}` | Scoring sentences that did not become a row, each verbatim, cited, with `why` from the six fixed reasons below. The list is required; empty is fine |
| `reviewed` | list of `{"cite", "why"}` | The coverage check's bookkeeping (see below): source lines that matched a scoring/gate trigger, were read, and are not scoring or gating content. `why` is from the four fixed reasons below. The list is required; empty is fine |
| `stop` | enum, optional | One of the three fixed stop phrases below. Its presence is the stop state |

No other key may exist at the top level or in a row. The checker rejects unknown keys, so there is nowhere in the file for free text that is not a cited quotation or a fixed phrase.

## The nine columns (each row)

The columns, always in this order, same for every RFP:

| # | Key | Header | Type | What it holds |
|---|---|---|---|---|
| 1 | `status` | Status | human | Always `""` on hand-over. The firm's workflow fills it |
| 2 | `criterion` | What the RFP will score (their exact words) | sourced | The criterion in the RFP's exact words. The row's number (1, 2, 3…) is a render-time index folded into this cell — it is not its own column and not a JSON key |
| 3 | `points` | Points for this item | sourced number | The points printed beside the criterion. Must appear as a number on the cited line(s) |
| 4 | `input_needed` | What the RFP asks you to provide | sourced | The **whole** ask: every bullet and sub-item the RFP lists under this criterion or its submittal item, not just the intro sentence. Multi-part when it runs past 12 lines or crosses a page |
| 5 | `input_source` | Where your team will get it | human | Always `""` |
| 6 | `evaluation_criteria` | What the scorer will look for | sourced | The criterion's own descriptive sentence when the RFP has one; the general evaluation sentence only when it has none |
| 7 | `answering_section` | Where it goes in your proposal | sourced | The submittal item, section, or form — filled only when the RFP itself ties that section/item/form to *this* criterion. See the guard below |
| 8 | `lead` | Lead for this section | human | Always `""` |
| 9 | `reviewer` | Reviewer for this section | human | Always `""` |

`section` is a **tenth, non-column field**: still sourced and cited on every row, but it does not get its own column. A rendering groups rows by it and shows it once, as a heading above the rows that share it ("From the RFP section: `<heading>` [citation]"), because repeating it on every row would say the same thing nine times.

Rows in a staged RFP also carry `stage`, whose value must be one of the `stated_total.stages` names.

There is no `claude_does` column. Earlier drafts of this contract had one with a fixed next-step phrase; a fixed phrase is a next-step nobody actually said, so it was removed. What happens to a row next is the firm's workflow, not this file's business.

### The `answering_section` guard

A part's text may never begin with an imperative verb — Provide, Describe, Identify, Define, Summarize, Include, List, Explain, Submit, Discuss, Demonstrate, Outline, Detail, Present, Show, Indicate. Those are instructions to the proposer, not the name of a section, item, or form; putting one here asserts something the RFP never said. If the RFP names the criterion and its points but never ties a specific submittal item, section, or form to *that* criterion, the value is `not in source` — even if the RFP has an "Evaluation Committee" or "Selection Criteria" section it never used to answer.

### `kind`, the nine fixed phrases (`disqualifiers`)

- `late submittal`
- `incomplete submittal or missing required item`
- `missing or incorrect required form`
- `prequalification, license, or registration required`
- `page, format, or delivery rule`
- `non-responsive or non-responsible determination`
- `explicit disqualification`
- `owner reserves the right to reject`
- `other gate stated in the source`

### `could_not_map[].why`, the six fixed reasons

- `applies to every row; no points of its own`
- `scoring method that applies to every row; no points of its own`
- `later stage whose criteria and points are not in this document`
- `submittal item the RFP does not tie to a scored criterion`
- `sits inside a scored criterion with no points of its own`
- `named criterion with no points printed`

A pass/fail gate that removes a proposal from scoring does **not** go here — it goes in `disqualifiers`.

### `reviewed[].why`, the four fixed reasons

- `not about how proposals are evaluated or rejected`
- `repeats a sentence already cited`
- `table of contents or index entry`
- `scoring of a different procurement or contract phase`

## Row order

Rows follow the RFP's order: each row's `criterion` citation must come later in the source than the previous row's. The checker enforces it.

## The stop state

The matrix is complete and valid when `stop` is set, even with zero rows. `stop` is one of:

- `points do not reconcile to the stated total` — the sum and the stated total disagree, and no row was adjusted to force a match.
- `no scoring table published` — `stated_total` is `not in source` and there are zero rows; any named-but-unscored criterion goes under `could_not_map` with `named criterion with no points printed`.
- `no total stated; rows are the RFP's own maximums` — the RFP lists criteria as independent maximums (e.g. 25/25/30/10/5/5) with no sentence stating a grand total. `stated_total` stays `not in source`, but the rows and their points stay, and the renderer prints their sum. Never invent stages to work around a missing total.

The renderer prints the stated total and the sum beside the stop, so the reader sees the gap without anyone typing a number.

## Coverage: nothing that looks like scoring or a gate goes unaccounted for

`check_matrix.py` scans every line of the source (case-insensitive, with Unicode hyphen variants such as U+2011 normalized to `-` for this scan only — never for verbatim text matching) for these triggers:

- **Scoring:** a number with "points"/"pts", a percent, "points possible", "weight(ed/ing)", "scor(e/ed/es/ing)", "evaluation criteria", "pass/fail", "not scored", "maximum", "max N".
- **Gates:** "non-responsive", "non-responsib…", "disqualif…", "reject…", "will/shall not be considered/evaluated/scored/accepted/opened/reviewed", "mandatory", "late proposals/submittals/bids/responses", "prequalif…".

Every line that matches has to fall inside at least one citation somewhere in the matrix: the `rfp` field, `stated_total`, any row's sourced field, a `disqualifiers` entry, a `could_not_map` entry, or a `reviewed` entry. A hit line that is cited nowhere fails the matrix, printed as `COVERAGE: p<page>:<line> not cited or reviewed: <line text>`. This is what catches a criterion, a gate, or an independent maximum that the translator's own reading missed.

## Rendered forms

- **Markdown** (`.matrix.md`): header with the RFP, stated total (or per-stage reconcile line), sum, reconcile verdict, and the coverage summary line; Part 1 (rows, grouped under their RFP-section heading, nine columns, citation after every sourced cell); a TOTAL line; Part 2 disqualifiers with a count; Part 3 could-not-map; a count of rows waiting on a person.
- **CSV** (`.matrix.csv`): the same nine columns and section groupings as the Markdown, citations inline, a TOTAL row.
- **XLSX** (`.matrix.xlsx`): one sheet, a repeated section-heading row above each group, Points as numbers with a live `=SUM(...)` TOTAL. A fresh workbook; no firm's template.
- **HTML** (`.matrix.html`): one self-contained file (inline CSS/JS, no network) embedding the full numbered source text, with a citation sidebar — clicking a citation opens the cited source page with the lines highlighted. Owned by the design worker; see `tools/matrix_template.html`.

## What the checker proves (exit 0)

1. Every citation parses, exists in the source, stays on one page, and covers at most 12 lines (2 for points).
2. Every sourced text — including each part of a multi-part cell — is a whole-word, whitespace-normalized run of its cited lines.
3. Every points value appears as a number on its cited line(s).
4. Every key is a contract key. Every human column (`status`, `input_source`, `lead`, `reviewer`) is present and empty; `kind` and every `why` come from their closed vocabularies; there is no `claude_does`, `owner`, or `human_check` key.
5. `answering_section` never begins with an imperative verb.
6. Rows are in the RFP's order.
7. The Points column reconciles to the stated total (per stage if staged), or `stop` says which stop state applies.
8. Every `disqualifiers` and `could_not_map` entry is cited and verbatim.
9. Coverage: every scoring/gate trigger line in the source is accounted for somewhere in the matrix.

Exit 1 names every failure. One failure is enough to refuse the matrix.
