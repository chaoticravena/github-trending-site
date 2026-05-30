"""
generate_data.py  [source_md]  [json_out]

  source_md  - filename inside data/  (default: repos_2023_2024_enriched.md)
  json_out   - path relative to project root  (default: data/repos.json)

Writes: data/<json_out>  +  docs/index.html
"""

import json, re, sys, shutil
from pathlib import Path

ROOT     = Path(__file__).parent.parent
HTML_OUT = ROOT / "docs" / "index.html"

# ── CLI args with defaults ────────────────────────────────────────────────────
_src_name  = sys.argv[1] if len(sys.argv) > 1 else "repos_2023_2024_enriched.md"
_json_rel  = sys.argv[2] if len(sys.argv) > 2 else "data/repos.json"

SRC      = ROOT / "data" / _src_name
JSON_OUT = ROOT / _json_rel

# ── derive title from filename  e.g. repos_2025_2026.md -> "2025-2026" ────────
_year_match = re.search(r'(\d{4})[_\-](\d{4})', _src_name)
YEAR_RANGE  = f"{_year_match.group(1)}–2026" if _year_match and _year_match.group(2) == "2026" \
              else (f"{_year_match.group(1)}–{_year_match.group(2)}" if _year_match else "")
TITLE       = f"GitHub Trending {YEAR_RANGE}".strip()
SUBTITLE    = "Python &amp; JavaScript repositories · sorted by days on trending · content potential scored"

# ── regex to parse enriched MD table rows ─────────────────────────────────────
ROW_RE = re.compile(
    r'^\| (\d+) \| \[([^\]]+)\]\(([^)]+)\) \| (\w+) \| (\d+) \| (.*?) \| (.+?) \|$'
)

