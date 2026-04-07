from __future__ import annotations

from mountrr.scanner import run_scan


async def test_deletions_empty_initially(client, e2e_setup):
    resp = await client.get("/api/deletions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["total"] == 0


async def test_deletion_logged_after_delete(client, e2e_setup):
    """Deleting a symlink must write a deletion_history row."""
    await run_scan("full")

    # Get the broken symlink
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    broken = resp.json()["items"][0]

    await client.delete(f"/api/symlinks/{broken['id']}")

    resp = await client.get("/api/deletions")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    row = data["items"][0]
    assert row["symlink_path"] == broken["symlink_path"]
    assert row["source"] == broken["source"]
    assert row["reason"] == "manual"
    assert row["deleted_at"] is not None


async def test_deletion_filter_by_source(client, e2e_setup):
    await run_scan("full")
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    broken = resp.json()["items"][0]
    source = broken["source"]

    await client.delete(f"/api/symlinks/{broken['id']}")

    resp = await client.get("/api/deletions", params={"source": source})
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp_other = await client.get("/api/deletions", params={"source": "nzb" if source == "rd" else "rd"})
    assert resp_other.json()["total"] == 0


async def test_cleanup_broken_deletes_all(client, e2e_setup):
    """POST /deletions/cleanup removes all broken symlinks in one shot."""
    await run_scan("full")

    resp = await client.post("/api/deletions/cleanup")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 1
    assert data["skipped"] == 0

    # No more broken symlinks
    resp = await client.get("/api/symlinks", params={"status": "broken"})
    assert resp.json()["total"] == 0
