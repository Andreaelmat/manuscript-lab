# Editorial report

Omit this instruction block from the delivered report. Keep the twelve sections below, in this order, even when a section is short. If a section has nothing to add, write "None." and one sentence explaining why. Do not add a thirteenth section. Do not give the novel a numeric score, a star rating, or a market valuation.

Write the report in the requested language. When that language is not English, translate the headings and keep their meaning and order. Italian equivalents:

| English heading | Italian heading |
| --- | --- |
| Editorial synthesis | Sintesi editoriale |
| Strengths | Punti di forza |
| Priority problems | Problemi prioritari |
| Structure | Analisi della struttura |
| Characters | Analisi dei personaggi |
| Pace and tension | Ritmo e tensione |
| Dialogue and style | Dialoghi e stile |
| Narrative continuity | Continuità narrativa |
| Chapter notes | Osservazioni per capitolo |
| Contested or rejected observations | Osservazioni contestate o respinte |
| Suggested interventions | Interventi suggeriti |
| Limits of the analysis | Limiti dell'analisi |

Cite every direct manuscript quotation, including those inside an explanation, a counterargument, or a chapter note, like this:

> [exact contiguous quotation]
>
> `[paragraph-id]`, [chapter id and title, or "unsegmented"]

The quotation must occur in that paragraph. Do not start it in the middle of a word or immediately after a quotation mark you omitted. If you mention the manuscript in the report's own language, paraphrase it and do not wrap the paraphrase in quotation marks or guillemets.

After `scripts/check_report.py` passes, a verified quotation still does not prove the interpretation. State that once, in the limits. `scripts/score_findings.py` may be summarized as a count of confirmed factual findings. That count is not a score of the novel.

Suggested interventions name a narrative job. They do not replace the author's prose.

---

# Editorial report: [manuscript title]

- Manuscript: `[file name]`
- SHA-256: `[manuscript sha256]`
- Mode: `[mode]`
- Depth: `[depth]`
- Scope: `[chapters, or "whole confirmed text"]`
- Report language: `[language]`

## 1. Editorial synthesis

[What the book is doing, what is working, and the few problems that most affect a reader's experience. No score.]

## 2. Strengths

[Passages or patterns worth protecting, each with a location. "None." is allowed.]

## 3. Priority problems

[The highest-value findings only. For each: finding id, why it matters, and the quotations.]

## 4. Structure

[How the book is built, including the opening and the ending. Relate scenes to their job in the book.]

## 5. Characters

[Wants, pressure, change, and any attribute that the text treats as both stable and incompatible.]

## 6. Pace and tension

[Where pressure starts, stalls, and changes. Do not call a book slow without a location.]

## 7. Dialogue and style

[Voice, differentiation, repetition, and exposition. Separate motif from restatement. Respect consistent stylistic choices.]

## 8. Narrative continuity

[Factual clashes that survive the end of the in-scope text. Also name apparent clashes that a later passage resolves.]

## 9. Chapter notes

[Only chapters that need a local observation. For a deep review, include every in-scope chapter, including chapters with no recommended change.]

### [Chapter id and title]

[Observation, or "No change recommended." plus the reason.]

## 10. Contested or rejected observations

[Findings whose verification status is `downgraded` or `rejected`, with the counterevidence. Include "None." when every filed finding still stands.]

## 11. Suggested interventions

[Directions tied to finding ids, in priority order. No replacement scenes.]

## 12. Limits of the analysis

- Segmentation: `[method, and whether it was ambiguous]`
- Unread or out-of-scope text: `[what was not read]`
- Quote check: `[counts from verification.json]`
- Normalized quotations: `[ids, or "none"]`
- Independent reviewer: `[not requested / not available / model name]`
- Same-model re-check: `[yes or no; a same-model pass is not independent]`
- Primary model: `[name, or "unspecified"]`
- Source file re-hashed: `[yes or no]`
- This report does not score the novel. Verified quotations are not the same thing as a correct editorial judgment.
