#!/usr/bin/env node
// Gera a descrição markdown de cada issue de um plano.json, no formato do contrato, para a
// sessão colar na criação da issue. Antes de gerar, valida o plano (schema, regras e camada):
// plano inválido não gera descrição.
//
//   node descricao-issue.mjs <plano.json> [--id <id_local>] [--json | --estrutura] [--camada <pasta>]
//
//   sem flag   um bloco por issue: "## <id_local>: <título>", a descrição e uma linha "---"
//   --id X     só a descrição da issue X, markdown puro (é o texto que vai no campo)
//   --json     lista com o que a criação precisa de cada issue: id_local, titulo, descricao,
//              milestone, pontos, estado, labels, responsavel (só o autorizado), data_limite
//   --estrutura  o que a etapa opcional cria antes das issues: o projeto (se for novo), as milestones
//              novas (nome, descricao, data só com marco) e o time. Projeto existente: nada a criar
//
// Exit 0: gerou. Exit 1: plano inválido (a lista de erros sai antes) ou --id inexistente.

import { readFileSync } from 'node:fs';
import { executadoDiretamente } from './lib/execucao.mjs';
import { detectar, carregar, usoCamada } from './lib/camada.mjs';
import { estruturaNova, gestorDe, montarDescricao } from './lib/plano.mjs';
import { validar } from './validar-plano.mjs';

/** O que a criação de uma issue recebe, a partir do item do plano e do gestor da camada. */
export function paraCriacao(issue, gestor) {
  return {
    id_local: issue.id_local,
    titulo: issue.titulo,
    descricao: montarDescricao(issue, gestor),
    milestone: issue.milestone ?? null,
    pontos: issue.pontos,
    estado: gestor.estado_inicial,
    labels: gestor.labels,
    responsavel: issue.responsavel_autorizado === true && issue.responsavel ? issue.responsavel : null,
    data_limite: issue.data_limite && issue.data_limite_fonte ? issue.data_limite : null,
  };
}

if (executadoDiretamente(import.meta.url)) {
  const argv = process.argv.slice(2);
  const { explicito, resto } = usoCamada(argv);
  const json = resto.includes('--json');
  const estrutura = resto.includes('--estrutura');
  const iId = resto.indexOf('--id');
  const id = iId >= 0 ? resto[iId + 1] : null;
  const arquivo = resto.find((a, i) => !a.startsWith('--') && resto[i - 1] !== '--id');
  if (!arquivo || (iId >= 0 && !id)) {
    console.error('uso: node descricao-issue.mjs <plano.json> [--id <id_local>] [--json | --estrutura] [--camada <pasta>]');
    process.exit(2);
  }
  let plano;
  try {
    plano = JSON.parse(readFileSync(arquivo, 'utf8'));
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
  const gestor = gestorDe(camada?.camada ?? null);
  const { erros } = validar(plano, { regras: camada?.regras ?? null, gestor });
  if (erros.length) {
    for (const e of erros) console.error(`ERRO   ${e}`);
    console.error(`\nplano inválido: ${erros.length} erro(s). Corrija com validar-plano.mjs antes de gerar a descrição`);
    process.exit(1);
  }
  if (estrutura) {
    console.log(JSON.stringify(estruturaNova(plano, gestor), null, 2));
    process.exit(0);
  }
  let issues = plano.issues;
  if (id) {
    issues = issues.filter((i) => i.id_local === id);
    if (!issues.length) {
      console.error(`--id ${id}: não existe em issues[]`);
      process.exit(1);
    }
  }
  if (json) console.log(JSON.stringify(issues.map((i) => paraCriacao(i, gestor)), null, 2));
  else if (id) console.log(montarDescricao(issues[0], gestor));
  else for (const i of issues) console.log(`## ${i.id_local}: ${i.titulo}\n\n${montarDescricao(i, gestor)}\n\n---\n`);
}
