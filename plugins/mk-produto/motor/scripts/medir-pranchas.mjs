#!/usr/bin/env node
// Estima a altura de cada prancha do canvas a partir do projeto.json e monta o
// plano de quebra. O teto de uma prancha é 8000 px e o canvas corta sem aviso:
// por isso a medida sai antes de publicar.
//
//   node medir-pranchas.mjs <projeto.json> [--camada <pasta>]          tabela legível
//   node medir-pranchas.mjs <projeto.json> [--camada <pasta>] --json   plano em JSON
//
// A largura do título depende da fonte: tokens.medidas.titulo_largura_char (da camada, ou o
// padrão neutro de skills/visual-de-projeto/tokens-padrao.json). Fonte condensada de exibição
// (muito estreita) fica perto de 0,46; fonte de sistema em negrito, perto de 0,58. Fonte de título
// larga estima mais linhas e mais altura: errar para cima só deixa branco no fim da prancha.
//
// Exit 0: todas as pranchas cabem. Exit 1: alguma unidade indivisível passa do
// teto (a lista diz qual). Avisos de janela e de trilhas não mudam o exit.
//
// A estimativa é conservadora (sobra de ~8%): sobrar branco no fim da prancha é
// aceitável, cortar conteúdo não é. As constantes foram calibradas contra a
// renderização real dos moldes com título condensado (19/10/2026): nos dois exemplos e
// num projeto de estresse (14 trilhas, 40 hipóteses, 12 grupos), a estimativa ficou de 7%
// a 18% acima da altura real, nunca abaixo. Com outra fonte de título, a calibração vale
// pelo `titulo_largura_char` do token: confira por captura na primeira publicação e ajuste.
// Ao mexer num molde, meça de novo.

import { readFileSync } from 'node:fs';
import { executadoDiretamente } from './lib/execucao.mjs';
import { detectar, carregar, tokensPadrao, usoCamada } from './lib/camada.mjs';

export const TETO = 8000;
export const LARGURA = 1440;
const SOBRE = 1.08; // margem sobre a estimativa
const ALVO = 7400; // teto de trabalho antes da sobra: 7400 x 1,08 = 7992, abaixo dos 8000
const TRILHAS_POR_PRANCHA = 12;
const SEMANAS_6_MESES = 26;

// ---- texto ----------------------------------------------------------------

function linhas(texto, tamanho, largura, negrito = false, largura_char = 0.5) {
  const t = String(texto ?? '').trim();
  if (!t) return 0;
  const cw = tamanho * (negrito ? largura_char + 0.06 : largura_char);
  const cpl = Math.max(4, Math.floor((largura / cw) * 0.92));
  return Math.max(1, Math.ceil(t.length / cpl));
}
let LARGURA_TITULO = 0.46;
const anton = (texto, tamanho, largura) => linhas(texto, tamanho, largura, false, LARGURA_TITULO);
const tem = (v) => v !== null && v !== undefined && String(v).trim() !== '';

// ---- Conceito -------------------------------------------------------------

