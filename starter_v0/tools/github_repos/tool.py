from __future__ import annotations

import os
from typing import Any

import requests

from tools._shared import TIMEOUT, clamp_int, err, pick


GITHUB_SEARCH_URL = "https://api.github.com/search/repositories"


def search_github_repos(query: str = "", language: str = "", sort_by: str = "stars", limit: int = 5) -> dict[str, Any]:
    try:
        query = (query or "").strip() if isinstance(query, str) else ""
        if not query:
            raise ValueError("query must be a non-empty string")
        language = (language or "").strip() if isinstance(language, str) else ""
        sort_by = pick(sort_by, ("stars", "updated", "best_match"), "stars")
        limit = clamp_int(limit, default=5, low=1, high=20)

        q = f"{query} language:{language}" if language else query
        params: dict[str, Any] = {"q": q, "per_page": limit}
        if sort_by != "best_match":
            params["sort"] = sort_by
            params["order"] = "desc"
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "AI20k-Day03-Research-Agent"}
        token = os.getenv("GITHUB_TOKEN")  # optional: raises rate limit from 10 to 30 req/min
        if token:
            headers["Authorization"] = f"Bearer {token}"

        response = requests.get(GITHUB_SEARCH_URL, params=params, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        items = [{
            "title": repo.get("full_name"),
            "url": repo.get("html_url"),
            "source": "github.com",
            "summary": repo.get("description") or "",
            "stars": repo.get("stargazers_count") or 0,
            "language": repo.get("language"),
            "updated": repo.get("pushed_at") or repo.get("updated_at"),
        } for repo in data.get("items", []) or [] if repo.get("full_name")]
        return {
            "tool": "search_github_repos",
            "query": query,
            "language": language or None,
            "sort_by": sort_by,
            "total_count": data.get("total_count", len(items)),
            "items": items[:limit],
        }
    except Exception as exc:
        return err("search_github_repos", exc)
