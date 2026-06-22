#!/usr/bin/env node
// Gera embeddings para todos os repos em build-time (Node.js).
// Saída: docs/data/repos_embeddings.json
// Uso: node scripts/precompute_embeddings.js

import { pipeline } from '@xenova/transformers';
import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT      = resolve(__dirname, '..');

const MODEL_NAME = 'Xenova/all-MiniLM-L6-v2';
const INPUT_PATHS = [
    resolve(ROOT, 'docs/data/repos_enriched.json'),
    resolve(ROOT, 'docs/data/repos.json'),
];
const OUTPUT_PATH = resolve(ROOT, 'docs/data/repos_embeddings.json');

function loadRepos() {
    for (const p of INPUT_PATHS) {
        try {
            const data = JSON.parse(readFileSync(p, 'utf8'));
            console.log(`Lendo ${data.length} repos de ${p}`);
            return data;
        } catch {}
    }
    throw new Error('Nenhum arquivo de repos encontrado: ' + INPUT_PATHS.join(', '));
}

function repoText(r) {
    return `${r.name} ${r.desc || ''} ${r.category || ''} ${r.lang || ''}`.trim();
}

async function main() {
    const repos = loadRepos();

    console.log(`Carregando modelo ${MODEL_NAME}...`);
    const extractor = await pipeline('feature-extraction', MODEL_NAME);
    console.log('Modelo carregado.\n');

    const results = [];
    const BATCH  = 32;
    const total  = repos.length;

    for (let i = 0; i < total; i += BATCH) {
        const slice = repos.slice(i, Math.min(i + BATCH, total));
        const texts = slice.map(repoText);

        const out = await extractor(texts, { pooling: 'mean', normalize: true });

        for (let j = 0; j < slice.length; j++) {
            const flat = Array.from(out[j].data);
            results.push({ url: slice[j].url, embedding: flat });
        }

        const done = Math.min(i + BATCH, total);
        const pct  = ((done / total) * 100).toFixed(1);
        process.stdout.write(`\r[${pct.padStart(5)}%] ${done}/${total} repos processados`);
    }

    console.log('\n');
    writeFileSync(OUTPUT_PATH, JSON.stringify(results));
    console.log(`Salvo: ${OUTPUT_PATH} (${results.length} entradas)`);
}

main().catch(err => { console.error(err); process.exit(1); });
