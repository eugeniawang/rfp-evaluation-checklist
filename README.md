# RFP → Evaluation Matrix

Live demo: https://eugeniawang.github.io/rfp-evaluation-matrix/

A folder that turns a public-sector Request for Proposals into the nine-column evaluation matrix a proposal manager builds by hand at the start of every pursuit. Drop it into a Claude project, hand it an RFP, get back one row per scored criterion, in the RFP's own words, with every cell cited to the page and line it came from, plus a list of everything that would get the proposal disqualified before scoring. A stdlib checker re-reads every citation and refuses the matrix if a single cell is not in the source, or if a scoring or gate sentence in the source was never accounted for.

Built for Clief Notes weekly competition #13, The Translator.

## What it converts

| | |
|---|---|
| **In** | An RFP / RFQ / solicitation (PDF with a text layer, or plain text), plus addenda. Public owners: cities, counties, state agencies, universities, transit. |
| **Out** | `outputs/<rfp>.matrix.json`, rendered as `.md`, `.csv`, `.xlsx` and `.html`. Nine columns, one row per scored item grouped under the RFP's own section headings, a TOTAL row, a "Disqualifiers" list (what gets a proposal thrown out before scoring), a "Could not map" list, and a stop state when the arithmetic does not reconcile, no scoring is published, or the RFP states no grand total. |
| **Who does this by hand** | Proposal managers and capture leads at construction, engineering and architecture firms, usually the afternoon the RFP drops, usually in a spreadsheet. |

## The folder

```
identity.md         what it converts, from what, to what, and what it refuses to do
rules.md            how each column is filled, what "verbatim" means, when to stop
examples.md         three real RFPs in, three matrices out, side by side
reference/schema.md the contract: every field, its type, its source, and what the checker proves
fixtures/           three public RFPs (PDF) and their numbered source text
outputs/            the three matrices (JSON, Markdown, CSV, XLSX, HTML)
tools/extract.py    PDF or text → numbered source text (p<page>:<line>| on every line)
tools/check_matrix.py    the gate: every claim in the matrix must be found in the source,
                         and every scoring/gate sentence in the source must be accounted for
tools/write_matrix.py    renders a matrix the gate accepted (md/csv/xlsx/html)
tools/matrix_template.html  the HTML rendering's markup/CSS/JS (citation sidebar, etc.)
tests/               45+ tests, most of them proving the gate refuses a specific kind of bad matrix
```

## Use it

**1. Attach the folder to a Claude project** (Claude.ai Projects with code execution enabled, or Claude Code with this directory open). `identity.md` and `rules.md` make Claude the translator. This only works where Claude can run `tools/extract.py` and `tools/check_matrix.py` itself — without code execution, Claude stops and asks for the numbered source text instead of citing a page it only looked at (rule 0).

**2. Extract the RFP.** Python 3.9+ and poppler (`brew install poppler` / `apt install poppler-utils`) for PDFs. `openpyxl` (`pip install openpyxl`) only if you want the XLSX rendering; without it you get Markdown and CSV and a note.

```
python3 tools/extract.py fixtures/your-rfp.pdf
```

That writes `fixtures/your-rfp.source.txt`. Every line looks like `p11:14|            Staff Experience - 40 points`. Attach that file too, or paste it.

**3. Ask for the matrix.**

> Translate `fixtures/your-rfp.source.txt` into an evaluation matrix. Write `outputs/your-rfp.matrix.json` per `reference/schema.md`.

Claude reads the source, writes the JSON, and says which human columns are waiting on a person.

**4. Check it. Then render it.**

```
python3 tools/check_matrix.py outputs/your-rfp.matrix.json
python3 tools/write_matrix.py outputs/your-rfp.matrix.json
```

`PASS` means every criterion, every points figure, every input sentence, every disqualifier and every "could not map" entry was found, verbatim and as whole words, on the one page it cites, that the points figure is printed on its own cited line, that no key exists outside the contract, that rows are in the RFP's order, that the points reconcile (or `stop` says why not), and that every scoring or gate sentence in the source is accounted for somewhere in the matrix (the coverage check). `FAIL` names each cell, or each uncited line, that was not. The renderer refuses a matrix the checker rejects, so nothing unverified becomes a spreadsheet.

**Try it on the shipped fixtures right now:**

