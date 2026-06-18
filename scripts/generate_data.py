"""
generate_data.py  [source_md_or_json]  [json_out]

  source   - .md or .json filename inside data/  (default: repos_enriched.json)
  json_out - path relative to project root        (default: data/repos.json)

Assigns granular category labels, writes JSON + docs/index.html.
"""

import json, re, sys, shutil
from collections import Counter
from pathlib import Path

ROOT     = Path(__file__).parent.parent
HTML_OUT = ROOT / "docs" / "index.html"

# ── CLI args ──────────────────────────────────────────────────────────────────
_src_name = sys.argv[1] if len(sys.argv) > 1 else "repos_enriched.json"
_json_rel = sys.argv[2] if len(sys.argv) > 2 else "data/repos.json"
SRC      = ROOT / "data" / _src_name
JSON_OUT = ROOT / _json_rel

# ── page title from filename ──────────────────────────────────────────────────
_ym = re.search(r'(\d{4})[_\-](\d{4})', _src_name)
YEAR_RANGE = f"{_ym.group(1)}–2026" if _ym and _ym.group(2) == "2026" \
             else (f"{_ym.group(1)}–{_ym.group(2)}" if _ym else "2023–2026")
TITLE    = f"GitHub Trending {YEAR_RANGE}"
SUBTITLE = "Python &amp; JavaScript · sorted by days on trending · content potential &amp; category scored"

# ── categories (ordered: first match wins) ────────────────────────────────────
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

# ── parse source (.json or .md) ───────────────────────────────────────────────
ROW_RE = re.compile(
    r'^\| (\d+) \| \[([^\]]+)\]\(([^)]+)\) \| (\w+) \| (\d+) \| (.*?) \| (.+?) \|$'
)

def parse_source(path: Path) -> list[dict]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
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

# ── HTML template ─────────────────────────────────────────────────────────────
HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>chaoticravena/repos · __TITLE__ · Python &amp; JS</title>
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Press+Start+2P&family=VT323&display=swap" rel="stylesheet">
<style>
:root{
  --bg:#0c0c0f;--surface:#13131a;--border:#1e1e2e;
  --text:#e8e8f0;--muted:#6666880;
  --pink:#ff6eb4;--teal:#00a896;
  --high:#ff6eb4;--med:#ffd700;--low:#555570;
}
*{box-sizing:border-box;margin:0;padding:0;border-radius:0!important}

body{
  background:var(--bg);
  color:var(--text);
  font-family:'VT323',monospace;
  font-size:19px;
  line-height:1.45;
  min-height:100vh;
  overflow-x:hidden;
}
a{color:var(--pink);text-decoration:none}
a:hover{color:var(--teal);text-decoration:underline}

@keyframes blink{0%,100%{opacity:1}50%{opacity:0}}
@keyframes px-load{from{width:0}to{width:100%}}
@keyframes scanline{0%{transform:translateY(-100%)}100%{transform:translateY(100vh)}}

/* ── loading screen ── */
#loading-screen{
  position:fixed;inset:0;background:var(--bg);z-index:9999;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:1.25rem;
}
.px-load-title{
  font-family:'Press Start 2P',monospace;font-size:clamp(8px,2vw,13px);
  color:var(--pink);text-shadow:0 0 12px var(--pink);letter-spacing:.1em;
}
.px-load-bar{
  width:220px;height:20px;border:2px solid var(--pink);
  background:var(--bg);position:relative;overflow:hidden;
}
.px-load-fill{
  height:100%;background:var(--pink);
  animation:px-load .9s steps(11) forwards;
}
.px-load-sub{
  font-family:'VT323',monospace;font-size:16px;color:var(--teal);letter-spacing:.05em;
}

/* ── CRT scanline (subtle, fixed) ── */
body::before{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:9998;
  background:repeating-linear-gradient(
    to bottom,
    transparent 0px,
    transparent 2px,
    rgba(0,0,0,.08) 2px,
    rgba(0,0,0,.08) 4px
  );
}

