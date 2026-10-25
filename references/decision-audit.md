# Decision and motivation audit

Read this file only during a `full` or `developmental` review, when you are judging a decision that matters. A `continuity` review and a `dialogue-style` review do not require it. A `survey` may skip it.

The question is whether the text makes the choice credible and effective. It is not whether the character chose the best available action. Do not score the decision.

Use the narrative fact ledger to recover what was stated earlier. What the reader knows is not what the character knows. Put the character's information in `information_available`. Put anything the reader knows and the character does not in `withheld_from_character`. Do not treat the second as a reason the character should have acted otherwise.

## Select the nodes

Record a decision only when the plot turns on it: someone commits, refuses, or passes an obstacle that had been made to matter. Leave ordinary movement unrecorded. An empty `decisions` list is valid.

For each recorded decision, name the character, the choice, the objective, the information available at that moment, the explicit motives, the implicit motives the text actually supports, the concrete obstacles, the emotional conflict, the consequences, and any later repercussions. Tie every claim to paragraph ids and a verbatim quotation.

## Do not penalize

Do not file a finding for:

- a choice that is not optimal
- a risk the person accepts with open eyes
- an emotional or impulsive act the scene supports
- a morally ugly act the scene supports
- a mistake that follows from incomplete information
- a choice whose motive arrives in a later chapter

Those belong in the audit as `credible` or `resolved_later`, with `warrants_finding` false.

## When a finding is warranted

File a finding only when a significant weakness remains after the checks below.

1. Re-read the scene from the index, not from the ledger alone.
2. Name the objective the text gives the person.
3. List alternatives the text actually puts within reach. Do not invent one that appears only in a later chapter, or one the person could not perceive.
4. Mark whether the person knows each alternative.
5. Look for an emotional or implicit motive that would make this choice the one they would make.
6. Look for a consequence that shows the book knows the choice cost something.
7. Look in later chapters for a motive, a constraint, or a reveal that explains it.
8. If the weakness is still significant, `warrants_finding` may be true. If not, leave it false.

`under_motivated` means the scene requires a choice and does not support why this person makes it. `obstacle_unexplained` means a concrete obstacle is declared and then is gone, with no means on the page. A locked door and a missing key are not the same problem as a person who will not turn the key they are holding.

## Alternatives

`consciously_refused` requires `known_to_character`. The person saw the safer road and did not take it. That is not, by itself, a defect.

`ignored` requires `known_to_character` or `reasonably_perceivable`. An alternative known only to the reader is not an alternative the character ignored.

## Check

The audit is optional to write. If you write `decision-audit.json`, check it:

```text
python "<skill-dir>/scripts/verify_decision_audit.py" --index "<work>/index.json" --audit "<work>/decision-audit.json" --output "<work>/decision-check.json"
```

The script checks shape, paragraph order, and quotations. `semantic_correctness` stays `not_assessed`. It does not decide whether the motive is good. A passed check is not a finding, and it is not a score.
