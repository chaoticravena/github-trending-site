"""
merge_repos.py
Parses the two enriched .md files, produces per-period JSONs, then
merges into data/repos.json — deduplicating by repo name and keeping
the highest `days` value. Rebuilds docs/index.html via generate_data.py.

Outputs
  data/repos_2023_2024.json
  data/repos_2025_2026.json
  data/repos.json          (merged, re-ranked by days desc)
  docs/index.html
"""

import json, re, sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA = ROOT / "data"

ROW_RE = re.compile(
    r'^\| (\d+) \| \[([^\]]+)\]\(([^)]+)\) \| (\w+) \| (\d+) \| (.*?) \| (.+?) \|$'
)

# ── parse one enriched MD ─────────────────────────────────────────────────────
def parse_md(path: Path) -> list[dict]:
    repos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        raw   = m.group(7).strip()
        label = re.search(r'(High|Medium|Low)', raw)
        label = label.group(1) if label else "Low"
        repos.append({
            "rank":   int(m.group(1)),
            "name":   m.group(2).strip(),
            "url":    m.group(3).strip(),
            "lang":   m.group(4).strip(),
            "days":   int(m.group(5)),
            "desc":   m.group(6).strip(),
            "rating": label,
        })
    return repos

# ── write pretty JSON ─────────────────────────────────────────────────────────
def save_json(path: Path, data: list[dict]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  Written {path.name:<35} {len(data):>5} repos  {path.stat().st_size//1024} KB")

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    md_a = DATA / "repos_2023_2024_enriched.md"
    md_b = DATA / "repos_2025_2026.md"

    for md in (md_a, md_b):
        if not md.exists():
            sys.exit(f"Missing: {md}")

    # 1 ── parse both periods
    print("Parsing source files ...")
    repos_a = parse_md(md_a)   # 2023-2024
    repos_b = parse_md(md_b)   # 2025-2026
    print(f"  2023-2024 : {len(repos_a):,} repos")
    print(f"  2025-2026 : {len(repos_b):,} repos")

    # 2 ── save per-period JSONs
    print("\nSaving per-period JSONs ...")
    save_json(DATA / "repos_2023_2024.json", repos_a)
    save_json(DATA / "repos_2025_2026.json", repos_b)

    # 3 ── merge: deduplicate by name, keep highest days
    print("\nMerging ...")
    merged: dict[str, dict] = {}

    for repo in repos_a + repos_b:
        name = repo["name"]
        if name not in merged or repo["days"] > merged[name]["days"]:
            merged[name] = repo

    # Re-rank by days descending (ties broken alphabetically)
    sorted_merged = sorted(
        merged.values(),
        key=lambda r: (-r["days"], r["name"].lower())
    )
    for i, r in enumerate(sorted_merged, 1):
        r["rank"] = i

    dupes = len(repos_a) + len(repos_b) - len(sorted_merged)
    print(f"  {len(repos_a):,} + {len(repos_b):,} entries")
    print(f"  {dupes:,} duplicates removed")
    print(f"  {len(sorted_merged):,} unique repos in merged set")

    save_json(DATA / "repos.json", sorted_merged)

    # 4 ── rebuild HTML by calling generate_data.py as a subprocess
    import subprocess
    print("\nRebuilding docs/index.html ...")
    subprocess.run(
        [sys.executable, "scripts/generate_data.py", "repos.json", "data/repos.json"],
        cwd=ROOT, check=True
    )

    print("\nDone.")
    print(f"  Top 5 by days:")
    for r in sorted_merged[:5]:
        print(f"    {r['days']:>3}d  [{r['lang']:<10}]  {r['name']}")

if __name__ == "__main__":
    main()
