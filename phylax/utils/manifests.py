"""Finding the manifests and lockfiles an audit needs.

Much narrower than `collect_files`. An audit does not want your source: it
wants the files that say what will be installed, and the server fetches the
packages themselves from their registries. Sending a whole tree would upload
megabytes to answer a question about a few kilobytes.
"""

from __future__ import annotations

from pathlib import Path

# Mirrors phylax_server.business.audit.manifests.ACCEPTED.
MANIFEST_NAMES = frozenset(
    {
        "package-lock.json",
        "npm-shrinkwrap.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "poetry.lock",
        "Pipfile.lock",
        "requirements.txt",
        "package.json",
        "pyproject.toml",
    }
)

SKIP_DIRS = frozenset(
    {
        ".git", ".venv", "__pycache__", "node_modules", "dist", "build",
        ".next", "coverage", ".tox", "vendor",
    }
)

MAX_BYTES = 8 * 1024 * 1024


def collect_manifests(root: str | Path) -> tuple[dict[str, str], list[str]]:
    """Return ``(files, skipped)`` for a project directory."""
    root = Path(root)
    files: dict[str, str] = {}
    skipped: list[str] = []
    total = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name not in MANIFEST_NAMES:
            continue
        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        name = rel.as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(f"{name}: not readable")
            continue

        size = len(text.encode("utf-8"))
        if total + size > MAX_BYTES:
            skipped.append(f"{name}: would pass the {MAX_BYTES:,} byte limit")
            continue

        files[name] = text
        total += size

    return files, skipped