/* ── floating Win95 error dialogs ── */
.win95-bg{position:fixed;inset:0;pointer-events:none;z-index:0;overflow:hidden}
.err-dlg{
  position:absolute;width:190px;
  background:#c0c0c0;border:2px solid;
  border-color:#fff #808080 #808080 #fff;
  opacity:.045;font-size:11px;color:#000;
  font-family:'Segoe UI',Arial,sans-serif;
}
.err-bar{
  background:#000080;color:#fff;
  padding:2px 4px;display:flex;justify-content:space-between;
  font-weight:bold;font-size:11px;align-items:center;
}
.err-xbtn{
  width:16px;height:14px;background:#c0c0c0;
  border:2px solid;border-color:#fff #808080 #808080 #fff;
  font-size:9px;display:inline-flex;align-items:center;justify-content:center;
}
.err-body{padding:10px;display:flex;gap:8px;align-items:flex-start;line-height:1.4}
.err-ico{font-size:22px}
.err-btns{padding:0 8px 8px;display:flex;justify-content:center;gap:6px}
.err-btn{
  min-width:58px;background:#c0c0c0;
  border:2px solid;border-color:#fff #808080 #808080 #fff;
  font-size:11px;font-family:'Segoe UI',Arial,sans-serif;padding:3px 6px;
}

/* ── page wrapper ── */
.page-wrap{position:relative;z-index:1}

/* ── header ── */
header{
  border-bottom:2px solid var(--teal);
  padding:1.75rem 1.5rem 1.25rem;
  position:relative;
}
.win-bar{
  display:flex;align-items:center;gap:.6rem;
  background:var(--teal);padding:.3rem .75rem;
  margin-bottom:1rem;
  box-shadow:4px 4px 0 var(--pink);
}
.win-bar-title{
  font-family:'Press Start 2P',monospace;font-size:8px;
  color:var(--bg);flex:1;text-align:center;letter-spacing:.06em;
}
.win-dots{display:flex;gap:5px}
.win-dot{
  width:11px;height:11px;background:var(--bg);
  border:1px solid rgba(0,0,0,.3);display:inline-block;
}
.win-dot.close{background:var(--pink)}