function secoesConceito(d) {
  const p = d.projeto ?? {};
  const kpis = d.kpis ?? [];
  const fontes = d.fontes_dados ?? [];
  const fases = d.fases ?? [];
  const lacunas = d.lacunas ?? [];

  // 0: hero. Filhos com gap 24: rótulo, nome, rótulo statement, statement, descrição, meta, kpis
  const nomeLin = linhas(p.nome, 96, 1312 - 88, true, 0.52);
  const stLin = tem(p.statement) ? anton(p.statement, 80, 1200) : 0;
  const stH = tem(p.statement) ? stLin * 76 : 76;
  const descLin = tem(p.descricao) ? linhas(p.descricao, 24, 1100) : 1;
  let kpiH;
  if (kpis.length) {
    const maxRot = Math.max(...kpis.map((k) => linhas(k.rotulo, 15, 264)));
    const card = 48 + 56 + 8 + maxRot * 21 + 8 + 17;
    const rows = Math.ceil(kpis.length / 4);
    kpiH = rows * card + (rows - 1) * 16;
  } else kpiH = 110;
  const hero = 15 + nomeLin * 96 + 15 + stH + descLin * 32.4 + 56 + kpiH + 24 * 6 + 40 + 32 + 64 + 1;

  // 1: fontes
  const cab = 11 + 8 + 59 + 24;
  let fontesH;
  if (fontes.length) {
    const cols = 3;
    const wDesc = (1312 - 32) / cols - 42;
    const rows = [];
    for (let i = 0; i < fontes.length; i += cols) {
      const mx = Math.max(...fontes.slice(i, i + cols).map((f) => Math.max(1, linhas(f.descricao || 'Descrição a definir.', 14, wDesc))));
      rows.push(42 + 19 + 8 + mx * 20.3);
    }
    fontesH = cab + rows.reduce((a, b) => a + b, 0) + (rows.length - 1) * 16;
  } else fontesH = cab + 100;

  // 2: fases
  let fasesH;
  if (fases.length) {
    const cols = Math.min(5, fases.length);
    const w = (1312 - 16 * (cols - 1)) / cols - 42;
    const rows = [];
    for (let i = 0; i < fases.length; i += 5) {
      const ch = fases.slice(i, i + 5);
      const mx = Math.max(
        ...ch.map((f) => {
          const nome = anton(f.nome, 32, w) * 32;
          const desc = Math.max(1, linhas(f.descricao || 'Descrição a definir.', 14, w)) * 20.3;
          const gate = Math.max(1, linhas(f.gate || 'portão a definir', 12, w - 20, true)) * 15.6;
          return 42 + 40 + 10 + nome + 10 + desc + 10 + 13 + gate;
        })
      );
      rows.push(mx);
    }
    fasesH = cab + rows.reduce((a, b) => a + b, 0) + (rows.length - 1) * 16;
  } else fasesH = cab + 100;

  // 3: lacunas. cabeçalho com texto à direita pode quebrar
  const cabLac = 11 + 8 + 59 + 24;
  let lacH;
  if (lacunas.length) {
    const rows = lacunas.map((l) => 41 + Math.max(linhas(l.o_que_falta, 16, 700, true) * 22.4, linhas('Depende de: ' + (l.depende_de || 'a definir'), 13, 300) * 18.2));
    lacH = cabLac + rows.reduce((a, b) => a + b, 0) + 2;
  } else lacH = cabLac + 100;

  // 4: próximas pranchas
  const proxH = 13 + 24 + 64 + 40 + 16 + 2 * 24 + 16 + 17;

  return [
    { nome: 'hero, KPIs', h: hero },
    { nome: 'fontes de dados', h: fontesH },
    { nome: 'fases e portões', h: fasesH },
    { nome: 'lacunas', h: lacH },
    { nome: 'próximas pranchas', h: proxH }
  ];
}

const TOPO = 14;
function rodape(d) {
  const f = d.ref?.fontes ?? [];
  // largura em px: texto de cada fonte mais o gap de 16 px entre elas e o rótulo "Fontes:"
  const larg = f.reduce((s, x) => s + String(x.rotulo || x.url || '').length * 6.2 + 16, 0) + 60;
  const l1 = Math.max(1, Math.ceil(larg / 1312));
  return 17 + l1 * 18 + 8 + 18;
}

function planoConceito(d) {
  const secs = secoesConceito(d);
  const fixo = 128 + TOPO + rodape(d);
  return partir(secs, fixo, 100, 'Conceito');
}

// ---- Capacidades ----------------------------------------------------------