```
for f in outputs/*.matrix.json; do python3 tools/check_matrix.py "$f"; done
python3 -m unittest discover tests
```

## What comes back

Every matrix leads with who, what, and when: the issuing public owner (`issuer`), the project or solicitation name (`title`), and the proposal due date (`due`) — each cited like any other fact, alongside the RFP's own number (`rfp`). The rendered header reads "`<issuer>` · `<title>`" as the big title, "RFP `<number>`" beneath it, and "Proposals due: `<due>`".

The nine columns, always in this order:

Status · What the RFP will score (their exact words) · Points for this item · What the RFP asks you to provide · Where your team will get it · What the scorer will look for · Where it goes in your proposal · Lead for this section · Reviewer for this section

Four of the real columns come from the RFP and carry a `[p<page>:<line>]` citation each (criterion, points, input needed, evaluation criteria); a fifth, "where it goes in your proposal", does too when the RFP actually ties a section to that criterion. The remaining four (Status, Input data source, Lead, Reviewer) are the firm's knowledge and workflow and are always empty on hand-over; the Markdown ends with a count of rows waiting on a person. `section` — the RFP's own heading for the scoring table — isn't a column at all; rows are grouped under it as a heading, since it would otherwise repeat on every row.

Above the table, Part 2 lists every **disqualifier**: every sentence that removes, rejects, or disqualifies a proposal, or makes something mandatory on pain of rejection, cited and tagged with one of nine fixed kinds (late submittal, missing form, non-responsive determination, and so on). Part 3 is "Could not map".

A cell with nothing in the RFP to cite says `not in source`. A matrix whose points do not add up to the RFP's stated total carries the fixed stop state `points do not reconcile to the stated total` instead of an adjusted row, and the rendering prints both numbers. An RFP with no published scoring produces a valid matrix with zero rows and the stop state `no scoring table published`. An RFP that lists criteria as independent maximums with no grand total keeps its rows and uses the stop state `no total stated; rows are the RFP's own maximums`.

## Why the checker is the point

The failure that makes RFP tooling untrustworthy is a criterion that reads well and is not what the RFP said — or a gate the RFP stated that silently disappeared. The scorer is reading their own words; a paraphrase loses the match, and a dropped disqualifier gets a proposal rejected for a reason nobody flagged. So the contract is mechanical: text must be a whole-word, whitespace-normalized run of the cited lines on one page, numbers must be printed on their one or two cited lines, every key must be a contract key, every explanation is a fixed phrase rather than free text, and every scoring or gate sentence in the source has to be cited somewhere or explicitly marked `reviewed`. The tests in `tests/test_matrix.py` prove the checker fails on a paraphrase, a respelled word, a mid-word fragment, an invented figure, a figure borrowed from a neighbouring line, a wrong or cross-page citation, an extra key, free text in `stop`, `kind`, or `why`, reordered rows, a filled human column, a disqualifier with a made-up kind, an `answering_section` that starts with an imperative verb, a multi-part cell with one bad part, an unreconciled sum, and a scoring/gate sentence (including one hidden behind a Unicode hyphen) that nothing accounts for. A gate that cannot fail is not a gate. Adversarial reviews of earlier versions found the substring, in-range-number, dropped-content and dropped-gate holes; this version closes them and ships the tests that would have caught them.

## Fixtures

All three are public documents, downloaded 2026-09-23 from the issuing agencies' sites:

- City of Tucker, GA, RFP 2026-016, CEI Services (100 points, three criteria)
- City of Tucker, GA, RFP 2026-008, Right-of-Way Maintenance (100 points, three criteria with descriptions)
- Colorado DOT, US 50 Passing Lanes, Construction Manager services, Final RFP 4/14/26 (60-point proposal + 40-point interview, sub-criteria)

## Limits, stated

- A scanned PDF with no text layer cannot be cited and is refused by `extract.py`. Run OCR first and feed the text.
- Column layouts that `pdftotext -layout` interleaves can split a criterion across lines in an odd order; cite a range and the checker joins the lines.
- Addenda are separate source files; a criterion changed by an addendum is cited to the addendum. The checker reads one source per matrix today, so an addendum-changed row should be built from a merged source text.
- The translator maps what the RFP says. Which internal system holds a resume, and who leads or reviews the cost form, is the firm's knowledge and stays in the human columns.

## License

MIT. The fixtures are public government solicitations reproduced for testing.
