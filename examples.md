---
title: Examples: the contract holding on three real RFPs
created: 2026-09-23 00:40
last_updated: 2026-09-25 18:22
owner: Gina Wang
status: active
---

# Examples: the contract holding on three real RFPs

Three public RFPs went in; three matrices with the same twelve columns came out. Each pair below shows an excerpt of the numbered source beside the rows it produced, so a reader can put a finger on the input line and the output cell at the same time. The full inputs are in `fixtures/`, the full outputs in `outputs/`, and every one passes `tools/check_matrix.py`.

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
p11:19|            Proposers shall provide not to exceed amounts for Engineering services and for
p11:20|            Testing services. Proposers should submit clearly defined staff rates and estimated
p11:21|            number of hours for proposed assigned staff.
```

The submittal requirements a page earlier:

```
p10:12|   3. In table format, provide a brief description of CEI services or related projects
p10:13|      completed within the last three (3) years. Include the name of the project owner,
p10:14|      contact name and email or phone number.
p10:18|   5. Provide the resumes of key personnel who will perform the work. Contractors shall
p10:20|      the City. Personnel information should include professional registrations, years of
p10:21|      experience, years with firm, and description of responsibilities associated with no
p10:22|      more than two (2) specific previous projects performed by the individual. Show all
```

**Output** (`outputs/tucker-ga-rfp-2026-016-cei-services.matrix.md`), three rows, stated total 100 [p11:10], sum 100, reconciles:

| # | RFP criterion (their words) | Points | Input needed | Proposal section that answers it |
|---|---|---|---|---|
| 1 | Staff Experience [p11:14] | 40 [p11:14] | Contractors shall clearly indicate the designated staff that will act as the primary point of contact with the City. [p10:18-p10:20] · Personnel information should include professional registrations, years of experience, years with firm, and description of responsibilities associated with no more than two (2) specific previous projects performed by the individual. Show all licenses and certifications of key personnel including registered professional engineer, land surveyor, and landscape architect. [p10:20-p10:24] | 5. Provide the resumes of key personnel who will perform the work. [p10:18] |
| 2 | Firm Qualifications and Similar Project Experience [p11:16] | 25 [p11:16] | In table format, provide a brief description of CEI services or related projects completed within the last three (3) years. Include the name of the project owner, contact name and email or phone number. [p10:12-p10:14] · 2. The selected firm shall have recent (within the past 24-month) construction inspection experience within Dekalb County on a similar project. Please provide previous experience in proposal. [p6:14-p6:16] | 3. In table format, provide a brief description of CEI services or related projects [p10:12] |
| 3 | Cost Proposal [p11:18] | 35 [p11:18] | Proposers shall provide not to exceed amounts for Engineering services and for Testing services. Proposers should submit clearly defined staff rates and estimated number of hours for proposed assigned staff. [p11:19-p11:21] | 3. Cost Proposal (submit as separate file) [p3:8] |

(Input data source, Owner, Human check: empty on all three rows. Claude does: empty on all three rows. Status: open.)

**What the contract did here:** row 1 and row 2's `input_needed` are each two citation parts from two different pages, joined with " · " — a single passage was never long enough to hold the whole ask. Row 3's proposal section comes from a numbered item on page 3, not from the scoring section itself. The en dash in row 2's criterion is the RFP's en dash; the checker would fail a hyphen. Seventeen sentences that remove, reject, or gate a proposal — late bids, GDOT prequalification, non-responsive and non-responsible determinations, the page-limit rule, the City's reservation of rights — sit under Part 2: Disqualifiers, each tagged with one of the fixed kinds. What's left under "Could not map" is five sentences that don't gate anything: the Organizational Chart and additional-references items the RFP never ties to a scored criterion, the comparative-evaluation and category-scoring sentences that apply to every row, and the oral-presentation clause whose criteria belong to a later stage.

## Example 2: a two-stage state DOT RFP with sub-criteria

**Input:** Colorado Department of Transportation, US 50 Passing Lanes, Construction Manager services, Final RFP 4/14/26. 49 pages. `fixtures/codot-us50-passing-lanes-cm-rfp.source.txt`.

There is no sentence stating a grand total. The RFP scores a written proposal out of 60 and an interview out of 40, and says elsewhere that the two are summed:

```
p32:8 |3.1.       EVALUATION CRITERIA FOR PROPOSALS (60 Points Possible)
p32:9 |       A. CM Project Management Team (10 Points Possible)
p32:10|          Composition and Commitment of the CM Project Management Team
p35:28|B. Contractor Capability (10 Points Possible)
p36:20|C. Strategic Project Approach (20 Points Possible)
p37:27|D. Approach to Risk, Schedule, and Pricing (20 Points Possible)
p38:8 |3.2       EVALUATION CRITERIA FOR INTERVIEWS (40 Points Possible)
p38:12|      A. Short Presentation (15 Points)
p38:19|      B. Question and Answer Session with the Selection Panel (25 Points)
p24:11|preconstruction CM services. The Proposers Technical Score and their Interview Score will be summed
p24:12|and tabulated which will be referred to as their “Total Score”, The Proposers’ “Total Scores” will be
```

Nowhere does Section 2.9 (Proposal Submittal) tie an individual Section 3.1 criterion to a numbered submittal item or form — the whole of Section 3 is one undifferentiated narrative — so every Proposal-stage row's `answering_section` is `not in source`, never a repurposed "Provide/Describe/Identify" sentence. Criterion D spreads its ask across three named sub-parts and a page break:

```
p37:36|           Schedule Approach
p37:37|           Describe the Proposer’s plan and approach to managing the construction schedule in such
p37:41|           Cost Model Approach
p37:42|           Describe the Proposer’s approach to Transparency and Accountability in the Cost Model.
p37:45|           Describe how the Proposer’s cost model will incorporate the variables that affect project
p38:5 |                 Independent Cost Estimator, and be reliable over multiple construction seasons.
```

**Output** (`outputs/codot-us50-passing-lanes-cm-rfp.matrix.md`), six rows, two stages, each reconciling on its own:

| # | Stage | RFP criterion (their words) | Points | Evaluation criteria (what the scorer looks for) | Proposal section that answers it |
|---|---|---|---|---|---|
| 1 | Proposal | A. CM Project Management Team [p32:9] | 10 [p32:9] | Composition and Commitment of the CM Project Management Team [p32:10] | not in source |
| 2 | Proposal | B. Contractor Capability [p35:28] | 10 [p35:28] | Prior Project Experience/Performance/References [p35:32] | not in source |
| 3 | Proposal | C. Strategic Project Approach [p36:20] | 20 [p36:20] | not in source | not in source |
| 4 | Proposal | D. Approach to Risk, Schedule, and Pricing [p37:27] | 20 [p37:27] | not in source | not in source |
| 5 | Interview | A. Short Presentation [p38:12] | 15 [p38:12] | The interview presentation and question/answer scoring will be based on the following criteria: ● Project Understanding and goals, ● Project Approach, ● Project Innovation, ● Team Collaboration ● Communication Skills, and ● Understanding of CM/GC Project Delivery Method. [p38:28-p38:34] | not in source |
| 6 | Interview | B. Question and Answer Session with the Selection Panel [p38:19] | 25 [p38:19] | (same, [p38:28-p38:34]) | not in source |

Proposal stage: 60 stated [p32:8], 60 summed. Interview stage: 40 stated [p38:8], 40 summed.

Row 4's `input_needed` is seven citation parts — Risk Approach, Schedule Approach, and Cost Model Approach, in the RFP's order — because no single ≤12-line, one-page passage holds all three. The last two parts are the sentence split by the page break shown above:

| part | text | cite |
|---|---|---|
| 6 of 7 | Describe how the Proposer's cost model will incorporate the variables that affect project costs, innovation, essential inputs needed, coordination with the Owner and their | p37:45-p37:46 |
| 7 of 7 | Independent Cost Estimator, and be reliable over multiple construction seasons. | p38:5 |

**What the contract did here:** rows 1-4's `evaluation_criteria` and `answering_section` no longer hold a repurposed "Provide/Describe/Identify" instruction sentence — an earlier draft had done that for all four Proposal rows, mistaking the ask for the name of the response vehicle. `answering_section` is `not in source` on every Proposal row because the RFP never names one; rows 3 and 4 also carry `evaluation_criteria: not in source`, because the RFP gives no standalone "what we will look for" sentence beyond the criterion name, and the sentence that draft had borrowed for it moved into `input_needed`, where it belongs. Fourteen gate sentences sit under Part 2: Disqualifiers. Two of them — "No Person or business entity … will be eligible to directly submit or participate in the submittal of a proposal for this initiative" [p20:31-p20:35] and "No firm that is ineligible for State contracts may be part of any Proposer Team" [p20:42-p20:43] — are the organizational-conflict-of-interest bars an earlier draft missed entirely. The Form B-1 and Form B-2 "Reject" gates and their softer "failure to certify … may cause" companions — four sentences in the same family — all appear now, tagged `missing or incorrect required form`; the earlier draft had caught only the first of them. `Claude does` is empty on all six rows, same as the three human columns.

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

**Output** (`outputs/tucker-ga-rfp-2026-008-row-maintenance.matrix.md`): three rows, the same twelve columns as Example 1, sum 100 against stated 100 [p14:11]. Row 1's evaluation criteria is the RFP's own sentence [p14:16-p14:17] instead of the general one, because this RFP supplies one, and its `answering_section` is `not in source` — the RFP never names a section for it. Row 2's criterion breaks across two source lines ("– 35" then "Points"); the criterion cell cites p14:19 and the checker finds the words there. Row 3 is the one row with a real proposal section, "Cost Proposal (form provided)" [p3:11], sitting beside a scoring sentence — "In scoring against stated criteria, the City may consider such factors as accepted industry standards…" [p13:35-p13:38] — reused as `evaluation_criteria` because this RFP gives no criterion-specific sentence for cost.

Twelve gate sentences — late bids, the City's reservation of rights, non-responsive and non-responsible determinations, incomplete and late submittals, the page-limit rule, and the "outside the formal response" disqualification — sit under Part 2: Disqualifiers. What's left under "Could not map" is two sentences: "Age and condition of equipment will be factored into contractor scoring for these services" [p5:36], which carries no points and no criterion, and the oral-presentation clause whose criteria belong to a later stage.

## The bar, checked

- **Same shape across inputs:** `tests/test_matrix.py::test_same_shape_across_inputs` asserts every row in every shipped matrix has exactly the twelve keys.
- **Every fact traces:** `python3 tools/check_matrix.py outputs/<any>.matrix.json` exits 0 on all three, and exits 1 when a test paraphrases a criterion, respells a word, quotes a fragment that ends mid-word, invents a points figure, points at a number on a neighbouring line, cites across a page, adds a key the contract does not name, writes free text into `stop`, `why`, or a disqualifier's `kind`, reorders rows, fills a human column, leaves `claude_does` non-empty, or leaves a coverage trigger line uncited and unreviewed.
- **Missing is marked, not filled:** `not in source` appears wherever the RFP is silent — most visibly the CDOT Proposal rows' `answering_section`, since that RFP never ties a criterion to a numbered submittal item.
