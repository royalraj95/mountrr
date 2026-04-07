"""
Arr API client — Radarr and Sonarr integration.

v1.0: Stub only. The client interface is defined here so routers can import it,
but auto-search-on-cleanup is deferred to v1.1.
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class ArrClient:
    """Generic *arr API client (Radarr / Sonarr)."""

    def __init__(self, url: str, api_key: str, name: str = "") -> None:
        self.url = url.rstrip("/")
        self.api_key = api_key
        self.name = name
        self._client = httpx.AsyncClient(
            headers={"X-Api-Key": api_key},
            timeout=10.0,
        )

    async def test_connection(self) -> bool:
        """Returns True if the instance is reachable and the API key is valid."""
        try:
            resp = await self._client.get(f"{self.url}/api/v3/system/status")
            return resp.status_code == 200
        except Exception as exc:
            logger.debug("Arr connection test failed (%s): %s", self.name, exc)
            return False

    async def search_movie(self, movie_id: int) -> bool:
        """Trigger a Radarr search for a specific movie. Returns True on success."""
        try:
            resp = await self._client.post(
                f"{self.url}/api/v3/command",
                json={"name": "MoviesSearch", "movieIds": [movie_id]},
            )
            return resp.status_code in (200, 201)
        except Exception as exc:
            logger.error("Radarr search failed: %s", exc)
            return False

    async def search_series(self, series_id: int) -> bool:
        """Trigger a Sonarr search for a specific series. Returns True on success."""
        try:
            resp = await self._client.post(
                f"{self.url}/api/v3/command",
                json={"name": "SeriesSearch", "seriesId": series_id},
            )
            return resp.status_code in (200, 201)
        except Exception as exc:
            logger.error("Sonarr search failed: %s", exc)
            return False

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "ArrClient":
        return self

    async def __aexit__(self, *_) -> None:
        await self.aclose()
