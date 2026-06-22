#!/usr/bin/env node
/**
 * fetch_trending.js
 *
 * Busca os últimos N dias do bonfy/github-trending, filtra Python/JavaScript,
 * mescla com o dataset existente (docs/data/repos.json) e regenera
 * docs/data/repos.json, data/repos.json e docs/data.js.
 *
 * Uso: node scripts/fetch_trending.js [--days 15]
 */

import { readFileSync, writeFileSync, mkdirSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT      = resolve(__dirname, '..');

const REPOS_JSON = resolve(ROOT, 'data/repos.json');
const DOCS_JSON  = resolve(ROOT, 'docs/data/repos.json');
const DATA_JS    = resolve(ROOT, 'docs/data.js');

const ALLOWED_LANGS = new Set(['python', 'javascript']);
const LANG_CANONICAL = { python: 'Python', javascript: 'Javascript' };

// ── categorias (idêntico ao generate_data.py) ─────────────────────────────
const CATEGORIES = [
    ['Agentic AI', ['agent','crewai','autogen','langgraph','mcp','tool-calling','tool_calling','autonomous','multi-agent','multiagent','agentic']],
    ['LLMs & Models', ['llm','gpt','claude','llama','mistral','gemini','fine-tun','finetun','gguf','ollama','ggml','transformers','huggingface','openai','chatgpt','anthropic','deepseek','qwen','falcon','vllm','lora','rlhf']],
    ['Image & Video', ['diffusion','comfyui','stable-diffusion','stablediffusion','image generation','text-to-image','text-to-video','animate','gan','inpaint','controlnet','dreambooth','video generation','img2img']],
    ['Audio & Voice', ['tts','whisper','speech','voice','audio','music','text-to-speech','stt','asr','transcri','vocal']],
    ['Data & Analytics', ['pandas','etl','dbt','kafka','airflow','polars','spark','databricks','bigquery','redshift','snowflake','pyspark','data analysis','data cleaning','sql','warehouse','analytics','matplotlib','plotly','jupyter']],
    ['Security', ['pentest','osint','ctf','vulnerability','forensic','exploit','hacking','malware','reverse engineer','cybersecurity','infosec','owasp','xss','injection','zero-day']],
    ['Games & Creative', ['game','3d','pixel','canvas','shader','graphics','opengl','unity','godot','pygame','raylib','threejs','creative coding']],
    ['Self-hosted', ['self-host','selfhost','homelab','home assistant','nas','nextcloud','jellyfin','plex','immich','download manager','paperless','torrent','media server']],
    ['Automation & Bots', ['bot','automat','workflow','n8n','selenium','playwright','rpa','scraper','crawler','zapier','webhook','scheduler']],
    ['Learning', ['tutorial','course','roadmap','awesome','interview','book','guide','learn','beginner','30-days','cheatsheet','primer','from scratch','algorithms','data structure','system design','leetcode']],
    ['DevTools', ['cli','docker','kubernetes','k8s','lint','test','debug','monitor','infra','devops','terraform','helm','ansible','formatter','linter','vscode','vim','neovim','shell','zsh','ci/cd','github action','build tool']],
    ['Web & APIs', ['fastapi','django','flask','react','next.js','nextjs','vue','svelte','angular','graphql','nuxt','tailwind','bootstrap','express','nodejs','rest api','frontend','backend','fullstack','typescript','web framework']],
];

function categorise(name, desc) {
    const text = `${name} ${desc || ''}`.toLowerCase();
    for (const [label, kws] of CATEGORIES) {
        if (kws.some(kw => text.includes(kw))) return label;
    }
    return 'Other';
}

// ── URL do arquivo bonfy ──────────────────────────────────────────────────
function bonfy_url(d) {
    const s = d.toISOString().slice(0, 10);   // YYYY-MM-DD
    return d.getFullYear() >= 2026
        ? `https://raw.githubusercontent.com/bonfy/github-trending/master/${s}.md`
        : `https://raw.githubusercontent.com/bonfy/github-trending/master/${d.getFullYear()}/${s}.md`;
}

async function fetchRaw(url) {
    try {
        const res = await fetch(url, { headers: { 'User-Agent': 'fetch_trending/1.0' } });
        if (res.ok) return await res.text();
        if (res.status !== 404) console.error(`  HTTP ${res.status}: ${url}`);
    } catch (e) {
        console.error(`  Erro ao buscar ${url}: ${e.message}`);
    }
    return null;
}

// ── parser do formato bonfy ───────────────────────────────────────────────
// Cada repo: * [owner / repo](url):descrição
const REPO_RE = /^\* \[([^\]]+)\]\(([^)]+)\)(?::(.*))?$/;

function parseBonfyMd(content) {
    const repos = [];
    let lang = null;
    for (const rawLine of content.split('\n')) {
        const line = rawLine.trimEnd();
        if (line.startsWith('#### ')) {
            lang = line.slice(5).trim().toLowerCase();
        } else if (line.startsWith('* [') && lang && ALLOWED_LANGS.has(lang)) {
            const m = REPO_RE.exec(line);
            if (!m) continue;
            const name = m[1].trim().replace(/\s*\/\s*/g, '/');
            const url  = m[2].trim();
            const desc = (m[3] || '').trim();
            repos.push({ name, url, desc, lang: LANG_CANONICAL[lang] });
        }
    }
    return repos;
}

// ── argparse básico ───────────────────────────────────────────────────────
function getArgs() {
    const args = process.argv.slice(2);
    const idx  = args.indexOf('--days');
    return { days: idx >= 0 ? parseInt(args[idx + 1], 10) : 15 };
}

