"""
Symlink source classifier.

Determines whether a symlink's target path belongs to the Real-Debrid mount,
NzbDAV mount, or is from some other/unknown source. Classification is based on
configurable substring patterns stored in the DB config table.
"""

from __future__ import annotations

import logging
from typing import Literal

logger = logging.getLogger(__name__)

Source = Literal["rd", "nzb", "other"]


def classify_symlink(
    target_path: str,
    rd_patterns: list[str],
    nzb_patterns: list[str],
) -> Source:
    """
    Classify a symlink's source based on its target path.

    Pattern matching is case-insensitive substring. RD patterns are checked first;
    if no RD match, NZB patterns are checked. Returns 'other' if no match.

    Args:
        target_path: The resolved target of the symlink (os.readlink() result).
        rd_patterns: List of substrings indicating a Real-Debrid target.
        nzb_patterns: List of substrings indicating an NzbDAV target.

    Returns:
        'rd', 'nzb', or 'other'
    """
    target_lower = target_path.lower()

    for pattern in rd_patterns:
        if pattern.lower() in target_lower:
            return "rd"

    for pattern in nzb_patterns:
        if pattern.lower() in target_lower:
            return "nzb"

    return "other"


def get_mount_path_for_source(
    source: Source,
    rd_mount: str,
    nzb_mount: str,
) -> str | None:
    """Return the mount base path for a given source classification."""
    if source == "rd":
        return rd_mount
    if source == "nzb":
        return nzb_mount
    return None
