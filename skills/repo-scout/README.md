# repo-scout · Claude Code skill

Finds open-source repos that fit **your** project. It searches the curated [github-trending-site](https://chaoticravena.github.io/github-trending-site/) collection (~6k repos that hit GitHub Trending since 2023, with category, stars, last commit, license and precomputed similar repos) and cross-checks live GitHub, so recommendations come from a search run instead of model memory.

Ask Claude things like:

- "what can I use to add transcription to my app?"
- "alternatives to openai/whisper"
- "is there a Claude skill for SEO audits?"
- "/repo-scout ideias agentes de voz"

It answers with a table per project piece: repo, role (dependency / reference / competitor), source, license, last push, and why it fits. Archived repos are dropped, and abandoned or copyleft repos are flagged.

## Install

Requires Python 3 and the [GitHub CLI](https://cli.github.com) logged in (`gh auth login`).

```bash
git clone --depth 1 https://github.com/chaoticravena/github-trending-site.git
cp -r github-trending-site/skills/repo-scout ~/.claude/skills/
```

Check it works:

```bash
python ~/.claude/skills/repo-scout/scout.py --selftest
```

## Run the script directly

```bash
python scout.py --local "whisper|transcri|subtitle" --gh "speech to text" --lang python
python scout.py --similar openai/whisper
python scout.py --local "seo|audit" --cat "Claude Skills"
```

Optional: put a `candidatos.json` next to `scout.py` (same shape as the collection's `repos.json`, with `"status": "candidato"`) to include your own shortlist in every search.
