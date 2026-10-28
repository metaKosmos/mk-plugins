#!/usr/bin/env node
// Monta a pasta project/ do canvas de um esboço: uma prancha por direção (A, B, C) lado a lado e,
// depois da escolha, a prancha final no mesmo canvas. Cada prancha é um fragmento HTML escrito
// por quem rodou a skill; este script o embrulha com os tokens da camada, confere o teto de 8000 px
// e grava o canvas.json.
//
//   node montar-esboco.mjs <esboco.json> <pasta> [--camada <pasta>]
//
// esboco.json: schema/esboco.schema.json. Os fragmentos (campo "arquivo") ficam ao lado dele.
// A primeira direção vira Main.dc.html (a entrada do canvas); as outras, Direcao-B.dc.html...;
// a final, Final.dc.html.
//
// Elemento visual: cada bloco da estrutura declara o seu ("visual": fluxograma, diagrama-de-blocos,
// linha-do-tempo, matriz, grafico, mapa-de-jornada, amostras-de-design ou texto). Com leitor visual
// (o padrão, só muda se esboco.json declarar "leitor": "textual"), o montador reprova direção sem
// nenhum bloco visual, sem "visual_dominante", com o mesmo dominante de outra direção, gráfico sem
// "fonte" e fragmento sem nenhum <svg>: a prancha que só tem texto em grade não passa.
//
// Fragmento: só HTML e style inline, com as CSS variables --vp-* (cor, fonte, raio) da camada.
// Reprovados: <script>, "{{" (o canvas lê como variável), traço longo e marca fora da grafia da
// camada, quando ela os define.
//
// A altura "h" de cada prancha vem da captura, não do palpite: o teto do canvas é 8000 px e o canvas
// corta sem aviso. Este script recusa h acima do teto, mas não mede o conteúdo. Se a captura
// mostrar corte, aumente o h e republique.
//
// Nada aqui publica: quem publica é a skill, com a ferramenta Artifact.

import { mkdirSync, readFileSync, realpathSync, writeFileSync } from 'node:fs';
import { dirname, extname, isAbsolute, join, resolve, sep } from 'node:path';
import { detectar, carregar, esquema, tokensPadrao, usoCamada, problemasDeTexto } from './lib/camada.mjs';
import { validarSchema } from './lib/schema.mjs';
import { blocoDeTokens, esc } from './lib/tokens-css.mjs';
import { dividirEstrutura, problemasVisuais } from './lib/esbocos.mjs';

const TETO = 8000;
const LARGURA = 1440;
const ESPACO = 80;

function falhar(msg, codigo = 1) {
  console.error(msg);
  process.exit(codigo);
}

const { explicito, resto } = usoCamada(process.argv.slice(2));
const [entrada, pasta] = resto;
if (!entrada || !pasta) falhar('uso: node montar-esboco.mjs <esboco.json> <pasta> [--camada <pasta>]', 2);

let spec;
try {
  spec = JSON.parse(readFileSync(entrada, 'utf8'));
} catch (e) {
  falhar(`${entrada}: não consegui ler. ${e.message}`);
}

const erros = [];
const sc = esquema('esboco.schema.json');
validarSchema(spec, sc, sc, '', erros);
if (!erros.length) {
  const rotulos = spec.direcoes.map((d) => d.rotulo);
  if (new Set(rotulos).size !== rotulos.length) erros.push('direcoes: rótulo repetido');
  if (spec.direcoes.length > 3) erros.push('direcoes: no máximo 3 (A, B, C)');
  erros.push(...problemasVisuais(spec));
}

let camada = null;
try {
  camada = carregar(detectar(explicito, [entrada]));
} catch (e) {
  falhar(e.message);
}
if (camada) console.log(`camada ${camada.dir}`);
else console.log('sem camada: tokens neutros do motor e sem regra de marca');
const tokens = camada?.tokens ?? tokensPadrao();
const regras = camada?.regras ?? null;

const pranchas = [];
if (!erros.length) {
  for (const d of spec.direcoes) {
    pranchas.push({ arquivo: pranchas.length ? `Direcao-${d.rotulo}.dc.html` : 'Main.dc.html', titulo: `${d.rotulo}: ${d.nome}`, fonte: d.arquivo, h: d.h, texto: [d.nome, d.privilegia, ...dividirEstrutura(d.estrutura).blocos], visual: d.estrutura });
  }
  if (spec.final) {
    pranchas.push({ arquivo: 'Final.dc.html', titulo: `Final: ${spec.final.escolha}`, fonte: spec.final.arquivo, h: spec.final.h, texto: [spec.final.escolha, ...dividirEstrutura(spec.final.estrutura).blocos], visual: spec.final.estrutura });
  }
  for (const t of [spec.titulo, spec.pedido, ...(spec.lacunas ?? []).flatMap((l) => [l.o_que_falta, l.depende_de])]) {
    for (const m of problemasDeTexto(t, regras)) erros.push(`"${String(t).slice(0, 40)}": ${m}`);
  }
}

const base = realpathSync(dirname(resolve(entrada)));

