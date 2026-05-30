# GitHub Trending Site

Static GitHub Pages site listing **5,849 unique Python & JavaScript repositories** sourced from daily GitHub trending snapshots (2023–2026), enriched with a **Content Potential** score (🔥 High / ⚡ Medium / 💤 Low).

## Live site

👉 [chaoticravena.github.io/github-trending-site](https://chaoticravena.github.io/github-trending-site)

## Features

- **5,849 repos** merged from 2023–2024 (4,749) and 2025–2026 (2,088), deduplicated
- Search by name or description
- Filter by language (Python / JavaScript)
- Filter by Content Potential (🔥 High / ⚡ Medium / 💤 Low)
- Sort any column
- Paginated — 50 repos per page

## Data pipeline

```
github-trending-master/        ← sibling folder with raw daily .md snapshots
        2023/ 2024/ 2025/ 2026-*.md

scripts/extract_and_enrich.py  → data/repos_2025_2026.md
                                   (extract Python+JS, score content potential)

scripts/merge_repos.py         → data/repos_2023_2024.json
                                  data/repos_2025_2026.json
                                  data/repos.json  (merged, deduped, re-ranked)
                                  docs/index.html

scripts/generate_data.py [src] [json_out]
                               → reads .md or .json, writes JSON + docs/index.html
```

## Repo structure

```
github-trending-site/
├── scripts/
│   ├── extract_and_enrich.py  # 2025-2026 extraction + Content Potential scoring
│   ├── merge_repos.py         # merge both periods, dedupe, rebuild site
│   └── generate_data.py       # parse source (MD or JSON) → JSON + index.html
├── data/
│   ├── repos_2023_2024_enriched.md   # enriched source — 2023-2024
│   ├── repos_2025_2026.md            # enriched source — 2025-2026
│   ├── repos_2023_2024.json          # per-period JSON
│   ├── repos_2025_2026.json          # per-period JSON
│   └── repos.json                    # merged dataset (site source of truth)
├── docs/
│   └── index.html                    # GitHub Pages root (self-contained)
└── README.md
```

## Usage

### Add new data and rebuild

```bash
# 1. Re-extract 2025-2026 from github-trending-master
python scripts/extract_and_enrich.py

# 2. Merge all periods and rebuild the site
python scripts/merge_repos.py

# 3. Push
git add . && git commit -m "update data" && git push
```

### Rebuild site from a specific source

```bash
# From an enriched .md file
python scripts/generate_data.py repos_2025_2026.md data/repos.json

# From the merged JSON directly
python scripts/generate_data.py repos.json data/repos.json
```

GitHub Pages serves from `docs/` on the `master` branch.

## Content Potential scoring

Each repo is scored on its name + description against keyword groups:

| Signal | Points |
|--------|-------:|
| AI/LLM, learning resources, popular frameworks, visual/creative, automation, social media, DX tools | +2 per group matched |
| APIs, security, DevOps, databases, testing, blockchain, mobile, IoT | +1 per group matched |
| Trending ≥ 60 days | +1 bonus |
| Low-signal patterns (proxy panels, niche infra, etc.) | −1 each |

**Thresholds:** `≥ 4 → 🔥 High` · `2–3 → ⚡ Medium` · `0–1 → 💤 Low`
