#!/usr/bin/env node
// Confere que doc, mapa (canvas), Linear e o arquivo do Drive apontam o mesmo link e a mesma
// versão do mesmo documento. A referência é o `documento` do projeto.json (id, url, versao);
// cada artefato informado é comparado com ela, e o título do doc.md manda na versão.
//
//   node conferir-versao.mjs conferir <projeto.json> [--doc doc.md] [--canvas dados/projeto.json]
//                                     [--linear texto.txt] [--drive arquivo.json]
//   node conferir-versao.mjs bloco <projeto.json>
//
// --doc     o doc.md que subiu: a versão vem da linha logo abaixo do título ("... · v3")
// --canvas  o dados/projeto.json que o mapa publicou (montar-canvas grava em project/dados/)
// --linear  o texto do projeto no Linear (descrição e recursos), lido por quem confere
// --drive   a resposta do `gws drive files get` do doc (id e description, onde a versão fica).
//           Grave com `2>/dev/null`; se vier misturada com o stderr, o que antecede o primeiro "{" é ignorado
// bloco     imprime a linha que vai na descrição do projeto no Linear
//
// Exit 0: tudo igual. Exit 1: divergência, uma por linha, com o artefato. Exit 2: uso.
// Nada aqui lê o Drive nem o Linear: quem roda a skill traz o conteúdo.

import { readFileSync } from 'node:fs';
import { blocoLinear, errosDoProjeto, errosDoLinear, versaoDoDoc, citaVersao, idDaUrl, RE_VERSAO } from './lib/documento.mjs';

function ler(arquivo) {
  try {
    return readFileSync(arquivo, 'utf8');
  } catch (erro) {
    console.error(`${arquivo}: não consegui ler. ${erro.message}`);
    process.exit(2);
  }
}

function lerJson(arquivo) {
  try {
    return JSON.parse(ler(arquivo));
  } catch (erro) {
    console.error(`${arquivo}: JSON ilegível. ${erro.message}`);
    process.exit(1);
  }
}

// A saída do gws traz "Using keyring backend: keyring" (stderr) antes do JSON quando foi gravada
// com `2>&1`: lê a partir do primeiro "{".
function lerJsonDoGws(arquivo) {
  const texto = ler(arquivo);
  const ini = texto.indexOf('{');
  try {
    if (ini < 0) throw new Error('sem JSON no arquivo');
    return JSON.parse(texto.slice(ini));
  } catch (erro) {
    console.error(`${arquivo}: JSON ilegível. ${erro.message}`);
    process.exit(1);
  }
}

const [comando, projetoArq, ...resto] = process.argv.slice(2);
if (!['conferir', 'bloco'].includes(comando) || !projetoArq) {
  console.error('uso: node conferir-versao.mjs conferir <projeto.json> [--doc doc.md] [--canvas dados.json] [--linear texto.txt] [--drive arquivo.json]\n     node conferir-versao.mjs bloco <projeto.json>');
  process.exit(2);
}

const projeto = lerJson(projetoArq);
const doc = projeto.documento;
if (!doc) {
  console.log(`ERRO   documento: ${projetoArq} não tem o bloco "documento" (id, url, versao): o projeto não registra qual doc do Drive é o dele`);
  process.exit(1);
}
if (!idDaUrl(doc.url) || !RE_VERSAO.test(doc.versao ?? '')) {
  console.log(`ERRO   documento: url ou versao inválidas em ${projetoArq} (esperado docs.google.com/document/d/<id> e v<N>)`);
  process.exit(1);
}

if (comando === 'bloco') {
  console.log(blocoLinear(doc));
  process.exit(0);
}

const opcoes = {};
for (let i = 0; i < resto.length; i += 2) {
  const nome = resto[i];
  if (!['--doc', '--canvas', '--linear', '--drive'].includes(nome) || !resto[i + 1]) {
    console.error(`argumento inesperado: ${nome}`);
    process.exit(2);
  }
  opcoes[nome.slice(2)] = resto[i + 1];
}

const erros = [];
const ok = [];
const confere = (rotulo, lista) => {
  for (const e of lista) erros.push(`${rotulo}: ${e}`);
  if (!lista.length) ok.push(`${rotulo}=ok`);
};

confere('projeto', errosDoProjeto(projeto));

if (opcoes.doc) {
  const v = versaoDoDoc(ler(opcoes.doc));
  confere('doc', v === null
    ? [`o título de ${opcoes.doc} não traz a versão (linha abaixo do #, "<data> · <autor> · v<N>")`]
    : v === doc.versao ? [] : [`o doc está em ${v} e o projeto.json cita ${doc.versao}`]);
}

if (opcoes.canvas) {
  const c = lerJson(opcoes.canvas);
  const lista = [];
  const d = c.documento;
  if (!d) lista.push('o mapa publicado não tem o bloco "documento": está desatualizado');
  else {
    if (d.id !== doc.id || d.url !== doc.url) lista.push(`o mapa aponta ${d.url} e o projeto aponta ${doc.url}`);
    if (d.versao !== doc.versao) lista.push(`o mapa está em ${d.versao} e o doc está em ${doc.versao}`);
  }
  const fonte = (c.ref?.fontes ?? []).find((f) => f?.url === doc.url);
  if (!fonte) lista.push(`o mapa não cita o link do documento (${doc.url}) em ref.fontes`);
  else if (!citaVersao(fonte.rotulo, doc.versao)) lista.push(`o mapa cita "${fonte.rotulo}" e o doc está em ${doc.versao}`);
  confere('canvas', lista);
}

if (opcoes.linear) confere('linear', errosDoLinear(ler(opcoes.linear), doc));

if (opcoes.drive) {
  const f = lerJsonDoGws(opcoes.drive);
  const lista = [];
  if (f.id !== doc.id) lista.push(`o arquivo do Drive é ${f.id} e o projeto aponta ${doc.id}`);
  if (!citaVersao(f.description, doc.versao)) lista.push(`o arquivo do Drive está em "${f.description ?? ''}" e o doc está em ${doc.versao}`);
  confere('drive', lista);
}

console.log(`documento=${doc.id}`);
console.log(`link=${doc.url}`);
console.log(`versao=${doc.versao}`);
for (const o of ok) console.log(o);
for (const e of erros) console.log(`ERRO   ${e}`);
if (erros.length) {
  console.log(`${erros.length} divergência(s)`);
  process.exit(1);
}
