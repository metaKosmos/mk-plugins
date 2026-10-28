#!/usr/bin/env node
// As fontes do levantamento que esta sessão alcança, e a escolha de fontes extras de quem roda.
//
//   node fontes-do-levantamento.mjs disponiveis --camada <pasta> --na-sessao <prefixos ou ferramentas>
//   node fontes-do-levantamento.mjs gestor     --camada <pasta> --na-sessao <prefixos ou ferramentas>
//   node fontes-do-levantamento.mjs ler         --camada <pasta>
//   node fontes-do-levantamento.mjs incluir     --camada <pasta> --nome <nome> --servidor <mcp__x__> [--como <texto>]
//   node fontes-do-levantamento.mjs remover     --camada <pasta> --nome <nome>
//   node fontes-do-levantamento.mjs caminho
//
// disponiveis  uma linha por fonte habilitada na camada, mais uma por fonte extra salva: disponível (com
//              o servidor que será usado) ou "não alcançável", que no dossiê é "não verificável daqui".
//              --na-sessao é a lista, separada por vírgula, dos servidores MCP que a sessão enxerga:
//              o prefixo (mcp__x__) ou o nome inteiro de uma ferramenta (mcp__x__get_team).
//              Vale `servidor`; sem ele na sessão, vale `servidor_alternativo`. Servidor de `proibido`
//              nunca é escolhido. O alternativo sai com o aviso de confirmar o workspace antes de ler.
// gestor       o servidor de ESCRITA da plano-no-linear: gestor.servidor, senão fontes.linear.servidor; sem ele
//              na sessão, gestor.servidor_alternativo, senão fontes.linear.servidor_alternativo. Nunca um de
//              `proibido`. O alternativo sai com o aviso de confirmar o workspace antes de qualquer escrita.
//              Exit 1 quando nenhum existe na sessão: "não verificável daqui", e nenhuma issue é criada.
// incluir      grava a fonte extra na máquina de quem roda (fora do plugin), para a empresa da camada.
//              Recusa o servidor que a camada proíbe e o que já é fonte padrão.
// caminho      onde a escolha fica: $VANTA_FONTES_ESCOLHIDAS, ou ~/.config/vanta-produto/fontes-escolhidas.json.
//
// Exit 0: ok. Exit 1: recusado, com o motivo. Exit 2: uso. Nada aqui instala nem autentica fonte.

import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join } from 'node:path';
import { detectar, escolherServidor, ler as lerJson, prefixosDaSessao } from './lib/camada.mjs';
import { gestorDe } from './lib/plano.mjs';

// O nome do servidor não leva "__": é o que separa o nome do resto e o que prefixosDaSessao reconhece.
const PREFIXO = /^mcp__(?:[A-Za-z0-9-]|_(?!_))+__$/;

const arquivoDasEscolhas = () =>
  process.env.VANTA_FONTES_ESCOLHIDAS || join(homedir(), '.config', 'vanta-produto', 'fontes-escolhidas.json');

function sair(codigo, texto) {
  (codigo === 2 ? console.error : console.log)(texto);
  process.exit(codigo);
}

function opcoes(args) {
  const o = {};
  for (let i = 0; i < args.length; i += 2) {
    if (!args[i].startsWith('--') || args[i + 1] === undefined) sair(2, `uso: opção sem valor em "${args[i]}"`);
    o[args[i].slice(2)] = args[i + 1];
  }
  return o;
}

function lerEscolhas() {
  const arq = arquivoDasEscolhas();
  if (!existsSync(arq)) return { versao: 1, empresas: {} };
  try {
    const j = JSON.parse(readFileSync(arq, 'utf8'));
    if (j?.versao !== 1 || typeof j.empresas !== 'object' || j.empresas === null) throw new Error('contrato inesperado (versao 1, empresas)');
    return j;
  } catch (e) {
    sair(1, `${arq}: ilegível, não vou sobrescrever. ${e.message}`);
  }
}

function camadaDe(o) {
  const dir = detectar(o.camada ?? null, []);
  if (!dir) sair(2, `camada não encontrada${o.camada ? ` em ${o.camada}` : ''}: informe --camada <pasta com camada.json>`);
  return lerJson(join(dir, 'camada.json'));
}

// O arquivo pode ter sido editado à mão: empresa sem `extras` (ou com outra coisa no lugar) vale lista vazia.
const extrasDe = (escolhas, camada) => {
  const x = escolhas.empresas[camada.empresa.nome]?.extras;
  return Array.isArray(x) ? x : [];
};

/** O servidor a usar numa fonte: o preferido, senão o alternativo. Nunca um de `proibido`. */
const escolherDaFonte = (fonte, naSessao) =>
  escolherServidor(fonte.servidor, [fonte.servidor_alternativo], Array.isArray(fonte.proibido) ? fonte.proibido : [], naSessao);

const NAO_VERIFICAVEL = 'não verificável daqui';