/** Caminho do fragmento, ou lança. O fragmento fica dentro da pasta do esboco.json: relativo, sem "..",
 *  só .html, e (depois de resolver links simbólicos) ainda dentro da pasta. */
function caminhoDoFragmento(rel) {
  if (isAbsolute(rel) || /^[A-Za-z]:/.test(rel)) throw new Error('caminho absoluto não é aceito');
  if (rel.split(/[\\/]+/).includes('..')) throw new Error('".." não é aceito');
  if (extname(rel).toLowerCase() !== '.html') throw new Error('só arquivo .html');
  const alvo = resolve(base, rel);
  if (!alvo.startsWith(base + sep)) throw new Error('fora da pasta do esboco.json');
  const real = realpathSync(alvo);
  if (!real.startsWith(base + sep)) throw new Error('o link simbólico aponta para fora da pasta do esboco.json');
  return real;
}
for (const p of pranchas) {
  if (p.h > TETO) erros.push(`${p.titulo}: h=${p.h} passa do teto de ${TETO} px. Divida o conteúdo em duas pranchas`);
  for (const t of p.texto) for (const m of problemasDeTexto(t, regras)) erros.push(`${p.titulo}, "${String(t).slice(0, 40)}": ${m}`);
  try {
    p.html = readFileSync(caminhoDoFragmento(p.fonte), 'utf8');
  } catch (e) {
    erros.push(`${p.titulo}: fragmento "${p.fonte}" recusado ou ilegível. ${e.message}`);
    continue;
  }
  if (/<script/i.test(p.html)) erros.push(`${p.titulo}: <script> não entra no fragmento. A prancha é HTML estático`);
  if (p.html.includes('{{')) erros.push(`${p.titulo}: "{{" no fragmento. O canvas lê como variável: troque o texto`);
  if (spec.leitor !== 'textual' && !/<svg[\s>]/i.test(p.html)) {
    erros.push(`${p.titulo}: o leitor é visual e o fragmento não tem nenhum <svg>. Desenhe o elemento visual (fluxograma, diagrama, linha do tempo, gráfico) em SVG inline, não só texto em grade`);
  }
  const visivel = p.html.replace(/<style[\s\S]*?<\/style>/gi, '').replace(/<[^>]*>/g, ' ');
  for (const m of problemasDeTexto(visivel, regras)) erros.push(`${p.titulo}: ${m}`);
}

if (erros.length) {
  for (const e of erros) console.error(`ERRO   ${e}`);
  falhar(`esboço inválido: ${erros.length} erro(s), nada foi montado`);
}

const projeto = join(pasta, 'project');
mkdirSync(projeto, { recursive: true });
const lang = camada?.camada.escrita?.idioma ?? 'pt-BR';

const casca = (p) => `<!doctype html>
<html lang="${esc(lang)}">
<head>
<meta charset="utf-8">
<title>${esc(p.titulo)}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
${blocoDeTokens(tokens)}
<style>
body{margin:0;background:var(--vp-fundo)}
</style>
</helmet>
<div style="width: ${LARGURA}px; box-sizing: border-box; padding: 64px; background: var(--vp-fundo); color: var(--vp-texto); font-family: var(--vp-fonte-corpo); font-weight: var(--vp-corpo-peso);">
${p.html}
</div>
</x-dc>
</body>
</html>
`;

const boards = {};
const order = [];
const arquivos = [];
let x = 0;
for (const p of pranchas) {
  writeFileSync(join(projeto, p.arquivo), casca(p));
  boards[p.arquivo] = { x, y: 0, w: LARGURA, h: p.h, title: p.titulo };
  order.push(p.arquivo);
  arquivos.push(`project/${p.arquivo}`);
  x += LARGURA + ESPACO;
}

const canvas = {
  v: 3,
  createdOnFiles: { v: 1, at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z') },
  title: spec.titulo,
  launch: { view: 'canvas' },
  pages: [],
  boards,
  order,
  notes: { t1: { kind: 'title1', text: spec.titulo, x: 0, y: -300, w: 240, maxW: x - ESPACO } },
  designSystems: []
};
writeFileSync(join(projeto, 'canvas.json'), JSON.stringify(canvas, null, 2) + '\n');

console.log(`gravado ${join(projeto, 'canvas.json')}`);
console.log(`\n${pranchas.length} prancha(s) de ${LARGURA} px:`);
for (const p of pranchas) {
  const v = dividirEstrutura(p.visual).visuais.filter((x) => x !== 'texto');
  console.log(`  ${p.arquivo.padEnd(20)} h=${p.h}  ${p.titulo}${v.length ? `  [visuais: ${[...new Set(v)].join(', ')}]` : ''}`);
}
for (const l of spec.lacunas ?? []) console.log(`lacuna  ${l.o_que_falta} (depende de ${l.depende_de})`);
console.log('\nPublicar (Artifact, action publish, com o url do canvas):');
console.log(JSON.stringify({ root: pasta, file_path: join(projeto, 'canvas.json'), files: Object.fromEntries(arquivos.map((a) => [a, a])) }, null, 2));