function planoCapacidades(d) {
  const cap = d.capacidades ?? [];
  const cabecalho = 13 + 8 + 91 + 90; // título 96px e legenda quebrada para baixo
  const fixo = 128 + TOPO + rodape(d) + cabecalho;
  if (!cap.length) return { partes: [{ de: 0, ate: 999, h: Math.round((fixo + 3 * 100 + 180 + 200) * SOBRE) }], avisos: [] };

  const wItem = (1312 - 32) / 3 - 64 - 10 - 90; // largura do texto, descontando a etiqueta de estado
  const alturaGrupo = (g) => {
    const itens = g.itens ?? [];
    const linhasItens = itens.reduce((s, c) => s + linhas(c.nome, 14, wItem, true) * 19 + (tem(c.descricao) ? linhas(c.descricao, 12, wItem) * 16.8 : 0), 0);
    const nomeL = anton(g.grupo, 40, (1312 - 32) / 3 - 64 - 60) * 40;
    return 64 + Math.max(48, nomeL) + 16 + 8 + 8 + 14 + 16 + 1 + 16 + linhasItens + Math.max(0, itens.length - 1) * 12 + (itens.length ? 0 : 20);
  };
  const alturas = cap.map(alturaGrupo);
  const linhasGrid = [];
  for (let i = 0; i < alturas.length; i += 3) linhasGrid.push({ h: Math.max(...alturas.slice(i, i + 3)), n: Math.min(3, alturas.length - i) });
  // O molde mostra a seção "Fora do go-live" sempre que há capacidade (com estado vazio quando
  // nenhuma está "depois" ou "fora"): medido em 19/10/2026, o canvas com tudo "no go-live" tinha
  // ~257 px a mais que a estimativa que só contava a seção com chips.
  const temFora = true;
  const fora = (() => {
    const chips = (e) => cap.flatMap((g) => (g.itens ?? []).filter((c) => c.estado === e).map((c) => (c.nome + ' · ' + g.grupo).length));
    const linhasChips = (arr) => Math.max(1, Math.ceil((arr.reduce((s, n) => s + n * 7.2 + 32, 0)) / (1312 / 2 - 64)));
    const a = linhasChips(chips('depois')), b = linhasChips(chips('fora'));
    const vazio = !chips('depois').length && !chips('fora').length; // só o texto "Nenhuma capacidade marcada" (~20 px)
    return 11 + 8 + 59 + 24 + 64 + 13 + 16 + (vazio ? 20 : Math.max(a, b) * 40 + Math.max(0, Math.max(a, b) - 1) * 8);
  })();

  const gap = 100, partes = [];
  let i = 0;
  while (i < linhasGrid.length) {
    let soma = 0, j = i;
    while (j < linhasGrid.length) {
      const add = linhasGrid[j].h + (j > i ? 16 : 0);
      const ultimoFora = j === linhasGrid.length - 1 && temFora ? fora + gap : 0;
      if (soma + add + ultimoFora + fixo + 3 * gap > ALVO && j > i) break;
      soma += add;
      j += 1;
    }
    const ultima = j >= linhasGrid.length;
    const h = fixo + 3 * gap + soma + (ultima && temFora ? gap + fora : 0);
    partes.push({ de: i * 3, ate: ultima ? 999 : j * 3, h: Math.round(h * SOBRE) });
    i = j;
  }
  return { partes, avisos: [] };
}

// ---- Hipóteses ------------------------------------------------------------

function planoHipoteses(d) {
  const hip = d.hipoteses ?? [];
  const lac = (d.lacunas ?? []).filter((l) => semAcento(l.secao) === 'hipoteses');
  const cabecalho = 13 + 8 + 91 + 90;
  const fixo = 128 + TOPO + rodape(d) + cabecalho;
  if (!hip.length) return { partes: [{ de: 0, ate: 999, h: Math.round((fixo + 3 * 100 + 100 + 200) * SOBRE) }], avisos: [] };

  const larg = 1312 - 64 - 72 - 5 * 24;
  const fr = 1.7 + 1.1 + 1.1 + 1.0;
  const u = (larg - 190) / fr;
  const alturaLinha = (h) => {
    const a = linhas(h.hipotese, 16, u * 1.7, true) * 22.4;
    const b = linhas(h.metrica || 'a definir', 14, u * 1.1) * 20.3;
    const c = linhas(h.resultado_esperado || 'a definir', 14, u * 1.1) * 20.3;
    const e = linhas(h.ferramenta || 'a definir', 14, u * 1.0) * 20.3;
    const f = 24 + 8 + linhas(h.fonte || 'Fonte a definir', 12, 190) * 16.8;
    return 48 + 1 + Math.max(a, b, c, e, f, 28);
  };
  const alturas = hip.map(alturaLinha);
  const tab = 49 + 2; // cabeçalho da tabela e bordas
  const lacH = lac.length ? 11 + 16 + lac.reduce((s, l) => s + 41 + Math.max(linhas(l.o_que_falta, 16, 800, true) * 22.4, 18), 0) + 2 : 0;
  const gap = 100, partes = [];
  let i = 0;
  while (i < alturas.length) {
    let soma = 0, j = i;
    while (j < alturas.length) {
      const ultima = j === alturas.length - 1;
      const extra = ultima && lacH ? lacH + gap : 0;
      if (fixo + 3 * gap + tab + soma + alturas[j] + extra > ALVO && j > i) break;
      soma += alturas[j];
      j += 1;
    }
    const ultima = j >= alturas.length;
    partes.push({ de: i, ate: ultima ? 999 : j, h: Math.round((fixo + 3 * gap + tab + soma + (ultima && lacH ? lacH + gap : 0)) * SOBRE) });
    i = j;
  }
  return { partes, avisos: [] };
}

// ---- Roadmap --------------------------------------------------------------

