# Esqueleto do documento de projeto mK

Este é o molde do Google Doc da mK. Vem de dois documentos reais: o de Teste A/B da Diana (modelo preferido do David) e o de recomendação de tabelas de medidas da Luiza (que ficou sem hipóteses e sem métricas, o que esta camada existe para evitar). Cumpre o contrato de esqueleto do motor (`motor/skills/documento-de-projeto/referencias/esqueleto-padrao.md`): a tabela "As seções", uma seção de hipóteses, uma de fases e uma de lacunas e riscos, as regras de fonte e o título em duas linhas. O esqueleto dá a forma. O conteúdo vem sempre do dossiê e da entrevista, nunca do esqueleto.

## Regras que valem para o documento inteiro

1. **Sem fonte não entra.** Número, nome de pessoa, nome de cliente, data, prazo e valor sem fonte não vão para o texto. Viram uma lacuna, e no lugar do dado fica "A definir (L3)", com o id da lacuna.
2. **Afirmação factual leva a fonte.** Link da reunião do Granola, da thread do Slack, da issue do Linear ou do documento do Drive, com a data. Em tabela, a fonte vai numa coluna "Fonte" ou no fim da célula. Três formas de citar, e só estas:

   | Fonte | Forma da citação |
   |---|---|
   | Reunião do Granola, thread do Slack, issue do Linear, documento do Drive | link com a data, por exemplo `[Granola 12/10](url)` |
   | Resposta dada na entrevista | `decisão de <Nome>, entrevista de DD/MM/AAAA`, sem link |
   | Arquivo local (ADR, sessão, pendência, proposta em disco) | `caminho:linha, registro de DD/MM`, sem link |

   Decisão dita em transcrição de reunião, conferida na transcrição, é fonte como qualquer outra: cita-se a reunião com a data e o trecho literal, e ela **não vira pergunta**. Decisão registrada em arquivo local também não vira lacuna nem pergunta.
3. **Dono da entrega se confere na transcrição.** O resumo do Granola às vezes inverte quem deve a entrega. Dono vindo só de resumo vai com a marca "(a confirmar na transcrição)" e entra na seção de lacunas.
4. **Contradição não se resolve calada.** Vale para duas fontes entre si e para a **premissa de quem responde a entrevista contra uma fonte**: o documento registra as duas versões, cada uma com fonte e data, na tabela de contradições da seção de lacunas, e diz quem resolve. Quem escreve o documento não escolhe lado. (Entre dois registros locais, a recomendação segue o mais recente, salvo indicação no próprio registro, mas o documento continua mostrando os dois lados.)
5. **Fonte inacessível é "não verificável daqui", com o motivo.** Nunca "não existe". Entra na seção de lacunas com o que ficou sem conferir.
6. **Marca e escrita.** "mK" (nunca MK nem mk), produtos "mK Fashion+", "mK AI Studio", "mK Platform". Sem traço longo e sem meia-risca: vírgula, dois-pontos ou ponto. Português brasileiro com diacríticos. Sem emoji. O `gerar-doc.py` reprova o que violar isso.
7. **Tom do modelo da Diana.** Parágrafo curto, frase direta, o porquê de cada fase em uma linha. Tabela no lugar de prosa quando há mais de três itens com os mesmos atributos. Parágrafo com 5 ou mais frases vira lista ou tabela.
8. **Seção opcional sem conteúdo com fonte é omitida**, não preenchida com generalidade. Seção obrigatória sem conteúdo fica com a frase "Sem [coisa] registrada. Lacuna: [o que falta]." e a lacuna correspondente na seção de lacunas.
9. **Não duplique o Linear.** O documento diz o que o projeto é e por que existe. O desdobramento em issues vem depois e fica fora desta skill.

## Título

Duas linhas antes da seção 0:

```
# Projeto <nome> | <produto mK>
<data de geração> · <autor do documento> · v<versão>
```

**Autor do documento é quem roda a skill**: o nome informado no pedido ou, na falta dele, o da conta autenticada (`gws auth status`). Nunca o dono do projeto, nunca o autor de uma fonte, e nunca um nome inventado: sem nome disponível, escreva o e-mail da conta.

## As 13 seções

