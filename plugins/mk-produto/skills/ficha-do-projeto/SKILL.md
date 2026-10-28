---
name: ficha-do-projeto
description: Monta a Ficha do Projeto da mK (template de documento da etapa 3): Google Doc nativo com as 13 seções do esqueleto, mais o projeto.json que alimenta o Mapa do Projeto. Levanta Linear mK, Granola, Slack, Drive e arquivos locais, entrevista só sobre o que as fontes não responderam e nunca inventa dado. Use quando o dev ou o David pedir a Ficha do Projeto, o documento ou o doc de um projeto ("faz a Ficha do 263", "Ficha do P-PROD-263", "monta o doc do projeto X", "organiza esse projeto antes de ir para o Linear", etapa 3 do fluxo de produto), mesmo que só diga o id do Linear ou uma frase de intenção.
---

# Ficha do Projeto (mK)

A Ficha do Projeto é produzida pela skill `documento-de-projeto` do motor. Siga-a em `../../motor/skills/documento-de-projeto/SKILL.md`, com a camada `../../camada/` (`camada.json`, `esqueleto.md`, `tokens.json`). Passe a camada ao motor por `--camada ${CLAUDE_PLUGIN_ROOT}/camada` (ou `VANTA_CAMADA`). Dentro do motor, "o plugin" é a pasta `${CLAUDE_PLUGIN_ROOT}/motor`: é lá que estão `scripts/validar-projeto.mjs` e `skills/documento-de-projeto/scripts/gerar-doc.py`.

Diga a quem roda a camada usada ("camada: mk-produto/camada, empresa metaKosmos").

## O que é específico da mK

- **Onde entra no fluxo de produto:** etapa 3, priorização de portfólio. O documento, a Ficha do Projeto, é o artefato dessa etapa (template listado em `camada/templates.json`). O desdobramento em issues no Linear vem depois, a partir do doc, e não faz parte desta skill.
- **Dono do módulo de produto:** Flávio. Dúvida sobre o esqueleto, o fluxo ou o contrato `projeto.json` vai para ele.
- **Fonte Linear:** só pelo servidor de `fontes.linear` da camada (ou o `servidor_alternativo`, depois de confirmar o workspace metaKosmos); nunca o `linear-214`.
- **Arquivos locais:** o vault de notas (David-OS) só existe na máquina do David. Fora dela a fonte fica "não aplicável" e a skill segue com as outras quatro. Num vault com várias empresas, só o trecho da mK sobe para o dossiê.
- **Acento do projeto** (`projeto.acento`), pela área no nome do projeto no Linear. A tabela vive em `camada/camada.json`: mK Platform `#E10600`, mK Fashion+ `#DC0B9F`, mK AI Studio `#D0FB12`, Dados / mK Insights `#7DD3FC` (o prefixo "Dados:" vence o produto citado depois), interno ou sem área `#7C3AED`.
- **Nome do arquivo no Drive:** `<produto mK> | Projeto <nome> - v1 | <DD/MM/AAAA>`. Pedido de outro nome de quem rodou vence.
