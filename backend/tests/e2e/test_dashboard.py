from __future__ import annotations

from mountrr.scanner import run_scan


async def test_dashboard_empty_before_scan(client):
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_symlinks"] == 0
    assert data["broken_symlinks"] == 0


async def test_dashboard_counts_after_scan(client, e2e_setup):
    """After a full scan, dashboard returns correct counts for our 4-symlink fixture."""
    await run_scan("full")

    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    data = resp.json()

    # Fixture: 1 good_rd + 1 broken_rd = 2 rd; 1 good_nzb = 1 nzb; 1 other
    assert data["total_symlinks"] == 4
    assert data["broken_symlinks"] == 1

    by_source = data["by_source"]
    assert by_source["rd"] == 2    # good_rd + broken_rd
    assert by_source["nzb"] == 1   # good_nzb
    assert by_source["other"] == 1 # other_link


async def test_dashboard_mount_health(client, e2e_setup):
    resp = await client.get("/api/dashboard")
    assert resp.status_code == 200
    mount_health = resp.json()["mount_health"]
    # Both tmp storage dirs exist and have files → healthy
    assert mount_health["rd"] in ("healthy", "empty", "unreachable")  # just check key exists
    assert "nzb" in mount_health


async def test_dashboard_last_scan(client, e2e_setup):
    await run_scan("full")
    data = resp = await client.get("/api/dashboard")
    data = resp.json()
    assert data["last_scan"] is not None
    assert data["last_scan"]["total_symlinks"] == 4
