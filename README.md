# GitHub Trending Site

Static GitHub Pages site listing **5,895 unique Python & JavaScript repositories** sourced from daily GitHub trending snapshots (2023–2026), enriched with content potential, category, and open-source license.

## Live site

👉 [chaoticravena.github.io/github-trending-site](https://chaoticravena.github.io/github-trending-site)

## Features

- **5,895 repos** — Python (3,749) and JavaScript (2,146), Go/Swift excluded
- Search by name or description
- Filter by language, content potential, category, and **license** (MIT, Apache-2.0, GPL-3.0…)
- Sort any column · paginated 50 repos/page · URL-driven state
- **AI Agent** (`agent.html`) — describe your project, get repo recommendations via semantic search + LLM (Anthropic, Groq, Gemini, OpenRouter)

## Data pipeline

```
bonfy/github-trending (daily .md snapshots on GitHub)
        ↓
scripts/fetch_trending.js   → fetches last N days, filters Python/JS,
                               merges into dataset, writes JSON + data.js
        ↓
scripts/enrich_licenses.js  → fetches license.spdx_id via GitHub GraphQL API
                               (batched 50 repos/query, skips already-enriched)
        ↓
scripts/precompute_embeddings.js  → generates all-MiniLM-L6-v2 embeddings
                                     at build-time for the AI agent
```

Automated via **GitHub Actions** on days 1 and 16 of each month (`.github/workflows/update-trending-repos.yml`).

## Repo structure

```
github-trending-site/
├── .github/workflows/
│   └── update-trending-repos.yml   # cron: days 1 & 16, workflow_dispatch
├── scripts/
│   ├── fetch_trending.js           # fetch bonfy data, merge, write JSON/data.js
│   ├── enrich_licenses.js          # add license field via GitHub GraphQL API
│   ├── precompute_embeddings.js    # build-time embeddings for agent.html
│   ├── generate_data.py            # legacy: parse MD/JSON → JSON + index.html
│   ├── merge_repos.py              # legacy: merge 2023-2024 + 2025-2026 periods
│   └── extract_and_enrich.py       # legacy: extract from raw snapshots
├── data/
│   └── repos.json                  # master dataset (source of truth)
├── docs/
│   ├── index.html                  # main table UI (GitHub Pages root)
│   ├── agent.html                  # AI agent UI
│   ├── data.js                     # REPOS array for index.html
│   └── data/
│       ├── repos.json              # mirror of data/repos.json for Pages
│       └── repos_embeddings.json   # pre-computed embeddings (384-dim, 5895 entries)
├── package.json                    # @xenova/transformers for Node.js
└── README.md
```

## Usage

### Update dataset (fetch last 15 days from bonfy)

```bash
node scripts/fetch_trending.js --days 15
```

### Enrich licenses (skips repos already enriched)

```bash
# requires GITHUB_TOKEN or `gh auth login`
node scripts/enrich_licenses.js

# force re-fetch all
node scripts/enrich_licenses.js --all
```

### Regenerate embeddings (after adding new repos)

```bash
node scripts/precompute_embeddings.js
```

GitHub Pages serves from `docs/` on the `master` branch.

## Dataset fields

| Field | Description |
|---|---|
| `name` | `owner/repo` |
| `url` | GitHub URL |
| `lang` | `Python` or `Javascript` |
| `days` | Total days on GitHub trending |
| `desc` | Repository description |
| `rating` | Content potential: `High` / `Medium` / `Low` |
| `category` | One of 13 categories (Agentic AI, LLMs & Models, Web & APIs…) |
| `license` | SPDX identifier (`MIT`, `Apache-2.0`…) or `null` |

## License distribution (top)

| License | Repos |
|---|---:|
| MIT | 2,056 |
| Apache-2.0 | 1,232 |
| NOASSERTION | 609 |
| GPL-3.0 | 377 |
| AGPL-3.0 | 235 |
| *(no license)* | 1,057 |