| # | Seção (título no doc) | Obrigatória | Alimenta no `projeto.json` |
|---|---|---|---|
| 0 | Cabeçalho | sim | `projeto.nome`, `dono`, `prazo`, `status`, `linear_id`, `linear_url`, `ref` |
| 1 | Resumo e por que existe | sim | `projeto.descricao`, `projeto.statement`, `projeto.destaque`, `kpis` |
| 2 | Contexto e direcionamento | sim | `ref.fontes`, `fontes_dados` |
| 3 | O que já existe hoje | não | `capacidades` com estado, quando descrevem o estado atual |
| 4 | Objetivo | sim | `projeto.kicker`, `projeto.statement` |
| 5 | Hipóteses e acompanhamento | sim | `hipoteses` |
| 6 | Escopo e frentes | sim | `capacidades` (grupo = frente; estado `no go-live`, `depois` ou `fora`; `null` quando a fonte não diz) |
| 7 | Requisitos e métricas | não | `kpis`, `hipoteses[].metrica` |
| 8 | Fases | sim | `fases`, `roadmap.itens`, `roadmap.marcos` |
| 9 | Definição de pronto | sim | `fases[].gate`, último marco do `roadmap` |
| 10 | Responsáveis e rituais | sim | `projeto.dono`, `roadmap.trilhas` (uma por responsável ou frente, e só quando há itens de roadmap) |
| 11 | Prioridades | não | `roadmap.itens`, `roadmap.dependencias` |
| 12 | Lacunas e riscos | sim | `lacunas` |

### 0. Cabeçalho (obrigatória)

Tabela de duas colunas, rótulo à esquerda e valor à direita. Linhas, nesta ordem:

<!-- larguras: 28,72 -->
| Campo | Valor |
|---|---|
| Missão | uma frase, no formato "provar X", "levar Y a todos os clientes" |
| Dono | pessoa responsável pelo projeto, com a fonte |
| Par técnico | quem implementa junto, quando houver |
| Revisores | quem valida o documento |
| Status | Definição, Em execução, Pausado ou Concluído, mais a versão do doc |
| Prazo final | data AAAA-MM-DD ou DD/MM/AAAA, com a fonte; marco intermediário na linha seguinte, se existir |
| Origem | reunião, revisão ou pedido que criou o projeto, com data e link |
| Linear | id e link do projeto |

Falta dono ou prazo: escreva "A definir (Ln)" e abra a lacuna. No `projeto.json`, `dono` e `prazo` ficam `null`. Dono ou prazo que veio da entrevista **tem fonte** (`decisão de <Nome>, entrevista de DD/MM/AAAA`) e não abre lacuna.

### 1. Resumo e por que existe (obrigatória)

Dois a três parágrafos curtos. Problema, público e evidência, nesta ordem. Cada evidência com número ou caso real e link (exemplo de forma: "pedido em 90% dos kickoffs" só entra se o número vier de fonte). Feche com uma lista curta dos efeitos do problema, se houver mais de dois.

### 2. Contexto e direcionamento (obrigatória)

Lista das decisões e direcionamentos, uma por linha, cada uma com data e quem decidiu, e o link da reunião ou da thread. Depois, o contexto de clientes e do produto, também com fonte. Use tabela quando houver decisões em várias reuniões:

<!-- larguras: 14,56,30 -->
| Data | Decisão ou direcionamento | Quem e fonte |
|---|---|---|
| DD/MM | o que foi decidido, em uma frase | nome, [Granola DD/MM](url) |

### 3. O que já existe hoje (opcional)

Só entra quando o projeto evolui algo que já existe. Estado do produto ou do sistema, com fonte (issue, PR, doc técnico). Se houver fluxo em partes, tabela Parte, Sistema, O que faz. Se houver problema conhecido, lista com o impacto no objetivo. Sem fonte técnica, omita a seção.

### 4. Objetivo (obrigatória)

Uma frase de objetivo e uma lista de 3 a 5 resultados verificáveis, cada um com o marco ou prazo quando existir. Resultado sem forma de verificar não entra.

### 5. Hipóteses e acompanhamento (obrigatória)

É a seção que falta no documento de medidas e que o David pediu. Toda hipótese entra antes de rodar. Depois de cada rodada, registre resultado e aprendizado, inclusive quando não se confirma. Frase de abertura de uma linha, depois a tabela:

<!-- larguras: 6,24,16,18,22,14 -->
| ID | Hipótese | Ferramenta de teste | Métrica acompanhada | Resultado esperado | Situação e fonte |
|---|---|---|---|---|---|
| H1 | "Se fizermos X, então Y acontece" | onde ou como se testa | o que se mede | valor ou direção esperada | a rodar, em curso ou resultado; link |

Se o projeto não tem hipótese registrada, escreva "Sem hipóteses registradas. Lacuna: [o que falta]." e abra a lacuna. Nunca invente hipótese para preencher. Projeto que não é experimento ainda assim tem hipótese: a crença de que a entrega resolve o problema, com a métrica que mostraria isso. Se o dossiê não traz essa crença, pergunte na etapa B.

### 6. Escopo e frentes (obrigatória)

Tabela de frentes e, abaixo, a lista de fora de escopo (obrigatória: sem ela o escopo não está fechado).

<!-- larguras: 22,38,20,20 -->
| Frente | O que entra | Cliente ou público | Responsável |
|---|---|---|---|
| A. nome | entregas da frente | quem usa | pessoa, com fonte |

