#!/usr/bin/env node
/**
 * enrich_licenses.js
 *
 * Preenche o campo `license` (SPDX id ou null) para todos os repos do dataset
 * que ainda não têm essa informação, usando a API GraphQL do GitHub (batches de
 * 50 repos por query → ~120 chamadas para 5895 repos, em vez de 5895).
 *
 * Requer GITHUB_TOKEN (ou GH_TOKEN) no ambiente, ou tenta `gh auth token`.
 * Sem token: limite de 60 req/h na API REST — GraphQL exige autenticação.
 *
 * Uso: node scripts/enrich_licenses.js [--batch 50] [--all]
 *   --all  reprocessa mesmo repos que já têm license (útil para corrigir)
 */

import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import { execSync } from 'child_process';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT      = resolve(__dirname, '..');
const DOCS_JSON = resolve(ROOT, 'docs/data/repos.json');
const DATA_JSON = resolve(ROOT, 'data/repos.json');
const DATA_JS   = resolve(ROOT, 'docs/data.js');

const GQL_URL = 'https://api.github.com/graphql';

// ── token ─────────────────────────────────────────────────────────────────────
function getToken() {
    if (process.env.GITHUB_TOKEN) return process.env.GITHUB_TOKEN;
    if (process.env.GH_TOKEN)     return process.env.GH_TOKEN;
    try { return execSync('gh auth token', { encoding: 'utf8' }).trim(); } catch {}
    return null;
}

// ── GraphQL batch query ───────────────────────────────────────────────────────
// Monta uma query com até N aliases, um por repo.
// Se o repo não existir ou for privado, o campo vem null (sem erro fatal).
function buildQuery(batch) {
    const fields = batch.map(({ alias, owner, name }) =>
        `  ${alias}: repository(owner: ${JSON.stringify(owner)}, name: ${JSON.stringify(name)}) { licenseInfo { spdxId } }`
    ).join('\n');
    return `query {\n${fields}\n}`;
}

async function fetchLicenses(batch, token) {
    const query = buildQuery(batch);
    const res = await fetch(GQL_URL, {
        method: 'POST',
        headers: {
            'Authorization': `bearer ${token}`,
            'Content-Type':  'application/json',
            'User-Agent':    'enrich_licenses/1.0',
        },
        body: JSON.stringify({ query }),
    });

    if (res.status === 403 || res.status === 429) {
        const retryAfter = res.headers.get('retry-after') || res.headers.get('x-ratelimit-reset');
        const waitSec = retryAfter
            ? Math.max(0, Number(retryAfter) - Math.floor(Date.now() / 1000)) + 2
            : 60;
        console.warn(`  Rate limit — aguardando ${waitSec}s...`);
        await new Promise(r => setTimeout(r, waitSec * 1000));
        return fetchLicenses(batch, token);   // retry
    }

    const json = await res.json();
    // errors parciais (repo não encontrado) vêm em json.errors mas data ainda é válido
    if (json.errors) {
        const fatal = json.errors.filter(e => !e.path);   // erros sem path = globais
        if (fatal.length) throw new Error(JSON.stringify(fatal));
    }
    return json.data || {};
}

// ── argparse ─────────────────────────────────────────────────────────────────
function getArgs() {
    const argv = process.argv.slice(2);
    return {
        batchSize: Number(argv[argv.indexOf('--batch') + 1] || 50),
        reprocessAll: argv.includes('--all'),
    };
}

