"""Step 1: Text loading and cleaning.

Loads the already-cleaned genus list file.  The original PDF-to-text
cleaning was done manually + scripts (Phase 1-3); this module simply
reads the canonical cleaned file.
"""
from pathlib import Path


def load_genus_list(path: Path) -> list[str]:
    """Read the cleaned genus list, returning non-empty, non-comment lines."""
    lines = path.read_text(encoding='utf-8').splitlines()
    return [l for l in lines if l.strip() and not l.startswith('#')]


def load_bibliography_lines(path: Path) -> list[str]:
    """Read the Literature Cited file, returning all lines."""
    return path.read_text(encoding='utf-8').splitlines()
