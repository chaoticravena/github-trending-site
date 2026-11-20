"""Busca determinística da repo-scout: compilado curado + candidatos + GitHub ao vivo, já com sinal fresco.

Uso: scout.py --local "kw1|kw2|kw3" --gh "kw1 kw2" [--gh "kw3"] [--lang python] [--cat "Claude Skills"] [--top 12]
     scout.py --similar owner/repo      (alternativas a um repo, pelos embeddings do compilado)
     scout.py --selftest
Saída (stdout, JSON): {"avisos": [...], "repos": [{name, fonte, rating, category, desc, stars, pushed, license, flags, url}]}
Arquivados e repos que não existem mais saem da lista. Nomes renomeados viram o nome canônico.
"""
import argparse
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import tempfile
import urllib.request

RAW = "https://raw.githubusercontent.com/chaoticravena/github-trending-site/master/"
COMPILADO_URL = RAW + "data/repos.json"
SIMILAR_URL = RAW + "docs/data/similar.json"
COMPILADO_CACHE = os.path.join(tempfile.gettempdir(), "repo-scout-compilado.json")
SIMILAR_CACHE = os.path.join(tempfile.gettempdir(), "repo-scout-similar.json")
CACHE_MAX_AGE = 7 * 86400  # ponytail: rebaixa o compilado 1x por semana; o pipeline roda a cada 15 dias
CANDIDATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "candidatos.json")  # opcional, pessoal
RATING = {"High": 0, "Medium": 1, "Low": 2}
COPYLEFT = re.compile(r"gpl|-sa\b", re.I)  # GPL, AGPL, LGPL e Creative Commons share-alike (CC-BY-SA)
GH_FIELDS = "fullName,description,stargazersCount,pushedAt,license,url,isArchived"


