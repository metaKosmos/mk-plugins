#!/usr/bin/env node
// Valida um projeto.json (contrato v1) contra schema/projeto.schema.json e
// confere o que o schema não alcança: referências entre trilhas, itens e
// dependências, datas reais, e as regras de escrita e de marca da CAMADA
// (grafias reprovadas, traço longo, cor de acento por área).
//
//   node validar-projeto.mjs <projeto.json> [--camada <pasta>]
//
// A camada é a pasta com camada.json, tokens.json e esqueleto.md (veja
// scripts/lib/camada.mjs para como ela é achada). Sem camada, só valem o schema
// e a semântica: nenhuma regra de marca é aplicada, e o aviso diz isso.
//
// Exit 0: válido (avisos podem sair). Exit 1: lista de erros, um por linha,
// cada um com o caminho do campo.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { executadoDiretamente } from './lib/execucao.mjs';
import { validarSchema, caminho } from './lib/schema.mjs';
import { errosDoProjeto } from './lib/documento.mjs';
import { detectar, carregar, usoCamada, problemasDeTexto, acentoEsperado } from './lib/camada.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SCHEMA = JSON.parse(readFileSync(join(AQUI, '..', 'schema', 'projeto.schema.json'), 'utf8'));

/** `regras`: o resultado de compilar() da camada, ou null/undefined sem camada. */
export function validar(dados, regras = null) {
  const erros = [];
  const avisos = [];
  validarSchema(dados, SCHEMA, SCHEMA, '', erros);
  if (dados && typeof dados === 'object' && !Array.isArray(dados)) conferirSemantica(dados, erros, avisos, regras);
  return { erros, avisos };
}

// ---- semântica ------------------------------------------------------------

function dataReal(texto) {
  if (typeof texto !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(texto)) return null;
  const t = Date.parse(`${texto}T00:00:00Z`);
  if (Number.isNaN(t)) return null;
  return new Date(t).toISOString().slice(0, 10) === texto ? t : null;
}

const SECOES = ['projeto', 'kpis', 'fontes_dados', 'fases', 'capacidades', 'hipoteses', 'roadmap'];

function semAcento(texto) {
  return String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z_]/g, '');
}

function conferirSemantica(d, erros, avisos, regras) {
  // datas que passaram no formato mas não existem (2026-02-31)
  for (const [onde, valor] of coletarDatas(d)) {
    if (valor !== null && dataReal(valor) === null) erros.push(`${onde}: "${valor}" não é uma data real`);
  }

  // escrita e marca da camada, em todo texto que não é link
  if (regras) {
    for (const [onde, valor] of coletarTextos(d)) {
      for (const problema of problemasDeTexto(valor, regras)) erros.push(`${onde}: ${problema}`);
    }
  } else {
    avisos.push('sem camada: regras de marca e de escrita não aplicadas (informe --camada <pasta>)');
  }

  // o doc é um só: o bloco `documento` e o que o mapa cita têm de bater
  erros.push(...errosDoProjeto(d));

  // ids duplicados
  const trilhas = d.roadmap?.trilhas ?? [];
  const itens = d.roadmap?.itens ?? [];
  const idsTrilha = duplicados(trilhas.map((t) => t?.id), 'roadmap.trilhas', erros);
  const idsItem = duplicados(itens.map((i) => i?.id), 'roadmap.itens', erros);
  duplicados((d.hipoteses ?? []).map((h) => h?.id).filter(Boolean), 'hipoteses', erros);

  // referências
  itens.forEach((item, i) => {
    if (item?.trilha && !idsTrilha.has(item.trilha)) {
      erros.push(`roadmap.itens[${i}].trilha: "${item.trilha}" não existe em roadmap.trilhas`);
    }
  });
  (d.roadmap?.dependencias ?? []).forEach((dep, i) => {
    for (const ponta of ['de', 'para']) {
      if (dep?.[ponta] && !idsItem.has(dep[ponta])) {
        erros.push(`roadmap.dependencias[${i}].${ponta}: "${dep[ponta]}" não existe em roadmap.itens`);
      }
    }
    if (dep?.de && dep.de === dep.para) erros.push(`roadmap.dependencias[${i}]: item depende dele mesmo`);
  });

  // janela
  const j = d.roadmap?.janela;
  if (j?.inicio && j?.fim) {
    const a = dataReal(j.inicio);
    const b = dataReal(j.fim);
    if (a !== null && b !== null && b <= a) erros.push('roadmap.janela: fim precisa ser depois do início');
    if (a !== null && b !== null) {
      itens.forEach((item, i) => {
        const t = dataReal(item?.inicio);
        if (t !== null && (t < a || t > b)) {
          avisos.push(`roadmap.itens[${i}] "${item.id}": início fora da janela, a barra aparece cortada`);
        }
      });
    }
  } else if (itens.length) {
    avisos.push('roadmap.janela ausente com itens no roadmap: o molde deriva a janela dos itens');
  }

  // lacunas apontando para seção que não existe
  (d.lacunas ?? []).forEach((l, i) => {
    if (l?.secao && !SECOES.includes(semAcento(l.secao))) {
      avisos.push(`lacunas[${i}].secao: "${l.secao}" não é uma seção conhecida (${SECOES.join(', ')}), a lacuna só aparece na lista geral`);
    }
  });

  // desconhecido sem lacuna
  const p = d.projeto ?? {};
  for (const campo of ['dono', 'prazo']) {
    if ((p[campo] === null || p[campo] === undefined || p[campo] === '') && !temLacuna(d, 'projeto', campo)) {
      avisos.push(`projeto.${campo} desconhecido sem lacuna: registre em lacunas[] com secao "projeto"`);
    }
  }
  // acento decidido pela área ou produto do nome: aviso, não erro (quem roda pode ter pedido outra cor)
  const esperado = acentoEsperado(p.nome, regras);
  if (esperado && typeof p.acento === 'string' && p.acento.toLowerCase() !== esperado[1].toLowerCase()) {
    avisos.push(`projeto.acento: ${p.acento} não bate com "${esperado[0]}" do nome (esperado ${esperado[1]}). Só mantenha se quem rodou pediu outra cor`);
  }
  for (const [campo, secao] of [['kpis', 'kpis'], ['capacidades', 'capacidades'], ['hipoteses', 'hipoteses'], ['fases', 'fases']]) {
    if (Array.isArray(d[campo]) && d[campo].length === 0 && !temLacuna(d, secao)) {
      avisos.push(`${campo} vazio sem lacuna: a prancha mostra o estado vazio, mas o motivo fica em branco`);
    }
  }
}

