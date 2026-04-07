"""Shared pytest fixtures for Mountrr backend tests."""

from __future__ import annotations

import pytest


@pytest.fixture
def tmp_media(tmp_path):
    """Create a temporary media directory tree with real symlinks for testing."""
    media = tmp_path / "media"
    rd_mount = tmp_path / "mnt" / "rd"
    nzb_mount = tmp_path / "mnt" / "nzb"

    for d in [media, rd_mount, nzb_mount]:
        d.mkdir(parents=True)

    # Create some real target files
    rd_file = rd_mount / "realdebrid" / "Movie.A.mkv"
    rd_file.parent.mkdir(parents=True)
    rd_file.write_text("fake video data")

    nzb_file = nzb_mount / "nzbdav" / "Show.S01E01.mkv"
    nzb_file.parent.mkdir(parents=True)
    nzb_file.write_text("fake video data")

    # Create symlinks
    movies_dir = media / "movies"
    movies_dir.mkdir()
    tv_dir = media / "tv"
    tv_dir.mkdir()

    # Good symlink → rd
    good_rd = movies_dir / "Movie.A.mkv"
    good_rd.symlink_to(rd_file)

    # Good symlink → nzb
    good_nzb = tv_dir / "Show.S01E01.mkv"
    good_nzb.symlink_to(nzb_file)

    # Broken symlink → rd (target missing)
    broken_rd = movies_dir / "Movie.B.mkv"
    broken_rd.symlink_to(rd_mount / "realdebrid" / "Movie.B.mkv")

    # Symlink to an unknown/other path
    other = movies_dir / "Other.mkv"
    other_target = tmp_path / "other" / "file.mkv"
    other_target.parent.mkdir(parents=True)
    other_target.write_text("other data")
    other.symlink_to(other_target)

    return {
        "media": str(media),
        "rd_mount": str(rd_mount),
        "nzb_mount": str(nzb_mount),
        "good_rd": str(good_rd),
        "good_nzb": str(good_nzb),
        "broken_rd": str(broken_rd),
        "other": str(other),
    }