def gh(*args):
    try:
        p = subprocess.run(["gh", *args], capture_output=True, encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return 127, "", "gh CLI não instalado (https://cli.github.com), rode `gh auth login` depois"
    return p.returncode, p.stdout, p.stderr.strip()


def fetch_cached(url, path, avisos):
    try:
        if not os.path.exists(path) or dt.datetime.now().timestamp() - os.path.getmtime(path) > CACHE_MAX_AGE:
            urllib.request.urlretrieve(url, path)
    except OSError as e:
        avisos.append(f"não baixou {url.rsplit('/', 1)[-1]} ({e}); usando cache se houver")
    return json.load(open(path, encoding="utf-8-sig")) if os.path.exists(path) else None


def load_compilado(avisos):
    d = fetch_cached(COMPILADO_URL, COMPILADO_CACHE, avisos) or []
    if os.path.exists(CANDIDATOS):
        d += json.load(open(CANDIDATOS, encoding="utf-8"))
    return d


def similar_to(name, data, avisos):
    """Vizinhos pré-calculados pelo pipeline do site (embeddings MiniLM, só repos não arquivados)."""
    s = fetch_cached(SIMILAR_URL, SIMILAR_CACHE, avisos)
    if not s:
        return []
    idx = {n.lower(): i for i, n in enumerate(s["names"])}
    i = idx.get(name.lower())
    if i is None:
        avisos.append(f"{name} não está no compilado; sem alternativas pré-calculadas, use --local/--gh")
        return []
    by_name = {r["name"].lower(): r for r in data}
    return [{**by_name[s["names"][j].lower()], "hits": None} for j in s["sim"][i] if s["names"][j].lower() in by_name]


def split_top(pattern):
    """Quebra no | só fora de parênteses/colchetes: "a|(b|c)" -> ["a", "(b|c)"]."""
    parts, depth, cur, esc = [], 0, "", False
    for ch in pattern:
        if esc:
            cur, esc = cur + ch, False
            continue
        if ch == "\\":
            esc = True
        elif ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        elif ch == "|" and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    return parts + [cur]


def search_local(data, pattern, top, lang=None, cat=None):
    """Rankeia por palavras-chave distintas que batem, depois rating da curadoria, depois estrelas.
    Arquivados (marcados pelo pipeline) nem entram, pra não gastar a query de sinal fresco."""
    kws = [re.compile(k, re.I) for k in split_top(pattern) if k.strip()]
    scored = []
    for r in data:
        if r.get("archived"):
            continue
        if lang and (r.get("lang") or "").lower() != lang.lower():
            continue
        if cat and (r.get("category") or "").lower() != cat.lower():
            continue
        text = f"{r['name']} {r.get('desc') or ''}"
        hits = sum(1 for k in kws if k.search(text))
        if hits:
            scored.append((-hits, RATING.get(r.get("rating"), 3), -(r.get("stars") or 0), {**r, "hits": hits}))
    scored.sort(key=lambda t: t[:3])
    return [r for *_, r in scored[:top]]


def search_gh(queries, lang, since, avisos):
    out = []
    for q in queries:
        for sort in (["--sort", "stars"], []):  # stars + best match, pra não viciar em repo velho e gigante
            args = ["search", "repos", *shlex.split(q), "--archived=false", f"--updated=>{since}",
                    "--limit", "10", "--json", GH_FIELDS, *sort]
            if lang:
                args += ["--language", lang]
            code, stdout, err = gh(*args)
            if code:
                avisos.append(f"gh search '{q}': {err}")
                continue
            out += json.loads(stdout)
    return out


def fresh_signal(names, avisos):
    """Uma query GraphQL pra todos: nome canônico, estrelas, push, arquivado, licença."""
    if not names:
        return {}
    parts = []
    for i, n in enumerate(names):
        owner, _, repo = n.partition("/")
        parts.append(f'r{i}: repository(owner: {json.dumps(owner)}, name: {json.dumps(repo)}) '
                     '{ nameWithOwner stargazerCount pushedAt isArchived url licenseInfo { spdxId } }')
    code, stdout, err = gh("api", "graphql", "-f", "query={ " + " ".join(parts) + " }")
    try:
        data = json.loads(stdout).get("data") or {}
    except json.JSONDecodeError:
        avisos.append(f"graphql falhou: {err}")
        return {}
    return {names[i]: data.get(f"r{i}") for i in range(len(names))}


def flags_for(r, since):
    f = []
    if r["pushed"] and r["pushed"][:10] < since:
        f.append("pode estar abandonado")
    lic = r["license"]
    if not lic or lic == "NOASSERTION":
        f.append("sem licença clara")
    elif COPYLEFT.search(lic):
        f.append(f"copyleft ({lic})")
    return f


def merge(local, remote):
    """local: entradas do compilado (já com sinal fresco em 'live'). remote: resultados do gh search."""
    out = {}
    for r in local:
        live = r.get("live")
        if live is None or live["isArchived"]:
            continue  # sumiu do GitHub ou arquivado
        key = live["nameWithOwner"].lower()
        out[key] = {
            "name": live["nameWithOwner"], "url": live["url"],
            "fonte": "candidato" if r.get("status") == "candidato" else "compilado",
            "rating": r.get("rating"), "category": r.get("category"), "desc": r.get("desc"),
            "stars": live["stargazerCount"], "pushed": live["pushedAt"],
            "license": (live.get("licenseInfo") or {}).get("spdxId"), "hits": r.get("hits"),
        }
    for r in remote:
        if r.get("isArchived"):
            continue
        key = r["fullName"].lower()
        if key in out:
            if out[key]["fonte"] == "compilado":
                out[key]["fonte"] = "ambos"
            continue
        out[key] = {
            "name": r["fullName"], "url": r["url"], "fonte": "github", "rating": None, "category": None,
            "desc": r.get("description"), "stars": r["stargazersCount"], "pushed": r["pushedAt"],
            "license": ((r.get("license") or {}).get("key") or "").upper() or None, "hits": None,
        }
    return list(out.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", default="", help='regex por palavra-chave, separadas por |, ex. "whisper|transcri|subtitle"')
    ap.add_argument("--gh", action="append", default=[], help="query do GitHub, palavras sem aspas, máx 3")
    ap.add_argument("--lang", help="filtra compilado e GitHub (python, javascript)")
    ap.add_argument("--cat", help='filtra o compilado por categoria, ex. "Claude Skills"')
    ap.add_argument("--similar", metavar="OWNER/REPO", help="alternativas a um repo do compilado")
    ap.add_argument("--top", type=int, default=12)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.local or a.gh or a.similar):
        ap.error("passe --local, --gh e/ou --similar")

    avisos = []
    since = (dt.date.today() - dt.timedelta(days=365)).isoformat()
    data = load_compilado(avisos) if (a.local or a.similar) else []
    local = search_local(data, a.local, a.top, a.lang, a.cat) if a.local else []
    if a.similar:
        seen = {r["name"].lower() for r in local}
        local += [r for r in similar_to(a.similar, data, avisos) if r["name"].lower() not in seen]
    signal = fresh_signal([r["name"] for r in local], avisos)
    for r in local:
        r["live"] = signal.get(r["name"])
    remote = search_gh(a.gh, a.lang, since, avisos)

    repos = merge(local, remote)
    for r in repos:
        r["flags"] = flags_for(r, since)
    order = {"ambos": 0, "compilado": 1, "candidato": 2, "github": 3}
    repos.sort(key=lambda r: (order[r["fonte"]], -(r["hits"] or 0), bool(r["flags"]), -r["stars"]))
    if not any(r["fonte"] != "github" for r in repos):
        avisos.append("nada no compilado, só GitHub ao vivo")

    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps({"avisos": avisos, "repos": repos}, ensure_ascii=False, indent=1))