function disponiveis(o) {
  const camada = camadaDe(o);
  const naSessao = prefixosDaSessao(o['na-sessao']);
  const linhas = [];
  for (const [nome, f] of Object.entries(camada.fontes ?? {})) {
    if (!f?.habilitada) continue;
    const e = escolherDaFonte(f, naSessao);
    if (e?.via === 'servidor') linhas.push(`${nome}: disponível (servidor ${e.prefixo})`);
    else if (e) linhas.push(`${nome}: disponível pelo servidor alternativo ${e.prefixo}; confirme o workspace da empresa (get_workspace ou get_team) antes de ler, como a camada pede`);
    else if (f.cli) linhas.push(`${nome}: disponível pelo CLI ${f.cli}, não conferido aqui (confira a conta antes de ler)`);
    else if (f.servidor || f.servidor_alternativo) {
      const quais = [f.servidor, f.servidor_alternativo].filter(Boolean).join(' nem ');
      linhas.push(`${nome}: não alcançável nesta sessão (${quais} não aparece). ${NAO_VERIFICAVEL}`);
    } else linhas.push(`${nome}: sem servidor: depende da pasta ou do acesso que a camada descreve`);
  }
  for (const x of extrasDe(lerEscolhas(), camada)) {
    if (typeof x?.servidor !== 'string' || x.servidor === '') {
      linhas.push(`extra ${x?.nome ?? '(sem nome)'}: ignorada, sem servidor em ${arquivoDasEscolhas()} (formato mcp__<servidor>__): corrija o arquivo ou rode incluir de novo`);
      continue;
    }
    linhas.push(naSessao.has(x.servidor)
      ? `extra ${x.nome}: disponível (servidor ${x.servidor})`
      : `extra ${x.nome}: não alcançável nesta sessão (${x.servidor} não aparece). ${NAO_VERIFICAVEL}`);
  }
  console.log(linhas.join('\n'));
}

const CONFIRMAR = 'confirme o workspace da empresa (get_workspace ou get_team) antes de qualquer escrita e pare se não for o da camada';

/** O servidor de ESCRITA do gestor (plano-no-linear). Exit 1 quando a sessão não alcança nenhum. */
function gestor(o) {
  const camada = camadaDe(o);
  const g = gestorDe(camada);
  const e = escolherServidor(g.servidor, g.alternativos, g.proibido, prefixosDaSessao(o['na-sessao']));
  if (e?.via === 'servidor') sair(0, `gestor: disponível (servidor ${e.prefixo})`);
  if (e) sair(0, `gestor: disponível pelo servidor alternativo ${e.prefixo}; ${CONFIRMAR}`);
  const quais = [g.servidor, ...g.alternativos].filter(Boolean);
  if (!quais.length) sair(1, 'gestor: sem servidor na camada (gestor.servidor e fontes.linear.servidor nulos): peça a quem roda o prefixo; nenhuma issue é criada');
  sair(1, `gestor: não alcançável nesta sessão (${quais.join(' nem ')} não aparece). ${NAO_VERIFICAVEL}; nenhuma issue é criada`);
}

function proibidosDa(camada) {
  return new Set(Object.values(camada.fontes ?? {}).flatMap((f) => (Array.isArray(f?.proibido) ? f.proibido : [])));
}

function padraoDe(camada, servidor) {
  return Object.entries(camada.fontes ?? {}).find(([, f]) => f?.servidor === servidor || f?.servidor_alternativo === servidor)?.[0];
}

function incluir(o) {
  const camada = camadaDe(o);
  const nome = (o.nome ?? '').trim();
  if (!nome) sair(2, 'uso: --nome é obrigatório');
  if (!PREFIXO.test(o.servidor ?? '')) sair(1, `"${o.servidor ?? ''}" não é um prefixo de servidor MCP. Formato esperado: mcp__<servidor>__, e o nome do servidor não leva "__" no meio (por exemplo mcp__claude_ai_Fathom__)`);
  if (proibidosDa(camada).has(o.servidor)) sair(1, `a camada de ${camada.empresa.nome} proíbe o servidor ${o.servidor}`);
  const padrao = padraoDe(camada, o.servidor);
  if (padrao) sair(1, `${o.servidor} já é fonte padrão da camada (${padrao}): não precisa incluir`);
  const escolhas = lerEscolhas();
  const emp = (escolhas.empresas[camada.empresa.nome] ??= {});
  if (!Array.isArray(emp.extras)) emp.extras = [];
  const novo = { nome, servidor: o.servidor, como: o.como ?? null };
  const i = emp.extras.findIndex((x) => String(x?.nome ?? '').toLowerCase() === nome.toLowerCase());
  if (i >= 0) emp.extras[i] = novo;
  else emp.extras.push(novo);
  const arq = arquivoDasEscolhas();
  mkdirSync(dirname(arq), { recursive: true });
  writeFileSync(arq, JSON.stringify(escolhas, null, 2) + '\n');
  console.log(`fonte extra ${nome} (${o.servidor}) salva para ${camada.empresa.nome} em ${arq}`);
}

function remover(o) {
  const camada = camadaDe(o);
  const escolhas = lerEscolhas();
  const emp = escolhas.empresas[camada.empresa.nome];
  const lista = Array.isArray(emp?.extras) ? emp.extras : [];
  const alvo = (o.nome ?? '').trim().toLowerCase();
  const resto = lista.filter((x) => String(x?.nome ?? '').toLowerCase() !== alvo);
  if (resto.length === lista.length) sair(1, `fonte extra "${o.nome ?? ''}" não está salva para ${camada.empresa.nome}`);
  emp.extras = resto;
  writeFileSync(arquivoDasEscolhas(), JSON.stringify(escolhas, null, 2) + '\n');
  console.log(`fonte extra ${o.nome} removida de ${camada.empresa.nome}`);
}

const [comando, ...args] = process.argv.slice(2);
const o = opcoes(args);
if (comando === 'disponiveis') disponiveis(o);
else if (comando === 'ler') console.log(JSON.stringify(extrasDe(lerEscolhas(), camadaDe(o)), null, 2));
else if (comando === 'gestor') gestor(o);
else if (comando === 'incluir') incluir(o);
else if (comando === 'remover') remover(o);
else if (comando === 'caminho') console.log(arquivoDasEscolhas());
else sair(2, 'uso: node fontes-do-levantamento.mjs disponiveis|gestor|ler|incluir|remover|caminho --camada <pasta> ...');
