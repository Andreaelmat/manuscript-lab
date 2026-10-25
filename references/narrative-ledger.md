# Narrative fact ledger

Read this file only while recording or checking narrative facts. It does not replace reading the manuscript.

Independent reviews of a long novel agreed more often when a later passage explained an apparent clash, and diverged when the claim was interpretive. A prose ledger cannot be queried or checked against paragraph ids. This file is the structured replacement. It is a retrieval aid. It is not a database, and it does not decide that two statements conflict.

## When to keep one

Keep `narrative-ledger.json` for a `full` or `continuity` review at `standard` or `deep` depth. A `survey` or `dialogue-style` review may skip it. Do not open a sixth mode for it.

Record a fact when a later finding might need to find it again: a date, an age, a death, an object’s location, a piece of knowledge, or a later revelation. Do not record every sentence.

## What an entry is

Each entry is one claim, tied to the paragraphs that state it.

- `statement` is your wording of the claim. It is not a substitute for the quotation.
- `event_time` is when the event happens in the story. `narration_time` is when the text states it. Leave either empty when the text does not distinguish them.
- `source` is `narrator`, `dialogue`, `memory`, `document`, or `inference`.
- `claim_kind` is one of:
  - `narrated_fact`: the narration presents it as so.
  - `potentially_false_statement`: a person says it, and the text does not establish it.
  - `character_knowledge`: what a person knows or does not know at that point.
  - `hypothesis`: your inference. This is not a fact.
  - `withheld_from_reader`: the book deliberately keeps something back. Say what shows the withholding.
- `certainty` is `certain`, `contested`, `revised`, or `unknown`.
- `incompatible_with` names other entry ids that cannot all stand, after you have read both passages. Do not link them because a summary made them look close.
- `revised_by` names a later entry that explains or replaces this one. Set `certainty` to `revised` when you do. Do not confirm an open factual defect for a claim that a later entry revises.

A hypothesis, a potentially false statement, or an inference cannot be `certain`. The checker rejects that combination. An empty `entries` list is valid when you have not yet recorded a claim.

## How to check it

Write the ledger yourself. Then run:

```text
python "<skill-dir>/scripts/verify_ledger.py" --index "<work>/index.json" --ledger "<work>/narrative-ledger.json" --output "<work>/ledger-check.json"
```

The script checks the schema, the manuscript hash, paragraph ids, and quotations. `semantic_correctness` stays `not_assessed`. `full_reading_established` stays false: listing a chapter id does not mean the chapter was read. If a quotation fails, fix it or drop the entry. Do not treat a verified quotation as proof of the claim.

Before you confirm a continuity finding, look up the entities in the ledger and re-read the cited paragraphs from `index.json`. If `revised_by` points at a later passage, the finding’s `editorial_status` is `rejected` unless the revision itself fails.

## What not to do

Do not fill a gap with a plausible fact. Do not copy a character’s speech into `narrated_fact` unless the narration adopts it. Do not let the ledger become the text you judge from. The novel remains the evidence.
