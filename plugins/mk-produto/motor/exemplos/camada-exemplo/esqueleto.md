# Esqueleto da Fábrica Exemplo (fictício)

Exemplo de esqueleto de camada: seis seções em vez de treze, para mostrar que a camada troca o molde sem tocar no motor. Vale o contrato de `skills/documento-de-projeto/referencias/esqueleto-padrao.md`: a tabela "As seções", uma seção de hipóteses, uma de fases e uma de lacunas e riscos, as regras de fonte, o formato de citação e o autor de quem roda a skill.

## As seções

| # | Seção (título no doc) | Obrigatória | Alimenta no `projeto.json` |
|---|---|---|---|
| 0 | Ficha | sim | `projeto.nome`, `dono`, `prazo`, `status`, `linear_id`, `linear_url`, `ref` |
| 1 | Problema e objetivo | sim | `projeto.descricao`, `projeto.statement`, `projeto.destaque`, `projeto.kicker`, `kpis` |
| 2 | O que entra e o que fica de fora | sim | `capacidades` (estado `no go-live`, `depois`, `fora` ou `null`), `fontes_dados` |
| 3 | Hipóteses | sim | `hipoteses` |
| 4 | Fases e prazos | sim | `fases`, `roadmap` (itens, marcos, trilhas, dependências) |
| 5 | Lacunas e riscos | sim | `lacunas` |

## Como cada seção se escreve

- **0. Ficha:** tabela de duas colunas (Campo, Valor) com Dono, Prazo final, Status, Origem e id no gestor de tarefas. Dono ou prazo sem fonte: "A definir (Ln)".
- **1. Problema e objetivo:** dois parágrafos curtos (problema com evidência, objetivo em uma frase) e uma lista de 3 resultados verificáveis.
- **2. O que entra e o que fica de fora:** tabela Frente, Entrega, Estado, mais a lista "Fora do escopo".
- **3. Hipóteses:** a tabela ID, Hipótese, Métrica, Resultado esperado, Situação e fonte. Sem hipótese registrada: "Sem hipóteses registradas. Lacuna: ...".
- **4. Fases e prazos:** tabela Fase, Período, Portão para a próxima.
- **5. Lacunas e riscos:** perguntas abertas (L1, L2...), tabela de contradições entre fontes (Assunto, Versão A com data, Versão B com data, Resolve quem) e tabela de riscos.

O título do documento segue o padrão: `# Projeto <nome> | <produto ou área>` e, na linha de baixo, `<data> · <quem roda a skill> · v<versão>`.