header h1{
  font-family:'Press Start 2P',monospace;
  font-size:clamp(9px,2.5vw,20px);
  color:var(--pink);
  text-shadow:3px 3px 0 rgba(0,168,150,.35);
  line-height:1.5;margin-bottom:.5rem;
}
.year-tag{
  font-family:'VT323',monospace;font-size:17px;
  color:var(--teal);margin-bottom:.25rem;
}
header p.sub{color:var(--muted,#666688);font-size:17px}

/* ── agent button ── */
.agent-link{
  display:inline-block;margin-top:.9rem;
  background:transparent;color:var(--pink);
  border:2px solid var(--pink);
  padding:.4rem 1rem;
  font-family:'Press Start 2P',monospace;font-size:8px;
  text-decoration:none;
  box-shadow:3px 3px 0 var(--teal);
  transition:box-shadow .08s,transform .08s,color .08s,border-color .08s;
}
.agent-link:hover{
  box-shadow:1px 1px 0 var(--teal);
  transform:translate(2px,2px);
  color:var(--teal);border-color:var(--teal);
  text-decoration:none;
}
.agent-link:active{box-shadow:none;transform:translate(3px,3px)}
.cursor{animation:blink 1s step-start infinite}

/* ── stats ── */
.stats{display:flex;gap:.6rem;flex-wrap:wrap;margin-top:1rem}
.stat{
  background:var(--surface);border:1px solid var(--border);
  border-bottom:2px solid var(--teal);
  padding:.25rem .7rem;font-size:17px;color:var(--muted,#666688);
}
.stat span{
  font-family:'Press Start 2P',monospace;font-size:9px;
  color:var(--text);display:inline-block;margin-right:4px;
}

/* ── controls ── */
.controls{
  display:flex;gap:.5rem;flex-wrap:wrap;padding:.65rem 1.5rem;
  background:var(--surface);border-bottom:2px solid var(--border);
  align-items:center;
}
input,select{
  background:var(--bg);border:2px solid var(--border);
  color:var(--teal);padding:.3rem .55rem;
  font-family:'VT323',monospace;font-size:19px;outline:none;
  caret-color:var(--pink);
}
input{flex:1;min-width:160px}
input:focus{border-color:var(--pink);color:var(--text)}
input::placeholder{color:#44445a}
select:focus{border-color:var(--teal)}
option{background:var(--surface);color:var(--text)}
.count{color:#44445a;font-size:16px;margin-left:auto;font-family:'VT323',monospace}

/* ── table ── */
.table-wrap{overflow-x:auto;padding:0 1.5rem 2rem}
table{width:100%;border-collapse:collapse;margin-top:.6rem;font-size:18px}

th{
  position:sticky;top:0;background:var(--bg);
  border-bottom:2px solid var(--teal);
  padding:.4rem .55rem;text-align:left;
  color:var(--teal);cursor:pointer;user-select:none;white-space:nowrap;
  font-family:'Press Start 2P',monospace;font-size:7px;text-transform:uppercase;
}
th:hover{color:var(--pink)}
th.sort-asc::after{content:" [^]";color:var(--pink)}
th.sort-desc::after{content:" [v]";color:var(--pink)}

td{
  padding:.38rem .55rem;border-bottom:1px solid var(--border);
  vertical-align:top;font-family:'VT323',monospace;
}
tr:hover td{background:rgba(255,110,180,.035)}
.rank{color:#44445a;width:40px;font-size:15px}
.days{color:var(--teal);width:52px;font-weight:600}
.desc{color:#888899;max-width:310px;font-size:17px}
.lang-py{color:#4ec9b0}
.lang-js{color:#ffd700}

/* ── badges ── */
.badge{
  display:inline-flex;align-items:center;gap:3px;
  padding:1px 5px;font-family:'Press Start 2P',monospace;font-size:6px;
  font-weight:600;white-space:nowrap;border:1px solid currentColor;
}
.badge-High{background:rgba(255,110,180,.12);color:var(--high)}
.badge-Medium{background:rgba(255,215,0,.1);color:var(--med)}
.badge-Low{background:rgba(80,80,100,.15);color:var(--low)}

.cat-badge{
  display:inline-flex;align-items:center;gap:3px;
  padding:1px 5px;font-family:'VT323',monospace;font-size:15px;
  font-weight:600;white-space:nowrap;
  /* color/bg via inline style */
}

/* ── pagination ── */
.pagination{
  display:flex;gap:.45rem;align-items:center;justify-content:center;
  padding:.85rem;border-top:1px solid var(--border);
  font-family:'VT323',monospace;font-size:19px;color:#44445a;
}
.pagination button{
  background:var(--surface);border:2px solid var(--border);
  color:var(--text);padding:.2rem .55rem;cursor:pointer;
  font-family:'VT323',monospace;font-size:19px;
  box-shadow:2px 2px 0 var(--teal);
  transition:box-shadow .07s,transform .07s,border-color .07s,color .07s;
}
.pagination button:disabled{opacity:.25;cursor:default;box-shadow:none}
.pagination button:not(:disabled):hover{
  border-color:var(--pink);color:var(--pink);box-shadow:2px 2px 0 var(--pink);
}
.pagination button:not(:disabled):active{box-shadow:none;transform:translate(2px,2px)}

/* ── empty state ── */
.empty-win{
  width:300px;margin:2.5rem auto;background:#c0c0c0;
  border:3px solid;border-color:#fff #808080 #808080 #fff;
  font-family:'Segoe UI',Arial,sans-serif;font-size:12px;color:#000;
}
.ew-bar{
  background:#000080;color:#fff;padding:3px 6px;
  display:flex;justify-content:space-between;align-items:center;
  font-weight:bold;font-size:12px;
}
.ew-xbtn{
  width:16px;height:14px;background:#c0c0c0;
  border:2px solid;border-color:#fff #808080 #808080 #fff;
  font-size:9px;display:inline-flex;align-items:center;justify-content:center;
}
.ew-body{padding:16px;display:flex;flex-direction:column;align-items:center;gap:10px;text-align:center}
.ew-ico{font-size:30px}
.ew-btn{
  min-width:70px;background:#c0c0c0;
  border:2px solid;border-color:#fff #808080 #808080 #fff;
  font-family:'Segoe UI',Arial,sans-serif;font-size:12px;padding:4px 8px;cursor:pointer;
}
.ew-btn:active{border-color:#808080 #fff #fff #808080}

/* ── footer ── */
footer{
  text-align:center;padding:.65rem;
  color:#44445a;font-size:15px;
  border-top:2px solid var(--border);background:var(--surface);
  font-family:'VT323',monospace;
}
</style>
</head>
<body>

<!-- pixel art loading screen -->
<div id="loading-screen">
  <div class="px-load-title">LOADING...</div>
  <div class="px-load-bar"><div class="px-load-fill"></div></div>
  <div class="px-load-sub">chaoticravena/repos · __YEAR_RANGE__</div>
</div>

<!-- decorative Win95 error dialogs -->
<div class="win95-bg" aria-hidden="true">
  <div class="err-dlg" style="top:7%;left:4%;transform:rotate(-4deg)">
    <div class="err-bar"><span>ERROR</span><span class="err-xbtn">✕</span></div>
    <div class="err-body"><span class="err-ico">⚠</span><span>404: Too many repos.<br>Abort, Retry, Fail?</span></div>
    <div class="err-btns"><button class="err-btn">Abort</button><button class="err-btn">Retry</button></div>
  </div>
  <div class="err-dlg" style="top:12%;right:5%;transform:rotate(3deg)">
    <div class="err-bar"><span>CRITICAL ERROR</span><span class="err-xbtn">✕</span></div>
    <div class="err-body"><span class="err-ico">\U0001f6d1</span><span>Stack overflow at<br>0x0000deadbeef</span></div>
    <div class="err-btns"><button class="err-btn">OK</button></div>
  </div>
  <div class="err-dlg" style="top:52%;left:1.5%;transform:rotate(-2.5deg)">
    <div class="err-bar"><span>WARNING</span><span class="err-xbtn">✕</span></div>
    <div class="err-body"><span class="err-ico">⚠</span><span>Infinite loop<br>detected in repos</span></div>
    <div class="err-btns"><button class="err-btn">Ignore</button></div>
  </div>
  <div class="err-dlg" style="bottom:8%;right:3%;transform:rotate(5deg)">
    <div class="err-bar"><span>FATAL</span><span class="err-xbtn">✕</span></div>
    <div class="err-body"><span class="err-ico">\U0001f480</span><span>System halted.<br>Star a repo to continue.</span></div>
    <div class="err-btns"><button class="err-btn">OK</button></div>
  </div>
</div>

<div class="page-wrap">
<header>
  <div class="win-bar">
    <div class="win-dots">
      <span class="win-dot close"></span>
      <span class="win-dot"></span>
      <span class="win-dot"></span>
    </div>
    <span class="win-bar-title">chaoticravena/repos — browser.exe</span>
  </div>
  <h1>chaoticravena/repos</h1>
  <p class="year-tag">__TITLE__</p>
  <p class="sub">__SUBTITLE__</p>
  <a href="agent.html" class="agent-link">&gt;_ AGENTE AI<span class="cursor">_</span></a>
  <div class="stats" id="stats"></div>
</header>

<div class="controls">
  <input type="search" id="q" placeholder="C:\\repos&gt; search_"/>
  <select id="lang">
    <option value="">[ all langs ]</option>
    <option value="Python">Python</option>
    <option value="Javascript">JavaScript</option>
  </select>
  <select id="rating">
    <option value="">[ all ratings ]</option>
    <option value="High">\U0001f525 High</option>
    <option value="Medium">&#x26a1; Medium</option>
    <option value="Low">\U0001f4a4 Low</option>
  </select>
  <select id="cat">
    <option value="">[ all categories ]</option>
    <option value="Agentic AI">\U0001f916 Agentic AI</option>
    <option value="LLMs &amp; Models">\U0001f9e0 LLMs &amp; Models</option>
    <option value="Image &amp; Video">\U0001f3a8 Image &amp; Video</option>
    <option value="Audio &amp; Voice">\U0001f399&#xfe0f; Audio &amp; Voice</option>
    <option value="Data &amp; Analytics">\U0001f4ca Data &amp; Analytics</option>
    <option value="Web &amp; APIs">\U0001f310 Web &amp; APIs</option>
    <option value="DevTools">\U0001f527 DevTools</option>
    <option value="Security">\U0001f512 Security</option>
    <option value="Learning">\U0001f4da Learning</option>
    <option value="Games &amp; Creative">\U0001f3ae Games &amp; Creative</option>
    <option value="Self-hosted">\U0001f3e0 Self-hosted</option>
    <option value="Automation &amp; Bots">&#x2699;&#xfe0f; Automation &amp; Bots</option>
    <option value="Other">\U0001f500 Other</option>
  </select>
  <span class="count" id="count"></span>
</div>

<div class="table-wrap">
<table id="tbl">
  <thead>
    <tr>
      <th data-col="rank" class="sort-asc">#</th>
      <th data-col="name">Repo</th>
      <th data-col="category">Category</th>
      <th data-col="lang">Lang</th>
      <th data-col="days">Days</th>
      <th data-col="desc">Description</th>
      <th data-col="rating">Potential</th>
    </tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>
</div>
<div class="pagination" id="pager"></div>
<footer>data :: <a href="https://github.com/trending" target="_blank">github.com/trending</a> · __YEAR_RANGE__ · chaoticravena/github-trending-site</footer>
</div>

<script>
const REPOS = __DATA__;
const RATING_EMOJI = {High:"\U0001f525",Medium:"&#x26a1;",Low:"\U0001f4a4"};
const CATS = {
  "Agentic AI":        {e:"\U0001f916", c:"#a78bfa", bg:"#1e1040"},
  "LLMs & Models":     {e:"\U0001f9e0", c:"#60a5fa", bg:"#0d1e3d"},
  "Image & Video":     {e:"\U0001f3a8", c:"#e879f9", bg:"#2a0e2e"},
  "Audio & Voice":     {e:"\U0001f399️", c:"#34d399", bg:"#0a2418"},
  "Data & Analytics":  {e:"\U0001f4ca", c:"#fb923c", bg:"#2a1500"},
  "Web & APIs":        {e:"\U0001f310", c:"#38bdf8", bg:"#0a1e30"},
  "DevTools":          {e:"\U0001f527", c:"#9ca3af", bg:"#1a1f27"},
  "Security":          {e:"\U0001f512", c:"#f87171", bg:"#2a0d0d"},
  "Learning":          {e:"\U0001f4da", c:"#a3e635", bg:"#162000"},
  "Games & Creative":  {e:"\U0001f3ae", c:"#818cf8", bg:"#141429"},
  "Self-hosted":       {e:"\U0001f3e0", c:"#4ade80", bg:"#0a2010"},
  "Automation & Bots": {e:"⚙️", c:"#fbbf24", bg:"#2a1800"},
  "Other":             {e:"\U0001f500", c:"#6b7280", bg:"#1a1e27"},
};
const PAGE_SIZE = 50;
let filtered=[...REPOS],sortCol="rank",sortDir=1,page=1;
;(()=>{
  const total=REPOS.length,
        high=REPOS.filter(r=>r.rating==="High").length,
        med=REPOS.filter(r=>r.rating==="Medium").length,
        low=REPOS.filter(r=>r.rating==="Low").length,
        py=REPOS.filter(r=>r.lang==="Python").length,
        js=REPOS.filter(r=>r.lang==="Javascript").length;
  document.getElementById("stats").innerHTML=[
    `<div class="stat"><span>${total.toLocaleString()}</span> repos</div>`,
    `<div class="stat"><span>${py.toLocaleString()}</span> Python</div>`,
    `<div class="stat"><span>${js.toLocaleString()}</span> JavaScript</div>`,
    `<div class="stat"><span style="color:var(--high)">${high.toLocaleString()}</span> \U0001f525 High</div>`,
    `<div class="stat"><span style="color:var(--med)">${med.toLocaleString()}</span> &#x26a1; Med</div>`,
    `<div class="stat"><span style="color:var(--low)">${low.toLocaleString()}</span> \U0001f4a4 Low</div>`,
  ].join("");
})();

// ── URL state ─────────────────────────────────────────────────────────────────
function _urlParams(){
  const p=new URLSearchParams(location.search);
  return{q:p.get('q')||'',lang:p.get('lang')||'',pot:p.get('pot')||'',cat:p.get('cat')||'',pg:parseInt(p.get('pg'))||1};
}
function applyURLState(){
  const{q,lang,pot,cat,pg}=_urlParams();
  document.getElementById('q').value=q;
  document.getElementById('lang').value=lang;
  document.getElementById('rating').value=pot;
  document.getElementById('cat').value=cat;
  page=pg;
}
function pushURL(replace){
  const q=document.getElementById('q').value,
        lg=document.getElementById('lang').value,
        rt=document.getElementById('rating').value,
        ct=document.getElementById('cat').value;
  const p=new URLSearchParams();
  if(q)p.set('q',q);if(lg)p.set('lang',lg);if(rt)p.set('pot',rt);if(ct)p.set('cat',ct);
  if(page>1)p.set('pg',page);
  const url=p.toString()?`?${p}`:location.pathname;
  if(replace)history.replaceState({},'',url);
  else history.pushState({},'',url);
}
window.addEventListener('popstate',()=>{applyURLState();applyFilters(false);});

function applyFilters(resetPage=true){
  const q=document.getElementById("q").value.toLowerCase(),
        lg=document.getElementById("lang").value,
        rt=document.getElementById("rating").value,
        ct=document.getElementById("cat").value;
  filtered=REPOS.filter(r=>{
    if(q&&!r.name.toLowerCase().includes(q)&&!(r.desc||"").toLowerCase().includes(q))return false;
    if(lg&&r.lang!==lg)return false;
    if(rt&&r.rating!==rt)return false;
    if(ct&&r.category!==ct)return false;
    return true;
  });
  filtered.sort((a,b)=>{
    let av=a[sortCol]??"",bv=b[sortCol]??"";
    if(typeof av==="string"){av=av.toLowerCase();bv=bv.toLowerCase();}
    return av<bv?-sortDir:av>bv?sortDir:0;
  });
  if(resetPage)page=1;
  const total=Math.ceil(filtered.length/PAGE_SIZE)||1;
  if(page>total)page=total;
  render();
}
function catBadge(cat){
  const info=CATS[cat]||CATS["Other"];
  return `<span class="cat-badge" style="background:${info.bg};color:${info.c}">${info.e} ${cat}</span>`;
}
function render(){
  const start=(page-1)*PAGE_SIZE,
        end=Math.min(page*PAGE_SIZE,filtered.length),
        rows=filtered.slice(start,end);
  const old=document.getElementById("empty-state");
  if(old)old.remove();
  if(!rows.length){
    document.getElementById("tbody").innerHTML="";
    const el=document.createElement("div");
    el.id="empty-state";el.className="empty-win";
    el.innerHTML=`<div class="ew-bar"><span>ERROR — 0 results</span><span class="ew-xbtn">✕</span></div>`+
      `<div class="ew-body"><div class="ew-ico">⚠</div>`+
      `<div>No repos match this filter.<br>Try a different query.</div>`+
      `<button class="ew-btn" onclick="document.getElementById('q').value='';`+
      `document.querySelectorAll('select').forEach(s=>s.value='');applyFilters();pushURL(false)">Clear filters</button></div>`;
    document.querySelector(".table-wrap").appendChild(el);
    document.getElementById("count").textContent="0 repos";
    renderPager();return;
  }
  document.getElementById("tbody").innerHTML=rows.map(r=>`
    <tr>
      <td class="rank">${r.rank}</td>
      <td><a href="${r.url}" target="_blank">${r.name}</a></td>
      <td>${catBadge(r.category||"Other")}</td>
      <td class="lang-${r.lang==="Python"?"py":"js"}">${r.lang==="Javascript"?"JS":r.lang}</td>
      <td class="days">${r.days}d</td>
      <td class="desc">${r.desc||""}</td>
      <td><span class="badge badge-${r.rating}">${RATING_EMOJI[r.rating]} ${r.rating}</span></td>
    </tr>`).join("");
  document.getElementById("count").textContent=
    `${filtered.length.toLocaleString()} repos · pg ${page}/${Math.ceil(filtered.length/PAGE_SIZE)||1}`;
  renderPager();
}
function renderPager(){
  const total=Math.ceil(filtered.length/PAGE_SIZE)||1,p=document.getElementById("pager");
  p.innerHTML=`
    <button onclick="goPage(1)" ${page<=1?"disabled":""}>[|&lt;]</button>
    <button onclick="goPage(${page-1})" ${page<=1?"disabled":""}>[&lt;&lt;]</button>
    <span>[ ${page} / ${total} ]</span>
    <button onclick="goPage(${page+1})" ${page>=total?"disabled":""}>[&gt;&gt;]</button>
    <button onclick="goPage(${total})" ${page>=total?"disabled":""}>[&gt;|]</button>`;
}
function goPage(n){page=n;render();window.scrollTo(0,0);pushURL(false);}
document.querySelectorAll("th[data-col]").forEach(th=>{
  th.addEventListener("click",()=>{
    const col=th.dataset.col;
    if(sortCol===col)sortDir*=-1;else{sortCol=col;sortDir=1;}
    document.querySelectorAll("th").forEach(t=>t.classList.remove("sort-asc","sort-desc"));
    th.classList.add(sortDir===1?"sort-asc":"sort-desc");
    applyFilters();pushURL(false);
  });
});
["lang","rating","cat"].forEach(id=>
  document.getElementById(id).addEventListener("change",()=>{applyFilters();pushURL(false);}));
let _st;
document.getElementById("q").addEventListener("input",()=>{
  clearTimeout(_st);_st=setTimeout(()=>{applyFilters();pushURL(true);},200);
});
// restore state from URL on load, then render
applyURLState();
applyFilters(false);
// remove loading screen after first render
const _ls=document.getElementById("loading-screen");
if(_ls)_ls.style.display="none";
</script>
</body>
</html>
"""

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    if not SRC.exists():
        sibling = ROOT.parent / "github-trending-master" / _src_name
        if sibling.exists():
            shutil.copy(sibling, SRC)
            print(f"Copied from {sibling}")
        else:
            raise FileNotFoundError(f"Source not found: {SRC}")

    print(f"Parsing  : {SRC.name}")
    repos = parse_source(SRC)
    print(f"Repos    : {len(repos):,}")

    # Assign / refresh category on every run
    for r in repos:
        r["category"] = categorise(r["name"], r.get("desc", ""))

    counts = Counter(r["category"] for r in repos)
    print("Categories:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {n:>5}  {cat}")

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    json_text = json.dumps(repos, ensure_ascii=False, indent=2)
    JSON_OUT.write_text(json_text, encoding="utf-8")
    print(f"JSON     : {JSON_OUT.name}  ({JSON_OUT.stat().st_size // 1024} KB)")

    # Mirror JSON into docs/data/ so GitHub Pages can serve it to agent.html
    docs_data = ROOT / "docs" / "data"
    docs_data.mkdir(parents=True, exist_ok=True)
    docs_json = docs_data / "repos.json"
    docs_json.write_text(json_text, encoding="utf-8")
    print(f"JSON     : docs/data/repos.json  ({docs_json.stat().st_size // 1024} KB)  [Pages mirror]")

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    html = (HTML_TEMPLATE
            .replace("__TITLE__",      TITLE)
            .replace("__SUBTITLE__",   SUBTITLE)
            .replace("__YEAR_RANGE__", YEAR_RANGE)
            .replace("__DATA__",       json.dumps(repos, ensure_ascii=False)))
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"HTML     : {HTML_OUT.name}  ({HTML_OUT.stat().st_size // 1024} KB)")
    print("Done.")

if __name__ == "__main__":
    main()
