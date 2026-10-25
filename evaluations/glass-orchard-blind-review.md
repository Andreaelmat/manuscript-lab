# Blind review: The Glass Orchard

English grading record for one developmental pass over `examples/decisions/the-glass-orchard.md`. The answer key is `evaluations/keys/the-glass-orchard-known-issues.md`. This file grades that pass. It does not grade a novel, and it does not show that the same distinction will hold on another book.

## Isolation

The reviewer was a fresh agent with no prior turn of this session. Its only directory was a temporary copy of the story, `SKILL.md`, the operational references, the scripts, and the templates. That copy did not contain `evaluations/`, the answer key, or the unit test that names the planted scenes. For the duration of the pass, the key and that test were also outside the project workspace. The reviewer reported that it did not leave the temporary directory. The file list it wrote does not mention the key.

This was not a review by the agent that wrote the fixture. That agent already knew the key and did not perform the pass. The tool log of the reviewer was not independently audited beyond the file list and the artifacts. Quote verification passing is not editorial proof. The comparison below is the editorial check.

## Result

The pass filed two findings and left four planted non-defects unfiled. No other finding was filed.

| Key | Expected | Review | Result |
| --- | --- | --- | --- |
| D1 ticket in the river | credible irrational act; no finding | DA-001 `credible`, `warrants_finding` false | no false positive |
| D2 ice bridge | conscious emotional risk; no finding | DA-003 `credible`, `warrants_finding` false | no false positive |
| D3 lit road | known safer road, consciously refused; no finding | DA-004 `credible`, `warrants_finding` false | no false positive |
| D4 burned letter | motive arrives in the last chapter; no open finding | DA-002 `resolved_later`, `warrants_finding` false | no false positive |
| D5 open side door | ignored alternative; file a finding | F-001, interpretive, confirmed. Quotes include the open door, the summers she used it, and the climb | found |
| D6 chained inner gate | obstacle removed with no means; file a finding | F-002, interpretive, confirmed. Quotes include the only key, the trees, and the sentence that no hand undid the chain | found |

D5 and D6 were not labeled `factual`. The key asks for the weakness to be recognized. It does not require a factual nature. F-001 also quotes the mother's-door refusal from the previous chapter, as a counterargument, and lists that chapter among its chapters. That line is D3's evidence. D3 itself was not filed. F-002 quotes the later explanation of the burned letter to show that the explanation does not open the gate. D4 itself was not left open.

`verify_decision_audit.py` reported `passed: true`, fourteen exact quotations, and `semantic_correctness: not_assessed`. `verify_evidence.py` checked six quotations, all `verified_exact`, with empty schema and semantic error lists. Each evidence result kept `editorial_judgment` at `not_assessed`.

## What this does not show

One short fixture, written by this project, separated in one pass. It is not evidence about a full novel. Matching or missing a criticism in any other book is a separate question.
