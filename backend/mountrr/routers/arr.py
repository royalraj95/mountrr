"""
Arr instances router — v1.1 placeholder.

In v1.0 only the test-connection endpoint is live, so users can configure and
validate arr instances in the Settings UI. The auto-search trigger is v1.1.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mountrr import database as db
from mountrr.arr_client import ArrClient

router = APIRouter(prefix="/arr", tags=["arr"])
logger = logging.getLogger(__name__)


class ArrInstanceCreate(BaseModel):
    name: str
    type: str  # 'radarr' | 'sonarr'
    url: str
    api_key: str
    media_paths: list[str] = []
    enabled: bool = True


class ArrTestRequest(BaseModel):
    url: str
    api_key: str


@router.get("/instances")
async def list_instances() -> dict:
    rows = await db.fetchall("SELECT * FROM arr_instances ORDER BY id")
    return {
        "items": [
            {
                "id": r["id"],
                "name": r["name"],
                "type": r["type"],
                "url": r["url"],
                "media_paths": r["media_paths"],
                "enabled": bool(r["enabled"]),
                "created_at": r["created_at"],
            }
            for r in rows
        ]
    }


@router.post("/instances")
async def create_instance(body: ArrInstanceCreate) -> dict:
    if body.type not in ("radarr", "sonarr"):
        raise HTTPException(status_code=400, detail="type must be 'radarr' or 'sonarr'")

    import json
    instance_id = await db.execute(
        "INSERT INTO arr_instances(name, type, url, api_key, media_paths, enabled) VALUES (?,?,?,?,?,?)",
        (body.name, body.type, body.url, body.api_key, json.dumps(body.media_paths), body.enabled),
    )
    return {"id": instance_id, "ok": True}


@router.delete("/instances/{instance_id}")
async def delete_instance(instance_id: int) -> dict:
    row = await db.fetchone("SELECT id FROM arr_instances WHERE id = ?", (instance_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Instance not found")
    await db.execute("DELETE FROM arr_instances WHERE id = ?", (instance_id,))
    return {"ok": True}


@router.post("/test")
async def test_connection(body: ArrTestRequest) -> dict:
    """Test an arr connection without saving it."""
    async with ArrClient(url=body.url, api_key=body.api_key, name="test") as client:
        ok = await client.test_connection()
    return {"ok": ok, "reachable": ok}
