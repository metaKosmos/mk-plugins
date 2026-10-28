// Carrega e valida a CAMADA: a pasta com o que é de uma empresa (marca, áreas e cores,
// fontes de dados, esqueleto do documento, tokens visuais). O motor não sabe nada disso:
// recebe por esta pasta.
//
// Contrato da pasta (todos os arquivos dentro dela):
//   camada.json     obrigatório   schema/camada.schema.json
//   tokens.json     opcional      schema/tokens.schema.json (o que faltar vem de tokens-padrao.json)
//   esqueleto.md    opcional      sem ele vale skills/documento-de-projeto/referencias/esqueleto-padrao.md
//   templates.json  opcional      schema/templates.schema.json (a lista de templates da empresa)
//
// Como a skill acha a pasta (primeira que existir):
//   1. caminho informado por quem chama (--camada <pasta>)
//   2. variável de ambiente VANTA_CAMADA
//   3. ./camada ao lado de onde o comando roda
//   4. camada/ ao lado do arquivo de entrada, ou na pasta acima dele

import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { validarSchema } from './schema.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
export const PLUGIN = resolve(AQUI, '..', '..');

// Prefixo que deixa URL, caminho, e-mail e #hash de fora de um padrão de marca.
// O mesmo texto vale em Python (gerar-doc.py), que compila com re.ASCII para o \w
// significar o mesmo nos dois.
export const ANTES = String.raw`(?<![\w/.:@#-])`;

export const expandir = (padrao) => String(padrao).replaceAll('{{ANTES}}', ANTES);

const DO_PREFIXO = /^(mcp__[A-Za-z0-9_-]+?__)/;

/** Prefixos MCP que a sessão enxerga, a partir de prefixos ou de nomes de ferramenta separados por vírgula. */
export function prefixosDaSessao(texto) {
  const s = new Set();
  for (const parte of String(texto ?? '').split(',')) {
    const m = DO_PREFIXO.exec(parte.trim());
    if (m) s.add(m[1]);
  }
  return s;
}

/**
 * O servidor a usar: o preferido; sem ele na sessão, o primeiro alternativo que exista. Nunca um de `proibidos`.
 * Devolve { via: 'servidor' | 'servidor_alternativo', prefixo } ou null.
 */
export function escolherServidor(preferido, alternativos, proibidos, naSessao) {
  const existe = (p) => typeof p === 'string' && p !== '' && !proibidos.includes(p) && naSessao.has(p);
  if (existe(preferido)) return { via: 'servidor', prefixo: preferido };
  const alt = (alternativos ?? []).find(existe);
  return alt ? { via: 'servidor_alternativo', prefixo: alt } : null;
}

export function ler(arquivo) {
  return JSON.parse(readFileSync(arquivo, 'utf8'));
}

export function esquema(nome) {
  return ler(join(PLUGIN, 'schema', nome));
}

