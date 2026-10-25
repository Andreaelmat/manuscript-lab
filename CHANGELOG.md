# Changelog

Public releases use semantic versions. `v0.1.0` is the first public snapshot. The procedure recorded in `SKILL.md` is methodology `1.1.1`. Those two numbers name different things: the release is the published package, and the methodology version is the editorial procedure inside it.

## 0.1.0 — 2026-10-25 — Experimental

First public release of Manuscript Lab, an Agent Skill for evidence-grounded editorial review of fiction manuscripts.

The package indexes DOCX, TXT, and Markdown with the Python standard library. A review can run in `full`, `developmental`, `continuity`, `dialogue-style`, or `critical-verification` mode, at `survey`, `standard`, or `deep` depth. A full or continuity review can keep a narrative fact ledger. A full or developmental review can keep a decision audit. Quotation checks are separate from editorial judgment. Findings remain compatible with the earlier record shape.

This release does not claim that a review will find every defect, or that a verified quotation makes an interpretation true. Unit tests check the scripts. They do not certify a novel.

### Known limits at publication

- Python 3.10 and newer is the documented requirement. The suite was executed locally on Python 3.12.10. The GitHub Actions workflow also requests 3.10; that job has not run until the repository is on GitHub.
- Compatibility tests check the Agent Skills package shape and the installer paths. They do not launch Cursor, Codex, or Claude Code.
- Chapter boundaries come from explicit chapter titles, or from two or more Word Heading 1 paragraphs. Other heading styles stay candidates.
- There is no git history in the publication snapshot. Private diagnostic files were kept outside this directory and were never committed.
