"""Tests for mountrr.classifier"""

import pytest
from mountrr.classifier import classify_symlink, get_mount_path_for_source

RD_PATTERNS = ["decypharr", "realdebrid", "zurg", "rd"]
NZB_PATTERNS = ["nzbdav", "nzb", "usenet"]


class TestClassifySymlink:
    def test_rd_pattern_match(self):
        target = "/mnt/rd/realdebrid/__all__/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "rd"

    def test_rd_decypharr_pattern(self):
        target = "/mnt/remote/decypharr/movies/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "rd"

    def test_rd_zurg_pattern(self):
        target = "/mnt/zurg/__all__/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "rd"

    def test_nzb_pattern_match(self):
        target = "/mnt/nzb/nzbdav/Show.S01E01.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "nzb"

    def test_nzb_usenet_pattern(self):
        target = "/mnt/usenet/completed/Show.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "nzb"

    def test_other_no_match(self):
        target = "/mnt/local/files/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "other"

    def test_case_insensitive_rd(self):
        target = "/mnt/rd/RealDebrid/__all__/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "rd"

    def test_case_insensitive_nzb(self):
        target = "/mnt/NZB/completed/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "nzb"

    def test_rd_takes_priority_over_nzb(self):
        # Contrived path that contains both patterns — rd should win
        target = "/mnt/rd/nzb/Movie.mkv"
        assert classify_symlink(target, RD_PATTERNS, NZB_PATTERNS) == "rd"

    def test_empty_patterns_returns_other(self):
        target = "/mnt/rd/realdebrid/Movie.mkv"
        assert classify_symlink(target, [], []) == "other"

    def test_custom_patterns(self):
        target = "/mnt/myservice/content/Movie.mkv"
        assert classify_symlink(target, ["myservice"], NZB_PATTERNS) == "rd"


class TestGetMountPath:
    def test_rd_returns_rd_mount(self):
        assert get_mount_path_for_source("rd", "/mnt/rd", "/mnt/nzb") == "/mnt/rd"

    def test_nzb_returns_nzb_mount(self):
        assert get_mount_path_for_source("nzb", "/mnt/rd", "/mnt/nzb") == "/mnt/nzb"

    def test_other_returns_none(self):
        assert get_mount_path_for_source("other", "/mnt/rd", "/mnt/nzb") is None
