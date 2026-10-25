# Manuscript Lab

Open-source Agent Skill for evidence-grounded editorial review of fiction manuscripts. It helps an agent read a long narrative, separate a possible factual problem from an interpretation, and check quotations against the original text.

**Public release:** `v0.1.0` (Experimental).
**Methodology version** recorded in `SKILL.md`: `1.1.1`.

Manuscript Lab is not a human editor. It does not guarantee that every error will be found, and it does not certify the quality of a novel. Two models can disagree on an interpretive finding. The shared part is the procedure, the index, and the programmatic quotation check.

## The problem it addresses

A long manuscript is hard to hold in one reading. Dates, objects, and knowledge drift. A character's choice can look unmotivated because the motive is missing, or because the reader wanted a safer choice. A review that rewrites the book, or that treats every odd decision as a defect, is a different job from a diagnosis.

This skill keeps the manuscript unchanged and asks the agent to attach each observation to a paragraph id and a verbatim quotation.

## What is available

- Indexing of DOCX, TXT, and Markdown, with stable paragraph ids.
- Five review modes and three depths, described below.
- An optional narrative fact ledger for full and continuity reviews.
- An optional decision audit for full and developmental reviews.
- JSON findings that separate the kind of claim, the quotation check, and the editorial status.
- A Markdown report template with twelve sections and no numeric score of the novel.
- Scripts that check quotations, report quotations, ledger shape, decision-audit shape, and the finding count rule.
- An installer that points Cursor, Codex, and Claude Code at one skill directory.
- Public fixtures for continuity and for decision audits. Their answer keys grade a finished review. They are not an input to the review.

Not included, and not claimed: a web application, a grammar checker, a rewriting engine, a database, a hosted API, or a guarantee of editorial correctness.

## Manuscript formats

| Format | How it is read |
| --- | --- |
| `.docx` | Visible document text, Heading styles, and table cells. Footnotes and headers are not indexed. Revisions marked deleted are skipped. A file that declares a document type or an XML entity is refused. |
| `.txt` | UTF-8, UTF-16 with a BOM, or Windows-1252. Blank lines split paragraphs. |
| `.md` | The same paragraph split. ATX and setext headings keep their visible text. |

Chapter boundaries are explicit titles such as `Chapter 1`, `Capitolo I`, or the equivalent with an Arabic or Roman number. Two or more Word Heading 1 paragraphs also become chapters. Any other heading stays a candidate. If segmentation is ambiguous, the review uses paragraph ids and says so.

Word counts in the index are navigation counts (`\S+` tokens). They are not a contractual word count.

## Requirements

- Python 3.10 or newer on Windows, macOS, or Linux. The standard library is the only dependency. There is no `requirements.txt` and no package to install. On Windows, `py -3` is an acceptable launcher. On macOS and Linux, `python3` is the same command.
- An agent that can read files and run Python. Cursor, Codex, and Claude Code can load the same directory. No client SDK is required.
- The local test suite was run with Python 3.12.10. The workflow in `.github/workflows/tests.yml` also requests 3.10. That job runs after the repository is on GitHub.