def selftest():
    data = [
        {"name": "a/whisper-subs", "desc": "whisper subtitle tool", "rating": "Low"},
        {"name": "b/subs", "desc": "subtitle editor", "rating": "High"},
        {"name": "c/other", "desc": "nothing here", "rating": "High"},
    ]
    got = [r["name"] for r in search_local(data, "whisper|subtitle", 5)]
    assert got == ["a/whisper-subs", "b/subs"], got  # 2 palavras batem > rating alto
    data2 = [
        {"name": "p/sub", "desc": "subtitle", "rating": "High", "lang": "Python", "category": "Audio & Voice", "stars": 5},
        {"name": "q/sub", "desc": "subtitle", "rating": "High", "lang": "Python", "category": "Audio & Voice", "stars": 50},
        {"name": "j/sub", "desc": "subtitle", "rating": "High", "lang": "Javascript", "category": "Audio & Voice"},
        {"name": "z/sub", "desc": "subtitle", "rating": "High", "lang": "Python", "archived": True},
    ]
    assert [r["name"] for r in search_local(data2, "subtitle", 5, lang="python")] == ["q/sub", "p/sub"]  # lang filtra, estrelas desempatam, arquivado sai
    assert [r["name"] for r in search_local(data2, "subtitle", 5, cat="audio & voice")] == ["q/sub", "p/sub", "j/sub"]
    assert split_top(r"a|\bgit\b.*(game|learn)|[x|y]|c\|d") == ["a", r"\bgit\b.*(game|learn)", "[x|y]", r"c\|d"]

    live = lambda n, arch=False: {"nameWithOwner": n, "url": "u", "stargazerCount": 10,
                                  "pushedAt": "2026-09-01T00:00:00Z", "isArchived": arch, "licenseInfo": {"spdxId": "MIT"}}
    local = [
        {"name": "old/FunClip", "rating": "High", "live": live("modelscope/FunClip")},  # renomeado
        {"name": "x/dead", "rating": "High", "live": None},  # sumiu
        {"name": "x/arch", "rating": "High", "live": live("x/arch", arch=True)},
    ]
    remote = [
        {"fullName": "modelscope/funclip", "url": "u", "stargazersCount": 10, "pushedAt": "2026-09-01", "isArchived": False, "license": {"key": "mit"}},
        {"fullName": "n/new", "url": "u", "stargazersCount": 5, "pushedAt": "2024-01-01", "isArchived": False, "license": {"key": "agpl-3.0"}},
    ]
    m = {r["name"]: r for r in merge(local, remote)}
    assert set(m) == {"modelscope/FunClip", "n/new"}, m
    assert m["modelscope/FunClip"]["fonte"] == "ambos"
    assert flags_for(m["n/new"], "2025-10-01") == ["pode estar abandonado", "copyleft (AGPL-3.0)"]
    assert flags_for(m["modelscope/FunClip"], "2025-10-01") == []
    assert flags_for({"pushed": "2026-09-01", "license": "CC-BY-SA-4.0"}, "2025-10-01") == ["copyleft (CC-BY-SA-4.0)"]
    print("selftest ok")


if __name__ == "__main__":
    main()
