# GitHub Trending Site

Static GitHub Pages site listing **6,242 unique Python & JavaScript repositories** sourced from daily GitHub trending snapshots (2023–2026), enriched with category, stars, last commit, archived status, license and similar-repo suggestions.

## Live site

👉 [chaoticravena.github.io/github-trending-site](https://chaoticravena.github.io/github-trending-site)

## Features

- **6,242 repos**, Python and JavaScript (Go/Swift excluded)
- Category chips with counts, including **✳️ Claude Skills** (skills and plugins for Claude Code and other agents)
- Health dot per repo (active / slowing / inactive or archived) and stars
- Filters: language, status (not archived, commit in last 90 days, trending in last 30 days), license (incl. one-click "OK for commercial use"), potential
- Sort by days on trending, stars, recently trending, latest commit or name; filters, sort, page and open repo all live in the URL
- **Detail panel**: full description, stats, `git clone` copy, share link and 5 similar repos
- **Favorites** stored in the browser, exportable as a Markdown list
- Mobile layout (rows become cards) · `/` focuses search · `Esc` closes the panel
- **AI Agent** (`agent.html`): describe your project, get recommendations via semantic search + LLM (Anthropic, Groq, Gemini, OpenRouter)
- **[repo-scout skill](skills/repo-scout)**: Claude Code skill that searches this collection + live GitHub for repos that fit your project

## Data pipeline

```
bonfy/github-trending (daily .md snapshots on GitHub)
        ↓
scripts/fetch_trending.js        → fetches last N days, filters Python/JS, merges,
                                    sets days / last_seen / category
        ↓
scripts/enrich_github.js         → stars, pushed, archived, license via GitHub GraphQL
                                    (50 repos/query, refreshes every repo each run)
        ↓
scripts/precompute_embeddings.js → all-MiniLM-L6-v2 embeddings (int8, for the agent)
                                    + top-5 similar repos per repo (for the detail panel)
```

Automated via **GitHub Actions** on days 1 and 16 of each month (`.github/workflows/update-trending-repos.yml`).

## Repo structure

```
github-trending-site/
├── .github/workflows/
│   └── update-trending-repos.yml   # cron: days 1 & 16, workflow_dispatch
├── scripts/
│   ├── fetch_trending.js           # fetch bonfy data, merge, write JSON/data.js
│   ├── enrich_github.js            # stars, pushed, archived, license via GitHub GraphQL
│   ├── precompute_embeddings.js    # embeddings (agent) + similar repos (detail panel)
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
│       ├── embeddings.json         # 384-dim embeddings, int8 + base64 (~3 MB)
│       └── similar.json            # top-5 similar repos per repo (~300 KB)
├── skills/
│   └── repo-scout/                 # Claude Code skill (see its README)
├── package.json                    # @xenova/transformers for Node.js
└── README.md
```

## Usage

### Update dataset (fetch last 15 days from bonfy)

```bash
node scripts/fetch_trending.js --days 15

# backfill last_seen only (doesn't add days or repos)
node scripts/fetch_trending.js --days 365 --seen-only
```

### Refresh GitHub data (stars, last commit, archived, license)

```bash
# requires GITHUB_TOKEN or `gh auth login`
node scripts/enrich_github.js
```

### Regenerate embeddings + similar repos

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
| `last_seen` | Last date on GitHub trending (`YYYY-MM-DD`) |
| `rating` | Potential: `High` / `Medium` / `Low` (how strongly it trended) |
| `category` | One of 14 categories (Claude Skills, Agentic AI, LLMs & Models, Web & APIs…) |
| `license` | SPDX identifier (`MIT`, `Apache-2.0`…) or `null` |
| `stars` | Stargazers at last refresh |
| `pushed` | Date of last push (`YYYY-MM-DD`) |
| `archived` | `true` if archived, deleted or private |

## License distribution (top)

| License | Repos |
|---|---:|
| MIT | 2,222 |
| Apache-2.0 | 1,328 |
| *(no license)* | 1,065 |
| NOASSERTION | 644 |
| GPL-3.0 | 387 |
| AGPL-3.0 | 253 |
