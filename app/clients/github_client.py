from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


class GitHubClient:
    """
    GitHub REST API client.
    """

    def __init__(self) -> None:
        self.base_url = settings.github_api_base_url.rstrip("/")
        self.timeout = 20.0

    def _build_headers(self) -> dict[str, str]:
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-API-Version": "2022-11-28",
        }
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        return headers

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:
        url = f"{self.base_url}{path}"

        with httpx.Client(timeout=self.timeout, headers=self._build_headers()) as client:
            response = client.request(method, url, params=params)

        response.raise_for_status()
        return response

    def _get_paginated(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        base_params = params.copy() if params else {}
        base_params["per_page"] = 100

        for page in range(1, max_pages + 1):
            page_params = {**base_params, "page": page}
            response = self._request("GET", path, params=page_params)
            data = response.json()

            if not isinstance(data, list):
                break

            results.extend(data)

            if len(data) < 100:
                break

        return results

    def get_rate_limit(self) -> dict[str, int]:
        """
        Return the current GitHub core rate-limit information.
        """
        response = self._request("GET", "/rate_limit")
        payload = response.json()

        resources = payload.get("resources", {})
        if not isinstance(resources, dict):
            resources = {}

        core = resources.get("core", {})
        if not isinstance(core, dict):
            core = {}

        return {
            "limit": int(core.get("limit", 0)),
            "remaining": int(core.get("remaining", 0)),
            "reset": int(core.get("reset", 0)),
        }

    def get_repository(self, owner: str, repo: str) -> dict[str, Any]:
        response = self._request("GET", f"/repos/{owner}/{repo}")
        return response.json()

    def get_contributors(
        self,
        owner: str,
        repo: str,
        include_anonymous: bool = False,
        max_pages: int = 5,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if include_anonymous:
            params["anon"] = "true"

        return self._get_paginated(
            f"/repos/{owner}/{repo}/contributors",
            params=params,
            max_pages=max_pages,
        )

    def get_commits(
        self,
        owner: str,
        repo: str,
        since: datetime | None = None,
        until: datetime | None = None,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}

        if since is not None:
            params["since"] = self._to_iso_8601_z(since)

        if until is not None:
            params["until"] = self._to_iso_8601_z(until)

        return self._get_paginated(
            f"/repos/{owner}/{repo}/commits",
            params=params,
            max_pages=max_pages,
        )

    @staticmethod
    def _to_iso_8601_z(dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = dt.astimezone(timezone.utc)

        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
