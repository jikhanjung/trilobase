"""
Versioned DB path helpers.

All canonical DBs use {name}-{version}.db naming:
  db/trilobase-{version}.db
  db/trilobase-assertion-{version}.db
  db/paleocore-{version}.db
"""

import glob
import os
import re

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_DB_DIR = os.path.join(_SCRIPT_DIR, '..', 'db')

_TRILOBASE_RE = re.compile(r'^trilobase-(\d+\.\d+\.\d+)\.db$')
_ASSERTION_RE = re.compile(r'^trilobase-assertion-(\d+\.\d+\.\d+)\.db$')
_PALEOCORE_RE = re.compile(r'^paleocore-(\d+\.\d+\.\d+)\.db$')


def _find_latest(pattern: str, regex: re.Pattern, label: str) -> str:
    """Glob for versioned DB files and return the latest by semver."""
    candidates = glob.glob(pattern)

    versioned = []
    for path in candidates:
        m = regex.search(os.path.basename(path))
        if m:
            parts = tuple(int(x) for x in m.group(1).split('.'))
            versioned.append((parts, path))

    if not versioned:
        raise FileNotFoundError(
            f"No {label} found (looked in {os.path.abspath(_DB_DIR)})")

    versioned.sort()
    return os.path.abspath(versioned[-1][1])


def find_trilobase_db() -> str:
    """Return the path to the latest db/trilobase-{version}.db."""
    return _find_latest(
        os.path.join(_DB_DIR, 'trilobase-*.db'),
        _TRILOBASE_RE, 'db/trilobase-*.db')


def find_assertion_db() -> str:
    """Return the path to the latest db/trilobase-assertion-{version}.db."""
    return _find_latest(
        os.path.join(_DB_DIR, 'trilobase-assertion-*.db'),
        _ASSERTION_RE, 'db/trilobase-assertion-*.db')


def find_paleocore_db() -> str:
    """Return the path to the latest db/paleocore-{version}.db."""
    return _find_latest(
        os.path.join(_DB_DIR, 'paleocore-*.db'),
        _PALEOCORE_RE, 'db/paleocore-*.db')
