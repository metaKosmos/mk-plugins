#!/usr/bin/env node
// Monta a pasta project/ de um canvas (tipo Design) a partir de um projeto.json:
// valida, mede, copia os moldes (com a quebra aplicada quando uma prancha passa
// do teto), grava o canvas.json e o dados/projeto.json.
//
//   node montar-canvas.mjs <projeto.json> "<título do canvas>" <pasta> [--camada <pasta>]
//   node montar-canvas.mjs <projeto.json> --so-dados <pasta> [--camada <pasta>]
//
// Os moldes não têm cor, fonte nem marca no código: leem CSS variables (--vp-*). Este script
// injeta em cada molde os tokens da camada (tokens.json sobre o padrão neutro do motor), as
// fontes e as palavras de marca que a caixa alta deve preservar.
//
// A pasta vira o `root` da publicação: <pasta>/project/... é o que vai para o
// canvas. O Conceito é publicado como Main.dc.html (a entrada do canvas).
// --so-dados grava só <pasta>/project/dados/projeto.json: é a republicação do
// conteúdo, sem tocar nos moldes nem no layout.
//
// Nada aqui publica: quem publica é a skill, com a ferramenta Artifact.

import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validar } from './validar-projeto.mjs';
import { planejar, LARGURA } from './medir-pranchas.mjs';
import { detectar, carregar, tokensPadrao, usoCamada } from './lib/camada.mjs';
import { blocoDeTokens as blocoDeTokensLib } from './lib/tokens-css.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const MOLDES = join(AQUI, '..', 'skills', 'visual-de-projeto', 'moldes');

function falhar(msg, codigo = 1) {
  console.error(msg);
  process.exit(codigo);
}

function blocoDeTokens(t) {
  try {
    return blocoDeTokensLib(t);
  } catch (erro) {
    return falhar(erro.message);
  }
}

function configDoMolde(t, camada) {
  const cfg = {
    caixa: t.fontes.titulo.caixa,
    preservar: camada?.regras.preservar ?? [],
    marca: camada?.camada.empresa.rotulo_canvas ?? '',
    cores: { fundo: t.cores.fundo, acento: t.cores.acento }
  };
  return JSON.stringify(cfg).replace(/</g, '\\u003c');
}

function opcoesDeAcento(t, camada) {
  const cores = [...(camada?.camada.areas ?? []).map((a) => a.cor), camada?.regras.acentoPadrao, t.cores.acento, t.cores.texto].filter(Boolean);
  return [...new Set(cores.map((c) => c.toLowerCase()))].map((c) => `"${c}"`).join(',');
}

function aplicarTokens(html, t, camada, arquivo) {
  if (!html.includes('<!--vp:tokens-->')) falhar(`molde sem o marcador <!--vp:tokens--> (${arquivo})`);
  if (!/\/\*vp:config\*\/[\s\S]*?\/\*vp:fim\*\//.test(html)) falhar(`molde sem o bloco vp:config (${arquivo})`);
  // funções no replace: o texto novo pode ter "$" e não deve ser lido como padrão de troca
  return html
    .replace('<!--vp:tokens-->', () => blocoDeTokens(t))
    .replace(/\/\*vp:config\*\/[\s\S]*?\/\*vp:fim\*\//, () => configDoMolde(t, camada))
    .replace('"__VP_OPCOES__"', () => opcoesDeAcento(t, camada));
}

function aplicarProps(html, props, arquivo) {
  let saida = html;
  for (const [chave, valor] of Object.entries(props)) {
    const re = new RegExp(`("${chave}":\\{"editor":"int","default":)\\d+`);
    if (!re.test(saida)) falhar(`molde sem a prop ${chave} (${arquivo}): o molde e o medidor divergiram`);
    saida = saida.replace(re, `$1${valor}`);
  }
  return saida;
}

const { explicito, resto } = usoCamada(process.argv.slice(2));
const [entrada, segundo, terceiro] = resto;
if (!entrada || !segundo) falhar('uso: node montar-canvas.mjs <projeto.json> "<título>" <pasta> [--camada <pasta>]\n     node montar-canvas.mjs <projeto.json> --so-dados <pasta> [--camada <pasta>]', 2);

const soDados = segundo === '--so-dados';
const pasta = terceiro;
if (!pasta) falhar('falta a pasta de saída', 2);

let dados;
try {
  dados = JSON.parse(readFileSync(entrada, 'utf8'));
} catch (erro) {
  falhar(`${entrada}: não consegui ler. ${erro.message}`);
}

let camada = null;
try {
  camada = carregar(detectar(explicito, [entrada]));
} catch (erro) {
  falhar(erro.message);
}
if (camada) console.log(`camada ${camada.dir}`);
const tokens = camada?.tokens ?? tokensPadrao();

const { erros, avisos } = validar(dados, camada?.regras ?? null);
for (const a of avisos) console.log(`aviso  ${a}`);
if (erros.length) {
  for (const e of erros) console.error(`ERRO   ${e}`);
  falhar('projeto.json inválido: nada foi montado');
}

const projeto = join(pasta, 'project');
mkdirSync(join(projeto, 'dados'), { recursive: true });
writeFileSync(join(projeto, 'dados', 'projeto.json'), JSON.stringify(dados, null, 2) + '\n');
console.log(`gravado ${join(projeto, 'dados', 'projeto.json')}`);
if (soDados) process.exit(0);

const titulo = segundo;
const plano = planejar(dados, tokens.medidas);
for (const a of plano.avisos) console.log(`aviso  ${a}`);
if (plano.acimaDoTeto) falhar('alguma prancha passa do teto de 8000 px mesmo depois da quebra: veja os avisos acima');

const boards = {};
const order = [];
const arquivos = [];
let x = 0;
for (const p of plano.pranchas) {
  let html = readFileSync(join(MOLDES, `${p.molde}.dc.html`), 'utf8');
  html = aplicarTokens(html, tokens, camada, p.arquivo);
  if (p.props) html = aplicarProps(html, p.props, p.arquivo);
  writeFileSync(join(projeto, p.arquivo), html);
  const entradaBoard = { x, y: 0, w: p.w, h: p.h, title: p.titulo };
  if (p.interativa) entradaBoard.is_interactive = true;
  boards[p.arquivo] = entradaBoard;
  order.push(p.arquivo);
  arquivos.push(`project/${p.arquivo}`);
  x += p.w + 80;
}
arquivos.push('project/dados/projeto.json');

const canvas = {
  v: 3,
  createdOnFiles: { v: 1, at: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z') },
  title: titulo,
  launch: { view: 'canvas' },
  pages: [],
  boards,
  order,
  notes: { t1: { kind: 'title1', text: titulo, x: 0, y: -300, w: 240, maxW: x - 80 } },
  designSystems: []
};
writeFileSync(join(projeto, 'canvas.json'), JSON.stringify(canvas, null, 2) + '\n');

console.log(`gravado ${join(projeto, 'canvas.json')}`);
console.log(`\n${plano.pranchas.length} prancha(s) de ${LARGURA} px:`);
for (const p of plano.pranchas) console.log(`  ${p.arquivo.padEnd(24)} h=${p.h}  ${p.titulo}`);
console.log('\nPublicar (Artifact, action publish, com o url do canvas):');
console.log(JSON.stringify({ root: pasta, file_path: join(projeto, 'canvas.json'), files: Object.fromEntries(arquivos.map((a) => [a, a])) }, null, 2));
