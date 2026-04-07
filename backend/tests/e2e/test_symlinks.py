from __future__ import annotations

import os

from mountrr.scanner import run_scan


async def test_list_symlinks_empty(client):
    resp = await client.get("/api/symlinks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_list_symlinks_after_scan(client, e2e_setup):
    await run_scan("full")
    resp = await client.get("/api/symlinks")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 4
    assert len(data["items"]) == 4


async def test_filter_by_status_broken(client, e2e_setup):
    await run_scan("full")
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["status"] == "broken"
    assert "Movie.B.mkv" in data["items"][0]["symlink_path"]


async def test_filter_by_source_rd(client, e2e_setup):
    await run_scan("full")
    resp = await client.get("/api/symlinks", params={"source": "rd"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
    for item in data["items"]:
        assert item["source"] == "rd"


async def test_filter_by_source_nzb(client, e2e_setup):
    await run_scan("full")
    resp = await client.get("/api/symlinks", params={"source": "nzb"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["source"] == "nzb"


async def test_delete_broken_symlink(client, e2e_setup):
    """Deleting a broken symlink removes the symlink file and logs a deletion_history row."""
    await run_scan("full")

    # Find the broken symlink row
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    broken = resp.json()["items"][0]
    broken_id = broken["id"]
    broken_path = broken["symlink_path"]

    # Confirm it exists on disk before deletion
    assert os.path.islink(broken_path)

    resp = await client.delete(f"/api/symlinks/{broken_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 1
    assert data["skipped"] == 0

    # Symlink must be gone from disk
    assert not os.path.exists(broken_path)

    # But the RD mount target files must be untouched (SAFETY check)
    remaining_targets = list(e2e_setup["rd_mount"].iterdir())
    assert len(remaining_targets) > 0, "RD target directory must not be empty after symlink deletion"

    # The healthy RD target (Movie.A.mkv) must still exist
    assert e2e_setup["rd_target"].exists()

    # The deleted row should no longer appear in symlinks list
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    assert resp.json()["total"] == 0


async def test_delete_nonexistent_symlink(client, e2e_setup):
    resp = await client.delete("/api/symlinks/99999")
    assert resp.status_code == 404


async def test_delete_symlink_dry_run(client, e2e_setup):
    """dry_run=true writes to deletion_history but does not unlink."""
    await run_scan("full")

    resp = await client.get("/api/symlinks", params={"status": "broken"})
    broken = resp.json()["items"][0]
    broken_path = broken["symlink_path"]

    resp = await client.delete(f"/api/symlinks/{broken['id']}", params={"dry_run": "true"})
    assert resp.status_code == 200
    assert resp.json()["dry_run"] is True

    # Symlink still exists (dry run)
    assert os.path.islink(broken_path)
