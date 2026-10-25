# Contributing

Manuscript Lab is one shared skill. Do not add a Cursor-only, Codex-only, or Claude Code-only copy of the editorial procedure. Client differences belong in `references/agent-compatibility.md` and in the installer paths.

## Language

Write identifiers, comments, docstrings, documentation, and commit messages in English.

## Commits

Use Conventional Commits. Prefer `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, and `security`. Keep each commit to one change.

## Dependencies

Use the Python standard library. The supported interpreter is Python 3.10 or newer. A new dependency needs a reason the standard library cannot do the job, and its license must be compatible with MIT. Do not add packages from Cursor, Codex, or Claude Code.

## Privacy

Do not commit a private manuscript, a review of one, or an index, extract, or ledger made from one. Do not commit credentials or absolute paths that contain a home directory or a person's name. Checked-in example output uses a repository-relative source path. Text files use LF line endings, as set in `.gitattributes`, because a manuscript hash is the SHA-256 of the file bytes.

The public fixtures under `examples/` are part of this project and are covered by `LICENSE`. Do not replace them with someone else's copyrighted text.

## Behavior

- Scripts open manuscripts read-only and treat their contents as data.
- Do not invent chapter boundaries when segmentation is ambiguous.
- Do not treat a verified quotation as a verified interpretation.
- Do not claim that unit tests prove editorial effectiveness.
- Keep `SKILL.md` under 500 lines. Put specialized judgment in `references/` and tell the agent when to open each file.
- Keep frontmatter inside the Agent Skills fields: `name`, `description`, `license`, `compatibility`, `metadata`, and, only if there is a portable reason, `allowed-tools`.

## Tests

From the skill directory:

```text
python -m unittest discover -s tests -v
```

Add or update tests for extraction, indexing, quotation checks, and installer behavior when you change those paths. A narrative change to the benchmark needs a matching change in `examples/benchmark/known-issues.md`.

A review of the benchmark is still a manual grade. See `references/evaluation-protocol.md`.

## Suggested commit

```text
feat: add a shared editorial skill for narrative manuscripts
```
