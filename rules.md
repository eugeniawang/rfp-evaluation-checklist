---
title: Rules: how an RFP becomes an evaluation matrix
created: 2026-09-23 00:36
last_updated: 2026-09-25 18:31
owner: Gina Wang
status: active
---

# Rules: how an RFP becomes an evaluation matrix

These rules are the whole method. Read them in order. `reference/schema.md` defines each field; this file says where each field's content comes from and what to do when it is missing.

## 0. Read the numbered source, never the PDF

Run `python3 tools/extract.py <rfp.pdf>` first. It writes `<rfp>.source.txt`, where every line is prefixed `p<page>:<line>|`. Every citation in the matrix points into that file. If the PDF has no text layer, the script says so and writes nothing; a scan cannot be cited, so it cannot be translated. Ask for a text copy.

Read the whole source once before writing a row. The scoring table is usually in a section called Evaluation, Selection Criteria, Basis of Award, or an appendix of evaluation forms. Addenda go through the same extractor and are read after the base RFP; a criterion changed by an addendum is cited to the addendum.

**No Python available (claude.ai without code execution):** this translator only works where it can run `tools/extract.py` and `tools/check_matrix.py` itself. In a claude.ai project, that means a project with code execution enabled, with this folder and the RFP PDF uploaded, so Claude runs the tools itself rather than reasoning about page numbers by eye. If code execution is not available, stop and reply with exactly: "I need the numbered source text: run python3 tools/extract.py <rfp.pdf> and attach the .source.txt." Never cite a PDF that was not run through the extractor — a citation to a page Claude only looked at, not numbered, is not verifiable.

## 1. One row per scored item, in the RFP's order

A row exists when the RFP names a thing it will score and attaches points, a weight, or a percentage to it. Rows follow the order the RFP lists them. Sub-criteria with their own points get their own rows; a sub-criterion with no points of its own stays inside its parent and is listed under "Could not map" if it matters (see rule 7).

An RFP that scores in stages (a written proposal worth 60, an interview worth 40) gets a `stage` on every row and a `stated_total.stages` list. Each stage reconciles on its own.

Some RFPs list criteria as independent maximums (25/25/30/10/5/5) with no sentence stating a grand total. Keep the rows as they are, set `stated_total` to `not in source`, and set `stop` to `no total stated; rows are the RFP's own maximums`. Do not invent a total by adding the maximums yourself, and do not fake a `stage` to make the numbers reconcile — the renderer prints the sum next to the stop so the reader sees it.

## 2. Which input feeds which field

| Field | Comes from | Citation |
|---|---|---|
| `rfp` | The RFP's own number, from a page header or the cover | the line it is printed on |
| `issuer` | The public owner's name, as printed (e.g. "City of Tucker") | the line it is printed on |
| `title` | The project or solicitation name, as printed (e.g. "Right-of-Way Maintenance") | the line it is printed on |
| `due` | Only the date and time proposals are due, quoted exactly as printed (e.g. `April 2, 2026, at 1:00pm EST`), without the RFP's own label such as "Proposal Deadline" | the line it is printed on |
| `stated_total` | The sentence that states the total ("carries a total weight of 100 points", "60 Points Possible") | that sentence |
| `section` | The heading of the RFP section that holds the scoring table. Not a column — it renders once, as a heading above the rows that share it | the heading line |
| `criterion` | The criterion **verbatim** as the RFP names it. Not shortened, not re-cased, not re-spelled | the line(s) it appears on |
| `points` | The number printed beside the criterion | the same line(s) |
| `input_needed` | The **whole** ask: every bullet and sub-item the RFP lists under this criterion or its submittal item — not just the intro sentence ("The proposal should include the following:" alone is a failure). Use a multi-part cell (`reference/schema.md`) when it runs past 12 lines or crosses a page | those lines, one citation per part |
| `evaluation_criteria` | The criterion's own descriptive sentence when the RFP has one; the general evaluation sentence only when it has none | those lines |
| `answering_section` | The numbered submittal item, proposal section, or form — filled **only when the RFP itself ties that section/item/form to this specific criterion**. An RFP having a "Proposal Submittal" section that covers everything is not the same as it naming that section for *this* criterion | those lines |
| `input_source` | **Human.** Where the firm keeps that input. Always empty | none |
| `lead` | **Human.** The person who supplies or confirms the input. Always empty | none |
| `reviewer` | **Human.** What passing looks like and who says so. Always empty | none |
| `status` | **Human.** Always empty; the firm's workflow fills it | none |
| `disqualifiers` | Every sentence that removes, rejects, disqualifies, or refuses to evaluate/score/consider a proposal or proposer, or makes something mandatory on pain of rejection, with one of the nine fixed `kind` phrases | the lines |
| `could_not_map` | Every scoring sentence in the source that did not become a row, with one of the six fixed reasons | the lines |
| `reviewed` | Every source line the coverage scan flags (rule 7) that turns out not to be scoring or gating content, with one of the four fixed reasons | the line |

## 3. Verbatim means verbatim

The text in a sourced cell must be a substring of the cited lines after whitespace is collapsed. Nothing else changes: not the quotation marks, not an en dash, not a stray capital, not a missing full stop in the original. If the RFP misspells a word, the matrix misspells it too. A cell that reads better than the RFP has been edited, and an edited cell fails the check.

A citation may span consecutive lines on one page (`p13:14-p13:17`) so a sentence broken across lines can be quoted whole. It may not cross a page and may not span more than 12 lines; if the words are that far apart, they are two citations — either two parts of a multi-part cell, or the cell is `not in source`. A points citation spans at most 2 lines, so the number found is the one printed beside the criterion and not one from nearby text. The match is whole-word: a quotation that starts or ends in the middle of a word fails.

