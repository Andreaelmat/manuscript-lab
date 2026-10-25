"""Install the same Manuscript Lab skill into Cursor, Codex, or Claude Code.

The installer links the canonical skill directory. It does not copy the
editorial logic into a second implementation.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from common import skill_root
from skill_manifest import validate_skill_directory


AGENTS = ("cursor", "codex", "claude")
PROJECT_PARENTS = {
    "cursor": Path(".cursor") / "skills",
    "codex": Path(".agents") / "skills",
    "claude": Path(".claude") / "skills",
}
USER_PARENTS = {
    "cursor": Path.home() / ".cursor" / "skills",
    "codex": Path.home() / ".agents" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}
SKILL_NAME = "manuscript-lab"


class InstallError(Exception):
    """The skill could not be installed."""


def destination(agent: str, scope: str, project: Path | None = None) -> Path:
    """Return the install path for one agent and scope.

    Args:
        agent: ``cursor``, ``codex``, or ``claude``.
        scope: ``project`` or ``user``.
        project: Project root for project scope.

    Returns:
        Destination directory named ``manuscript-lab``.

    Raises:
        InstallError: The agent, scope, or project path is invalid.
    """
    if agent not in AGENTS:
        raise InstallError(f"Unknown agent {agent!r}. Expected one of: {', '.join(AGENTS)}.")
    if scope == "user":
        return USER_PARENTS[agent] / SKILL_NAME
    if scope != "project":
        raise InstallError("Scope must be 'project' or 'user'.")
    if project is None:
        raise InstallError("Project scope requires a project directory.")
    root = project.expanduser().resolve()
    if not root.is_dir():
        raise InstallError(f"Project directory not found: {root}")
    return root / PROJECT_PARENTS[agent] / SKILL_NAME


def install_skill(
    agents: list[str],
    scope: str,
    project: Path | None = None,
    copy: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> list[str]:
    """Link or copy this skill into each requested agent directory.

    Args:
        agents: Agent ids. ``all`` is expanded by the caller.
        scope: ``project`` or ``user``.
        project: Project root for project scope.
        copy: When True, copy files. When False, symlink or junction them.
        force: Replace an existing install at the guarded destination.
        dry_run: Report destinations without writing.

    Returns:
        Lines describing each destination.

    Raises:
        InstallError: Validation, path safety, or linking fails.
    """
    source = skill_root()
    errors = validate_skill_directory(source)
    if errors:
        joined = "\n".join(errors)
        raise InstallError(f"Skill package is invalid:\n{joined}")
    messages: list[str] = []
    for agent in agents:
        target = destination(agent, scope, project)
        messages.append(_install_one(source, target, copy=copy, force=force, dry_run=dry_run))
    return messages


def main(argv: list[str] | None = None) -> int:
    """Run the installer.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        ``0`` on success, ``1`` when ``--check`` fails, ``2`` on install errors.
    """
    try:
        return _run(argv)
    except InstallError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _run(argv: list[str] | None) -> int:
    """Parse arguments and install or validate.

    Args:
        argv: Arguments excluding the program name.

    Returns:
        Process exit code.
    """
    parser = _parser()
    args = parser.parse_args(argv)
    if args.check:
        errors = validate_skill_directory(skill_root())
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        print(f"ok: {skill_root()}")
        return 0
    agents = _agents(args.agent)
    if args.agent == "all" and args.scope == "project":
        print(
            "note: Cursor also scans .agents/skills and .claude/skills. Installing all "
            "three into one project can list Manuscript Lab more than once in Cursor.",
            file=sys.stderr,
        )
    messages = install_skill(
        agents,
        args.scope,
        Path(args.project) if args.project else None,
        copy=args.copy,
        force=args.force,
        dry_run=args.dry_run,
    )
    print("\n".join(messages))
    return 0


def _parser() -> argparse.ArgumentParser:
    """Build the command-line parser.

    Returns:
        Parser for the installer.
    """
    parser = argparse.ArgumentParser(description="Install Manuscript Lab for a compatible agent.")
    parser.add_argument("--agent", choices=[*AGENTS, "all"], help="Target agent, or all")
    parser.add_argument("--scope", choices=["project", "user"], help="Project or user install")
    parser.add_argument("--project", help="Project root used when scope is project")
    parser.add_argument("--copy", action="store_true", help="Copy files instead of linking")
    parser.add_argument("--force", action="store_true", help="Replace an existing guarded install")
    parser.add_argument("--dry-run", action="store_true", help="Print destinations without writing")
    parser.add_argument("--check", action="store_true", help="Validate the skill package and exit")
    return parser


def _agents(value: str | None) -> list[str]:
    """Expand the agent argument.

    Args:
        value: ``cursor``, ``codex``, ``claude``, or ``all``.

    Returns:
        Agent ids in a stable order.

    Raises:
        InstallError: The argument is missing.
    """
    if value is None:
        raise InstallError("Pass --agent or use --check.")
    if value == "all":
        return list(AGENTS)
    return [value]


def _install_one(source: Path, target: Path, copy: bool, force: bool, dry_run: bool) -> str:
    """Install one destination.

    Args:
        source: Canonical skill directory.
        target: Destination directory.
        copy: Copy instead of linking.
        force: Replace an existing guarded destination.
        dry_run: Do not write.

    Returns:
        A status line.

    Raises:
        InstallError: The destination is unsafe or cannot be created.
    """
    _refuse_self_install(source, target)
    action = "copy" if copy else "link"
    if dry_run:
        return f"dry-run {action} {source} -> {target}"
    if target.exists() or target.is_symlink():
        _replace_existing(target, force)
    target.parent.mkdir(parents=True, exist_ok=True)
    if copy:
        shutil.copytree(source, target, ignore=_ignore_runtime)
        return f"copied {source} -> {target}"
    _link_directory(source, target)
    return f"linked {source} -> {target}"


def _refuse_self_install(source: Path, target: Path) -> None:
    """Refuse a destination inside the canonical skill directory.

    Args:
        source: Canonical skill directory.
        target: Requested destination.

    Raises:
        InstallError: The link would point the skill at itself.
    """
    source_resolved = source.resolve()
    target_location = _without_following_link(target)
    if target_location == source_resolved or _is_inside(target_location, source_resolved):
        raise InstallError("Refusing to install the skill inside its own directory.")


def _without_following_link(path: Path) -> Path:
    """Resolve a path without following the path itself when it is a link.

    Args:
        path: Destination path. It may not exist yet.

    Returns:
        The destination location. An existing symlink or junction is not
        resolved to the skill it points at.
    """
    if path.is_symlink() or _is_junction(path):
        return path.parent.resolve() / path.name
    return path.resolve()


def _is_inside(path: Path, parent: Path) -> bool:
    """Return whether ``path`` is strictly inside ``parent``.

    Args:
        path: Candidate child path.
        parent: Directory that must not contain the child.

    Returns:
        True when ``path`` is a descendant of ``parent``.
    """
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return path != parent


def _replace_existing(target: Path, force: bool) -> None:
    """Remove an existing install at a guarded skill path.

    Args:
        target: Existing destination.
        force: Whether replacement was requested.

    Raises:
        InstallError: The path is not a guarded skill install, or force was
            not requested.
    """
    if not force:
        raise InstallError(f"{target} already exists. Pass --force to replace it.")
    if not _is_guarded(target):
        raise InstallError(f"Refusing to replace {target}: it is not a manuscript-lab skill path.")
    _remove_install(target)


def _is_guarded(target: Path) -> bool:
    """Return whether a path is a Manuscript Lab skill install location.

    Args:
        target: Destination path.

    Returns:
        True when the last two parents match an agent skill directory and the
        folder name is ``manuscript-lab``.
    """
    if target.name != SKILL_NAME or target.parent.name != "skills":
        return False
    return target.parent.parent.name in {".cursor", ".agents", ".claude"}


def _remove_install(target: Path) -> None:
    """Remove a symlink, junction, or copied skill directory.

    Args:
        target: Guarded install path.

    Raises:
        InstallError: The path cannot be removed safely.
    """
    if target.is_symlink() or _is_junction(target):
        _unlink_directory(target)
        return
    if target.is_dir():
        shutil.rmtree(target)
        return
    target.unlink()


def _is_junction(target: Path) -> bool:
    """Return whether a Windows path is a directory junction.

    Args:
        target: Path that exists.

    Returns:
        True on Windows when the path has the reparse-point attribute and is
        not a symlink.
    """
    if os.name != "nt" or not target.exists():
        return False
    attributes = getattr(target.lstat(), "st_file_attributes", 0)
    return bool(attributes & 0x400) and not target.is_symlink()


def _unlink_directory(target: Path) -> None:
    """Remove a symlink or junction without deleting the target contents.

    Args:
        target: Link or junction.

    Raises:
        InstallError: The link cannot be removed.
    """
    try:
        if target.is_symlink():
            target.unlink()
            return
        os.rmdir(target)
    except OSError as exc:
        raise InstallError(f"Could not remove existing link {target}: {exc}") from exc


def _link_directory(source: Path, target: Path) -> None:
    """Create a directory symlink, or a Windows junction if that is refused.

    Args:
        source: Canonical skill directory.
        target: Link path. Its parent must already exist.

    Raises:
        InstallError: Neither a symlink nor a junction can be created.
    """
    try:
        os.symlink(source, target, target_is_directory=True)
        return
    except OSError as symlink_error:
        if os.name != "nt":
            raise InstallError(
                f"Could not create symlink {target}: {symlink_error}. "
                "Re-run with --copy."
            ) from symlink_error
    _create_junction(source, target)


def _create_junction(source: Path, target: Path) -> None:
    """Create a Windows directory junction.

    Args:
        source: Canonical skill directory.
        target: Junction path.

    Raises:
        InstallError: ``mklink`` fails.
    """
    result = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not target.exists():
        detail = (result.stderr or result.stdout or "mklink failed").strip()
        raise InstallError(f"Could not link {target}: {detail}. Re-run with --copy.")


def _ignore_runtime(directory: str, names: list[str]) -> set[str]:
    """Skip caches and nested agent installs while copying.

    Args:
        directory: Current source directory. Unused; copytree requires it.
        names: Entry names in that directory.

    Returns:
        Names that ``shutil.copytree`` should skip.
    """
    del directory
    skipped = {"__pycache__", ".git", ".venv", "venv", ".cursor", ".agents", ".claude"}
    return {name for name in names if name in skipped or name.endswith(".pyc")}


if __name__ == "__main__":
    sys.exit(main())
