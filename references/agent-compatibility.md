# Agent compatibility

Read this file when installing the skill or when a client does not list it. Do not load it during a literary review.

Manuscript Lab is one skill directory. Cursor, Codex, and Claude Code discover that directory from different parents. The installer points those parents at the same files. It does not keep a separate editorial implementation per client.

The package follows the Agent Skills specification: `SKILL.md` starts with YAML frontmatter, and `name` and `description` are present. Optional spec fields used here are `license`, `compatibility`, and `metadata`. Proprietary fields are not required. In particular the skill does not set invocation flags, model overrides, hooks, or tool allowlists.

Confirm the paths below against the current client documentation if an installer path is rejected. The layout was checked against the Agent Skills specification, Cursor's Agent Skills documentation, OpenAI's Codex skills documentation, and Claude Code's skills documentation.

## Where each client looks

| Client | Project skill | User skill |
| --- | --- | --- |
| Cursor | `.cursor/skills/manuscript-lab/` | `~/.cursor/skills/manuscript-lab/` |
| Codex | `.agents/skills/manuscript-lab/` | `~/.agents/skills/manuscript-lab/` |
| Claude Code | `.claude/skills/manuscript-lab/` | `~/.claude/skills/manuscript-lab/` |

Cursor also discovers `.agents/skills/`, `.claude/skills/`, and `.codex/skills/` in the project, and the user-level versions of those directories. Codex walks upward from the working directory to the repository root looking for `.agents/skills/`. Claude Code loads `.claude/skills/` from the working directory and from parent directories up to the repository root.

The folder that contains `SKILL.md` must be named `manuscript-lab`, because `name` must match the parent directory.

## Differences that matter

- Installing the skill into all three project directories can make Cursor list it more than once, because Cursor scans the Cursor, Codex, and Claude directories. Codex does not merge two skills that share a name; both can appear. Claude Code loads a skill once when several locations are symlinks to the same directory.
- Claude Code substitutes argument placeholders and its own skill-directory variable inside a skill body. This skill does not use those tokens. Do not add them. Cursor and Codex do not document that substitution.
- Claude Code accepts extra frontmatter keys of its own. Packaging the same file for claude.ai rejects keys outside the open specification. This skill stays inside the specification so one file serves both.
- Cursor can hide a skill until it is named explicitly, or tint it as a mode. Those controls are client extensions. Leaving them unset lets each client apply the skill when the request matches the description.
- None of the three clients is a Python dependency. The scripts use the standard library and run from any working directory when invoked by absolute path.
- Editorial judgments are not guaranteed to match across models or clients. The shared part is the procedure, the index, and the quotation check.

## What the compatibility tests do

`tests/test_compatibility.py` checks the package against those published constraints: manifest fields, directory name, relative resources, installer destinations, and the absence of client-only requirements. It does not launch Cursor, Codex, or Claude Code. A passing test means the package is shaped so those clients can discover it. It does not mean a live session produced a good review.
