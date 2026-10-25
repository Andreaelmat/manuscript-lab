"""Shared fixtures for Manuscript Lab tests."""

from __future__ import annotations

import os
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def run_script(
    name: str,
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one bundled script in a subprocess.

    Args:
        name: File name inside ``scripts``.
        args: Arguments after the script path.
        cwd: Working directory. Defaults to a path that is not the skill root
            only when the caller sets it.

    Returns:
        The completed process with UTF-8 stdout and stderr.
    """
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def run_installed(
    skill_dir: Path,
    manuscript: Path,
    cwd: Path,
) -> subprocess.CompletedProcess[str]:
    """Run the extractor from an installed copy or link.

    Args:
        skill_dir: Installed skill directory.
        manuscript: Manuscript to extract.
        cwd: Working directory that is not the skill directory.

    Returns:
        The completed extractor process.
    """
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    script = skill_dir / "scripts" / "extract_manuscript.py"
    return subprocess.run(
        [sys.executable, str(script), str(manuscript)],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        check=False,
    )


def write_docx(path: Path, body_xml: str) -> None:
    """Write a minimal DOCX package.

    Args:
        path: Destination ``.docx`` path.
        body_xml: Inner XML of ``w:body``, excluding ``w:body`` itself.
    """
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>{body_xml}'
        "<w:sectPr/></w:body></w:document>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    relationships = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/'
        'relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/'
        'relationships/officeDocument" Target="word/document.xml"/>'
        "</Relationships>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)


def paragraph_xml(text: str, style: str | None = None) -> str:
    """Build one DOCX paragraph.

    Args:
        text: Visible paragraph text. XML metacharacters are escaped.
        style: Optional paragraph style such as ``Heading1``.

    Returns:
        A ``w:p`` element.
    """
    escaped = (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    style_xml = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    return (
        f"<w:p>{style_xml}<w:r><w:t xml:space=\"preserve\">"
        f"{escaped}</w:t></w:r></w:p>"
    )
