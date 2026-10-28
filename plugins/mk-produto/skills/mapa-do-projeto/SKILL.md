---
name: mapa-do-projeto
description: Monta o Mapa do Projeto da mK: canvas visual com 4 pranchas (Conceito, Capacidades, Roadmap, Hipóteses), para validar e compartilhar internamente. Use quando pedirem o Mapa do Projeto, o visual, o canvas, o roadmap ou o conceito de um projeto ("faz o Mapa do 263", "Mapa do Projeto do P-PROD-263"), a partir de um projeto.json, da Ficha do Projeto (Google Doc ou .docx) ou de um projeto do Linear mK. Também para atualizar um Mapa que já existe (republicar só o JSON).
---

# Mapa do Projeto (mK)

O Mapa do Projeto é produzido pela skill `visual-de-projeto` do motor. Siga-a em `../../motor/skills/visual-de-projeto/SKILL.md`, com a camada `../../camada/`. Passe a camada aos scripts por `--camada ${CLAUDE_PLUGIN_ROOT}/camada` (ou `VANTA_CAMADA`). Dentro do motor, "o plugin" é a pasta `${CLAUDE_PLUGIN_ROOT}/motor`: os scripts são `motor/scripts/validar-projeto.mjs`, `medir-pranchas.mjs` e `montar-canvas.mjs`.

Diga a quem roda a camada usada ("camada: mk-produto/camada, empresa metaKosmos").

## O que é específico da mK

- **Projeto do Linear:** só pelo servidor de `fontes.linear` da camada (ou o `servidor_alternativo`, depois de confirmar o workspace metaKosmos); nunca o `linear-214`.
- **Visual:** vocabulário claro do mK Orbit (Anton nos títulos, Helvetica Neue no corpo, fundo branco), em `camada/tokens.json`. O tipo Design do canvas já está em `camada.json` (`canvas.type_url`).
- **Regras de cor por área:** o acento sai do prefixo do nome do projeto no Linear, na tabela de `camada/camada.json`: mK Platform `#E10600`, mK Fashion+ `#DC0B9F`, mK AI Studio `#D0FB12`, Dados / mK Insights `#7DD3FC` ("Dados:" vence o produto citado depois), interno ou sem área `#7C3AED`. Só muda se quem roda pediu outra cor.
- **Título do canvas:** só o nome do projeto, sem prefixo "mK Projeto:". Se quem roda pedir outro título, o pedido vence: grave o mesmo título no `title` e na nota do `canvas.json`.
- **Onde entra no fluxo de produto:** o Mapa acompanha a Ficha do Projeto da etapa 3 (priorização de portfólio). Framing e PRD da Entrega, quando existirem, leem o mesmo `projeto.json`. A lista dos templates e do estado de cada um está em `camada/templates.json`.
- **Dono do módulo de produto:** Flávio.