function planoRoadmap(d) {
  const r = d.roadmap ?? {};
  const itens = r.itens ?? [];
  const trilhas = r.trilhas ?? [];
  const avisos = [];
  const j = r.janela;
  if (j?.inicio && j?.fim) {
    const semanas = Math.ceil((Date.parse(j.fim) - Date.parse(j.inicio)) / 86400000 / 7);
    if (semanas > SEMANAS_6_MESES) {
      avisos.push(`roadmap: janela de ${semanas} semanas, acima de 6 meses. O Gantt fica denso (rótulo a cada ${semanas > 26 ? 4 : 2} semanas). Divida em dois projeto.json por período, cada um com janela de até 26 semanas`);
    }
  }
  const fixo = 128 + TOPO + rodape(d) + 112;
  if (!itens.length) {
    // Estado vazio: 5 blocos empilhados com gap de 100 (topo, cabeçalho, cartão "Sem etapas",
    // grade de marcos quando há marcos, rodapé), logo 4 gaps com marcos e 3 sem. Medido no
    // canvas real (19/10/2026): ~1108 px com 2 marcos e 10 fontes; a versão antiga estimava 1008.
    const lac = (d.lacunas ?? []).filter((l) => semAcento(l.secao) === 'roadmap');
    const msg = 'O projeto ainda não registra etapas com início e fim.' + ((r.marcos ?? []).length ? ' Os marcos com data aparecem abaixo.' : '')
      + (lac.length ? ' Lacuna: ' + lac.map((l) => String(l.o_que_falta ?? '') + (tem(l.depende_de) ? ` (depende de ${l.depende_de})` : '')).join(' · ') + '.' : ' Nenhuma lacuna registrada para esta seção: confirme se ela não se aplica.');
    const cartao = 2 + 96 + 13 + 12 + linhas(msg, 20, 1000) * 29;
    const nMarcos = (r.marcos ?? []).filter((m) => m?.data).length;
    const grade = nMarcos ? 2 + 64 + 13 + 16 + nMarcos * 27 + (nMarcos - 1) * 16 : 0;
    const h = 128 + TOPO + rodape(d) + 112 + cartao + grade + (nMarcos ? 4 : 3) * 100;
    return { partes: [{ de: 0, ate: 999, h: Math.round(h * SOBRE) }], avisos };
  }

  // Gantt: legenda + instrução + caixa + nota
  const gantt0 = 18 + 16 + 36 + 16 + 65 + 2 + 16 + 36;
  const porTrilha = trilhas.map((t) => ({ id: t.id, nome: t.nome, n: itens.filter((i) => i.trilha === t.id).length }));
  const alturaTrilha = (t) => 48 + t.n * 88;

  const marcos = (r.marcos ?? []).length, entregas = itens.reduce((s, i) => s + (i.entregas ?? []).length, 0), deps = (r.dependencias ?? []).length;
  const rod = 64 + 13 + 16 + Math.max(
    marcos * 27 + Math.max(0, marcos - 1) * 16 + (marcos ? 0 : 20),
    entregas * 41 + Math.max(0, entregas - 1) * 16 + (entregas ? 0 : 20),
    deps * 40 + Math.max(0, deps - 1) * 16 + (deps ? 0 : 20)
  );

  const gap = 100, partes = [];
  let i = 0;
  while (i < porTrilha.length) {
    let soma = 0, j2 = i;
    while (j2 < porTrilha.length) {
      const ultima = j2 === porTrilha.length - 1;
      const extra = ultima ? gap + rod : 0;
      const total = fixo + 3 * gap + gantt0 + soma + alturaTrilha(porTrilha[j2]) + extra;
      if ((total > ALVO || j2 - i >= TRILHAS_POR_PRANCHA) && j2 > i) break;
      soma += alturaTrilha(porTrilha[j2]);
      j2 += 1;
    }
    const ultima = j2 >= porTrilha.length;
    const h = fixo + 3 * gap + gantt0 + soma + (ultima ? gap + rod : 0);
    partes.push({
      de: i, ate: ultima ? 999 : j2, h: Math.round(h * SOBRE),
      trilhas: porTrilha.slice(i, j2).map((t) => t.nome)
    });
    i = j2;
  }
  if (trilhas.length > TRILHAS_POR_PRANCHA) {
    avisos.push(`roadmap: ${trilhas.length} trilhas, acima de ${TRILHAS_POR_PRANCHA}. O plano divide em ${partes.length} pranchas "Roadmap: <trilhas>", sem partir nenhuma trilha`);
  }
  return { partes, avisos };
}

// ---- quebra genérica ------------------------------------------------------

function partir(secs, fixo, gap, rotulo) {
  const partes = [];
  const avisos = [];
  let i = 0;
  while (i < secs.length) {
    let soma = 0, j = i;
    while (j < secs.length) {
      const add = secs[j].h + (j > i ? gap : 0);
      if (fixo + 2 * gap + soma + add > ALVO && j > i) break;
      soma += add;
      j += 1;
    }
    const h = fixo + 2 * gap + soma;
    partes.push({ de: i, ate: j >= secs.length ? 5 : j, h: Math.round(h * SOBRE), secoes: secs.slice(i, j).map((s) => s.nome) });
    if (h * SOBRE > TETO) avisos.push(`${rotulo}: a seção "${secs[i].nome}" sozinha passa de ${TETO} px`);
    i = j;
  }
  return { partes, avisos };
}