// ── main ──────────────────────────────────────────────────────────────────
async function main() {
    const { days } = getArgs();
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const dates = Array.from({ length: days }, (_, i) => {
        const d = new Date(today);
        d.setDate(d.getDate() - (days - 1 - i));   // cronológico
        return d;
    });

    // 1) Buscar bonfy ─────────────────────────────────────────────────────
    console.log(`Buscando ${days} dias do bonfy/github-trending...`);
    const bonfyMap = new Map();   // url → {name, url, lang, desc, appearances}
    let fetched = 0;

    for (const d of dates) {
        const url     = bonfy_url(d);
        const content = await fetchRaw(url);
        if (!content) {
            console.log(`  ${d.toISOString().slice(0,10)}  404/erro — ignorado`);
            continue;
        }
        const repos = parseBonfyMd(content);
        fetched++;
        console.log(`  ${d.toISOString().slice(0,10)}  ${String(repos.length).padStart(3)} repos (Python/JS)`);

        for (const r of repos) {
            if (bonfyMap.has(r.url)) {
                bonfyMap.get(r.url).appearances++;
                if (r.desc && !bonfyMap.get(r.url).desc) bonfyMap.get(r.url).desc = r.desc;
            } else {
                bonfyMap.set(r.url, { ...r, appearances: 1 });
            }
        }
    }

    console.log(`\nTotal de datas buscadas: ${fetched}/${days}`);
    console.log(`Repos únicos Python/JS no período: ${bonfyMap.size}`);

    // Safeguard: eliminar Go/Swift caso apareçam
    let goSwiftSkipped = 0;
    for (const [url, r] of bonfyMap) {
        if (!['Python', 'Javascript'].includes(r.lang)) { bonfyMap.delete(url); goSwiftSkipped++; }
    }
    if (goSwiftSkipped) console.log(`Repos Go/Swift bloqueados: ${goSwiftSkipped}`);

    // 2) Carregar dataset existente ───────────────────────────────────────
    let existing = new Map();
    try {
        const raw = readFileSync(DOCS_JSON, 'utf8');
        for (const r of JSON.parse(raw)) existing.set(r.url, r);
    } catch {
        try {
            const raw = readFileSync(REPOS_JSON, 'utf8');
            for (const r of JSON.parse(raw)) existing.set(r.url, r);
        } catch { /* dataset vazio */ }
    }
    console.log(`Repos existentes no dataset: ${existing.size}`);

    // 3) Mesclar ──────────────────────────────────────────────────────────
    let added = 0, updated = 0;
    for (const [url, bonfy] of bonfyMap) {
        const app = bonfy.appearances;
        if (existing.has(url)) {
            const r = existing.get(url);
            r.days = (r.days || 0) + app;
            if (bonfy.desc && !r.desc) r.desc = bonfy.desc;
            updated++;
        } else {
            existing.set(url, {
                name:   bonfy.name,
                url,
                lang:   bonfy.lang,
                days:   app,
                desc:   bonfy.desc,
                rating: app >= 5 ? 'High' : app >= 2 ? 'Medium' : 'Low',
            });
            added++;
        }
    }

    console.log(`\nNovos repos adicionados       : ${added}`);
    console.log(`Repos existentes incrementados : ${updated}`);

    // 4) Atualizar category e rating nos novos ────────────────────────────
    for (const r of existing.values()) {
        r.category = categorise(r.name, r.desc);
        if ((r.days || 0) <= 15 && !r.rating) {
            r.rating = r.days >= 5 ? 'High' : r.days >= 2 ? 'Medium' : 'Low';
        }
    }

    // 5) Re-rankear por days desc ─────────────────────────────────────────
    const merged = [...existing.values()].sort((a, b) =>
        (b.days || 0) - (a.days || 0) || a.name.toLowerCase().localeCompare(b.name.toLowerCase())
    );
    merged.forEach((r, i) => { r.rank = i + 1; });

    // Estatísticas
    const langCount = {};
    for (const r of merged) langCount[r.lang] = (langCount[r.lang] || 0) + 1;
    console.log(`\nDataset final: ${merged.length} repos`);
    for (const [lang, n] of Object.entries(langCount).sort((a, b) => b[1] - a[1]))
        console.log(`  ${lang.padEnd(12)} ${n}`);
    const goSwift = Object.entries(langCount)
        .filter(([l]) => ['go','swift','Go','Swift'].includes(l))
        .reduce((s, [, n]) => s + n, 0);
    console.log(`  Go + Swift   ${goSwift}  (deve ser 0)`);

    // 6) Salvar ───────────────────────────────────────────────────────────
    const jsonText = JSON.stringify(merged, null, 2);

    mkdirSync(dirname(REPOS_JSON), { recursive: true });
    writeFileSync(REPOS_JSON, jsonText, 'utf8');
    console.log(`\nSalvo: ${REPOS_JSON}  (${Math.round(Buffer.byteLength(jsonText) / 1024)} KB)`);

    mkdirSync(dirname(DOCS_JSON), { recursive: true });
    writeFileSync(DOCS_JSON, jsonText, 'utf8');
    console.log(`Salvo: ${DOCS_JSON}  (${Math.round(Buffer.byteLength(jsonText) / 1024)} KB)`);

    const dataJs = `const REPOS = ${JSON.stringify(merged)};\n`;
    writeFileSync(DATA_JS, dataJs, 'utf8');
    console.log(`Salvo: ${DATA_JS}  (${Math.round(Buffer.byteLength(dataJs) / 1024)} KB)`);

    console.log('\nConcluído.');
}

main().catch(err => { console.error(err); process.exit(1); });
