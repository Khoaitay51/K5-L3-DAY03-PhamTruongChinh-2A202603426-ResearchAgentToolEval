---
name: github_repos
track: bonus
kind: live_api
provider: GitHub REST API search/repositories (no key required)
requires_env: []
inputs: [query, language, sort_by, limit]
outputs: [items, total_count]
side_effect: false
---
# github_repos

Searches public GitHub repositories (`https://api.github.com/search/repositories`).
Works without a key (10 req/min). Optional `GITHUB_TOKEN` in `.env` raises the limit.

- `language`: optional filter, appended to the query as `language:<x>`.
- `sort_by`: `stars` (default) | `updated` | `best_match` (GitHub relevance, no sort param).
- `limit` is clamped to 1..20; unknown `sort_by` falls back to `stars`.
- Empty `query` returns an error dict without calling the network.

Each item: `title` (owner/repo), `url`, `source`, `summary` (description), `stars`,
`language`, `updated`.

Team-added tool (Day 03 lab).
