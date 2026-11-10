from __future__ import annotations

from typing import Any

import requests

from tools._shared import TIMEOUT, clamp_int, err, pick


HF_MODELS_URL = "https://huggingface.co/api/models"


def search_hf_models(query: str = "", task: str = "", sort_by: str = "downloads", limit: int = 5) -> dict[str, Any]:
    try:
        query = (query or "").strip() if isinstance(query, str) else ""
        task = (task or "").strip() if isinstance(task, str) else ""
        if not query and not task:
            raise ValueError("provide a non-empty query or task")
        sort_by = pick(sort_by, ("downloads", "likes", "lastModified", "trendingScore"), "downloads")
        limit = clamp_int(limit, default=5, low=1, high=20)

        params: dict[str, Any] = {"sort": sort_by, "direction": -1, "limit": limit}
        if query:
            params["search"] = query
        if task:
            params["pipeline_tag"] = task

        response = requests.get(HF_MODELS_URL, params=params, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, list):
            raise ValueError(f"unexpected response shape: {type(data).__name__}")

        items = []
        for model in data:
            model_id = model.get("id") or model.get("modelId")
            if not model_id:
                continue
            tag = model.get("pipeline_tag") or "unknown task"
            items.append({
                "title": model_id,
                "url": f"https://huggingface.co/{model_id}",
                "source": "huggingface.co",
                "summary": f"{tag}; {model.get('downloads') or 0} downloads, {model.get('likes') or 0} likes",
                "task": model.get("pipeline_tag"),
                "downloads": model.get("downloads") or 0,
                "likes": model.get("likes") or 0,
                "updated": model.get("lastModified"),
            })
        return {
            "tool": "search_hf_models",
            "query": query or None,
            "task": task or None,
            "sort_by": sort_by,
            "items": items[:limit],
        }
    except Exception as exc:
        return err("search_hf_models", exc)
