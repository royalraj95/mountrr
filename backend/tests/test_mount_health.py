"""Tests for mountrr.mount_health"""

import os
import pytest
from mountrr.mount_health import check_mount_health_sync


class TestCheckMountHealthSync:
    def test_healthy_mount_with_files(self, tmp_path):
        # Directory with at least one file
        (tmp_path / "file.mkv").write_text("data")
        assert check_mount_health_sync(str(tmp_path)) == "healthy"

    def test_empty_mount(self, tmp_path):
        # Directory exists but is empty
        assert check_mount_health_sync(str(tmp_path)) == "empty"

    def test_unreachable_nonexistent_path(self):
        assert check_mount_health_sync("/nonexistent/path/xyz") == "unreachable"

    def test_nested_directory_counts_as_healthy(self, tmp_path):
        # A subdirectory (not a file) still makes it non-empty
        (tmp_path / "subdir").mkdir()
        assert check_mount_health_sync(str(tmp_path)) == "healthy"

    def test_hidden_files_count_as_content(self, tmp_path):
        (tmp_path / ".hidden").write_text("data")
        assert check_mount_health_sync(str(tmp_path)) == "healthy"