// ── main ──────────────────────────────────────────────────────────────────────
async function main() {
    const { batchSize, reprocessAll } = getArgs();

    const token = getToken();
    if (!token) {
        console.error('Erro: GITHUB_TOKEN não encontrado. Execute `gh auth login` ou defina a variável.');
        process.exit(1);
    }
    console.log(`Token: ${token.slice(0, 8)}...`);

    // Carregar dataset
    const repos = JSON.parse(readFileSync(DOCS_JSON, 'utf8'));
    console.log(`Dataset: ${repos.length} repos`);

    // Selecionar repos que precisam de enriquecimento
    const todo = repos.filter(r => reprocessAll || !('license' in r));
    console.log(`Repos sem license: ${todo.length}${reprocessAll ? ' (modo --all)' : ''}\n`);

    if (!todo.length) {
        console.log('Nada a fazer — todos os repos já têm o campo license.');
        return;
    }

    // Construir mapa url→repo para atualização rápida
    const byUrl = new Map(repos.map(r => [r.url, r]));

    let processed = 0, withLicense = 0, nullLicense = 0, errors = 0;
    const startTime = Date.now();

    for (let i = 0; i < todo.length; i += batchSize) {
        const slice = todo.slice(i, i + batchSize);

        // Montar batch com aliases válidos (só letras/dígitos/underscore)
        const batch = slice.map((r, j) => {
            const parts = r.name.split('/');
            return {
                alias: `r${i + j}`,
                owner: parts[0],
                name:  parts.slice(1).join('/'),
                url:   r.url,
            };
        });

        let data = {};
        try {
            data = await fetchLicenses(batch, token);
        } catch (err) {
            console.error(`  Erro no batch ${i}–${i + slice.length - 1}: ${err.message}`);
            errors += slice.length;
            // Marca como null para não bloquear
            for (const b of batch) {
                const r = byUrl.get(b.url);
                if (r) r.license = null;
            }
            processed += slice.length;
            continue;
        }

        for (const b of batch) {
            const r = byUrl.get(b.url);
            if (!r) continue;
            const node = data[b.alias];
            const spdx = node?.licenseInfo?.spdxId ?? null;
            r.license = spdx;
            if (spdx) withLicense++; else nullLicense++;
        }

        processed += slice.length;

        // Progresso a cada batch
        const pct   = ((processed / todo.length) * 100).toFixed(1);
        const elSec = ((Date.now() - startTime) / 1000).toFixed(0);
        const eta   = processed < todo.length
            ? Math.round((Date.now() - startTime) / processed * (todo.length - processed) / 1000)
            : 0;
        process.stdout.write(
            `\r[${pct.padStart(5)}%] ${processed}/${todo.length}  ` +
            `com licença: ${withLicense}  sem: ${nullLicense}  ${elSec}s  ETA ${eta}s  `
        );

        // Pausa leve entre batches para não estressar a API
        if (i + batchSize < todo.length) await new Promise(r => setTimeout(r, 200));
    }

    console.log('\n');

    // Salvar JSON atualizado
    const jsonText = JSON.stringify(repos, null, 2);
    writeFileSync(DOCS_JSON, jsonText, 'utf8');
    writeFileSync(DATA_JSON, jsonText, 'utf8');
    console.log(`Salvo: ${DOCS_JSON}  (${Math.round(Buffer.byteLength(jsonText) / 1024)} KB)`);

    // Salvar data.js
    const dataJs = `const REPOS = ${JSON.stringify(repos)};\n`;
    writeFileSync(DATA_JS, dataJs, 'utf8');
    console.log(`Salvo: ${DATA_JS}  (${Math.round(Buffer.byteLength(dataJs) / 1024)} KB)`);

    // Resumo
    const licensed = repos.filter(r => r.license).length;
    const noLic    = repos.filter(r => r.license === null).length;
    const pending  = repos.filter(r => !('license' in r)).length;
    console.log(`\nResumo do dataset completo:`);
    console.log(`  Com licença  : ${licensed}`);
    console.log(`  Sem licença  : ${noLic}`);
    console.log(`  Pendente     : ${pending}`);
    if (errors) console.log(`  Erros de API : ${errors}`);

    // Top licenças
    const freq = {};
    for (const r of repos) if (r.license) freq[r.license] = (freq[r.license] || 0) + 1;
    const top = Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 10);
    console.log('\nTop licenças:');
    for (const [lic, n] of top) console.log(`  ${lic.padEnd(20)} ${n}`);

    console.log('\nConcluído.');
}

main().catch(err => { console.error(err); process.exit(1); });
