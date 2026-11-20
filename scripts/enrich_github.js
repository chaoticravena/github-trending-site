#!/usr/bin/env node
// Atualiza license, stars, pushed e archived de todos os repos via GitHub GraphQL
// (50 repos por query, ~125 chamadas para 6k repos). Roda inteiro a cada vez:
// estrelas e último push mudam, então não existe "já enriquecido".
// Token: GITHUB_TOKEN, GH_TOKEN ou `gh auth token`.
// Uso: node scripts/enrich_github.js [--batch 50]

import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const ROOT      = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const DOCS_JSON = resolve(ROOT, 'docs/data/repos.json');
const DATA_JSON = resolve(ROOT, 'data/repos.json');
const DATA_JS   = resolve(ROOT, 'docs/data.js');

function getToken() {
    if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN;
    if (process.env.GH_TOKEN)     return process.env.GH_TOKEN;
    try { return execSync('gh auth token', { encoding: 'utf8' }).trim(); } catch { return null; }
}

function buildQuery(batch) {
    return 'query {\n' + batch.map(({ alias, owner, name }) =>
        `  ${alias}: repository(owner: ${JSON.stringify(owner)}, name: ${JSON.stringify(name)}) ` +
        '{ nameWithOwner stargazerCount pushedAt isArchived licenseInfo { spdxId } }'
    ).join('\n') + '\n}';
}

async function fetchBatch(batch, token, attempt = 1) {
    const res = await fetch('https://api.github.com/graphql', {
        method: 'POST',
        headers: { Authorization: `bearer ${token}`, 'Content-Type': 'application/json', 'User-Agent': 'enrich_github/1.0' },
        body: JSON.stringify({ query: buildQuery(batch) }),
    });
    if ((res.status === 403 || res.status === 429 || res.status >= 500) && attempt <= 5) {
        const reset = Number(res.headers.get('x-ratelimit-reset'));
        const waitSec = res.headers.get('retry-after')
            ? Number(res.headers.get('retry-after'))
            : reset ? Math.max(0, reset - Math.floor(Date.now() / 1000)) + 2 : 30 * attempt;
        console.warn(`\n  HTTP ${res.status}, aguardando ${waitSec}s (tentativa ${attempt})...`);
        await new Promise(r => setTimeout(r, waitSec * 1000));
        return fetchBatch(batch, token, attempt + 1);
    }
    const json = await res.json();
    // erros com path = repo não encontrado (vem null em data); sem path = erro global
    const fatal = (json.errors || []).filter(e => !e.path);
    if (fatal.length || !json.data) throw new Error(JSON.stringify(fatal.length ? fatal : json).slice(0, 300));
    return json.data;
}

async function main() {
    const argv = process.argv.slice(2);
    const batchSize = argv.includes('--batch') ? Number(argv[argv.indexOf('--batch') + 1]) : 50;
    const token = getToken();
    if (!token) { console.error('Erro: sem GITHUB_TOKEN. Rode `gh auth login` ou defina a variável.'); process.exit(1); }

    const repos = JSON.parse(readFileSync(DOCS_JSON, 'utf8'));
    console.log(`Dataset: ${repos.length} repos`);
    let missing = 0, failed = 0;

    for (let i = 0; i < repos.length; i += batchSize) {
        const slice = repos.slice(i, i + batchSize);
        const batch = slice.map((r, j) => {
            const [owner, ...rest] = r.name.split('/');
            return { alias: `r${j}`, owner, name: rest.join('/'), repo: r };
        });
        let data;
        try { data = await fetchBatch(batch, token); }
        catch (err) { console.error(`\n  Batch ${i} falhou, mantendo valores antigos: ${err.message}`); failed += slice.length; continue; }

        for (const b of batch) {
            const node = data[b.alias];
            if (!node) { missing++; b.repo.archived = true; continue; }  // apagado ou privado: trata como morto
            if (node.nameWithOwner !== b.repo.name) {   // renomeado/transferido: passa a usar o nome atual
                b.repo.name = node.nameWithOwner;
                b.repo.url  = `https://github.com/${node.nameWithOwner}`;
            }
            b.repo.license  = node.licenseInfo?.spdxId ?? null;
            b.repo.stars    = node.stargazerCount;
            b.repo.pushed   = node.pushedAt ? node.pushedAt.slice(0, 10) : null;
            b.repo.archived = node.isArchived;
        }
        process.stdout.write(`\r[${String(Math.min(i + batchSize, repos.length)).padStart(5)}/${repos.length}]`);
        await new Promise(r => setTimeout(r, 150));
    }

    // renomeações podem gerar duas entradas pro mesmo repo: junta somando days (cada nome contou dias diferentes)
    const merged = new Map();
    for (const r of repos) {
        const key = r.url.toLowerCase(), prev = merged.get(key);
        if (!prev) { merged.set(key, r); continue; }
        const [keep, drop] = (prev.days || 0) >= (r.days || 0) ? [prev, r] : [r, prev];
        keep.days = (keep.days || 0) + (drop.days || 0);
        if ((drop.last_seen || '') > (keep.last_seen || '')) keep.last_seen = drop.last_seen;
        if (!keep.desc) keep.desc = drop.desc;
        const order = { High: 0, Medium: 1, Low: 2 };
        if ((order[drop.rating] ?? 3) < (order[keep.rating] ?? 3)) keep.rating = drop.rating;
        merged.set(key, keep);
    }
    const dupes = repos.length - merged.size;
    repos.length = 0;
    repos.push(...[...merged.values()].sort((a, b) =>
        (b.days || 0) - (a.days || 0) || a.name.toLowerCase().localeCompare(b.name.toLowerCase())));
    repos.forEach((r, i) => { r.rank = i + 1; });
    if (dupes) console.log(`\nDuplicatas por renomeação juntadas: ${dupes}`);

    const jsonText = JSON.stringify(repos, null, 2);
    writeFileSync(DOCS_JSON, jsonText, 'utf8');
    writeFileSync(DATA_JSON, jsonText, 'utf8');
    writeFileSync(DATA_JS, `const REPOS = ${JSON.stringify(repos)};\n`, 'utf8');

    const alive = repos.filter(r => !r.archived).length;
    console.log(`\n\nVivos: ${alive}  arquivados/sumidos: ${repos.length - alive} (sumidos: ${missing})  falhas: ${failed}`);
    console.log(`Com licença: ${repos.filter(r => r.license).length}`);
    // falha parcial não derruba o workflow: os repos do lote ficam com os valores da rodada anterior
    if (failed) console.warn(`::warning::${failed} repos sem atualização nesta rodada`);
}

main().catch(err => { console.error(err); process.exit(1); });
