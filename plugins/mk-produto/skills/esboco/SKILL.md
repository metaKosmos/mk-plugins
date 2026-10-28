---
name: esboco
description: Esboço da mK, o modo exploratório para quando o resultado visual ainda não está claro. Gera 2 a 3 direções de organizar o mesmo conteúdo (não variações de cor), mostra lado a lado num canvas, pergunta qual seguir ou qual mistura, constrói a escolhida na prancha final e registra o formato para reconhecê-lo na próxima vez. Use quando pedirem um esboço, opções de formato ou layout, "não sei como isso deve ficar", "me mostra caminhos para esse material", ou quando o pedido não cabe em nenhum template da lista (Ficha do Projeto, Mapa do Projeto, Painel de Portfólio, Mapa de Processo, Framing, PRD da Entrega).
---

# Esboço (mK)

Siga o motor em `../../motor/skills/esboco/SKILL.md`, com a camada `../../camada/`. Passe a camada aos scripts por `--camada ${CLAUDE_PLUGIN_ROOT}/camada` (ou `VANTA_CAMADA`). Dentro do motor, "o plugin" é a pasta `${CLAUDE_PLUGIN_ROOT}/motor`: os scripts são `motor/scripts/esbocos.mjs` e `motor/scripts/montar-esboco.mjs`.

Diga a quem roda a camada usada ("camada: mk-produto/camada, empresa metaKosmos").

## O que é específico da mK

- **Antes de esboçar, confira os templates:** se o pedido cabe num template com estado "pronto" em `camada/templates.json` (Ficha do Projeto, Mapa do Projeto), use a skill dele. O esboço é para o que ainda não tem molde.
- **Fonte de dados:** Linear só pelo servidor de `fontes.linear` da camada (ou o `servidor_alternativo`, depois de confirmar o workspace metaKosmos); nunca o `linear-214`. Tema que pede dado de projeto reaproveita o dossiê da Ficha do Projeto, por referência.
- **Visual:** vocabulário claro do mK Orbit (Anton nos títulos, Helvetica Neue no corpo, fundo branco), em `camada/tokens.json`. Cor de acento: material de **processo ou interno** (Mapa de Processo, fluxo, regras de design) usa o acento padrão da camada (`acento_padrao`, #7C3AED), mesmo quando cita um projeto de uma área. A cor do produto, pela tabela de áreas de `camada/camada.json` (mK Platform, mK Fashion+, mK AI Studio, Dados / mK Insights), só entra quando o material é **do projeto** daquela área. Em título que leva "mK", não use `text-transform: uppercase`: a caixa alta vira "MK".
- **Leitor e elemento visual:** o leitor de material de produto e de processo da mK é visual (gente de produto, muito visual). Cada direção declara o elemento visual dominante e cada bloco o seu, em SVG inline (regra 9 do motor). Mapa de Processo, por exemplo, pede fluxograma, diagrama de arquitetura, regras de design com amostras, gráficos com dado de fonte e fila em linha do tempo, não caixas de texto em grade. Carregue `artifact-diagramming` e `dataviz` quando disponíveis. O montador reprova direção sem bloco visual.
- **Canvas:** o tipo Design já está em `camada.json` (`canvas.type_url`).
- **Registro:** `esbocos.registro` está nulo na camada, então vale o padrão do motor, `~/.config/vanta-produto/esbocos.jsonl`, uma cópia por máquina. Só as linhas de empresa "metaKosmos" são lidas.
- **Segunda vez do mesmo formato:** a proposta de template usa a lista de `camada/templates.json`. Nome pelo que o template entrega, estado "em esboço". Quem decide é o David; mudança no contrato de template passa pelo Flávio, dono do módulo de produto.
- **Título do canvas:** só o nome do material, sem prefixo "mK:".
