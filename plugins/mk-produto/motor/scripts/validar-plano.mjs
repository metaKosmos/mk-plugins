#!/usr/bin/env node
// Valida um plano.json (contrato v1) contra schema/plano.schema.json e confere o que o schema
// não alcança: título por interface e não por mecanismo, teste principal de quem usa, pontos
// dentro da escada e do teto, responsável só com ordem, dependências que existem e não fecham
// ciclo, conferência com fonte e SHA, e as regras de escrita e de marca da CAMADA.
//
//   node validar-plano.mjs <plano.json> [--camada <pasta>]
//
// Escada, teto, estado inicial e rótulos do contrato vêm do bloco `gestor` da camada. Sem
// camada valem os padrões neutros (escada 1, 2, 3, 5, 8, teto 5) e nenhuma regra de marca é
// aplicada, e o aviso diz isso.
//
// Exit 0: válido (avisos podem sair). Exit 1: lista de erros, um por linha, cada um com o
// caminho do campo.

import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { executadoDiretamente } from './lib/execucao.mjs';
import { validarSchema, caminho } from './lib/schema.mjs';
import { detectar, carregar, usoCamada, problemasDeTexto } from './lib/camada.mjs';
import { GESTOR_PADRAO, TERMOS_MECANISMO, gestorDe, montarDescricao, palavras, semAcento } from './lib/plano.mjs';

const AQUI = dirname(fileURLToPath(import.meta.url));
const SCHEMA = JSON.parse(readFileSync(join(AQUI, '..', 'schema', 'plano.schema.json'), 'utf8'));

const LIMITE_PALAVRAS = 150;
const ID_DO_GESTOR = /^[A-Za-z][A-Za-z0-9]*-\d+$/;
// O teste principal é escrito por quem usa ("abro X, faço Y, vejo Z"). Passa quando tem uma
// ação de quem usa, na primeira pessoa do presente, e uma observação do resultado. A ação é
// reconhecida por uma lista ampla de verbos e, para o verbo que a lista não conhece, por uma
// forma que só verbo tem: palavra em -o seguida de artigo ou possessivo ("inspeciono o painel").
// Palavra em -o que não é verbo (projeto, resultado, pedido) não vem seguida de artigo.
const VERBOS_DE_QUEM_USA = [
  'abro', 'entro', 'acesso', 'clico', 'rodo', 'peço', 'pergunto', 'comento', 'gero', 'digo', 'falo', 'escolho', 'seleciono',
  'envio', 'mando', 'preencho', 'digito', 'escrevo', 'arrasto', 'subo', 'baixo', 'copio', 'colo', 'salvo', 'edito',
  'crio', 'apago', 'filtro', 'busco', 'procuro', 'compartilho', 'aprovo', 'recuso', 'marco', 'ativo', 'desativo',
  'instalo', 'conecto', 'configuro', 'faço', 'executo', 'inicio', 'confirmo', 'cadastro', 'pago', 'compro', 'finalizo',
  'fecho', 'publico', 'importo', 'exporto', 'leio', 'confiro', 'consigo', 'recebo', 'vejo',
  'uso', 'utilizo', 'chamo', 'invoco', 'converso', 'testo', 'solicito', 'requisito', 'pesquiso', 'respondo', 'repito',
  'refaço', 'rejeito', 'aceito', 'adiciono', 'removo', 'excluo', 'altero', 'troco', 'mudo', 'movo', 'organizo', 'agrupo',
  'toco', 'aperto', 'pressiono', 'navego', 'volto', 'avanço', 'desconecto', 'autorizo', 'permito', 'bloqueio', 'libero',
  'reviso', 'anexo', 'carrego', 'imprimo', 'agendo', 'programo', 'simulo', 'reinicio', 'atualizo', 'recarrego',
  'cancelo', 'estorno', 'reembolso', 'emito', 'assino', 'lanço', 'vinculo', 'associo', 'mesclo', 'divido', 'separo',
  'restauro', 'duplico', 'clono', 'renomeio', 'nomeio', 'convido', 'indico', 'atribuo', 'insiro', 'incluo', 'monto',
  'disparo', 'aciono', 'ligo', 'desligo', 'provo', 'experimento', 'insisto', 'levo', 'trago', 'coloco', 'ponho', 'deixo',
];
// Observação do resultado, que não conta como ação mesmo estando na primeira pessoa.
const OBSERVA = ['vejo', 'vê', 'aparece', 'aparecem', 'recebo', 'leio', 'confiro', 'encontro', 'noto', 'observo', 'verifico', 'checo', 'surge', 'mostra', 'mostram'];
const ABRE_O_TESTE = /^(em|no|na|ao)\b/i;
const letras = '\\p{L}';
const VERBO_DE_QUEM_USA = new RegExp(`(?<![${letras}])(${VERBOS_DE_QUEM_USA.join('|')})(?![${letras}])`, 'giu');
const OBSERVACAO = new RegExp(`(?<![${letras}])(${OBSERVA.join('|')})(?![${letras}])`, 'iu');
const MOSTRA_O_QUE_VE = new RegExp(`(?<![${letras}])(${[...OBSERVA, 'veja', 'abre', 'consigo'].join('|')})(?![${letras}])`, 'iu');
// palavra em -o (4+ letras) seguida de artigo ou possessivo; "como", "todo" e afins não são verbo
const VERBO_PELA_FORMA = new RegExp(`(?<![${letras}])([${letras}]{3,}o)\\s+(?:o|a|os|as|um|uma|meu|minha|meus|minhas)(?![${letras}])`, 'giu');
const NAO_E_VERBO = new Set(['como', 'todo', 'mesmo', 'tanto', 'muito', 'pouco', 'outro', 'segundo', 'quanto', 'cujo', 'junto', 'logo']);

