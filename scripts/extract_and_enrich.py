"""
extract_and_enrich.py
Reads 2025 + 2026 trending .md files from the sibling github-trending-master folder.
- Languages : python, javascript only
- Excludes  : repos with "-macos" in the name
- Dedupes   : one entry per repo, most-recent description wins
- Sorts     : by trending frequency (days appeared) desc
- Enriches  : adds Content Potential (High / Medium / Low)
- Writes    : ../data/repos_2025_2026.md
"""

import re
from collections import defaultdict
from pathlib import Path

# ── paths ─────────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
TRENDING   = ROOT.parent / "github-trending-master"   # sibling folder
OUT        = ROOT / "data" / "repos_2025_2026.md"

YEARS  = {"2025", "2026"}
LANGS  = {"python", "javascript"}

# ── regexes ───────────────────────────────────────────────────────────────────
REPO_LINE   = re.compile(r'^\* \[.+?\]\(https://github\.com/([^)]+)\):?(.*)', re.IGNORECASE)
LANG_HEADER = re.compile(r'^####\s+(\w[\w\-]*)', re.IGNORECASE)

# ── content-potential scoring ─────────────────────────────────────────────────
HIGH_GROUPS = [
    ["gpt", "llm", "chatgpt", "openai", "claude", "gemini", "langchain",
     "stable-diffusion", "diffusion", "midjourney", "dall-e", "copilot",
     "huggingface", "transformers", "ggml", "llama", "mistral", "falcon",
     "generative", "text-to-image", "text-to-video", "whisper", "embeddings",
     "vector", "rag", "agent", "autogpt", "gpt4", "gpt-4", "gpt3",
     "neural", "deep learning", "machine learning", "artificial intelligence",
     "vibe coding", "mcp", "agentic", "cursor", "codex"],
    ["tutorial", "beginner", "learn", "learning", "guide", "primer",
     "30-days", "roadmap", "course", "interview", "prep", "cheatsheet",
     "algorithms", "data structure", "data-structure", "challenge",
     "from scratch", "for beginners", "flashcard", "awesome"],
    ["react", "next.js", "nextjs", "vue", "svelte", "angular", "nuxt",
     "tailwind", "bootstrap", "remix", "vite", "webpack", "babel",
     "typescript", "javascript framework", "web framework"],
    ["3d", "animation", "graphic", "canvas", "visualization", "visualiz",
     "audio", "video", "music", "image", "photo", "pixel", "shader",
     "webgl", "creative coding", "art", "game", "games", "gamedev",
     "rendering", "ui library", "component library"],
    ["automation", "automate", "workflow", "productivity", "cli tool",
     "command-line", "no-code", "low-code", "scraper", "crawler",
     "download", "youtube-dl", "yt-dlp", "obsidian", "notion",
     "home automation", "home assistant", "smart home"],
    ["discord", "tiktok", "youtube", "instagram", "twitter", "reddit",
     "telegram", "whatsapp", "social media", "streaming", "twitch",
     "content creator", "influencer"],
    ["vscode", "extension", "plugin", "neovim", "vim", "terminal",
     "shell", "zsh", "bash", "dotfiles", "devtools", "debugger",
     "linter", "formatter", "code generation"],
]

MEDIUM_GROUPS = [
    ["api", "rest api", "graphql", "sdk", "library", "framework"],
    ["security", "vulnerability", "pentest", "hacking", "exploit", "ctf",
     "cybersecurity", "infosec", "owasp"],
    ["docker", "kubernetes", "k8s", "devops", "ci/cd", "deploy",
     "infrastructure", "terraform", "helm", "ansible"],
    ["database", "sql", "postgres", "mysql", "mongodb", "redis",
     "sqlite", "orm", "migration"],
    ["testing", "test", "e2e", "unit test", "mock", "benchmark"],
    ["monitoring", "dashboard", "metrics", "logging", "observability",
     "analytics", "grafana"],
    ["blockchain", "crypto", "web3", "nft", "solidity", "ethereum",
     "defi", "smart contract"],
    ["mobile", "ios", "android", "react native", "flutter",
     "cross-platform"],
    ["iot", "raspberry", "arduino", "hardware", "embedded", "firmware"],
]

LOW_PATTERNS = [
    r"\bxray\b", r"\bvmess\b", r"\bvless\b", r"\btrojan proxy\b",
    r"\bwireguard panel\b", r"\bopenzeppelin\b", r"\bsolidity\b",
    r"\bzigbee\b", r"\bmqtt\b", r"multi-protocol", r"expire day & traffic",
    r"\bcosign\b", r"\bminikube\b",
]

