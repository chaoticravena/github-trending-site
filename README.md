# GitHub Trending Site

Static GitHub Pages site showing Python & JavaScript trending repositories from 2023–2024, enriched with a **Content Potential** score (🔥 High / ⚡ Medium / 💤 Low).

## Live site

👉 [View on GitHub Pages](https://YOUR_USERNAME.github.io/github-trending-site)

## Features

- 4,749 repos sourced from daily GitHub trending snapshots (2023–2024)
- Search by name or description
- Filter by language (Python / JavaScript)
- Filter by content potential
- Sort any column
- Paginated (50 per page)

## Repo structure

```
github-trending-site/
├── scripts/
│   └── generate_data.py   # parses MD → JSON + index.html
├── data/
│   ├── repos_2023_2024_enriched.md   # source data
│   └── repos.json                    # generated
├── docs/
│   └── index.html                    # GitHub Pages root
└── README.md
```

## Regenerate the site

```bash
python scripts/generate_data.py
```

Then commit and push — GitHub Pages serves from `docs/`.
