"""
strip_desc_suffix.py

One-shot: strips the ' — for <audience>' suffix that enrich_descriptions.py
adds to desc fields, then regenerates docs/data.js and docs/index.html.

Run once; generate_data.py will keep stripping on future regenerations.
"""
import json, re, subprocess, sys
from pathlib import Path

ROOT      = Path(__file__).parent.parent
SUFFIX_RE = re.compile(r'\s*—\s*for\s.+$', re.IGNORECASE)
SOURCES   = [
    ROOT / "data" / "repos_enriched.json",
    ROOT / "data" / "repos.json",
]

def strip(desc: str) -> str:
    return SUFFIX_RE.sub('', desc).strip() if desc else desc

def process(path: Path) -> None:
    if not path.exists():
        return
    repos = json.loads(path.read_text(encoding="utf-8"))
    before = sum(len(r.get("desc", "")) for r in repos)
    changed = 0
    for r in repos:
        old = r.get("desc", "")
        new = strip(old)
        if new != old:
            r["desc"] = new
            changed += 1
    after = sum(len(r.get("desc", "")) for r in repos)
    path.write_text(json.dumps(repos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{path.name}: {changed:,} descs trimmed, -{before - after:,} chars")

def main():
    print("=== strip_desc_suffix ===")
    for src in SOURCES:
        process(src)

    print("\nRegenerating site...")
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "generate_data.py")],
        cwd=ROOT, check=True
    )

if __name__ == "__main__":
    main()
