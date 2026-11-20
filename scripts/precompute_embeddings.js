#!/usr/bin/env node
// Gera em build-time, a partir de docs/data/repos.json:
//   docs/data/embeddings.json  {model, dim, urls[], q}  q = base64 de int8 (dim bytes por repo)
//   docs/data/similar.json     {names[], sim[][]}       sim[i] = índices dos 5 repos mais parecidos (vivos)
// Uso: node scripts/precompute_embeddings.js

import { pipeline } from '@xenova/transformers';
import { readFileSync, writeFileSync } from 'fs';
import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';

const ROOT  = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const MODEL = 'Xenova/all-MiniLM-L6-v2';
const DIM   = 384;
const TOP   = 5;

const repoText = r => `${r.name} ${r.desc || ''} ${r.category || ''} ${r.lang || ''}`.trim();

// int8 com escala por vetor; o browser renormaliza ao decodificar, então a escala não precisa ser salva
function quantize(vecs) {
    const out = new Int8Array(vecs.length * DIM);
    vecs.forEach((v, i) => {
        let max = 0;
        for (const x of v) max = Math.max(max, Math.abs(x));
        for (let k = 0; k < DIM; k++) out[i * DIM + k] = Math.round(v[k] / (max || 1) * 127);
    });
    return Buffer.from(out.buffer).toString('base64');
}

// ponytail: força bruta O(n²·dim), ~15s para 6k repos; troque por ANN se passar de ~50k
function topSimilar(vecs, alive) {
    const n = vecs.length;
    return vecs.map((a, i) => {
        const best = [];   // [score, idx] em ordem decrescente
        for (let j = 0; j < n; j++) {
            if (j === i || !alive[j]) continue;
            const b = vecs[j];
            let s = 0;
            for (let k = 0; k < DIM; k++) s += a[k] * b[k];
            if (best.length < TOP || s > best[best.length - 1][0]) {
                best.push([s, j]);
                best.sort((x, y) => y[0] - x[0]);
                if (best.length > TOP) best.pop();
            }
        }
        return best.map(([, j]) => j);
    });
}

async function main() {
    const repos = JSON.parse(readFileSync(resolve(ROOT, 'docs/data/repos.json'), 'utf8'));
    console.log(`${repos.length} repos. Carregando ${MODEL}...`);
    const extractor = await pipeline('feature-extraction', MODEL);

    const vecs = [];
    for (let i = 0; i < repos.length; i += 32) {
        const out = await extractor(repos.slice(i, i + 32).map(repoText), { pooling: 'mean', normalize: true });
        for (let j = 0; j < out.dims[0]; j++) vecs.push(out.data.slice(j * DIM, (j + 1) * DIM));
        process.stdout.write(`\r  embeddings ${vecs.length}/${repos.length}`);
    }

    console.log('\n  calculando vizinhos...');
    const sim = topSimilar(vecs, repos.map(r => !r.archived));

    const emb = JSON.stringify({ model: MODEL, dim: DIM, urls: repos.map(r => r.url), q: quantize(vecs) });
    writeFileSync(resolve(ROOT, 'docs/data/embeddings.json'), emb);
    const simJson = JSON.stringify({ names: repos.map(r => r.name), sim });
    writeFileSync(resolve(ROOT, 'docs/data/similar.json'), simJson);
    console.log(`Salvo: embeddings.json (${Math.round(emb.length / 1024)} KB), similar.json (${Math.round(simJson.length / 1024)} KB)`);
}

main().catch(err => { console.error(err); process.exit(1); });