# ── parse: auto-detects .json vs .md ─────────────────────────────────────────
def parse_source(path: Path) -> list[dict]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    repos = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        raw = m.group(7).strip()
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
<title>__TITLE__ · Python &amp; JS</title>
<style>
  :root{
    --bg:#0d1117;--surface:#161b22;--border:#30363d;
    --text:#e6edf3;--muted:#8b949e;
    --accent:#58a6ff;--high:#ff7b72;--med:#d29922;--low:#8b949e;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font:14px/1.6 'Segoe UI',system-ui,sans-serif;min-height:100vh}
  a{color:var(--accent);text-decoration:none}
  a:hover{text-decoration:underline}
  header{padding:2rem 1.5rem 1rem;border-bottom:1px solid var(--border)}
  header h1{font-size:1.5rem;font-weight:700;margin-bottom:.25rem}
  header p{color:var(--muted);font-size:.85rem}
  .stats{display:flex;gap:1rem;flex-wrap:wrap;margin-top:1rem}
  .stat{background:var(--surface);border:1px solid var(--border);border-radius:8px;
        padding:.5rem 1rem;font-size:.8rem;color:var(--muted)}
  .stat span{font-weight:700;color:var(--text);font-size:1rem}
  .controls{display:flex;gap:.75rem;flex-wrap:wrap;padding:1rem 1.5rem;
            border-bottom:1px solid var(--border);align-items:center}
  input,select{background:var(--surface);border:1px solid var(--border);
               color:var(--text);border-radius:6px;padding:.4rem .75rem;font-size:.85rem}
  input{flex:1;min-width:200px}
  input:focus,select:focus{outline:none;border-color:var(--accent)}
  .count{color:var(--muted);font-size:.8rem;margin-left:auto}
  .table-wrap{overflow-x:auto;padding:0 1.5rem 2rem}
  table{width:100%;border-collapse:collapse;margin-top:1rem;font-size:.82rem}
  th{position:sticky;top:0;background:var(--bg);border-bottom:2px solid var(--border);
     padding:.5rem .75rem;text-align:left;color:var(--muted);cursor:pointer;user-select:none;white-space:nowrap}
  th:hover{color:var(--text)}
  th.sort-asc::after{content:" ▲"}
  th.sort-desc::after{content:" ▼"}
  td{padding:.45rem .75rem;border-bottom:1px solid var(--border);vertical-align:top}
  tr:hover td{background:var(--surface)}
  .rank{color:var(--muted);width:50px}
  .days{font-weight:600;width:80px}
  .desc{color:var(--muted);max-width:420px}
  .lang-py{color:#3572A5}
  .lang-js{color:#f1e05a}
  .badge{display:inline-flex;align-items:center;gap:4px;border-radius:4px;
         padding:2px 7px;font-size:.75rem;font-weight:600;white-space:nowrap}
  .badge-High{background:#3d1f1e;color:var(--high)}
  .badge-Medium{background:#2d2208;color:var(--med)}
  .badge-Low{background:#1c1f24;color:var(--low)}
  .pagination{display:flex;gap:.5rem;align-items:center;justify-content:center;
              padding:1rem;color:var(--muted);font-size:.82rem}
  .pagination button{background:var(--surface);border:1px solid var(--border);
                     color:var(--text);border-radius:6px;padding:.3rem .75rem;
                     cursor:pointer;font-size:.8rem}
  .pagination button:disabled{opacity:.35;cursor:default}
  .pagination button:not(:disabled):hover{border-color:var(--accent);color:var(--accent)}
  footer{text-align:center;padding:1rem;color:var(--muted);font-size:.75rem;
         border-top:1px solid var(--border)}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <p>__SUBTITLE__</p>
  <div class="stats" id="stats"></div>
</header>
<div class="controls">
  <input type="search" id="q" placeholder="Search repo name or description…"/>
  <select id="lang">
    <option value="">All languages</option>
    <option value="Python">Python</option>
    <option value="Javascript">JavaScript</option>
  </select>
  <select id="rating">
    <option value="">All ratings</option>
    <option value="High">\U0001f525 High</option>
    <option value="Medium">⚡ Medium</option>
    <option value="Low">\U0001f4a4 Low</option>
  </select>
  <span class="count" id="count"></span>
</div>
<div class="table-wrap">
<table id="tbl">
  <thead>
    <tr>
      <th data-col="rank" class="sort-asc">#</th>
      <th data-col="name">Repo</th>
      <th data-col="lang">Language</th>
      <th data-col="days">Days</th>
      <th data-col="desc">Description</th>
      <th data-col="rating">Content Potential</th>
    </tr>
  </thead>
  <tbody id="tbody"></tbody>
</table>
</div>
<div class="pagination" id="pager"></div>
<footer>Data sourced from <a href="https://github.com/trending" target="_blank">github.com/trending</a> · __YEAR_RANGE__</footer>
<script>
const REPOS = __DATA__;
const RATING_EMOJI = {High:"\U0001f525",Medium:"⚡",Low:"\U0001f4a4"};
const PAGE_SIZE = 50;
let filtered=[...REPOS],sortCol="rank",sortDir=1,page=1;
;(()=>{
  const total=REPOS.length,high=REPOS.filter(r=>r.rating==="High").length,
        med=REPOS.filter(r=>r.rating==="Medium").length,low=REPOS.filter(r=>r.rating==="Low").length,
        py=REPOS.filter(r=>r.lang==="Python").length,js=REPOS.filter(r=>r.lang==="Javascript").length;
  document.getElementById("stats").innerHTML=[
    `<div class="stat"><span>${total.toLocaleString()}</span> repos</div>`,
    `<div class="stat"><span>${py.toLocaleString()}</span> Python</div>`,
    `<div class="stat"><span>${js.toLocaleString()}</span> JavaScript</div>`,
    `<div class="stat"><span style="color:var(--high)">${high.toLocaleString()}</span> \U0001f525 High</div>`,
    `<div class="stat"><span style="color:var(--med)">${med.toLocaleString()}</span> ⚡ Medium</div>`,
    `<div class="stat"><span style="color:var(--low)">${low.toLocaleString()}</span> \U0001f4a4 Low</div>`,
  ].join("");
})();
function applyFilters(){
  const q=document.getElementById("q").value.toLowerCase(),
        lg=document.getElementById("lang").value,
        rt=document.getElementById("rating").value;
  filtered=REPOS.filter(r=>{
    if(q&&!r.name.toLowerCase().includes(q)&&!r.desc.toLowerCase().includes(q))return false;
    if(lg&&r.lang!==lg)return false;
    if(rt&&r.rating!==rt)return false;
    return true;
  });
  filtered.sort((a,b)=>{let av=a[sortCol],bv=b[sortCol];
    if(typeof av==="string"){av=av.toLowerCase();bv=bv.toLowerCase();}
    return av<bv?-sortDir:av>bv?sortDir:0;
  });
  page=1;render();
}
function render(){
  const start=(page-1)*PAGE_SIZE,end=Math.min(page*PAGE_SIZE,filtered.length),rows=filtered.slice(start,end);
  document.getElementById("tbody").innerHTML=rows.map(r=>`
    <tr>
      <td class="rank">${r.rank}</td>
      <td><a href="${r.url}" target="_blank">${r.name}</a></td>
      <td class="lang-${r.lang==="Python"?"py":"js"}">${r.lang==="Javascript"?"JavaScript":r.lang}</td>
      <td class="days">${r.days}d</td>
      <td class="desc">${r.desc||""}</td>
      <td><span class="badge badge-${r.rating}">${RATING_EMOJI[r.rating]} ${r.rating}</span></td>
    </tr>`).join("");
  document.getElementById("count").textContent=
    `${filtered.length.toLocaleString()} repos · page ${page}/${Math.ceil(filtered.length/PAGE_SIZE)||1}`;
  renderPager();
}
function renderPager(){
  const total=Math.ceil(filtered.length/PAGE_SIZE)||1,p=document.getElementById("pager");
  p.innerHTML=`
    <button onclick="goPage(1)" ${page<=1?"disabled":""}>«</button>
    <button onclick="goPage(${page-1})" ${page<=1?"disabled":""}>‹</button>
    <span>Page ${page} / ${total}</span>
    <button onclick="goPage(${page+1})" ${page>=total?"disabled":""}>›</button>
    <button onclick="goPage(${total})" ${page>=total?"disabled":""}>»</button>`;
}
function goPage(n){page=n;render();window.scrollTo(0,0);}
document.querySelectorAll("th[data-col]").forEach(th=>{
  th.addEventListener("click",()=>{
    const col=th.dataset.col;
    if(sortCol===col)sortDir*=-1;else{sortCol=col;sortDir=1;}
    document.querySelectorAll("th").forEach(t=>t.classList.remove("sort-asc","sort-desc"));
    th.classList.add(sortDir===1?"sort-asc":"sort-desc");
    applyFilters();
  });
});
["q","lang","rating"].forEach(id=>document.getElementById(id).addEventListener("input",applyFilters));
applyFilters();
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

    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(repos, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"JSON     : {JSON_OUT}  ({JSON_OUT.stat().st_size // 1024} KB)")

    HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    html = (HTML_TEMPLATE
            .replace("__TITLE__",      TITLE)
            .replace("__SUBTITLE__",   SUBTITLE)
            .replace("__YEAR_RANGE__", YEAR_RANGE)
            .replace("__DATA__",       json.dumps(repos, ensure_ascii=False)))
    HTML_OUT.write_text(html, encoding="utf-8")
    print(f"HTML     : {HTML_OUT}  ({HTML_OUT.stat().st_size // 1024} KB)")
    print("Done.")

if __name__ == "__main__":
    main()
