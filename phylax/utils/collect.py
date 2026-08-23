"""Reading a directory into the file map ``artifacts.analyse`` expects.

The server's own limits are mirrored here so an oversized artifact is trimmed
deliberately and the caller is told what was dropped, rather than meeting a 413
that does not say which file was at fault.
"""

from __future__ import annotations

from pathlib import Path

# Mirrors phylax_server.business.routers.artifacts.
MAX_FILES = 200
MAX_FILE_BYTES = 512 * 1024
MAX_TOTAL_BYTES = 4 * 1024 * 1024

TEXT_SUFFIXES = frozenset(
    {
        ".cfg", ".cjs", ".go", ".ini", ".java", ".js", ".json", ".jsx", ".kt",
        ".lock", ".md", ".mjs", ".php", ".ps1", ".py", ".rb", ".rs", ".sh",
        ".toml", ".ts", ".tsx", ".txt", ".yaml", ".yml",
    }
)

# Extensionless files that still carry real signal.
TEXT_NAMES = frozenset(
    {"Dockerfile", "Makefile", "Procfile", "SKILL.md", ".npmrc", "binding.gyp"}
)

SKIP_DIRS = frozenset(
    {
        ".git", ".venv", "__pycache__", "node_modules", "dist", "build",
        ".next", "coverage", ".tox",
    }
)


def collect_files(root: str | Path) -> tuple[dict[str, str], list[str]]:
    """Return ``(files, skipped)`` for a directory.

    Paths are POSIX-normalised because the server keys findings by them, and a
    backslash on Windows produces findings nobody can locate.

    Skipping is reported rather than silent: a truncated artifact that presents
    itself as fully analysed is worse than one that says what it left out.
    """
    root = Path(root)
    files: dict[str, str] = {}
    skipped: list[str] = []
    total = 0

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        rel = path.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        name = rel.as_posix()
        if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in TEXT_NAMES:
            continue

        try:
            body = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            skipped.append(f"{name}: not readable as utf-8")
            continue

        size = len(body.encode("utf-8"))
        if size > MAX_FILE_BYTES:
            skipped.append(f"{name}: {size:,} bytes, over the {MAX_FILE_BYTES:,} limit")
            continue
        if len(files) >= MAX_FILES:
            skipped.append(f"{name}: past the {MAX_FILES} file limit")
            continue
        if total + size > MAX_TOTAL_BYTES:
            skipped.append(f"{name}: would pass the {MAX_TOTAL_BYTES:,} byte limit")
            continue

        files[name] = body
        total += size

    return files, skipped
