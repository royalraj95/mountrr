from __future__ import annotations


async def test_get_settings_has_defaults(client, e2e_setup):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "scan_interval_minutes" in data
    assert "rd_patterns" in data
    assert "nzb_patterns" in data
    assert "media_dirs" in data
    assert "rd_mount_path" in data
    assert "nzb_mount_path" in data
    assert isinstance(data["rd_patterns"], list)
    assert isinstance(data["media_dirs"], list)


async def test_update_scan_interval(client, e2e_setup):
    resp = await client.put("/api/settings", json={"scan_interval_minutes": 60})
    assert resp.status_code == 200

    resp = await client.get("/api/settings")
    assert resp.json()["scan_interval_minutes"] == 60


async def test_update_dry_run(client, e2e_setup):
    resp = await client.put("/api/settings", json={"dry_run": True})
    assert resp.status_code == 200

    resp = await client.get("/api/settings")
    assert resp.json()["dry_run"] is True


async def test_update_rd_patterns(client, e2e_setup):
    new_patterns = ["decypharr", "zurg", "realdebrid", "myrd"]
    resp = await client.put("/api/settings", json={"rd_patterns": new_patterns})
    assert resp.status_code == 200

    resp = await client.get("/api/settings")
    assert resp.json()["rd_patterns"] == new_patterns


async def test_partial_update_does_not_overwrite_others(client, e2e_setup):
    """PUT with one field must not clobber the others."""
    # Set scan_interval
    await client.put("/api/settings", json={"scan_interval_minutes": 30})
    # Get current rd_patterns
    before = (await client.get("/api/settings")).json()["rd_patterns"]

    # Update only dry_run
    await client.put("/api/settings", json={"dry_run": False})

    after = (await client.get("/api/settings")).json()
    assert after["scan_interval_minutes"] == 30
    assert after["rd_patterns"] == before