/** As ações de quem usa em primeira pessoa que o teste traz, sem as observações do resultado. */
function acoesDeQuemUsa(texto) {
  const achadas = new Set();
  for (const v of texto.match(VERBO_DE_QUEM_USA) ?? []) achadas.add(v.toLowerCase());
  for (const m of texto.matchAll(VERBO_PELA_FORMA)) achadas.add(m[1].toLowerCase());
  for (const palavra of [...achadas]) {
    if (OBSERVA.includes(palavra) || NAO_E_VERBO.has(palavra)) achadas.delete(palavra);
  }
  return achadas;
}
const PR_COM_HASH = /\bPR\s*#\d/i;

/** `regras`: resultado de compilar() da camada, ou null. `gestor`: gestorDe(camada). */
export function validar(dados, { regras = null, gestor = GESTOR_PADRAO } = {}) {
  const erros = [];
  const avisos = [];
  validarSchema(dados, SCHEMA, SCHEMA, '', erros);
  if (dados && typeof dados === 'object' && !Array.isArray(dados)) conferir(dados, erros, avisos, regras, gestor);
  return { erros, avisos };
}

function dataReal(texto) {
  if (typeof texto !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(texto)) return null;
  const t = Date.parse(`${texto}T00:00:00Z`);
  if (Number.isNaN(t)) return null;
  return new Date(t).toISOString().slice(0, 10) === texto ? t : null;
}

const cheio = (v) => typeof v === 'string' && v.trim() !== '';