function ehPasta(p) {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

/** Devolve a pasta da camada, ou null. `ancoras` são arquivos ou pastas perto da entrada. */
export function detectar(explicito, ancoras = []) {
  const candidatos = [];
  if (explicito) candidatos.push(resolve(explicito));
  else {
    if (process.env.VANTA_CAMADA) candidatos.push(resolve(process.env.VANTA_CAMADA));
    candidatos.push(resolve('camada'));
    for (const a of ancoras) {
      if (!a) continue;
      const base = ehPasta(a) ? resolve(a) : dirname(resolve(a));
      candidatos.push(join(base, 'camada'), join(base, '..', 'camada'));
    }
  }
  return candidatos.find((c) => existsSync(join(c, 'camada.json'))) ?? null;
}

function mesclar(base, extra) {
  if (extra === undefined) return base;
  if (base && typeof base === 'object' && !Array.isArray(base) && extra && typeof extra === 'object' && !Array.isArray(extra)) {
    const saida = { ...base };
    for (const [k, v] of Object.entries(extra)) saida[k] = mesclar(base[k], v);
    return saida;
  }
  return extra;
}

export function tokensPadrao() {
  return ler(join(PLUGIN, 'skills', 'visual-de-projeto', 'tokens-padrao.json'));
}

/** Tokens finais: o padrão do motor com o que a camada sobrescreve. */
export function tokensDe(dir) {
  const padrao = tokensPadrao();
  const arquivo = dir ? join(dir, 'tokens.json') : null;
  return arquivo && existsSync(arquivo) ? mesclar(padrao, ler(arquivo)) : padrao;
}

export function validarCamada(dir) {
  const erros = [];
  const avisos = [];
  const arq = join(dir, 'camada.json');
  let c;
  try {
    c = ler(arq);
  } catch (e) {
    return { erros: [`camada.json: ilegível. ${e.message}`], avisos, camada: null, tokens: null };
  }
  const sc = esquema('camada.schema.json');
  validarSchema(c, sc, sc, '', erros);

  const compilaveis = [
    ...(c.marca?.reprovar ?? []).map((r, i) => [`marca.reprovar[${i}]`, r]),
    ...(c.marca?.normalizar ?? []).map((r, i) => [`marca.normalizar[${i}]`, r]),
    ...(c.areas ?? []).map((r, i) => [`areas[${i}]`, r]),
  ];
  for (const [onde, r] of compilaveis) {
    if (typeof r?.padrao !== 'string') continue;
    try {
      new RegExp(expandir(r.padrao), r.ignorar_caixa ? 'i' : '');
    } catch (e) {
      erros.push(`${onde}.padrao: expressão regular inválida. ${e.message}`);
    }
    if (/\(\?<[A-Za-z]/.test(r.padrao) && !/\(\?<[!=]/.test(r.padrao)) {
      erros.push(`${onde}.padrao: grupo nomeado muda de sintaxe entre JavaScript e Python. Use grupo numerado`);
    }
  }
  (c.marca?.normalizar ?? []).forEach((r, i) => {
    if (r?.para && !(r.aceitar ?? []).includes(r.para)) {
      avisos.push(`marca.normalizar[${i}]: "para" ("${r.para}") não está em "aceitar": a troca seria reprovada na checagem seguinte`);
    }
  });

  // Servidor que a própria fonte proíbe não pode ser o preferido nem o alternativo: a camada se contradiz.
  for (const [nome, f] of Object.entries(c.fontes ?? {})) {
    const proibidos = Array.isArray(f?.proibido) ? f.proibido : [];
    for (const campo of ['servidor', 'servidor_alternativo']) {
      if (typeof f?.[campo] === 'string' && proibidos.includes(f[campo])) {
        erros.push(`fontes.${nome}.${campo}: "${f[campo]}" também está em fontes.${nome}.proibido. A camada se contradiz`);
      }
    }
  }

  const g = c.gestor;
  if (g && typeof g === 'object') {
    // Mesma regra do gestorDe: proibido próprio, senão o da fonte linear.
    const proibidosDoGestor = Array.isArray(g.proibido) && g.proibido.length ? g.proibido : (Array.isArray(c.fontes?.linear?.proibido) ? c.fontes.linear.proibido : []);
    for (const campo of ['servidor', 'servidor_alternativo']) {
      if (typeof g[campo] === 'string' && proibidosDoGestor.includes(g[campo])) {
        erros.push(`gestor.${campo}: "${g[campo]}" está em ${g.proibido?.length ? 'gestor.proibido' : 'fontes.linear.proibido'}, que vale para o gestor. A camada se contradiz`);
      }
    }
    const escada = Array.isArray(g.escada_pontos) ? g.escada_pontos : null;
    if (escada) {
      if (escada.length === 0) erros.push('gestor.escada_pontos: vazia');
      else if (escada.some((v, i) => i > 0 && v <= escada[i - 1])) erros.push('gestor.escada_pontos: precisa ser crescente, sem repetir');
    }
    if (g.teto_pontos !== undefined && escada && !escada.includes(g.teto_pontos)) {
      erros.push(`gestor.teto_pontos: ${g.teto_pontos} não está em gestor.escada_pontos (${escada.join(', ')})`);
    }
    if (Array.isArray(g.contrato_campos) && g.contrato_campos.length !== 11) {
      erros.push('gestor.contrato_campos: são onze rótulos (modo, fluxo, repos, pode mexer em, resultado, o que entrega, teste principal, portão, fora, se nunca for feita, contexto)');
    }
  }

  let tokens = null;
  const arqTok = join(dir, 'tokens.json');
  if (existsSync(arqTok)) {
    try {
      const t = ler(arqTok);
      const st = esquema('tokens.schema.json');
      validarSchema(t, st, st, 'tokens', erros);
    } catch (e) {
      erros.push(`tokens.json: ilegível. ${e.message}`);
    }
  }
  try {
    tokens = tokensDe(dir);
  } catch {
    /* já reportado */
  }
  const limiar = c.esbocos?.similaridade_minima;
  if (typeof limiar === 'number' && limiar > 1) erros.push('esbocos.similaridade_minima: o máximo é 1');
  conferirTemplates(dir, c, erros, avisos);
  if (!existsSync(join(dir, 'esqueleto.md'))) avisos.push('esqueleto.md ausente: vale o esqueleto padrão do motor');
  return { erros, avisos, camada: c, tokens };
}

export const ARQUIVO_TEMPLATES = 'templates.json';

/** Lê o templates.json da camada: { versao, templates[] }, ou null quando não existe. Lança se ilegível. */
export function lerTemplates(dir) {
  const arq = join(dir, ARQUIVO_TEMPLATES);
  return existsSync(arq) ? ler(arq) : null;
}

/** Confere o templates.json contra o contrato e contra o que o schema não alcança: nome único,
 *  skill que existe no motor, estado coerente com a skill e a mesma regra de escrita da camada. */
function conferirTemplates(dir, c, erros, avisos) {
  let t;
  try {
    t = lerTemplates(dir);
  } catch (e) {
    erros.push(`${ARQUIVO_TEMPLATES}: ilegível. ${e.message}`);
    return;
  }
  if (!t) return;
  const antes = erros.length;
  const st = esquema('templates.schema.json');
  validarSchema(t, st, st, 'templates', erros);
  if (erros.length > antes) return;
  let regras = null;
  try {
    regras = compilar(c);
  } catch {
    /* padrão inválido já foi reportado */
  }
  const vistos = new Set();
  t.templates.forEach((x, i) => {
    const onde = `templates.templates[${i}]`;
    const chave = x.nome.trim().toLowerCase();
    if (vistos.has(chave)) erros.push(`${onde}.nome: "${x.nome}" repetido. O nome é único`);
    vistos.add(chave);
    if (x.skill_do_motor !== null && !existsSync(join(PLUGIN, 'skills', x.skill_do_motor, 'SKILL.md'))) {
      erros.push(`${onde}.skill_do_motor: a skill "${x.skill_do_motor}" não existe no motor`);
    }
    if (x.estado === 'pronto' && x.skill_do_motor === null) {
      erros.push(`${onde}.estado: "pronto" pede skill_do_motor. Sem skill, o estado é "em esboço", "a trazer" ou "a construir"`);
    }
    if (x.estado !== 'pronto' && x.skill_do_motor !== null) {
      avisos.push(`${onde}: tem skill_do_motor mas o estado é "${x.estado}". Confira se não é "pronto"`);
    }
    for (const campo of ['nome', 'entrega']) {
      for (const p of problemasDeTexto(x[campo], regras)) erros.push(`${onde}.${campo}: ${p}`);
    }
  });
}

/** Carrega (ou devolve null quando não há pasta). Lança se a camada é inválida. */
export function carregar(dir) {
  if (!dir) return null;
  const { erros, camada, tokens } = validarCamada(dir);
  if (erros.length) throw new Error(`camada inválida em ${dir}:\n  ${erros.join('\n  ')}`);
  return { dir, camada, tokens, regras: compilar(camada) };
}

const bandeiras = (r) => (r.ignorar_caixa ? 'gi' : 'g');

/** Compila as expressões da camada uma vez. */
export function compilar(c) {
  const m = c.marca ?? {};
  return {
    travessaoProibido: !!c.escrita?.travessao_proibido,
    preservar: m.preservar_caixa ?? [],
    reprovar: (m.reprovar ?? []).map((r) => ({ re: new RegExp(expandir(r.padrao), bandeiras(r)), mensagem: r.mensagem })),
    normalizar: (m.normalizar ?? []).map((r) => ({ re: new RegExp(expandir(r.padrao), bandeiras(r)), para: r.para, aceitar: r.aceitar ?? [r.para] })),
    areas: (c.areas ?? []).map((a) => ({ nome: a.nome, cor: a.cor, re: new RegExp(expandir(a.padrao), a.ignorar_caixa === false ? '' : 'i'), vence: !!a.vence_no_prefixo })),
    acentoPadrao: c.acento_padrao ?? '#7C3AED',
  };
}

const URL_NO_TEXTO = /https?:\/\/[^\s)>\]|]+/g;

/** Problemas de grafia e de escrita de um texto. Lista vazia: limpo. URL no meio do texto
 *  nunca reprova (o gerar-doc.py faz o mesmo: tira a URL antes de conferir). */
export function problemasDeTexto(texto, regras) {
  const achados = [];
  if (!regras) return achados;
  texto = String(texto).replace(URL_NO_TEXTO, '');
  if (regras.travessaoProibido && /[\u2014\u2013]/.test(texto)) {
    achados.push('traço longo ou meia-risca. Use vírgula, dois-pontos ou ponto');
  }
  for (const r of regras.reprovar) {
    r.re.lastIndex = 0;
    if (r.re.test(texto)) achados.push(r.mensagem);
  }
  for (const r of regras.normalizar) {
    for (const achado of texto.match(r.re) ?? []) {
      if (!r.aceitar.includes(achado)) achados.push(`escrito "${achado}". A grafia é "${r.para}"`);
    }
  }
  return achados;
}

/** Cor de acento esperada para o nome de um projeto: [área, cor] ou null. */
export function acentoEsperado(nome, regras) {
  if (!regras) return null;
  const n = nome ?? '';
  const vencedora = regras.areas.find((a) => a.vence && a.re.test(n));
  if (vencedora) return [vencedora.nome, vencedora.cor];
  const achadas = regras.areas.filter((a) => !a.vence && a.re.test(n));
  return achadas.length === 1 ? [achadas[0].nome, achadas[0].cor] : null;
}

export function usoCamada(argv) {
  const i = argv.indexOf('--camada');
  if (i < 0) return { explicito: null, resto: argv };
  return { explicito: argv[i + 1] ?? null, resto: [...argv.slice(0, i), ...argv.slice(i + 2)] };
}