Fora do escopo neste momento:
- item que alguém poderia supor que entra, com a razão em meia linha

Entrega cujo estado (entra agora, depois, fora) nenhuma fonte diz fica sem estado no texto ("estado a definir") e vira `estado: null` no JSON, com lacuna.

### 7. Requisitos e métricas (opcional)

Requisitos em lista. Métricas em tabela com a situação de cada uma:

<!-- larguras: 34,16,16,34 -->
| Métrica | Uso | Situação | Observação e fonte |
|---|---|---|---|
| nome da métrica | principal, acionável ou reportada | existe, a criar ou pronta | quem cria, onde vive |

Omita se o projeto não tem métrica com fonte.

### 8. Fases (obrigatória)

Frase de abertura dizendo o que o prazo final exige. Tabela com o porquê de cada fase e o portão para a próxima. É o formato mais elogiado do modelo da Diana:

<!-- larguras: 22,16,32,30 -->
| Fase | Período | Por que existe | Portão para a próxima fase |
|---|---|---|---|
| 1. nome | mês ou datas, com fonte | o que a fase sustenta para o cliente ou para o time | critério verificável; "Não se aplica" na última |

Depois da tabela, se uma fase tem detalhe que não cabe na linha, um subtítulo curto por fase com lista de atividades e o entregável. Datas de fase sem fonte viram "A definir (Ln)".

### 9. Definição de pronto (obrigatória)

Frase que diz quando o projeto está feito, e a lista de critérios, um por frente quando houver frentes. Cada critério é verificável por alguém que não participou. Se um critério depende de valor ainda não definido (volume mínimo, meta), escreva "Critério a definir:" e abra a lacuna.

### 10. Responsáveis e rituais (obrigatória)

<!-- larguras: 24,76 -->
| Pessoa | Papel |
|---|---|
| nome | o que responde neste projeto, com a fonte da atribuição |

Depois, uma linha de rituais: cadência e participantes da revisão, do sync e do acompanhamento. Pessoa só entra se uma fonte a liga ao projeto.

### 11. Prioridades (opcional)

Ações imediatas, com dono e prazo. Só ações que saíram de reunião, issue ou entrevista.

<!-- larguras: 56,22,22 -->
| Ação | Responsável | Prazo |
|---|---|---|
| verbo no infinitivo e o objeto | pessoa | data ou "A definir (Ln)" |

### 12. Lacunas e riscos (obrigatória)

Três partes. Perguntas abertas em lista numerada com id (L1, L2...), cada uma com o que falta, de quem depende e a fonte que a gerou. Contradições em tabela. Riscos em tabela.

Perguntas abertas:
- L1. o que falta saber, de quem depende, onde apareceu (seção do doc ou fonte)

Contradições entre fontes (inclui a premissa de quem respondeu a entrevista contra uma fonte):

<!-- larguras: 20,32,32,16 -->
| Assunto | Versão A (fonte e data) | Versão B (fonte e data) | Resolve quem |
|---|---|---|---|
| o que diverge | o que diz uma, com fonte e data | o que diz a outra, com fonte e data | pessoa ou papel |

<!-- larguras: 36,28,36 -->
| Risco | Impacto | Mitigação |
|---|---|---|
| o que pode dar errado | o que acontece se der | o que já está combinado, com fonte; se não há, "A definir" |

Entram aqui, sem exceção: dado sem fonte que ficou de fora de outra seção, contradição entre fontes, dono a confirmar, e fonte não verificável com o motivo ("Granola de [pessoa]: reunião fora do workspace acessível"). Sem contradição, omita a tabela de contradições. Risco sem fonte não é inventado: se o dossiê não traz risco algum, escreva "Sem riscos registrados nas fontes. Lacuna: validar riscos com [dono]." e pergunte na etapa B.

## Lacunas no `projeto.json`

Cada lacuna da seção de lacunas que deixou vazio ou nulo algo do `projeto.json` vira um item de `lacunas[]`, com `secao`, `o_que_falta` e `depende_de`. O `secao` do JSON não é o número da seção do doc: é uma destas chaves, e o validador avisa quando outra aparece.

| Lacuna deixou vazio | `secao` no JSON |
|---|---|
| dono, prazo, status, nome, descrição, statement | `projeto` |
| indicadores | `kpis` |
| fontes de dados do projeto | `fontes_dados` |
| fases, períodos, portões | `fases` |
| entregas e estado delas (inclui `estado: null`) | `capacidades` |
| hipóteses, métricas | `hipoteses` |
| datas de itens, dependências, marcos | `roadmap` |

Lacuna de dono ou prazo cita a palavra "dono" ou "prazo" em `o_que_falta` (o validador procura o termo). O id Ln do texto do doc não vai para o JSON. A lacuna que só existe no doc (contradição entre fontes, fonte não verificável) pode ficar de fora do JSON.