function conferir(d, erros, avisos, regras, gestor) {
  const issues = Array.isArray(d.issues) ? d.issues : [];

  // datas que passaram no formato mas não existem
  for (const [onde, valor] of coletarDatas(d)) {
    if (dataReal(valor) === null) erros.push(`${onde}: "${valor}" não é uma data real`);
  }

  // escrita e marca da camada, e autolink indevido, em todo texto que não é link
  if (regras) {
    for (const [onde, valor] of coletarTextos(d)) {
      for (const problema of problemasDeTexto(valor, regras)) erros.push(`${onde}: ${problema}`);
    }
  } else {
    avisos.push('sem camada: regras de marca e de escrita não aplicadas, vale a escada neutra (informe --camada <pasta>)');
  }
  for (const [onde, valor] of coletarTextos(d)) {
    if (PR_COM_HASH.test(valor)) erros.push(`${onde}: "PR #N" vira link para a issue errada no gestor. Escreva "PR N", sem o "#"`);
  }

  // projeto e milestones novos: a etapa opcional de estrutura, só depois do ok
  const projeto = d.ref?.projeto;
  if (projeto?.novo === true && cheio(projeto.id)) {
    erros.push('ref.projeto.id: projeto novo não tem id. Tire "novo" se o projeto já existe');
  }
  (Array.isArray(d.milestones) ? d.milestones : []).forEach((m, i) => {
    if (m?.novo !== true) return;
    const onde = (campo) => caminho(caminho('milestones', i), campo);
    if (cheio(m.id)) erros.push(`${onde('id')}: milestone nova não tem id. Tire "novo" se ela já existe`);
    if (m.data && !cheio(m.data_fonte)) erros.push(`${onde('data_fonte')}: obrigatório com data. Data sem marco da pessoa é chute`);
    if (!(projeto?.novo === true || cheio(projeto?.id))) {
      erros.push(`${caminho('milestones', i)}: milestone nova precisa de ref.projeto com id ou novo`);
    }
  });

  // ids locais
  const ids = new Set();
  issues.forEach((it, i) => {
    if (typeof it?.id_local !== 'string') return;
    if (ids.has(it.id_local)) erros.push(`issues[${i}].id_local: "${it.id_local}" repetido`);
    ids.add(it.id_local);
  });

  const milestones = Array.isArray(d.milestones) ? d.milestones : [];
  const hoje = dataReal(d.ref?.data);
  const termos = [...TERMOS_MECANISMO, ...(gestor.termos_mecanismo ?? []).map(semAcento)];
  const reTermos = new RegExp(`(?<![a-z0-9])(${termos.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})(?![a-z0-9])`);

  issues.forEach((it, i) => {
    if (!it || typeof it !== 'object') return;
    const c = (campo) => caminho(caminho('issues', i), campo);

    // título: <Superfície>: <o que o usuário faz>, nunca por mecanismo
    if (cheio(it.titulo)) {
      if (!/^[^:]{2,}:\s*\S/.test(it.titulo)) {
        erros.push(`${c('titulo')}: "${it.titulo}" não segue "<Superfície>: <o que o usuário faz>"`);
      }
      const achado = semAcento(it.titulo).match(reTermos);
      if (achado) {
        erros.push(`${c('titulo')}: "${achado[1]}" é mecanismo. Escreva pelo que o usuário faz na interface`);
      }
      if (it.titulo.length > 100) avisos.push(`${c('titulo')}: ${it.titulo.length} caracteres, passa de 100`);
    }

    // teste principal: abro X, faço Y, vejo Z
    if (cheio(it.teste_principal)) {
      const t = it.teste_principal.trim();
      const partes = t.split(/[,;]/).map((p) => p.trim()).filter(Boolean);
      const verbos = new Set((t.match(VERBO_DE_QUEM_USA) ?? []).map((v) => v.toLowerCase()));
      const quemUsa = acoesDeQuemUsa(t).size > 0 && OBSERVACAO.test(t);
      if (!ABRE_O_TESTE.test(t) && partes.length < 3 && verbos.size < 2 && !quemUsa) {
        erros.push(`${c('teste_principal')}: precisa ser "abro X, faço Y, vejo Z" (uma ação de quem usa em primeira pessoa e o que se vê, como uso e vejo, ou as três partes, ou começa por em, no, na)`);
      } else if (!MOSTRA_O_QUE_VE.test(t)) {
        avisos.push(`${c('teste_principal')}: não diz o que se vê no fim ("vejo ...")`);
      }
    }

    // pontos: dentro da escada e do teto da camada
    if (it.pontos === null) {
      erros.push(`${c('pontos')}: sem estimativa. Use um valor da escada (${gestor.escada_pontos.join(', ')})`);
    } else if (Number.isInteger(it.pontos)) {
      if (!gestor.escada_pontos.includes(it.pontos)) {
        erros.push(`${c('pontos')}: ${it.pontos} fora da escada (${gestor.escada_pontos.join(', ')})`);
      } else if (it.pontos > gestor.teto_pontos) {
        erros.push(`${c('pontos')}: ${it.pontos} passa do teto de ${gestor.teto_pontos}. Fatie por fluxo`);
      }
    }

    // responsável só com ordem
    if (cheio(it.responsavel)) {
      if (it.responsavel_autorizado !== true) {
        erros.push(`${c('responsavel')}: "${it.responsavel}" sem responsavel_autorizado. Atribuir a alguém é mexer na fila dele: sem ordem explícita, use responsavel_sugerido`);
      } else if (!cheio(it.autorizado_por)) {
        erros.push(`${c('autorizado_por')}: obrigatório com responsavel_autorizado (a ordem, com quem deu e quando)`);
      }
    } else if (it.responsavel_autorizado === true) {
      avisos.push(`${c('responsavel_autorizado')}: verdadeiro sem responsavel`);
    }

    // data só com marco da pessoa
    if (it.data_limite && !cheio(it.data_limite_fonte)) {
      erros.push(`${c('data_limite_fonte')}: obrigatório com data_limite. Data sem marco da pessoa é chute`);
    }

    // milestone: o nome é exato, e a entrada no gestor é pelo id
    if (cheio(it.milestone) && milestones.length) {
      const m = milestones.find((x) => x?.nome === it.milestone);
      if (!m) {
        const quase = milestones.find((x) => typeof x?.nome === 'string' && x.nome.trim() === it.milestone.trim());
        erros.push(
          quase
            ? `${c('milestone')}: "${it.milestone}" difere de "${quase.nome}" só no espaço das pontas. Use o nome exato do gestor`
            : `${c('milestone')}: "${it.milestone}" não existe em milestones[]`
        );
      } else if (!cheio(m.id) && m.novo !== true) {
        avisos.push(`${c('milestone')}: "${m.nome}" sem id em milestones[]. A issue entra pelo id`);
      } else if (m.data && hoje !== null && dataReal(m.data) !== null && dataReal(m.data) < hoje) {
        avisos.push(`${c('milestone')}: "${m.nome}" venceu em ${m.data}. Vira pergunta a quem roda, não chute`);
      } else if (!m.data) {
        avisos.push(`${c('milestone')}: "${m.nome}" sem data. Vira pergunta a quem roda, não chute`);
      }
    } else if (cheio(it.milestone) && !milestones.length) {
      avisos.push(`${c('milestone')}: sem milestones[] lidas do gestor, o nome não foi conferido`);
    }

    // o contrato cabe em 150 palavras e o contexto em 3 linhas
    if (['modo', 'fluxo', 'resultado', 'teste_principal', 'portao', 'fora', 'se_nunca_for_feita', 'contexto'].every((k) => typeof it[k] === 'string')
        && ['repos', 'pode_mexer_em', 'entrega'].every((k) => Array.isArray(it[k]) && it[k].every((v) => typeof v === 'string'))) {
      const n = palavras(montarDescricao(it, gestor));
      if (n > LIMITE_PALAVRAS) avisos.push(`${c('(descrição)')}: ${n} palavras, passa de ${LIMITE_PALAVRAS}. Detalhe vai em comentário`);
    }
    if (cheio(it.contexto) && it.contexto.trim().split('\n').length > 3) {
      avisos.push(`${c('contexto')}: mais de 3 linhas`);
    }
  });

  // dependências
  const referencia = (valor) => ids.has(valor) || ID_DO_GESTOR.test(valor);
  const grafo = new Map();
  issues.forEach((it, i) => {
    for (const campo of ['bloqueia', 'relacionada']) {
      (Array.isArray(it?.[campo]) ? it[campo] : []).forEach((alvo, j) => {
        const onde = `${caminho(caminho('issues', i), campo)}[${j}]`;
        if (typeof alvo !== 'string') return;
        if (alvo === it.id_local) erros.push(`${onde}: issue ligada a ela mesma`);
        else if (!referencia(alvo)) erros.push(`${onde}: "${alvo}" não é id_local da proposta nem id de issue do gestor`);
      });
    }
    grafo.set(it?.id_local, (Array.isArray(it?.bloqueia) ? it.bloqueia : []).filter((a) => ids.has(a)));
  });
  const ciclo = acharCiclo(grafo);
  if (ciclo) erros.push(`issues: bloqueio em ciclo (${ciclo.join(' > ')})`);

  // conferência: estado com fonte, SHA e motivo
  (Array.isArray(d.conferencia) ? d.conferencia : []).forEach((c, i) => {
    const onde = (campo) => caminho(caminho('conferencia', i), campo);
    if (c?.estado === 'existe' || c?.estado === 'parcial') {
      if (!/^\S+:\d+/.test(c.fonte ?? '')) erros.push(`${onde('fonte')}: "${c.estado}" pede caminho:linha`);
      if (!cheio(c.repo)) erros.push(`${onde('repo')}: "${c.estado}" pede o repositório onde a fonte foi vista (a fonte é só caminho:linha)`);
    }
    if (c?.estado === 'não existe' && !cheio(c.repo)) {
      erros.push(`${onde('repo')}: "não existe" pede o repositório onde se procurou (sem isso a linha não diz onde a ausência foi vista)`);
    }
    // a fonte é caminho:linha dentro de repo: com o prefixo do repo o caminho não abre
    if (cheio(c?.repo) && cheio(c?.fonte)) {
      const prefixado = c.repo.split(',').map((r) => r.trim()).filter(Boolean).find((r) => c.fonte.trim().startsWith(`${r}/`));
      if (prefixado) erros.push(`${onde('fonte')}: "${c.fonte}" traz o prefixo "${prefixado}/". Escreva caminho:linha sem o prefixo do repo`);
    }
    if (['existe', 'parcial', 'não existe'].includes(c?.estado) && !/^[0-9a-f]{7,40}$/.test(c.sha ?? '')) {
      erros.push(`${onde('sha')}: "${c.estado}" pede o SHA do HEAD lido`);
    }
    if (c?.estado === 'não verificável daqui' && !cheio(c.motivo)) {
      erros.push(`${onde('motivo')}: "não verificável daqui" pede o motivo (o erro ou a falta de acesso)`);
    }
  });

  if (issues.length === 0) avisos.push('issues vazio: nada a criar. Registre o motivo em lacunas[] ou em nao_viram_issue[]');
}

