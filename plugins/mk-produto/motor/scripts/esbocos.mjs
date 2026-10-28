#!/usr/bin/env node
// O registro de esboços da skill esboco: consultar, registrar, promover e comparar.
//
//   node esbocos.mjs consultar --estrutura "Capa|Problema|Solução" [--visuais "texto|fluxograma|grafico"] [--estrutura "..." [--visuais "..."]] [--camada <pasta>] [--registro <arquivo>]
//   node esbocos.mjs registrar --pedido "..." --rotulo A --nome "..." --estrutura "a|b|c" --visuais "fluxograma|texto|grafico" [--privilegia "..."] [--visual-dominante fluxograma] [--leitor visual|textual] [--canvas <url>] [--data AAAA-MM-DD]
//   node esbocos.mjs promover  --nome "..." --entrega "..." --estrutura "a|b|c" [--etapa 3]
//   node esbocos.mjs comparar  --estrutura "a|b|c" [--visuais "..."] --estrutura "x|y|z" [--visuais "..."]      (não precisa de camada)
//
// A estrutura é a lista de blocos do material, separados por "|" (o nome de um bloco pode ter vírgula).
// `--visuais` é a lista do elemento visual de cada bloco, na mesma ordem e também separada por "|":
// fluxograma, diagrama-de-blocos, linha-do-tempo, matriz, grafico, mapa-de-jornada, amostras-de-design ou
// texto (bloco sem elemento visual). Com mais de uma --estrutura, o n-ésimo --visuais é o da n-ésima.
// O registrar recusa estrutura sem nenhum bloco visual, salvo --leitor textual (declarado por quem pediu).
// Todos os comandos imprimem JSON. A camada vem de --camada, VANTA_CAMADA ou ./camada (sem ela, só
// `comparar` roda: o registro é por empresa e a empresa é a da camada).
//
// Exit 0: ok. Exit 1: registro ou promoção recusados (a lista de erros vai no JSON). Exit 2: uso.

import { detectar, carregar, usoCamada } from './lib/camada.mjs';
import { caminhoDoRegistro, consultar, limiarDa, ehParecido, LEITORES, promover, registrar, similaridade } from './lib/esbocos.mjs';

function sair(obj, codigo = 0) {
  console.log(JSON.stringify(obj, null, 2));
  process.exit(codigo);
}

function uso(msg) {
  console.error(msg);
  process.exit(2);
}

/** Flags `--nome valor`, com repetição (--estrutura duas vezes vira lista). */
function flags(argv) {
  const f = {};
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (!a.startsWith('--')) uso(`argumento inesperado: ${a}`);
    const v = argv[i + 1];
    if (v === undefined || v.startsWith('--')) uso(`falta o valor de ${a}`);
    (f[a.slice(2)] ??= []).push(v);
    i++;
  }
  return f;
}

const um = (f, k) => f[k]?.[0] ?? null;
const bloco = (s) => s.split('|').map((b) => b.trim()).filter(Boolean);
/** Rascunhos {estrutura, visuais}: o n-ésimo --visuais acompanha a n-ésima --estrutura. */
const rascunhosDe = (f) => (f.estrutura ?? []).map((e, i) => ({ estrutura: bloco(e), visuais: f.visuais?.[i] ? bloco(f.visuais[i]) : null }));

const { explicito, resto } = usoCamada(process.argv.slice(2));
const [cmd, ...args] = resto;
if (!cmd) uso('uso: node esbocos.mjs consultar|registrar|promover|comparar ... [--camada <pasta>]');
const f = flags(args);

if (cmd === 'comparar') {
  const [ra, rb] = rascunhosDe(f);
  if (!ra || !rb) uso('comparar pede duas --estrutura');
  const sim = similaridade(ra.estrutura, rb.estrutura, ra.visuais, rb.visuais);
  sair({ ...sim, limiar: Number(um(f, 'limiar') ?? 0.6), parecido: ehParecido(sim, Number(um(f, 'limiar') ?? 0.6)) });
}

if (!['consultar', 'registrar', 'promover'].includes(cmd)) uso(`comando desconhecido: ${cmd}`);

const dir = detectar(explicito, []);
if (!dir) uso('camada não encontrada: o registro é por empresa. Informe --camada <pasta> ou VANTA_CAMADA');
let camada;
try {
  camada = carregar(dir).camada;
} catch (e) {
  uso(e.message);
}
const arquivo = caminhoDoRegistro(camada, um(f, 'registro'));

if (cmd === 'consultar') {
  const rascunhos = rascunhosDe(f);
  if (!rascunhos.length) uso('consultar pede ao menos uma --estrutura (o rascunho de cada direção)');
  sair({ camada: dir, ...consultar({ camada, dirCamada: dir, arquivo, rascunhos }) });
}

if (cmd === 'registrar') {
  const leitor = um(f, 'leitor') ?? 'visual';
  if (!LEITORES.includes(leitor)) uso(`--leitor: ${LEITORES.join(' ou ')}`);
  const r = registrar({
    camada,
    dirCamada: dir,
    arquivo,
    entrada: {
      data: um(f, 'data') ?? undefined,
      pedido: um(f, 'pedido') ?? '',
      leitor,
      direcao: {
        rotulo: um(f, 'rotulo') ?? '',
        nome: um(f, 'nome') ?? '',
        ...(um(f, 'privilegia') ? { privilegia: um(f, 'privilegia') } : {}),
        ...(um(f, 'visual-dominante') ? { visual_dominante: um(f, 'visual-dominante') } : {})
      },
      estrutura: bloco(um(f, 'estrutura') ?? ''),
      visuais: um(f, 'visuais') ? bloco(um(f, 'visuais')) : undefined,
      canvas: um(f, 'canvas')
    }
  });
  if (r.erros) sair({ registrado: false, erros: r.erros }, 1);
  sair({
    registrado: true,
    registro: arquivo,
    entrada: r.entrada,
    ocorrencia: r.antes.ocorrencias_anteriores + 1,
    parecidos_anteriores: r.antes.parecidos.map((p) => ({ data: p.data, pedido: p.pedido, pontuacao: p.pontuacao, visual: p.visual })),
    template: r.antes.template,
    propor_template: r.antes.propor_template,
    limiar: limiarDa(camada)
  });
}

if (cmd === 'promover') {
  const etapa = um(f, 'etapa');
  const r = promover({
    dirCamada: dir,
    nome: um(f, 'nome') ?? '',
    entrega: um(f, 'entrega') ?? '',
    estrutura: bloco(um(f, 'estrutura') ?? ''),
    etapa: etapa === null ? null : /^\d+$/.test(etapa) ? Number(etapa) : etapa
  });
  if (r.erros) sair({ promovido: false, erros: r.erros }, 1);
  sair({ promovido: true, arquivo: r.arquivo, template: r.template });
}