def score(name: str, desc: str, days: int) -> str:
    text       = (name + " " + desc).lower()
    high_hits  = sum(1 for g in HIGH_GROUPS  if any(kw in text for kw in g))
    med_hits   = sum(1 for g in MEDIUM_GROUPS if any(kw in text for kw in g))
    low_pen    = sum(1 for p in LOW_PATTERNS  if re.search(p, text))
    freq_bonus = 1 if days >= 60 else 0
    s = high_hits * 2 + med_hits - low_pen + freq_bonus
    return "High" if s >= 4 else "Medium" if s >= 2 else "Low"

RATING_EMOJI = {"High": "🔥", "Medium": "⚡", "Low": "💤"}

# ── file collection ───────────────────────────────────────────────────────────
def collect_md_files() -> list[Path]:
    if not TRENDING.exists():
        raise FileNotFoundError(f"github-trending-master not found at: {TRENDING}")
    return sorted(p for p in TRENDING.rglob("*.md") if p.stem[:4] in YEARS)

# ── parse one file ────────────────────────────────────────────────────────────
def parse_file(path: Path) -> list[dict]:
    entries, current_lang = [], ""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.rstrip("\n")
            m = LANG_HEADER.match(line)
            if m:
                current_lang = m.group(1).lower()
                continue
            if current_lang not in LANGS:
                continue
            m = REPO_LINE.match(line)
            if m:
                name = m.group(1).strip()
                desc = m.group(2).strip()
                if "-macos" not in name.lower():
                    entries.append({"name": name, "language": current_lang, "description": desc})
    return entries

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    md_files = collect_md_files()
    print(f"Files   : {len(md_files)} (2025-2026)")

    frequency: dict[str, int]  = defaultdict(int)
    latest:    dict[str, dict] = {}

    for path in md_files:
        seen_today: set[str] = set()
        for entry in parse_file(path):
            name = entry["name"]
            if name not in seen_today:
                frequency[name] += 1
                seen_today.add(name)
            latest[name] = entry

    print(f"Unique  : {len(latest):,} repos")

    sorted_repos = sorted(
        latest.values(),
        key=lambda r: (-frequency[r["name"]], r["name"].lower())
    )

    counts = {"High": 0, "Medium": 0, "Low": 0}
    OUT.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("# GitHub Trending — Python & JavaScript (2025–2026)\n\n")
        f.write(f"> Extracted from **{len(md_files)} daily files** | "
                f"**{len(sorted_repos):,} unique repos** | sorted by trending frequency\n")
        f.write(">\n")
        # rating breakdown placeholder — fill after counting
        placeholder = "> __RATINGS__\n"
        f.write(placeholder)
        f.write("\n---\n\n")
        f.write("| # | Repo | Language | Days Trending | Description | Content Potential |\n")
        f.write("|---|------|----------|:-------------:|-------------|:-----------------:|\n")

        for i, r in enumerate(sorted_repos, 1):
            name  = r["name"]
            lang  = r["language"].capitalize()
            desc  = r["description"].replace("|", "\\|")
            days  = frequency[name]
            url   = f"https://github.com/{name}"
            rating = score(name, r["description"], days)
            counts[rating] += 1
            emoji  = RATING_EMOJI[rating]
            f.write(f"| {i} | [{name}]({url}) | {lang} | {days} | {desc} | {emoji} {rating} |\n")

    # Patch the placeholder with real counts
    text = OUT.read_text(encoding="utf-8")
    rating_line = (f"**Ratings:** "
                   f"🔥 High: {counts['High']:,} · "
                   f"⚡ Medium: {counts['Medium']:,} · "
                   f"💤 Low: {counts['Low']:,}")
    OUT.write_text(text.replace("__RATINGS__", rating_line), encoding="utf-8")

    print(f"High    : {counts['High']:,}")
    print(f"Medium  : {counts['Medium']:,}")
    print(f"Low     : {counts['Low']:,}")
    print(f"Saved   : {OUT}")

    # Top-10 preview
    print("\nTop 10 by frequency:")
    for r in sorted_repos[:10]:
        print(f"  {frequency[r['name']]:>3}d  [{r['language']}]  {r['name']}")

if __name__ == "__main__":
    main()
