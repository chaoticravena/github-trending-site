"""
fetch_trending.py

Busca os últimos N_DAYS do bonfy/github-trending, filtra Python/JavaScript,
mescla com o dataset existente (docs/data/repos.json) e regenera os artefatos
web (docs/data.js, docs/index.html).

Uso:  python scripts/fetch_trending.py [--days 15]
"""

import json
import re
import sys
import subprocess
import argparse
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path
from collections import Counter

ROOT       = Path(__file__).parent.parent
REPOS_JSON = ROOT / "data" / "repos.json"   # fonte de dados do projeto
DOCS_JSON  = ROOT / "docs" / "data" / "repos.json"  # mirror para GitHub Pages

ALLOWED_LANGS = {"python", "javascript"}

# Mapeamento para o formato canônico do projeto
LANG_CANONICAL = {"python": "Python", "javascript": "Javascript"}

# ── categorias (idêntico ao generate_data.py para consistência) ──────────────
CATEGORIES = [
    ("Agentic AI", [
        "agent", "crewai", "autogen", "langgraph", "mcp", "tool-calling",
        "tool_calling", "autonomous", "multi-agent", "multiagent", "agentic",
    ]),
    ("LLMs & Models", [
        "llm", "gpt", "claude", "llama", "mistral", "gemini", "fine-tun",
        "finetun", "gguf", "ollama", "ggml", "transformers", "huggingface",
        "openai", "chatgpt", "anthropic", "deepseek", "qwen", "falcon",
        "vllm", "lora", "rlhf",
    ]),
    ("Image & Video", [
        "diffusion", "comfyui", "stable-diffusion", "stablediffusion",
        "image generation", "text-to-image", "text-to-video", "animate",
        "gan", "inpaint", "controlnet", "dreambooth", "video generation", "img2img",
    ]),
    ("Audio & Voice", [
        "tts", "whisper", "speech", "voice", "audio", "music",
        "text-to-speech", "stt", "asr", "transcri", "vocal",
    ]),
    ("Data & Analytics", [
        "pandas", "etl", "dbt", "kafka", "airflow", "polars", "spark",
        "databricks", "bigquery", "redshift", "snowflake", "pyspark",
        "data analysis", "data cleaning", "sql", "warehouse", "analytics",
        "matplotlib", "plotly", "jupyter",
    ]),
    ("Security", [
        "pentest", "osint", "ctf", "vulnerability", "forensic", "exploit",
        "hacking", "malware", "reverse engineer", "cybersecurity", "infosec",
        "owasp", "xss", "injection", "zero-day",
    ]),
    ("Games & Creative", [
        "game", "3d", "pixel", "canvas", "shader", "graphics",
        "opengl", "unity", "godot", "pygame", "raylib", "threejs", "creative coding",
    ]),
    ("Self-hosted", [
        "self-host", "selfhost", "homelab", "home assistant", "nas",
        "nextcloud", "jellyfin", "plex", "immich", "download manager",
        "paperless", "torrent", "media server",
    ]),
    ("Automation & Bots", [
        "bot", "automat", "workflow", "n8n", "selenium", "playwright",
        "rpa", "scraper", "crawler", "zapier", "webhook", "scheduler",
    ]),
    ("Learning", [
        "tutorial", "course", "roadmap", "awesome", "interview", "book",
        "guide", "learn", "beginner", "30-days", "cheatsheet", "primer",
        "from scratch", "algorithms", "data structure", "system design", "leetcode",
    ]),
    ("DevTools", [
        "cli", "docker", "kubernetes", "k8s", "lint", "test", "debug",
        "monitor", "infra", "devops", "terraform", "helm", "ansible",
        "formatter", "linter", "vscode", "vim", "neovim", "shell", "zsh",
        "ci/cd", "github action", "build tool",
    ]),
    ("Web & APIs", [
        "fastapi", "django", "flask", "react", "next.js", "nextjs", "vue",
        "svelte", "angular", "graphql", "nuxt", "tailwind", "bootstrap",
        "express", "nodejs", "rest api", "frontend", "backend", "fullstack",
        "typescript", "web framework",
    ]),
]
OTHER = "Other"

def categorise(name: str, desc: str) -> str:
    text = (name + " " + desc).lower()
    for label, kws in CATEGORIES:
        if any(kw in text for kw in kws):
            return label
    return OTHER

# ── fetch bonfy raw file ──────────────────────────────────────────────────────
# 2026 files are at root; earlier years are in YYYY/ subfolders.
def bonfy_url(d: date) -> str:
    date_str = d.strftime("%Y-%m-%d")
    if d.year >= 2026:
        return f"https://raw.githubusercontent.com/bonfy/github-trending/master/{date_str}.md"
    return f"https://raw.githubusercontent.com/bonfy/github-trending/master/{d.year}/{date_str}.md"