The scripts do not need a network connection or an API key. The agent you use may still send the manuscript to its model provider. See [Privacy](#privacy).

## Installation

The installable directory is this folder, and it must stay named `manuscript-lab`, because the Agent Skills `name` has to match the parent directory.

From this directory, check the package:

```text
python scripts/install_skill.py --check
```

Install for one client. A link stays current when this directory changes. Use `--copy` when a link is not available. Copies go stale until you install again with `--force`.

```text
python scripts/install_skill.py --agent cursor --scope project --project /path/to/your-book
python scripts/install_skill.py --agent codex --scope user
python scripts/install_skill.py --agent claude --scope project --project /path/to/your-book
```

| Client | Project skill | User skill |
| --- | --- | --- |
| Cursor | `.cursor/skills/manuscript-lab/` | `~/.cursor/skills/manuscript-lab/` |
| Codex | `.agents/skills/manuscript-lab/` | `~/.agents/skills/manuscript-lab/` |
| Claude Code | `.claude/skills/manuscript-lab/` | `~/.claude/skills/manuscript-lab/` |

Cursor also scans `.agents/skills/` and `.claude/skills/`. Installing all three clients into one project can list the skill more than once in Cursor. The installer prints that note when `--agent all` is used with a project scope. The compatibility tests check these paths and the manifest. They do not launch the three applications. Details are in `references/agent-compatibility.md`.

## Using it

Open the project where the skill is installed and ask in ordinary language. You can set the report language, the mode, the depth (`survey`, `standard`, or `deep`), and a chapter range.

- Analyze this novel as a professional editor.
- Run a full editorial review. Produce an editorial report without changing the text.
- Check inconsistencies between chapters.
- Look at structure, tension, and motivation.
- Analyze the dialogue and the characters' voices.
- Critically verify these earlier notes.

The agent writes `extract.json`, `index.json`, `index.md`, `findings.json`, `verification.json`, and `editorial-report.md` under `manuscript-lab-output/` next to the manuscript, or under a directory you name. The manuscript file is opened read-only.

You can index a file yourself. Run the commands from any working directory by passing absolute paths. The scripts find their schemas from their own location.

```text
python scripts/index_manuscript.py path/to/novel.md --output index.json --outline index.md
python scripts/verify_ledger.py --index index.json --ledger narrative-ledger.json --output ledger-check.json
python scripts/verify_decision_audit.py --index index.json --audit decision-audit.json --output decision-check.json
python scripts/verify_evidence.py --index index.json --findings findings.json --output verification.json
python scripts/check_report.py --index index.json --findings findings.json --report editorial-report.md --output report-check.json
python scripts/score_findings.py --findings findings.json --output score.json
```

`score.json` counts confirmed factual findings and excludes rejected ones. That count is not a score of the novel.

## Review modes

| Mode | What the agent concentrates on |
| --- | --- |
| `full` | The whole editorial pass: structure, character, pace, dialogue, continuity, and a report. |
| `developmental` | Structure, tension, motivation, scene function, and revelations. |
| `continuity` | Dates, objects, knowledge, and events that cannot all be true. |
| `dialogue-style` | Dialogue, voice, repetition, and prose rhythm. |
| `critical-verification` | A second look at notes or findings that already exist. |

A continuity review and a dialogue-style review do not require the decision audit. A survey or a dialogue-style review may skip the ledger.

## Depth

- `survey` reads the index, the opening, the ending, and the first and last three body paragraphs of each in-scope chapter. It files at most five findings and names what was not read.
- `standard` reads every in-scope paragraph before a global judgment.
- `deep` does a standard reading, writes a note for every in-scope chapter, and records a counterargument for every finding that stays confirmed.

## Narrative fact ledger

During a `full` or `continuity` review at `standard` or `deep` depth, the agent keeps a ledger of claims that later continuity checks may need: what was narrated, what a character said that may be false, what a character knows, and what is still a hypothesis. Each entry points at paragraph ids. The script `verify_ledger.py` checks the shape and the quotations. It does not extract the facts, and it does not prove that two claims conflict. `full_reading_established` in its output stays false. Listing a chapter id does not mean that chapter was read in full.

The shape is `templates/narrative-ledger.json`. The procedure is `references/narrative-ledger.md`.

## Decision and motivation audit

During a `full` or `developmental` review at `standard` or `deep` depth, the agent audits the decisions that turn the plot. The question is whether the text makes the choice credible. It is not whether the character chose the best available action.

A choice can be irrational, risky, emotional, selfish, or based on incomplete information and still be credible. A motive that arrives in a later chapter is not an open defect. A finding is for a choice the narration needs and does not support, or for a declared obstacle that disappears without a means. There is no numeric score of a decision.

`verify_decision_audit.py` checks ids, alternatives, and quotations. `semantic_correctness` stays `not_assessed`. A passing check does not prove the motive.

The shape is `templates/decision-audit.json`. The procedure is `references/decision-audit.md`.

## Quotation checks

A finding has three separate layers:

- `nature`: `factual`, `interpretive`, or `strength`.
- `quote_check` on each quotation: filled by `verify_evidence.py`. The script's `editorial_judgment` stays `not_assessed`.
- `editorial_status`: `unreviewed`, `confirmed`, `downgraded`, or `rejected`. That status is the agent's judgment after the critical procedure.

`verify_evidence.py` accepts an exact quotation or a normalized one (compatible quotes, dashes, and whitespace) and says which. A quotation found in a different paragraph is not verified. `check_report.py` applies the same standard to direct quotations in the report. Neither script decides whether the interpretation is right.

Older findings may use `judgment_type` and `verification_status`. New files should use `nature` and `editorial_status`. Both shapes still validate.

## Example output

`templates/findings.json` is a format example bound to the public fixture `examples/benchmark/the-lantern-house.md`. It is not a finished review. One factual item and one strength look like this:

```json
{
  "id": "F-001",
  "nature": "factual",
  "editorial_status": "unreviewed",
  "quote_check_on_evidence": "unchecked until verify_evidence.py runs",
  "title": "12 March is both Tuesday and Wednesday"
}
```

A saved review of that same public fixture, including the Italian report requested for that run, is in `examples/benchmark/manuscript-lab-output/the-lantern-house/`. The report's own quotation check still fails on one paraphrase wrapped in quotation marks. That failure is kept on purpose. It shows the checker catching a span that is not in the manuscript. It does not show that the rest of the report is editorially right.

## Benchmarks

Grade a finished review with `references/evaluation-protocol.md`. Do not open an answer key while producing the review. A review by the agent that wrote the fixture is contaminated. A green unit-test run is not that grade.

| Fixture | What a grading pass can use it for | Answer key |
| --- | --- | --- |
| `examples/benchmark/the-lantern-house.md` | A short continuity and structure fixture. The key sits beside the story for the original test. | `examples/benchmark/known-issues.md` |
| `examples/long-distance/the-mile-road.md` | Contradictions spread across 18 chapters. | `evaluations/keys/the-mile-road-known-issues.md` |
| `examples/decisions/the-glass-orchard.md` | Credible irrational, emotional, and consciously refused choices, beside an ignored alternative and an unexplained obstacle. | `evaluations/keys/the-glass-orchard-known-issues.md` |

`examples/ambiguous-coast.md` is a heading fixture. Its headings are not confirmed chapters.

Grading notes for the public fixtures live under `evaluations/`. During a review, do not open that directory.

## Limits

- The skill does not replace a human editor.
- A survey does not read the whole book. A partial chapter list must say what was not read.
- Explicit chapter titles, or two or more Heading 1 paragraphs, are the only automatic chapter boundaries.
- Deterministic checks can verify quotations, ids, and record shape. They cannot verify that an interpretation is fair.
- The same model checking its own findings is a re-check, not an independent review.
- The public fixtures are short, and this project wrote them. A match on a fixture is not proof about another book.
- Stronger long-form coverage, a richer critical-verification pass, and comparison across models are future work. See [Roadmap](#roadmap).

## Privacy

The Python scripts do not call an external API. They read the manuscript as data and write local artifacts.

The agent that follows the skill can still process the manuscript through its own provider, under that provider's settings and terms. This project cannot promise that a manuscript stays entirely on your machine.

Do not commit private manuscripts, private reviews, or indexes of them. The public repository is only this skill, its tests, and its original fixtures.

## Roadmap

These items are not in `v0.1.0`:

- Advanced critical verification, beyond the current confirm, downgrade, and reject procedure.
- Cross-model editorial comparison, when a second model is actually available.
- Stronger long-form reading coverage, so a deep pass over a full novel is easier to audit.
- More blind editorial benchmarks that this project's own authors did not write.
- Further work on semantic checks. Quotation and shape checks will stay separate from interpretive judgment.

No dates are attached. A later release will say what landed.

## License and contributing

MIT. See `LICENSE`. The scripts, the references, and the original fixtures in `examples/` are part of that grant. There are no third-party runtime dependencies.

Contributions, commit style, and the privacy rule for private manuscripts are in `CONTRIBUTING.md`. Vulnerability reports are in `SECURITY.md`.
