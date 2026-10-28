// O registro de esboços: o que a skill esboco guarda para reconhecer, na vez seguinte, um
// formato que já foi usado. Um arquivo .jsonl (uma linha por esboço escolhido), FORA do cache do
// plugin, para sobreviver à atualização dele.
//
// Cada linha: { versao, data, empresa, pedido, leitor, direcao: {rotulo, nome, privilegia?, visual_dominante?},
//               estrutura[], visuais[], canvas }
// `visuais` é alinhado a `estrutura`: o elemento visual de cada bloco (fluxograma, grafico... ou "texto").
// Linha antiga, sem `visuais`, continua valendo e é comparada só pelos nomes dos blocos.
// "empresa" é a da camada: o registro pode ser um arquivo só, mas cada empresa só lê as próprias linhas.
//
// "Formato parecido" é uma conta sobre a ESTRUTURA (a lista ordenada de blocos) e sobre o elemento
// visual de cada bloco, não sobre o texto do pedido nem sobre a cor. Está descrita em `similaridade`.

import { appendFileSync, existsSync, mkdirSync, readFileSync, unlinkSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { lerTemplates, ARQUIVO_TEMPLATES, validarCamada, problemasDeTexto, compilar } from './camada.mjs';

export const REGISTRO_PADRAO = '~/.config/vanta-produto/esbocos.jsonl';
export const LIMIAR_PADRAO = 0.6;
export const MIN_BLOCOS = 3;
export const MIN_EM_COMUM = 3;
const LIMITE_BLOCO = 0.5;

/** Elementos visuais que um bloco pode ter. "texto" é o bloco sem elemento visual: apoio. */
export const VISUAIS = ['fluxograma', 'diagrama-de-blocos', 'linha-do-tempo', 'matriz', 'grafico', 'mapa-de-jornada', 'amostras-de-design'];
export const TEXTO = 'texto';
export const LEITORES = ['visual', 'textual'];
/** O peso do visual na pontuação: com todos os visuais diferentes a pontuação cai para esta fração. */
const PISO_VISUAL = 0.4;

/** Estrutura do esboco.json (itens "nome" ou {bloco, visual, fonte}) em listas alinhadas. */
export function dividirEstrutura(itens) {
  const blocos = [];
  const visuais = [];
  const fontes = [];
  for (const i of itens ?? []) {
    if (typeof i === 'string') {
      blocos.push(i);
      visuais.push(TEXTO);
      fontes.push(null);
    } else {
      blocos.push(i.bloco);
      visuais.push(i.visual ?? TEXTO);
      fontes.push(i.fonte ?? null);
    }
  }
  return { blocos, visuais, fontes };
}

const temVisual = (visuais) => (visuais ?? []).some((v) => v && v !== TEXTO);

/** Problemas dos elementos visuais de um esboco.json já aprovado pelo schema. Valem quando o leitor é
 *  visual (o padrão): cada direção e a final precisam de ao menos um bloco visual; cada direção declara
 *  um elemento visual dominante que aparece nos blocos dela; as direções diferem nele; gráfico leva fonte.
 *  Leitor "textual", declarado por quem pediu, dispensa tudo isto menos a fonte do gráfico. */
export function problemasVisuais(spec) {
  const p = [];
  const textual = spec.leitor === 'textual';
  const dominantes = new Map();
  const itens = [...spec.direcoes.map((d) => ({ nome: `direção ${d.rotulo}`, estrutura: d.estrutura, d })), ...(spec.final ? [{ nome: 'final', estrutura: spec.final.estrutura, d: null }] : [])];
  for (const { nome, estrutura, d } of itens) {
    const { blocos, visuais, fontes } = dividirEstrutura(estrutura);
    visuais.forEach((v, i) => {
      if (v === 'grafico' && !fontes[i]) p.push(`${nome}, bloco "${blocos[i]}": gráfico sem "fonte". Gráfico só com dado com fonte: ponha a fonte ou troque o visual`);
    });
    if (textual) continue;
    if (!temVisual(visuais)) {
      p.push(`${nome}: nenhum bloco visual. O leitor é visual (padrão): dê a cada bloco principal um elemento (${VISUAIS.join(', ')}) em "visual", ou declare "leitor": "textual" se quem pediu disse que o leitor é textual`);
      continue;
    }
    if (!d) continue;
    if (!d.visual_dominante) {
      p.push(`${nome}: falta "visual_dominante", o elemento visual que domina a direção`);
    } else if (!visuais.includes(d.visual_dominante)) {
      p.push(`${nome}: visual_dominante "${d.visual_dominante}" não aparece em nenhum bloco da direção`);
    } else if (dominantes.has(d.visual_dominante)) {
      p.push(`direções ${dominantes.get(d.visual_dominante)} e ${d.rotulo}: o mesmo elemento visual dominante (${d.visual_dominante}). Direções diferem no elemento visual dominante, não só na ordem dos blocos`);
    } else {
      dominantes.set(d.visual_dominante, d.rotulo);
    }
  }
  return p;
}

const PARADAS = new Set(['de', 'do', 'da', 'dos', 'das', 'e', 'o', 'a', 'os', 'as', 'um', 'uma', 'para', 'com', 'em', 'no', 'na', 'nos', 'nas', 'por', 'ao', 'aos']);

function radical(t) {
  if (t.length <= 3) return t;
  if (t.endsWith('oes')) return `${t.slice(0, -3)}ao`;
  if (t.endsWith('ns')) return `${t.slice(0, -2)}m`;
  return t.endsWith('s') ? t.slice(0, -1) : t;
}

/** Palavras de um nome de bloco: sem acento nem caixa, sem artigo e preposição, no singular. */
export function palavrasDoBloco(texto) {
  return String(texto)
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .split(' ')
    .filter((p) => p && !PARADAS.has(p))
    .map(radical);
}

function jaccard(a, b) {
  const A = new Set(a);
  const B = new Set(b);
  if (!A.size && !B.size) return 0;
  let comum = 0;
  for (const x of A) if (B.has(x)) comum++;
  return comum / (A.size + B.size - comum);
}

function longestIncreasing(seq) {
  const fim = [];
  for (const x of seq) {
    let lo = 0;
    let hi = fim.length;
    while (lo < hi) {
      const m = (lo + hi) >> 1;
      if (fim[m] < x) lo = m + 1;
      else hi = m;
    }
    fim[lo] = x;
  }
  return fim.length;
}

/**
 * Quanto duas estruturas se parecem, de 0 a 1.
 *
 *  1. Dois blocos casam quando as palavras deles (sem acento, caixa, artigo, plural) se parecem
 *     pelo menos 50% (Jaccard). Cada bloco casa com no máximo um do outro lado: pareia primeiro
 *     os mais parecidos.
 *  2. `conjunto` = casados / (blocos de A + blocos de B - casados): o Jaccard dos blocos.
 *  3. `ordem` = fração dos casados que aparece na mesma ordem relativa nos dois lados.
 *  4. pontuação = 0,7 x conjunto + 0,3 x ordem. Sem bloco casado, 0.
 *  5. Com os elementos visuais dos dois lados (`va`, `vb`, alinhados a `a` e `b`), `visual` = fração dos
 *     casados com o mesmo elemento visual, e a pontuação do passo 4 é multiplicada por
 *     0,4 + 0,6 x visual. Mesmos blocos com visuais todos diferentes caem a 40% e deixam de ser
 *     parecidos. Se um lado não tem visuais (linha antiga do registro), `visual` é null e nada muda.
 *
 * Contam como "formato parecido" duas estruturas com pontuação >= o limiar da camada (0,6 por
 * padrão) E pelo menos 3 blocos em comum: dois blocos iguais ("Capa", "Resumo") não fazem formato.
 */
export function similaridade(a, b, va = null, vb = null) {
  const pa = a.map(palavrasDoBloco);
  const pb = b.map(palavrasDoBloco);
  const pares = [];
  pa.forEach((x, i) =>
    pb.forEach((y, j) => {
      const igual = !x.length && !y.length && String(a[i]).trim().toLowerCase() === String(b[j]).trim().toLowerCase();
      const s = igual ? 1 : jaccard(x, y);
      if (s >= LIMITE_BLOCO) pares.push({ i, j, s });
    })
  );
  pares.sort((p, q) => q.s - p.s || p.i - q.i || p.j - q.j);
  const usadoA = new Set();
  const usadoB = new Set();
  const casados = [];
  for (const p of pares) {
    if (usadoA.has(p.i) || usadoB.has(p.j)) continue;
    usadoA.add(p.i);
    usadoB.add(p.j);
    casados.push(p);
  }
  const m = casados.length;
  if (!m) return { pontuacao: 0, em_comum: 0, conjunto: 0, ordem: 0, visual: null, blocos_em_comum: [] };
  const conjunto = m / (a.length + b.length - m);
  casados.sort((p, q) => p.i - q.i);
  const ordem = longestIncreasing(casados.map((p) => p.j)) / m;
  const arred = (x) => Math.round(x * 1000) / 1000;
  const comVisual = Array.isArray(va) && Array.isArray(vb) && va.length === a.length && vb.length === b.length;
  const visual = comVisual ? casados.filter((p) => (va[p.i] || TEXTO) === (vb[p.j] || TEXTO)).length / m : null;
  const base = 0.7 * conjunto + 0.3 * ordem;
  return {
    pontuacao: arred(visual === null ? base : base * (PISO_VISUAL + (1 - PISO_VISUAL) * visual)),
    em_comum: m,
    conjunto: arred(conjunto),
    ordem: arred(ordem),
    visual: visual === null ? null : arred(visual),
    blocos_em_comum: casados.map((p) => a[p.i])
  };
}

export const ehParecido = (sim, limiar = LIMIAR_PADRAO) => sim.em_comum >= MIN_EM_COMUM && sim.pontuacao >= limiar;

/** '~' vale a pasta do usuário. */
export function expandirCaminho(caminho) {
  if (caminho === '~') return homedir();
  if (caminho.startsWith('~/')) return join(homedir(), caminho.slice(2));
  return resolve(caminho);
}

/** Caminho do registro: o informado, o da camada (esbocos.registro) ou o padrão. */
export function caminhoDoRegistro(camada, explicito = null) {
  return expandirCaminho(explicito ?? camada?.esbocos?.registro ?? REGISTRO_PADRAO);
}

export const limiarDa = (camada) => camada?.esbocos?.similaridade_minima ?? LIMIAR_PADRAO;

/** Lê o registro. Linha ilegível ou fora de forma vira aviso e é pulada: um registro com uma linha
 *  ruim não pode travar o esboço. Arquivo ausente é registro vazio. */
export function lerRegistro(arquivo) {
  const entradas = [];
  const avisos = [];
  if (!existsSync(arquivo)) return { entradas, avisos };
  readFileSync(arquivo, 'utf8')
    .split('\n')
    .forEach((linha, n) => {
      if (!linha.trim()) return;
      try {
        const e = JSON.parse(linha);
        if (!e || typeof e !== 'object' || !Array.isArray(e.estrutura) || typeof e.pedido !== 'string' || typeof e.data !== 'string') {
          throw new Error('faltam data, pedido ou estrutura');
        }
        entradas.push(e);
      } catch (erro) {
        avisos.push(`linha ${n + 1} ignorada: ${erro.message}`);
      }
    });
  return { entradas, avisos };
}

const DATA = /^\d{4}-\d{2}-\d{2}$/;

export function hojeLocal(agora = new Date()) {
  const z = (n) => String(n).padStart(2, '0');
  return `${agora.getFullYear()}-${z(agora.getMonth() + 1)}-${z(agora.getDate())}`;
}

/** Problemas de um registro a gravar. Lista vazia: pode gravar. */
export function problemasDoRegistro(e, regras) {
  const p = [];
  if (!DATA.test(e.data ?? '')) p.push('data: use AAAA-MM-DD');
  if (!e.empresa) p.push('empresa: vazia');
  if (!e.pedido?.trim()) p.push('pedido: vazio');
  if (!e.direcao?.rotulo || !e.direcao?.nome) p.push('direcao: faltam rotulo e nome');
  if (!Array.isArray(e.estrutura) || e.estrutura.length < MIN_BLOCOS || e.estrutura.some((b) => typeof b !== 'string' || !b.trim())) {
    p.push(`estrutura: no mínimo ${MIN_BLOCOS} blocos com nome. Abaixo disso é item, não formato`);
  }
  if (!LEITORES.includes(e.leitor)) p.push(`leitor: ${LEITORES.join(' ou ')}`);
  if (e.visuais !== undefined && e.visuais !== null) {
    if (!Array.isArray(e.visuais) || e.visuais.length !== (e.estrutura ?? []).length) {
      p.push('visuais: um por bloco, na ordem da estrutura');
    } else {
      for (const v of e.visuais) if (v !== TEXTO && !VISUAIS.includes(v)) p.push(`visuais: "${v}" fora do permitido (${[...VISUAIS, TEXTO].join(' | ')})`);
    }
  }
  if (e.direcao?.visual_dominante && !VISUAIS.includes(e.direcao.visual_dominante)) p.push(`visual_dominante: "${e.direcao.visual_dominante}" fora do permitido (${VISUAIS.join(' | ')})`);
  if (e.leitor !== 'textual' && !temVisual(e.visuais)) {
    p.push(`visuais: nenhum bloco visual. O leitor é visual (padrão): informe o elemento de cada bloco (${VISUAIS.join(', ')}), ou use leitor textual se quem pediu declarou`);
  }
  const textos = [e.pedido, e.direcao?.nome, e.direcao?.privilegia, ...(Array.isArray(e.estrutura) ? e.estrutura : [])].filter((x) => typeof x === 'string');
  for (const t of textos) for (const m of problemasDeTexto(t, regras)) p.push(`"${t.slice(0, 40)}": ${m}`);
  return [...new Set(p)];
}

/** O que o registro e os templates da camada dizem sobre estas estruturas. `rascunhos` é uma lista de
 *  estruturas (as direções que a skill pensa em propor, ou a estrutura final): cada uma é a lista de
 *  blocos ou `{estrutura, visuais}`, com o elemento visual de cada bloco. */
export function consultar({ camada, dirCamada, arquivo, rascunhos: brutos }) {
  const rascunhos = brutos.map((r) => (Array.isArray(r) ? { estrutura: r, visuais: null } : r));
  const empresa = camada.empresa.nome;
  const limiar = limiarDa(camada);
  const { entradas, avisos } = lerRegistro(arquivo);
  const proprias = entradas.filter((e) => e.empresa === empresa);
  const parecidos = [];
  for (const e of proprias) {
    const melhor = rascunhos.map((r) => similaridade(r.estrutura, e.estrutura, r.visuais, e.visuais ?? null)).sort((x, y) => y.pontuacao - x.pontuacao)[0];
    if (melhor && ehParecido(melhor, limiar)) {
      parecidos.push({
        data: e.data,
        pedido: e.pedido,
        direcao: e.direcao,
        estrutura: e.estrutura,
        visuais: e.visuais ?? null,
        canvas: e.canvas ?? null,
        pontuacao: melhor.pontuacao,
        visual: melhor.visual,
        blocos_em_comum: melhor.blocos_em_comum
      });
    }
  }
  parecidos.sort((x, y) => y.pontuacao - x.pontuacao || y.data.localeCompare(x.data));

  let template = null;
  const tpls = dirCamada ? lerTemplates(dirCamada)?.templates ?? [] : [];
  for (const t of tpls) {
    if (!t.estrutura?.length) continue;
    const melhor = rascunhos.map((r) => similaridade(r.estrutura, t.estrutura)).sort((x, y) => y.pontuacao - x.pontuacao)[0];
    if (melhor && ehParecido(melhor, limiar) && (!template || melhor.pontuacao > template.pontuacao)) {
      template = { nome: t.nome, estado: t.estado, estrutura: t.estrutura, pontuacao: melhor.pontuacao };
    }
  }
  const segunda = parecidos.length >= 1;
  return {
    registro: arquivo,
    empresa,
    limiar,
    entradas_lidas: entradas.length,
    entradas_da_empresa: proprias.length,
    avisos,
    parecidos,
    template,
    ocorrencias_anteriores: parecidos.length,
    segunda_ocorrencia: segunda,
    propor_template: segunda && !template
  };
}

/** Grava um esboço escolhido. Devolve a entrada e o que o registro diz dela ANTES de gravar:
 *  quantas vezes o formato já tinha aparecido e se é hora de propor template. */
export function registrar({ camada, dirCamada, arquivo, entrada }) {
  const regras = compilar(camada);
  const e = {
    versao: 1,
    data: entrada.data ?? hojeLocal(),
    empresa: camada.empresa.nome,
    pedido: entrada.pedido,
    leitor: entrada.leitor ?? 'visual',
    direcao: entrada.direcao,
    estrutura: entrada.estrutura,
    ...(entrada.visuais ? { visuais: entrada.visuais } : {}),
    canvas: entrada.canvas ?? null
  };
  const problemas = problemasDoRegistro(e, regras);
  if (problemas.length) return { erros: problemas };
  const antes = consultar({ camada, dirCamada, arquivo, rascunhos: [{ estrutura: e.estrutura, visuais: e.visuais ?? null }] });
  mkdirSync(dirname(arquivo), { recursive: true });
  appendFileSync(arquivo, `${JSON.stringify(e)}\n`);
  return { entrada: e, antes };
}

/** Lista a estrutura como template "em esboço" em templates.json (criando o arquivo se não houver).
 *  Valida a camada depois e desfaz se ficou inválida. */
export function promover({ dirCamada, nome, entrega, estrutura, etapa = null }) {
  if (!nome?.trim() || !entrega?.trim()) return { erros: ['promover pede nome e entrega'] };
  if (!Array.isArray(estrutura) || estrutura.length < MIN_BLOCOS) return { erros: [`estrutura: no mínimo ${MIN_BLOCOS} blocos`] };
  const arq = join(dirCamada, ARQUIVO_TEMPLATES);
  const existia = existsSync(arq);
  const original = existia ? readFileSync(arq, 'utf8') : null;
  const t = existia ? JSON.parse(original) : { versao: 1, templates: [] };
  if (t.templates.some((x) => x.nome.trim().toLowerCase() === nome.trim().toLowerCase())) {
    return { erros: [`já existe um template chamado "${nome}"`] };
  }
  const novo = { nome, entrega, skill_do_motor: null, etapa, estado: 'em esboço', estrutura };
  t.templates.push(novo);
  writeFileSync(arq, `${JSON.stringify(t, null, 2)}\n`);
  const { erros } = validarCamada(dirCamada);
  if (erros.length) {
    if (existia) writeFileSync(arq, original);
    else unlinkSync(arq);
    return { erros };
  }
  return { template: novo, arquivo: arq };
}