function acharCiclo(grafo) {
  const estado = new Map();
  const pilha = [];
  const visitar = (no) => {
    estado.set(no, 1);
    pilha.push(no);
    for (const alvo of grafo.get(no) ?? []) {
      if (estado.get(alvo) === 1) return [...pilha.slice(pilha.indexOf(alvo)), alvo];
      if (!estado.get(alvo)) {
        const achado = visitar(alvo);
        if (achado) return achado;
      }
    }
    pilha.pop();
    estado.set(no, 2);
    return null;
  };
  for (const no of grafo.keys()) {
    if (!estado.get(no)) {
      const achado = visitar(no);
      if (achado) return achado;
    }
  }
  return null;
}

const CAMPOS_DATA = new Set(['data', 'data_limite']);

function coletarDatas(no, onde = '', saida = []) {
  if (Array.isArray(no)) no.forEach((v, i) => coletarDatas(v, caminho(onde, i), saida));
  else if (no && typeof no === 'object') {
    for (const [k, v] of Object.entries(no)) {
      if (CAMPOS_DATA.has(k) && typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)) saida.push([caminho(onde, k), v]);
      else coletarDatas(v, caminho(onde, k), saida);
    }
  }
  return saida;
}

function coletarTextos(no, onde = '', saida = []) {
  if (typeof no === 'string') {
    if (!/^https?:\/\//.test(no)) saida.push([onde || '(raiz)', no]);
  } else if (Array.isArray(no)) no.forEach((v, i) => coletarTextos(v, caminho(onde, i), saida));
  else if (no && typeof no === 'object') {
    for (const [k, v] of Object.entries(no)) {
      if (k === 'url' || k === 'doc_url' || k === 'sha') continue;
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
    console.error('uso: node validar-plano.mjs <plano.json> [--camada <pasta>]');
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
  const { erros, avisos } = validar(dados, { regras: camada?.regras ?? null, gestor: gestorDeCamada(camada) });
  for (const a of avisos) console.log(`aviso  ${a}`);
  for (const e of erros) console.log(`ERRO   ${e}`);
  console.log(erros.length ? `\ninválido: ${erros.length} erro(s), ${avisos.length} aviso(s)` : `\nválido: 0 erros, ${avisos.length} aviso(s)`);
  process.exit(erros.length ? 1 : 0);
}

function gestorDeCamada(camada) {
  return gestorDe(camada?.camada ?? null);
}
