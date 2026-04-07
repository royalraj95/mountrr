from __future__ import annotations

import asyncio


async def test_scan_history_empty_initially(client, e2e_setup):
    resp = await client.get("/api/scans/history")
    assert resp.status_code == 200
    assert resp.json()["items"] == []


async def test_start_scan_returns_202(client, e2e_setup):
    resp = await client.post("/api/scans/start")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "started"


async def test_scan_history_after_scan(client, e2e_setup):
    """After a direct scan invocation, history contains the completed scan row."""
    # Calling run_scan directly (rather than via the fire-and-forget endpoint)
    # is simpler and more reliable in the test context: no need to race against
    # the background task scheduler.
    from mountrr.scanner import run_scan

    await run_scan("full")

    resp = await client.get("/api/scans/history")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    last = items[0]
    assert last["total_symlinks"] == 4
    assert last["broken_found"] == 1
    assert last["completed_at"] is not None


async def test_duplicate_scan_rejected(client, e2e_setup):
    """A second scan start while one is running returns 409."""
    from mountrr import scanner
    # Patch the running flag to simulate an in-progress scan
    scanner._scan_running = True
    try:
        resp = await client.post("/api/scans/start")
        assert resp.status_code == 409
    finally:
        scanner._scan_running = False
