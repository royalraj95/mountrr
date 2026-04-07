"""Tests for scanner helper functions."""

import os
import pytest
from mountrr.scanner import _collect_symlinks, _evaluate_symlink


RD_PATTERNS = ["realdebrid", "decypharr", "zurg", "rd"]
NZB_PATTERNS = ["nzbdav", "nzb", "usenet"]


class TestCollectSymlinks:
    def test_finds_symlinks(self, tmp_media):
        symlinks = _collect_symlinks([tmp_media["media"]])
        assert len(symlinks) >= 4  # good_rd, good_nzb, broken_rd, other

    def test_only_returns_symlinks(self, tmp_media):
        # Add a regular file — should not be in results
        regular = os.path.join(tmp_media["media"], "movies", "regular.txt")
        with open(regular, "w") as f:
            f.write("not a symlink")
        symlinks = _collect_symlinks([tmp_media["media"]])
        assert regular not in symlinks

    def test_missing_dir_is_skipped(self, tmp_path):
        result = _collect_symlinks([str(tmp_path / "nonexistent")])
        assert result == []

    def test_multiple_dirs(self, tmp_media, tmp_path):
        extra_dir = tmp_path / "extra"
        extra_dir.mkdir()
        result = _collect_symlinks([tmp_media["media"], str(extra_dir)])
        assert len(result) >= 4


class TestEvaluateSymlink:
    def test_good_rd_symlink(self, tmp_media):
        mount_health = {"rd": "healthy", "nzb": "healthy"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["good_rd"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert status == "ok"
        assert source == "rd"
        assert size is not None
        assert size > 0

    def test_good_nzb_symlink(self, tmp_media):
        mount_health = {"rd": "healthy", "nzb": "healthy"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["good_nzb"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert status == "ok"
        assert source == "nzb"

    def test_broken_rd_symlink_on_healthy_mount(self, tmp_media):
        mount_health = {"rd": "healthy", "nzb": "healthy"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["broken_rd"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert status == "broken"
        assert source == "rd"
        assert size is None

    def test_broken_symlink_not_marked_on_unreachable_mount(self, tmp_media):
        """SAFETY: must never mark broken when mount is down."""
        mount_health = {"rd": "unreachable", "nzb": "healthy"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["broken_rd"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert status == "unknown"  # NOT broken
        assert source == "rd"

    def test_broken_symlink_not_marked_on_empty_mount(self, tmp_media):
        """SAFETY: must never mark broken when mount is empty."""
        mount_health = {"rd": "empty", "nzb": "healthy"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["broken_rd"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert status == "unknown"  # NOT broken

    def test_other_source_always_evaluated(self, tmp_media):
        """'other' source symlinks are always evaluated regardless of mount health."""
        mount_health = {"rd": "unreachable", "nzb": "unreachable"}
        status, source, target, size = _evaluate_symlink(
            tmp_media["other"], RD_PATTERNS, NZB_PATTERNS, mount_health
        )
        assert source == "other"
        assert status == "ok"