def fetch_raw(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "fetch_trending/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status == 200:
                return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            print(f"  HTTP {e.code}: {url}", file=sys.stderr)
    except Exception as e:
        print(f"  Erro ao buscar {url}: {e}", file=sys.stderr)
    return None

# ── parser do formato bonfy ───────────────────────────────────────────────────
# Cada repo: * [owner / repo](url):descrição
REPO_RE = re.compile(r"^\* \[([^\]]+)\]\(([^)]+)\)(?::(.*))?$")

def parse_bonfy_md(content: str) -> list[dict]:
    repos = []
    current_lang = None
    for line in content.splitlines():
        line = line.rstrip()
        if line.startswith("#### "):
            current_lang = line[5:].strip().lower()
        elif line.startswith("* [") and current_lang in ALLOWED_LANGS:
            m = REPO_RE.match(line)
            if not m:
                continue
            # "owner / repo" → "owner/repo"
            raw_name = re.sub(r"\s*/\s*", "/", m.group(1).strip())
            url  = m.group(2).strip()
            desc = (m.group(3) or "").strip()
            repos.append({
                "name": raw_name,
                "url":  url,
                "desc": desc,
                "lang": LANG_CANONICAL[current_lang],
            })
    return repos

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=15,
                        help="Quantos dias buscar do bonfy (default: 15)")
    args = parser.parse_args()

    today = date.today()
    dates = [today - timedelta(days=i) for i in range(args.days)]

    # 1) Buscar bonfy ----------------------------------------------------------
    print(f"Buscando {args.days} dias do bonfy/github-trending...")
    # url→{name, url, lang, desc, appearances}
    bonfy_map: dict[str, dict] = {}
    fetched = 0
    for d in reversed(dates):   # cronológico (mais antigo → mais novo)
        url = bonfy_url(d)
        content = fetch_raw(url)
        if content is None:
            print(f"  {d}  404/erro — ignorado")
            continue
        repos = parse_bonfy_md(content)
        fetched += 1
        print(f"  {d}  {len(repos):>3} repos (Python/JS)")
        for r in repos:
            key = r["url"]
            if key in bonfy_map:
                bonfy_map[key]["appearances"] += 1
                # Atualiza desc se vier preenchida
                if r["desc"] and not bonfy_map[key]["desc"]:
                    bonfy_map[key]["desc"] = r["desc"]
            else:
                bonfy_map[key] = {**r, "appearances": 1}

    print(f"\nTotal de datas buscadas: {fetched}/{args.days}")
    print(f"Repos únicos Python/JS no período: {len(bonfy_map)}")

    # Filtra explicitamente Go/Swift (salvaguarda)
    go_swift_skipped = sum(
        1 for r in bonfy_map.values()
        if r["lang"] not in ("Python", "Javascript")
    )
    if go_swift_skipped:
        print(f"Repos Go/Swift ignorados: {go_swift_skipped}")
    bonfy_map = {k: v for k, v in bonfy_map.items()
                 if v["lang"] in ("Python", "Javascript")}

    # 2) Carregar dataset existente -------------------------------------------
    existing: dict[str, dict] = {}
    if REPOS_JSON.exists():
        for r in json.loads(REPOS_JSON.read_text(encoding="utf-8")):
            existing[r["url"]] = r
    print(f"Repos existentes no dataset: {len(existing)}")

    # 3) Mesclar ---------------------------------------------------------------
    added   = 0
    updated = 0
    for url, bonfy in bonfy_map.items():
        app = bonfy["appearances"]
        if url in existing:
            # Repo já existe: incrementa dias e atualiza desc se vazia
            existing[url]["days"] = existing[url].get("days", 0) + app
            if bonfy["desc"] and not existing[url].get("desc"):
                existing[url]["desc"] = bonfy["desc"]
            updated += 1
        else:
            # Repo novo
            rating = "High" if app >= 5 else ("Medium" if app >= 2 else "Low")
            existing[url] = {
                "name":  bonfy["name"],
                "url":   url,
                "lang":  bonfy["lang"],
                "days":  app,
                "desc":  bonfy["desc"],
                "rating": rating,
            }
            added += 1

    print(f"\nNovos repos adicionados : {added}")
    print(f"Repos existentes incrementados: {updated}")

    # 4) Aplicar category e recomputar rating para todos os novos -------------
    for r in existing.values():
        r["category"] = categorise(r["name"], r.get("desc", ""))
        # Só recomputa rating para repos sem histórico longo (novos do bonfy)
        if r.get("days", 0) <= 15 and r.get("rating") in (None, ""):
            d = r["days"]
            r["rating"] = "High" if d >= 5 else ("Medium" if d >= 2 else "Low")

    # 5) Re-rankear por days desc ---------------------------------------------
    merged = sorted(existing.values(), key=lambda r: (-r.get("days", 0), r["name"].lower()))
    for i, r in enumerate(merged, 1):
        r["rank"] = i

    # Estatísticas de linguagem
    lang_count = Counter(r["lang"] for r in merged)
    print(f"\nDataset final: {len(merged)} repos")
    for lang, n in sorted(lang_count.items(), key=lambda x: -x[1]):
        print(f"  {lang:<12} {n:>5}")
    go_swift = sum(n for lang, n in lang_count.items()
                   if lang.lower() in ("go", "swift"))
    print(f"  Go + Swift   {go_swift:>5}  (deve ser 0)")

    # 6) Salvar ---------------------------------------------------------------
    json_text = json.dumps(merged, ensure_ascii=False, indent=2)
    REPOS_JSON.parent.mkdir(parents=True, exist_ok=True)
    REPOS_JSON.write_text(json_text, encoding="utf-8")
    print(f"\nSalvo: {REPOS_JSON}  ({REPOS_JSON.stat().st_size // 1024} KB)")

    DOCS_JSON.parent.mkdir(parents=True, exist_ok=True)
    DOCS_JSON.write_text(json_text, encoding="utf-8")
    print(f"Salvo: {DOCS_JSON}  ({DOCS_JSON.stat().st_size // 1024} KB)")

    # 7) Regenerar artefatos web (data.js + index.html) -----------------------
    print("\nRegenerando docs/data.js e docs/index.html ...")
    subprocess.run(
        [sys.executable, "scripts/generate_data.py", "repos.json", "data/repos.json"],
        cwd=ROOT, check=True
    )
    print("\nConcluído.")

if __name__ == "__main__":
    main()
