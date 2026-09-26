---
title: Examples: the contract holding on three real RFPs
created: 2026-09-23 00:40
last_updated: 2026-09-25 18:40
owner: Gina Wang
status: active
---

# Examples: the contract holding on three real RFPs

Three public RFPs went in; three matrices with the same nine columns came out. Each pair below shows an excerpt of the numbered source beside the rows it produced, so a reader can put a finger on the input line and the output cell at the same time. The full inputs are in `fixtures/`, the full outputs in `outputs/`, and every one passes `tools/check_matrix.py`.

Every matrix also carries who, what, and when at the top (`issuer`, `title`, `due` — Ruling 18:49), each sourced and cited like any other fact. Example 1's: `issuer` "City of Tucker" [Page 1, line 1], `title` "Construction, Engineering and Inspection (CEI) Services" [Page 1, line 8], `due` "received no later than July 9, 2026 at 1:00pm EST" [Page 2, line 34]. The rendered header reads "City of Tucker · Construction, Engineering and Inspection (CEI) Services" as the big title, "RFP City of Tucker Request for Proposal 2026-016" (the `rfp` field, verbatim as printed) beneath it, and "Proposals due: received no later than July 9, 2026 at 1:00pm EST" with its own citation.

## Example 1: a short city RFP with a clean 100-point table

**Input:** City of Tucker, Georgia, RFP 2026-016, Construction Engineering and Inspection services. 22 pages. `fixtures/tucker-ga-rfp-2026-016-cei-services.source.txt`.

The scoring section, as extracted:

```
p11:7 |   4. Selection Criteria
p11:9 |      The Evaluation Committee will evaluate the quality and completeness of each proposal
p11:10|      as it addresses each requirement of the RFP. The RFP carries a total weight of 100 points.
p11:14|            Staff Experience - 40 points
p11:16|            Firm Qualifications and Similar Project Experience – 25 Points
p11:18|            Cost Proposal – 35 points
```

**Output** (`outputs/tucker-ga-rfp-2026-016-cei-services.matrix.md`), grouped under the heading "From the RFP section: 4. Selection Criteria [Page 11, line 7]", three rows, stated total 100 [Page 11, line 10], sum 100, do they match: yes:

| What the RFP will score (their exact words) | Points for this item | Where it goes in your proposal |
|---|---|---|
| 1. Staff Experience [Page 11, line 14] | 40 [Page 11, line 14] | 5. Provide the resumes of key personnel who will perform the work. [Page 10, line 18] |
| 2. Firm Qualifications and Similar Project Experience [Page 11, line 16] | 25 [Page 11, line 16] | 3. In table format, provide a brief description of CEI services or related projects [Page 10, line 12] |
| 3. Cost Proposal [Page 11, line 18] | 35 [Page 11, line 18] | 3. Cost Proposal (submit as separate file) [Page 3, line 8] |

(Status, Input data source, Lead, Reviewer: empty on all three rows.)

**What the contract did here:** rows 1 and 2's `input_needed` are each two citation parts, joined with " · ", because the ask splits across a gap the checker's 12-line/one-page span can't bridge in one citation: row 1 splits the primary-contact sentence [Page 10, lines 18-20] from the personnel-background sentence right after it [Page 10, lines 20-24]; row 2 splits the CEI-experience sentence [Page 10, lines 12-14] from a DeKalb County experience requirement four pages earlier [Page 6, lines 14-16]. All three rows share one `evaluation_criteria` sentence [Page 11, lines 9-10], since the RFP gives no criterion-specific one here. Row 3's proposal section comes from a numbered item on page 3, not from the scoring section itself. Seventeen sentences that remove, reject, or gate a proposal — late bids, GDOT prequalification, non-responsive and non-responsible determinations, the page-limit rule, the City's reservation of rights — sit under Part 2: Disqualifiers, each tagged with one of the nine fixed kinds. What's left under Part 3, "Other things the RFP says about scoring," is five sentences that don't gate anything: the Organizational Chart item [Page 10, line 16] and the additional-references item [Page 10, lines 26-27], neither tied to a scored criterion; the comparative-evaluation sentence that applies to every row [Page 10, lines 34-37]; the category-scoring sentence [Page 11, lines 11-12]; and the oral-presentation clause whose criteria belong to a later stage [Page 11, lines 25-27].