function semAcento(texto) {
  return String(texto ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z_]/g, '');
}

// ---- plano ----------------------------------------------------------------

const MOLDES = [
  { molde: 'Conceito', publicado: 'Main', titulo: 'Conceito', plano: planoConceito, prop: ['secaoDe', 'secaoAte'], interativa: false },
  { molde: 'Capacidades', publicado: 'Capacidades', titulo: 'Capacidades', plano: planoCapacidades, prop: ['grupoDe', 'grupoAte'], interativa: false },
  { molde: 'Roadmap', publicado: 'Roadmap', titulo: 'Roadmap', plano: planoRoadmap, prop: ['trilhaDe', 'trilhaAte'], interativa: true },
  { molde: 'Hipoteses', publicado: 'Hipoteses', titulo: 'Hipóteses', plano: planoHipoteses, prop: ['linhaDe', 'linhaAte'], interativa: false }
];

export function planejar(d, medidas = {}) {
  LARGURA_TITULO = medidas.titulo_largura_char ?? LARGURA_TITULO;
  const pranchas = [];
  const avisos = [];
  for (const m of MOLDES) {
    const { partes, avisos: av } = m.plano(d);
    avisos.push(...av);
    partes.forEach((p, k) => {
      const dividida = partes.length > 1;
      const sufixo = k === 0 ? '' : String(k + 1);
      let titulo = m.titulo;
      if (dividida) {
        if (m.molde === 'Roadmap' && p.trilhas) titulo = p.trilhas.length <= 3 ? `Roadmap: ${p.trilhas.join(', ')}` : `Roadmap: ${p.trilhas[0]} a ${p.trilhas[p.trilhas.length - 1]}`;
        else titulo = `${m.titulo} ${k + 1}`;
      }
      const prancha = {
        molde: m.molde,
        arquivo: `${m.publicado}${sufixo}.dc.html`,
        titulo,
        w: LARGURA,
        h: Math.min(TETO, Math.max(200, p.h)),
        hEstimada: p.h,
        interativa: m.interativa,
        props: dividida ? { [m.prop[0]]: p.de, [m.prop[1]]: p.ate } : null
      };
      if (p.h > TETO) {
        avisos.push(`${prancha.arquivo}: estimativa de ${p.h} px, acima do teto de ${TETO} px. Alguma unidade indivisível é grande demais`);
        prancha.acimaDoTeto = true;
      }
      pranchas.push(prancha);
    });
  }
  return { teto: TETO, pranchas, avisos, acimaDoTeto: pranchas.some((p) => p.acimaDoTeto) };
}

// ---- CLI ------------------------------------------------------------------

if (executadoDiretamente(import.meta.url)) {
  const { explicito, resto } = usoCamada(process.argv.slice(2));
  const arquivo = resto.find((x) => !x.startsWith('--'));
  if (!arquivo) {
    console.error('uso: node medir-pranchas.mjs <projeto.json> [--camada <pasta>] [--json]');
    process.exit(2);
  }
  const d = JSON.parse(readFileSync(arquivo, 'utf8'));
  const camada = carregar(detectar(explicito, [arquivo]));
  const tokens = camada?.tokens ?? tokensPadrao();
  const plano = planejar(d, tokens.medidas);
  if (resto.includes('--json')) console.log(JSON.stringify(plano, null, 2));
  else {
    console.log(`teto por prancha: ${TETO} px  (título: ${LARGURA_TITULO} de largura por caractere)\n`);
    for (const p of plano.pranchas) {
      const quebra = p.props ? `  quebra: ${Object.entries(p.props).map(([k, v]) => `${k}=${v}`).join(' ')}` : '';
      console.log(`${p.arquivo.padEnd(24)} ${String(p.hEstimada).padStart(5)} px  ${p.hEstimada <= TETO ? 'cabe' : 'PASSA'}  ${p.titulo}${quebra}`);
    }
    if (plano.avisos.length) console.log('');
    for (const a of plano.avisos) console.log(`aviso  ${a}`);
    console.log(`\n${plano.pranchas.length} prancha(s), ${plano.acimaDoTeto ? 'alguma passa do teto' : 'todas cabem'}`);
  }
  process.exit(plano.acimaDoTeto ? 1 : 0);
}
