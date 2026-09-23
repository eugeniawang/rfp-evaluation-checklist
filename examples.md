---
title: Examples: the contract holding on three real RFPs
created: 2026-09-23 00:40
last_updated: 2026-09-23 00:40
owner: Gina Wang
status: active
---

# Examples: the contract holding on three real RFPs

Three public RFPs went in; three matrices with the same twelve columns came out. Each pair below shows an excerpt of the numbered source beside the rows it produced, so a reader can put a finger on the input line and the output cell at the same time. The full inputs are in `fixtures/`, the full outputs in `outputs/`, and every one passes `tools/check_matrix.py`.

## Example 1: a short city RFP with a clean 100-point table

**Input:** City of Tucker, Georgia, RFP 2026-016, Construction Engineering and Inspection services. 23 pages. `fixtures/tucker-ga-rfp-2026-016-cei-services.source.txt`.

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

| # | RFP criterion (their words) | Points | Input needed | Proposal section that answers it | Claude does |
|---|---|---|---|---|---|
| 1 | Staff Experience [p11:14] | 40 [p11:14] | Personnel information should include professional registrations, years of experience, years with firm, and description of responsibilities associated with no more than two (2) specific previous projects performed by the individual. Show all licenses and certifications of key personnel including registered professional engineer, land surveyor, and landscape architect. [p10:20-p10:24] | 5. Provide the resumes of key personnel who will perform the work. [p10:18] | draft |
| 2 | Firm Qualifications and Similar Project Experience [p11:16] | 25 [p11:16] | In table format, provide a brief description of CEI services or related projects completed within the last three (3) years. Include the name of the project owner, contact name and email or phone number. [p10:12-p10:14] | 3. In table format, provide a brief description of CEI services or related projects [p10:12] | draft |
| 3 | Cost Proposal [p11:18] | 35 [p11:18] | Proposers shall provide not to exceed amounts for Engineering services and for Testing services. Proposers should submit clearly defined staff rates and estimated number of hours for proposed assigned staff. [p11:19-p11:21] | not in source | assemble |

(Input data source, Owner, Human check: empty on all three rows. Status: open.)

**What the contract did here:** row 3 has no proposal section because the RFP never names one for cost, so the cell says `not in source` rather than borrowing "Cost Proposal Form" from another RFP. The en dash in row 2's criterion is the RFP's en dash; the checker would fail a hyphen. Three sentences about scoring did not become rows and are listed under "Could not map": the comparative-evaluation sentence that applies to every row, the oral-presentation clause whose criteria are not in this document, and the three-additional-references item the RFP never ties to a criterion.

## Example 2: a two-stage state DOT RFP with sub-criteria

**Input:** Colorado Department of Transportation, US 50 Passing Lanes, Construction Manager services, Final RFP 4/14/26. 50 pages. `fixtures/codot-us50-passing-lanes-cm-rfp.source.txt`.

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

**Output** (`outputs/codot-us50-passing-lanes-cm-rfp.matrix.md`), six rows, two stages, each reconciling on its own:

| # | Stage | RFP criterion (their words) | Points | Evaluation criteria (what the scorer looks for) | Proposal section that answers it | Claude does |
|---|---|---|---|---|---|---|
| 1 | Proposal | A. CM Project Management Team [p32:9] | 10 [p32:9] | Composition and Commitment of the CM Project Management Team [p32:10] | Provide a graphic showing the CM’s organizational chart, complete with working titles for the team for the preconstruction phase. [p35:14-p35:15] | draft |
| 2 | Proposal | B. Contractor Capability [p35:28] | 10 [p35:28] | Prior Project Experience/Performance/References [p35:32] | Provide a summary of the Proposer’s previous project experience relevant to the general scope and construction value of work for this Project. [p35:33-p35:34] | draft |
| 3 | Proposal | C. Strategic Project Approach [p36:20] | 20 [p36:20] | Identify how the Proposer will manage schedule, budget, and incorporation of innovation. [p36:23-p36:24] | Provide a narrative that describes the Proposer’s project specific plan and approach to meeting the Project Goals. [p36:22-p36:23] | draft |
| 4 | Proposal | D. Approach to Risk, Schedule, and Pricing [p37:27] | 20 [p37:27] | Describe the techniques and tools that the Proposer will use to quantify the risk, establish a risk pool, and participate in management of the risk pools and contingencies. [p37:31-p37:32] | Define the key steps to risk management that the Proposer will employ. Describe how those steps will be applied to both the preconstruction and construction process. [p37:29-p37:30] | draft |
| 5 | Interview | A. Short Presentation [p38:12] | 15 [p38:12] | The interview presentation and question/answer scoring will be based on the following criteria: ● Project Understanding and goals, ● Project Approach, ● Project Innovation, ● Team Collaboration ● Communication Skills, and ● Understanding of CM/GC Project Delivery Method. [p38:28-p38:34] | not in source | prepare |
| 6 | Interview | B. Question and Answer Session with the Selection Panel [p38:19] | 25 [p38:19] | (same, [p38:28-p38:34]) | not in source | prepare |

Proposal stage: 60 stated [p32:8], 60 summed. Interview stage: 40 stated [p38:8], 40 summed.

**What the contract did here:** the interview rows get `prepare` rather than `draft`, and `not in source` for the answering section, because nothing written answers a live session. The 1-to-5 scoring scale in Appendix B, the Form B-1 pass/fail gate, and the Safety Record narrative that sits inside criterion A without its own points are all under "Could not map" with a reason each, so a proposal manager sees them and decides, rather than discovering them at Gate 1.

## Example 3: same issuer, different shape

**Input:** City of Tucker RFP 2026-008, Right-of-Way Maintenance. 30 pages. Same city as Example 1, a different service, a different scoring split (35 / 35 / 30), and the criteria carry descriptive sentences this time:

```
p14:15|        Proposed Management Plan and Approach – 35 points
p14:16|        The proposal shall outline the plan that the company will use to provide the most
p14:17|        effective delivery of the requested services as outlined in the Scope of Work.
p14:19|        Qualifications and Similar Project Experience of the Company and Staff – 35
p14:20|        Points
p14:27|        Cost Proposal – 30 points
```

**Output** (`outputs/tucker-ga-rfp-2026-008-row-maintenance.matrix.md`): three rows, the same twelve columns as Example 1, sum 100 against stated 100 [p14:11]. Row 1's evaluation criteria is now the RFP's own sentence [p14:16-p14:17] instead of the general one, because this RFP supplies one. Row 2's criterion breaks across two source lines ("– 35" then "Points"); the criterion cell cites p14:19 and the checker finds the words there. One scoring sentence buried in the scope of work, "Age and condition of equipment will be factored into contractor scoring for these services." [p5:36], carries no points and no criterion, so it is under "Could not map" for a person to place.

## The bar, checked

- **Same shape across inputs:** `tests/test_matrix.py::test_same_shape_across_inputs` asserts every row in every shipped matrix has exactly the twelve keys.
- **Every fact traces:** `python3 tools/check_matrix.py outputs/<any>.matrix.json` exits 0 on all three, and exits 1 when a test paraphrases a criterion, respells a word, invents a points figure, or fills a human column.
- **Missing is marked, not filled:** three `not in source` cells across the three outputs, each where the RFP is silent.