function temLacuna(d, secao, termo) {
  return (d.lacunas ?? []).some(
    (l) => semAcento(l?.secao) === secao && (!termo || semAcento(l?.o_que_falta).includes(termo))
  );
}

function duplicados(ids, onde, erros) {
  const vistos = new Set();
  for (const id of ids) {
    if (id === undefined || id === null) continue;
    if (vistos.has(id)) erros.push(`${onde}: id "${id}" repetido`);
    vistos.add(id);
  }
  return vistos;
}

const CAMPOS_DATA = new Set(['data', 'inicio', 'fim', 'prazo']);

function coletarDatas(no, onde = '', saida = []) {
  if (Array.isArray(no)) no.forEach((v, i) => coletarDatas(v, caminho(onde, i), saida));
  else if (no && typeof no === 'object') {
    for (const [k, v] of Object.entries(no)) {
      if (CAMPOS_DATA.has(k) && (typeof v === 'string' || v === null) && /^\d{4}-\d{2}-\d{2}$/.test(v ?? '')) {
        saida.push([caminho(onde, k), v]);
      } else if (k === 'feriados' && Array.isArray(v)) {
        v.forEach((f, i) => /^\d{4}-\d{2}-\d{2}$/.test(f ?? '') && saida.push([`${caminho(onde, k)}[${i}]`, f]));
      } else coletarDatas(v, caminho(onde, k), saida);
    }
  }
  return saida;
}

function coletarTextos(no, onde = '', saida = []) {
  if (typeof no === 'string') {
    if (!/^(https?:\/\/|#[0-9a-fA-F]{6}$)/.test(no)) saida.push([onde || '(raiz)', no]);
  } else if (Array.isArray(no)) no.forEach((v, i) => coletarTextos(v, caminho(onde, i), saida));
  else if (no && typeof no === 'object') {
    for (const [k, v] of Object.entries(no)) {
      if (k === 'url' || k === 'linear_url') continue;
      coletarTextos(v, caminho(onde, k), saida);
    }
  }
  return saida;
}

// ---- CLI ------------------------------------------------------------------

if (executadoDiretamente(import.meta.url)) {
  const { explicito, resto } = usoCamada(process.argv.slice(2));
  const arquivo = resto[0];
  if (!arquivo) {
    console.error('uso: node validar-projeto.mjs <projeto.json> [--camada <pasta>]');
    process.exit(2);
  }
  let dados;
  try {
    dados = JSON.parse(readFileSync(arquivo, 'utf8'));
  } catch (erro) {
    console.error(`${arquivo}: JSON ilegível. ${erro.message}`);
    process.exit(1);
  }
  let camada = null;
  try {
    camada = carregar(detectar(explicito, [arquivo]));
  } catch (erro) {
    console.error(erro.message);
    process.exit(1);
  }
  if (camada) console.log(`camada ${camada.dir}`);
  const { erros, avisos } = validar(dados, camada?.regras ?? null);
  for (const a of avisos) console.log(`aviso  ${a}`);
  for (const e of erros) console.log(`ERRO   ${e}`);
  console.log(erros.length ? `\ninválido: ${erros.length} erro(s), ${avisos.length} aviso(s)` : `\nválido: 0 erros, ${avisos.length} aviso(s)`);
  process.exit(erros.length ? 1 : 0);
}
