---
name: hf_models
track: bonus
kind: live_api
provider: Hugging Face Hub API (no key)
requires_env: []
inputs: [query, task, sort_by, limit]
outputs: [items]
side_effect: false
---
# hf_models

Searches models on the Hugging Face Hub (`https://huggingface.co/api/models`). No API key.

- `query`: free-text model name search (e.g. `qwen`, `whisper`).
- `task`: optional pipeline tag filter (e.g. `text-generation`, `automatic-speech-recognition`).
  At least one of `query` / `task` is required.
- `sort_by`: `downloads` (default) | `likes` | `lastModified` | `trendingScore`;
  unknown values fall back to `downloads`.
- `limit` is clamped to 1..20.

Each item: `title` (model id), `url`, `source`, `summary`, `task`, `downloads`, `likes`, `updated`.

Team-added tool (Day 03 lab).