A sourced field may be a list of 1 to 10 `{"text", "cite"}` parts instead of one, for an ask spread across several passages (a bullet list longer than 12 lines, or one that crosses a page). Every part is checked on its own. `criterion` and `points` are never lists — one object only.

## 4. When a field has no source, say so

The value is the exact phrase `not in source`. Not blank, not "n/a", not a best guess. Common cases:

- The RFP names the criterion and points but never ties a specific submittal item/section/form to *this* criterion: `answering_section` is `not in source`.
- The RFP scores an interview: `answering_section` is `not in source`, because nothing written answers it.
- The RFP names criteria in its evaluation section but never prints a points figure for them: this is **not** a row with `points: "not in source"` — the checker never accepts that. It is zero rows, `stated_total` is `not in source`, `stop` is `no scoring table published`, and each named criterion is listed under `could_not_map` with the reason `named criterion with no points printed`.

## 5. The human columns stay empty

`input_source`, `lead`, `reviewer`, and `status` are the firm's knowledge and workflow, not the RFP's. The translator never fills them, and `check_matrix.py` fails a matrix where it did. The rendered Markdown ends with a count of rows waiting on a person, so nobody mistakes an empty column for a finished one. There is no `claude_does` column — what happens to a row next is the firm's workflow, decided outside this file.

## 6. Reconcile, or stop

Sum the Points column. It must equal the stated total (or each stage's total). If it does not:

- Do not change a row.
- Set `stop` to the fixed phrase `points do not reconcile to the stated total`. The renderer prints the stated total and the sum beside it; nothing is typed by hand.
- Hand it over. This is a conversation with the proposal manager, not a rounding decision.

If the RFP publishes no scoring table at all, the matrix has zero rows, `stated_total` is `not in source`, and `stop` is `no scoring table published` (see rule 4 for named-but-unscored criteria). If the RFP lists criteria as independent maximums with no grand total, keep the rows and use `stop` = `no total stated; rows are the RFP's own maximums` (rule 1). Each is a complete, valid output.

## 7. Nothing that matters gets dropped

Before finishing, search the source for every sentence that assigns points, states a total, names something the owner will score or factor in, or removes a proposal from scoring (non-responsive, pass/fail, late, incomplete, disqualifying, "reserves the right to reject", a required form or license). Every gate goes in `disqualifiers`, cited, with one of the nine fixed `kind` phrases. Everything else that assigns or states scoring but isn't a row's own criterion goes under `could_not_map` with one of the six fixed reasons. A criterion the RFP marks "Not Scored" (or pass/fail, or 0 points) goes to `disqualifiers` if missing it would get the proposal rejected, otherwise to `could_not_map` with `submittal item the RFP does not tie to a scored criterion`.

`check_matrix.py`'s coverage check backs this rule with a machine scan: every source line that contains a scoring or gate trigger word (a points figure, "weight", "scored", "non-responsive", "reject", "mandatory", "late", "disqualif…", "maximum", "not scored", and their neighbors) must be cited somewhere — a row, `disqualifiers`, `could_not_map`, or, for a line that turns out not to be scoring/gating content after all, `reviewed`. A line the scan flags that nobody accounted for fails the matrix and prints as `COVERAGE: p<page>:<line> not cited or reviewed: <line text>`. Sentences that merely mention evaluation without assigning, scoring, or gating anything ("the RFP states the relative importance of all evaluation criteria") are `reviewed`, not left out silently.

**Before handing over, re-read for drops specifically:**

1. For each row, re-read the source from that criterion to the next criterion (or the next section break). Every requirement line in that span is in `input_needed` or `could_not_map` — an intro sentence alone ("the proposal should include the following:") without its bullets is a failure.
2. Run the coverage check (it's part of `check_matrix.py`, rule 9) and account for every hit.
3. For every named criterion, confirm the row's `input_needed` and `evaluation_criteria` reflect everything the RFP names under it — not just the first sentence.

## 8. What never goes in

- A points value the RFP does not print.
- A criterion reworded "the way it is usually written".
- A section name borrowed from the last RFP you saw.
- An `answering_section` guessed from a general submittal section the RFP never tied to this specific criterion — see rule 2.
- A date, a deadline, a contact, a page limit, or anything else not asked for by the nine columns or the who/what/when fields, even when it is true and useful. The matrix is not the place for it. The one exception is the proposal due date itself, which belongs in the top-level `due` field, cited like every other fact — not a deadline for questions, not an award date, not a contract start date.
- Anything about the firm: names, systems, past proposals. Those are the human columns' business.

## 9. Prove it before handing over

```
python3 tools/check_matrix.py outputs/<rfp>.matrix.json
python3 tools/write_matrix.py outputs/<rfp>.matrix.json
```

The first refuses any cell whose text is not at its citation as whole words, any points figure not printed on its one or two cited lines, any citation that crosses a page or runs past 12 lines, any key the contract does not name, any filled human column, any free text in `stop`, `kind`, or `why`, any row out of the RFP's order, any `answering_section` that starts with an imperative verb, any sum that does not reconcile without a `stop`, and any scoring/gate line in the source that nothing in the matrix accounts for (the coverage check). The second renders only a matrix the first accepted. A matrix that has not passed the checker is a draft, not an output.

Leave no helper scripts behind: write only the files under `outputs/` named in this rule. A one-off `build_<rfp>.py` or similar left in the folder root is not part of the contract, confuses the next person reading the repo, and does not get committed.
