---
title: Rules: how an RFP becomes an evaluation matrix
created: 2026-09-23 00:36
last_updated: 2026-09-23 00:49
owner: Gina Wang
status: active
---

# Rules: how an RFP becomes an evaluation matrix

These rules are the whole method. Read them in order. `reference/schema.md` defines each field; this file says where each field's content comes from and what to do when it is missing.

## 0. Read the numbered source, never the PDF

Run `python3 tools/extract.py <rfp.pdf>` first. It writes `<rfp>.source.txt`, where every line is prefixed `p<page>:<line>|`. Every citation in the matrix points into that file. If the PDF has no text layer, the script says so and writes nothing; a scan cannot be cited, so it cannot be translated. Ask for a text copy.

Read the whole source once before writing a row. The scoring table is usually in a section called Evaluation, Selection Criteria, Basis of Award, or an appendix of evaluation forms. Addenda go through the same extractor and are read after the base RFP; a criterion changed by an addendum is cited to the addendum.

## 1. One row per scored item, in the RFP's order

A row exists when the RFP names a thing it will score and attaches points, a weight, or a percentage to it. Rows follow the order the RFP lists them. Sub-criteria with their own points get their own rows; a sub-criterion with no points of its own stays inside its parent and is listed under "Could not map" if it matters (see rule 7).

An RFP that scores in stages (a written proposal worth 60, an interview worth 40) gets a `stage` on every row and a `stated_total.stages` list. Each stage reconciles on its own.

## 2. Which input feeds which field

| Field | Comes from | Citation |
|---|---|---|
| `rfp` | The RFP's own title or number, from a page header or the cover | the line it is printed on |
| `stated_total` | The sentence that states the total ("carries a total weight of 100 points", "60 Points Possible") | that sentence |
| `section` | The heading of the RFP section that holds the scoring table | the heading line |
| `criterion` | The criterion **verbatim** as the RFP names it. Not shortened, not re-cased, not re-spelled | the line(s) it appears on |
| `points` | The number printed beside the criterion | the same line(s) |
| `input_needed` | What the RFP tells the proposer to supply for this criterion: the submittal requirement, the "provide…" or "shall include…" sentence that this criterion scores | those lines |
| `evaluation_criteria` | What the RFP says the scorer will look for in this criterion: the descriptive sentence under the criterion, or the general evaluation sentence if there is no specific one | those lines |
| `answering_section` | The numbered submittal item, proposal section, or form the RFP says carries the response | those lines |
| `input_source` | **Human.** Where the firm keeps that input. Always empty | none |
| `owner` | **Human.** Who supplies it. Always empty | none |
| `claude_does` | One of three fixed phrases (schema §claude_does), chosen by the kind of response the RFP asks for: prose (draft), a form (assemble), or a live session (prepare) | none; it is a label, not a fact |
| `human_check` | **Human.** Always empty | none |
| `status` | Always `open` | none |
| `could_not_map` | Every scoring sentence in the source that did not become a row, with one of six fixed reasons | the lines |

## 3. Verbatim means verbatim

The text in a sourced cell must be a substring of the cited lines after whitespace is collapsed. Nothing else changes: not the quotation marks, not an en dash, not a stray capital, not a missing full stop in the original. If the RFP misspells a word, the matrix misspells it too. A cell that reads better than the RFP has been edited, and an edited cell fails the check.

A citation may span consecutive lines on one page (`p13:14-p13:17`) so a sentence broken across lines can be quoted whole. It may not cross a page and may not span more than 12 lines; if the words are that far apart, they are two citations, or the cell is `not in source`. A points citation spans at most 2 lines, so the number found is the one printed beside the criterion and not one from nearby text. The match is whole-word: a quotation that starts or ends in the middle of a word fails.

## 4. When a field has no source, say so

The value is the exact phrase `not in source`. Not blank, not "n/a", not a best guess. Common cases:

- The RFP names the criterion and points but never says what the response section is called: `answering_section` is `not in source`.
- The RFP scores an interview: `answering_section` is `not in source`, because nothing written answers it.
- The RFP publishes criteria but no points: every `points` is `not in source`, `stated_total` is `not in source`, and the matrix carries a `stop` (rule 6).

## 5. The three human columns stay empty

`input_source`, `owner`, `human_check` are the firm's knowledge, not the RFP's. The translator never fills them, and `check_matrix.py` fails a matrix where it did. The rendered Markdown ends with a count of rows waiting on a person, so nobody mistakes an empty column for a finished one.

## 6. Reconcile, or stop

Sum the Points column. It must equal the stated total (or each stage's total). If it does not:

- Do not change a row.
- Set `stop` to the fixed phrase `points do not reconcile to the stated total`. The renderer prints the stated total and the sum beside it; nothing is typed by hand.
- Hand it over. This is a conversation with the proposal manager, not a rounding decision.

If the RFP publishes no scoring table at all, the matrix has zero rows, `stated_total` is `not in source`, and `stop` is `no scoring table published`. That is a complete, valid output.

## 7. Nothing that matters gets dropped

Before finishing, search the source for every sentence that assigns points, states a total, names something the owner will score or factor in, or removes a proposal from scoring (non-responsive, pass/fail, short list). Each one either sits in a row or appears under `could_not_map` with a citation and one of the six fixed reasons in `reference/schema.md`. Sentences that merely mention evaluation without assigning, scoring, or gating anything ("the RFP states the relative importance of all evaluation criteria") are not scoring content and are left alone.

## 8. What never goes in

- A points value the RFP does not print.
- A criterion reworded "the way it is usually written".
- A section name borrowed from the last RFP you saw.
- A date, a deadline, a contact, a page limit, or anything else not asked for by the twelve columns, even when it is true and useful. The matrix is not the place for it.
- Anything about the firm: names, systems, past proposals. Those are the human columns' business.

## 9. Prove it before handing over

```
python3 tools/check_matrix.py outputs/<rfp>.matrix.json
python3 tools/write_matrix.py outputs/<rfp>.matrix.json
```

The first refuses any cell whose text is not at its citation as whole words, any points figure not printed on its one or two cited lines, any citation that crosses a page or runs past 12 lines, any key the contract does not name, any filled human column, any free text in `stop` or `why`, any row out of the RFP's order, and any sum that does not reconcile without a `stop`. The second renders only a matrix the first accepted. A matrix that has not passed the checker is a draft, not an output.
