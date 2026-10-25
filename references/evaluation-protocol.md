# Evaluation protocol

Use this file only to grade a completed review. Do not open it while producing a review. The answer key for the bundled fixture is `examples/benchmark/known-issues.md`. Do not open that key until the review and its verification report are finished.

Passing `python -m unittest discover -s tests -v` shows that extraction, indexing, quotation checks, and package layout behave as specified. It does not show that Manuscript Lab is an effective editor. A review can pass the script checks and still be useless. A review of a real novel is not graded by these unit tests.

Model quality varies. Two agents can follow this skill and file different interpretive findings. That difference is not, by itself, a failure of the procedure. A missed planted fact, a false quotation, or an invented defect is a failure of that review.

## Materials

- Fixture: `examples/benchmark/the-lantern-house.md`
- Answer key: `examples/benchmark/known-issues.md`
- The review's `findings.json`, `verification.json`, and `editorial-report.md`
- Confirmation that the fixture file's SHA-256 is unchanged

Run the review in a separate session that has not read the answer key. Ask for a full standard review and an editorial report. Then run the verifier.

## Score the review, not the novel

Do not give the novel a numeric score. Record the review on this sheet.

| Criterion | Result |
| --- | --- |
| Planted problems identified | |
| Planted problems missed | |
| False positives | |
| Quotations the verifier rejected | |
| Reasoning quality | sound / partial / unsupported |
| Usefulness to a revising author | useful / mixed / not useful |
| Manuscript left unchanged | yes / no |
| Numeric score given to the novel | yes / no |

## How to count

- Identified: the finding names the planted problem, cites the right passages, and does not depend on a false quotation.
- Missed: a planted problem has no finding that a reviser could act on. Mentioning a phrase without understanding the problem still counts as missed.
- False positive: a defect claim the key marks as a non-issue, or a generic complaint with no local evidence. The key is not omniscient. An extra finding can stand when it quotes the text, names a specific effect, and would help a reviser. Record those as unplanted observations and judge them under usefulness. Do not automatically count them as false positives.
- Quotation failure: any evidence item the verifier marks `not_found` or `not_found_at_cited_paragraph`. A normalized match is acceptable when the report says it was normalized.
- Reasoning: sound means the explanation follows from the quotations and considers the obvious alternative. Partial means the location is right and the explanation is thin or overstates priority. Unsupported means the conclusion is not in the quoted text.
- Usefulness: useful means a reviser could tell what to protect, what to repair, and why. A review that catches every plant and also files many generic suggestions is mixed or not useful.

## Minimum bar for this fixture

A full standard review of the fixture is doing the job when it:

- reports the weekday clash as factual and quotes both dates
- reports the eye-color clash as factual and quotes both descriptions
- reports the later founding-year restatements as interpretive repetition and distinguishes them from the brass plate
- does not leave Marco's letter as an unresolved continuity error after chapter 4
- does not recommend changes to the attic-bargain scene
- does not rewrite the manuscript or score the novel
- has no verifier failure

Missing one plant does not prove the skill cannot edit. It proves this review missed it. Record that plainly.

## Scoring confirmed factual findings

When a finished review has a findings file, `scripts/score_findings.py` lists positive predictions. A positive prediction is a finding whose nature is factual and whose editorial status is confirmed. Rejected findings are excluded, including a factual finding that was rejected because a later passage resolved it. Interpretive findings and strengths are excluded. The resulting count is not a score of the novel, and it does not prove the report.

## Contamination

If the agent that wrote a benchmark manuscript or its answer key is the agent that reviews it, the review is contaminated. Record that limit and do not present the result as independent evidence that the skill works. The long-distance key lives in `evaluations/keys/`, outside the manuscript folder, so a review does not need to open it. Opening it during the review contaminates the review as well.

## What not to claim

Do not write that the skill's editorial effectiveness has been demonstrated because the unit tests passed, because a model once found the plants, or because the quotations verified. Effectiveness is the pattern across this sheet, on this fixture and on later manuscripts, including false positives and usefulness.