## Example 2: a two-stage state DOT RFP with sub-criteria

**Input:** Colorado Department of Transportation, US 50 Passing Lanes, Construction Manager services, Final RFP 4/14/26. 49 pages. `fixtures/codot-us50-passing-lanes-cm-rfp.source.txt`.

There is no sentence stating a grand total. The RFP scores a written proposal out of 60 and an interview out of 40, and says elsewhere that the two are summed:

```
p32:8 |3.1.       EVALUATION CRITERIA FOR PROPOSALS (60 Points Possible)
p32:9 |       A. CM Project Management Team (10 Points Possible)
p35:28|B. Contractor Capability (10 Points Possible)
p36:20|C. Strategic Project Approach (20 Points Possible)
p37:27|D. Approach to Risk, Schedule, and Pricing (20 Points Possible)
p38:8 |3.2       EVALUATION CRITERIA FOR INTERVIEWS (40 Points Possible)
p38:12|      A. Short Presentation (15 Points)
p38:19|      B. Question and Answer Session with the Selection Panel (25 Points)
p24:11|preconstruction CM services. The Proposers Technical Score and their Interview Score will be summed
p24:12|and tabulated which will be referred to as their “Total Score”,
```

Nowhere does Section 2.9 (Proposal Submittal) tie an individual Section 3.1 criterion to a numbered submittal item or form — the whole of Section 3 is one undifferentiated narrative — so every Proposal-stage row's `answering_section` is `not in source` (rendered `not in source (the RFP doesn't say)`), never a repurposed "Provide/Describe/Identify" sentence. Criterion D spreads its ask across three named sub-parts and a page break:

```
p37:36|           Schedule Approach
p37:37|           Describe the Proposer’s plan and approach to managing the construction schedule in such
p37:41|           Cost Model Approach
p37:42|           Describe the Proposer’s approach to Transparency and Accountability in the Cost Model.
p37:45|           Describe how the Proposer’s cost model will incorporate the variables that affect project
p38:5 |                 Independent Cost Estimator, and be reliable over multiple construction seasons.
```

**Output** (`outputs/codot-us50-passing-lanes-cm-rfp.matrix.md`): "Proposal stage — the RFP says it scores out of 60. The items below add up to 60. Do they match? Yes" and the same sentence for the Interview stage at 40/40; six rows across the two stages:

| Stage | What the RFP will score (their exact words) | Points for this item | What the scorer will look for | Where it goes in your proposal |
|---|---|---|---|---|
| Proposal | A. CM Project Management Team [Page 32, line 9] | 10 [Page 32, line 9] | Composition and Commitment of the CM Project Management Team [Page 32, line 10] | not in source (the RFP doesn't say) |
| Proposal | B. Contractor Capability [Page 35, line 28] | 10 [Page 35, line 28] | Prior Project Experience/Performance/References [Page 35, line 32] | not in source (the RFP doesn't say) |
| Proposal | C. Strategic Project Approach [Page 36, line 20] | 20 [Page 36, line 20] | not in source (the RFP doesn't say) | not in source (the RFP doesn't say) |
| Proposal | D. Approach to Risk, Schedule, and Pricing [Page 37, line 27] | 20 [Page 37, line 27] | not in source (the RFP doesn't say) | not in source (the RFP doesn't say) |
| Interview | A. Short Presentation [Page 38, line 12] | 15 [Page 38, line 12] | The interview presentation and question/answer scoring will be based on the following criteria… [Page 38, lines 28-34] | not in source (the RFP doesn't say) |
| Interview | B. Question and Answer Session with the Selection Panel [Page 38, line 19] | 25 [Page 38, line 19] | (same, [Page 38, lines 28-34]) | not in source (the RFP doesn't say) |

Row 4's `input_needed` is seven citation parts — Risk Approach, Schedule Approach, and Cost Model Approach, in the RFP's order — because no single ≤12-line, one-page passage holds all three. The last two parts are the sentence split by the page break shown above (`p37:45-p37:46` then `p38:5`).

**What the contract did here:** rows 1-4's `evaluation_criteria` and `answering_section` no longer hold a repurposed "Provide/Describe/Identify" instruction sentence — an earlier draft had done that for all four Proposal rows, mistaking the ask for the name of the response vehicle. `answering_section` is `not in source` on every Proposal row because the RFP never names one; rows 3 and 4 also carry `evaluation_criteria: not in source`, because the RFP gives no standalone "what we will look for" sentence beyond the criterion name. Fourteen gate sentences sit under Part 2: Disqualifiers, including the organizational-conflict-of-interest bars and the Form B-1/B-2 "Reject" gates and their softer "failure to certify … may cause" companions. Exactly one sentence — the scoring-increments/Evaluation-Assessment-Guidelines sentence at page 44 — sits under Part 3, tagged "scoring method that applies to every row; no points of its own". `Lead`, `Reviewer`, `Input data source`, and `Status` are empty on all six rows; there is no `Claude does` column.

## Example 3: same issuer, different shape

**Input:** City of Tucker RFP 2026-008, Right-of-Way Maintenance. 29 pages. Same city as Example 1, a different service, a different scoring split (35 / 35 / 30), and the criteria carry descriptive sentences this time:

```
p14:15|        Proposed Management Plan and Approach – 35 points
p14:16|        The proposal shall outline the plan that the company will use to provide the most
p14:17|        effective delivery of the requested services as outlined in the Scope of Work.
p14:19|        Qualifications and Similar Project Experience of the Company and Staff – 35
p14:20|        Points
p14:27|        Cost Proposal – 30 points
```

**Output** (`outputs/tucker-ga-rfp-2026-008-row-maintenance.matrix.md`): three rows, the same nine columns as Example 1, grouped under "4. Selection Criteria" [Page 14, line 8], sum 100 against stated 100 [Page 14, line 11], do they match: yes. Row 1's evaluation criteria is the RFP's own sentence [Page 14, lines 16-17] instead of the general one, because this RFP supplies one, and its `answering_section` is `not in source` — the RFP never names a section for it. Row 2's `evaluation_criteria` is the RFP's own five-line description of what the report must demonstrate [Page 14, lines 21-25]; its `answering_section` is `not in source` too, for the same reason as row 1. Row 3 is the one row with a real proposal section, "Cost Proposal (form provided)" [Page 3, line 11], sitting beside a scoring sentence — "In scoring against stated criteria, the City may consider such factors as accepted industry standards…" [Page 13, lines 35-38] — reused as `evaluation_criteria` because this RFP gives no criterion-specific sentence for cost.

Twelve gate sentences — late bids, the City's reservation of rights, non-responsive and non-responsible determinations, incomplete and late submittals, the page-limit rule, and the "outside the formal response" disqualification — sit under Part 2: Disqualifiers. Part 3, "Other things the RFP says about scoring," carries three sentences: "Age and condition of equipment will be factored into contractor scoring for these services" [Page 5, line 36], which carries no points and no criterion; the category-scoring sentence [Page 14, lines 12-13]; and the oral-presentation clause whose criteria belong to a later stage.

## The bar, checked

- **Same shape across inputs:** `tests/test_matrix.py::test_same_shape_across_inputs` asserts every row in every shipped matrix has exactly the same set of real keys (the nine columns plus `section` and, where staged, `stage`).
- **Every fact traces:** `python3 tools/check_matrix.py outputs/<any>.matrix.json` exits 0 on all three, and exits 1 when a test paraphrases a criterion, respells a word, quotes a fragment that ends mid-word, invents a points figure, points at a number on a neighbouring line, cites across a page, adds a key the contract does not name (including a retired `claude_does`, `owner`, or `human_check`), writes free text into `stop`, `why`, or a disqualifier's `kind`, reorders rows, fills a human column (`status`, `input_source`, `lead`, or `reviewer`), gives `answering_section` a part that opens with an imperative verb, breaks a multi-part cell's second part, or leaves a coverage trigger line — including one hidden behind a Unicode hyphen — uncited and unreviewed.
- **Missing is marked, not filled:** the literal JSON string `not in source` appears wherever the RFP is silent, in every rendering; the Markdown adds the plain-English gloss " (the RFP doesn't say)" after it, the CSV and XLSX leave it bare. Most visible in the CDOT Proposal rows' `answering_section`, since that RFP never ties a criterion to a numbered submittal item.
