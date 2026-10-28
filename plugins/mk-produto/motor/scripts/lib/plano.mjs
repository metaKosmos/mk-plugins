// O que o validador e o gerador de descrição do plano.json dividem: os padrões neutros do
// bloco `gestor` da camada e o formato da descrição de uma issue.

/** Padrões do motor. Sem `gestor` na camada (ou sem camada), valem estes. */
export const GESTOR_PADRAO = Object.freeze({
  servidor: null,
  servidor_alternativo: null,
  proibido: [],
  time: null,
  estado_inicial: 'Backlog',
  escada_pontos: [1, 2, 3, 5, 8],
  teto_pontos: 5,
  contrato_campos: [
    'Modo', 'Fluxo', 'Repos', 'Pode mexer em', 'Resultado', 'O que entrega',
    'Teste principal', 'Portão', 'Fora', 'Se nunca for feita', 'Contexto',
  ],
  termos_mecanismo: [],
  labels: [],
  quem_atribui: 'quem prioriza',
  como: null,
});

/** Palavras que denunciam título por mecanismo e não por interface (sem acento, minúsculas). */
export const TERMOS_MECANISMO = [
  'endpoint', 'api', 'tabela', 'coluna', 'migracao', 'refatorar', 'refatoracao', 'schema',
  'backend', 'frontend', 'query', 'worker', 'cron', 'banco de dados',
];

/** O `gestor` final: o que a camada define sobre os padrões. `camada` é o camada.json já lido, ou null. */
export function gestorDe(camada) {
  const g = camada?.gestor ?? {};
  const linear = camada?.fontes?.linear ?? {};
  const saida = { ...GESTOR_PADRAO };
  for (const [k, v] of Object.entries(g)) if (v !== undefined && v !== null) saida[k] = v;
  saida.servidor = g.servidor ?? linear.servidor ?? null;
  // Alternativos para escrita, em ordem: o do gestor, depois o da fonte linear.
  saida.alternativos = [g.servidor_alternativo, linear.servidor_alternativo].filter((p, i, a) => typeof p === 'string' && p !== '' && a.indexOf(p) === i);
  saida.proibido = g.proibido?.length ? g.proibido : linear.proibido ?? [];
  return saida;
}

export const semAcento = (texto) =>
  String(texto ?? '')
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase();

export const palavras = (texto) => String(texto).split(/\s+/).filter(Boolean).length;

/**
 * A descrição de uma issue, no formato do contrato de onze campos (rótulos de gestor.contrato_campos):
 *
 *   **Modo:** direto
 *   **Fluxo:** ...
 *   **Repos:** a, b            (ou "nenhum")
 *   **Pode mexer em:** x, y
 *   **Resultado:** ...
 *   **O que entrega:**         (checklist, um "- [ ]" por item)
 *   - [ ] ...
 *   **Teste principal:** ...
 *   **Portão:** ...
 *   **Fora:** ...
 *   **Se nunca for feita:** ...
 *   **Contexto:** ...
 *
 *   Responsável sugerido: <nome> (<quem atribui> atribui)
 *
 * Responsável sugerido só sai quando a issue nasce sem responsável.
 */
export function montarDescricao(issue, gestor = GESTOR_PADRAO) {
  const [rModo, rFluxo, rRepos, rPode, rResultado, rEntrega, rTeste, rPortao, rFora, rSeNunca, rContexto] =
    gestor.contrato_campos;
  const checklist = (issue.entrega ?? []).map((item) => `- [ ] ${item.trim()}`).join('\n');
  const linhas = [
    `**${rModo}:** ${issue.modo}`,
    `**${rFluxo}:** ${issue.fluxo.trim()}`,
    `**${rRepos}:** ${issue.repos?.length ? issue.repos.join(', ') : 'nenhum'}`,
    `**${rPode}:** ${(issue.pode_mexer_em ?? []).join(', ')}`,
    `**${rResultado}:** ${issue.resultado.trim()}`,
    `**${rEntrega}:**\n${checklist}`,
    `**${rTeste}:** ${issue.teste_principal.trim()}`,
    `**${rPortao}:** ${issue.portao.trim()}`,
    `**${rFora}:** ${issue.fora.trim()}`,
    `**${rSeNunca}:** ${issue.se_nunca_for_feita.trim()}`,
    `**${rContexto}:** ${issue.contexto.trim()}`,
  ];
  if (!issue.responsavel && issue.responsavel_sugerido?.trim()) {
    linhas.push('', `Responsável sugerido: ${issue.responsavel_sugerido.trim()} (${gestor.quem_atribui} atribui)`);
  }
  return linhas.join('\n');
}

/**
 * O que a etapa opcional de estrutura cria no gestor antes das issues: o projeto, se `ref.projeto.novo`,
 * e as milestones marcadas `novo`. Data de milestone só vai com o marco da pessoa (`data_fonte`).
 */
export function estruturaNova(plano, gestor = GESTOR_PADRAO) {
  const p = plano.ref?.projeto;
  return {
    projeto: p?.novo === true ? { nome: p.nome, descricao: p.descricao ?? null } : null,
    milestones: (plano.milestones ?? [])
      .filter((m) => m.novo === true)
      .map((m) => ({ nome: m.nome, descricao: m.descricao ?? null, data: m.data && m.data_fonte ? m.data : null })),
    time: gestor.time ?? null,
  };
}
