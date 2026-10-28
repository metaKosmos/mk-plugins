---
name: projeto-issues
description: Quebra o projeto aprovado da mK em issues no Linear (workspace metaKosmos, time Product). Parte do Google Doc da Ficha do Projeto e do projeto.json, confere nos repositórios o que já existe, mostra a proposta de issues por interface (milestone, título, teste principal, pontos, responsável sugerido), pergunta o que as fontes não decidem e só cria depois do ok, cada issue com o contrato de onze campos (modo, fluxo, repos, pode mexer em, resultado, o que entrega, teste principal, portão, fora, se nunca for feita, contexto), pontos na escada 1-2-3-5-8 e dependências ligadas. Use quando pedirem para "quebrar o projeto no Linear", "criar as issues do projeto", "transformar o plano em issues", "desdobrar no Linear", "abrir as issues da Ficha", mesmo que só digam o nome ou o id do projeto (por exemplo "quebra o projeto de leads no Linear").
---

# Issues do Projeto (mK)

A proposta e a criação das issues são feitas pela skill `plano-no-linear` do motor. Siga-a em `../../motor/skills/plano-no-linear/SKILL.md`, com a camada `../../camada/`. Passe a camada aos scripts por `--camada ${CLAUDE_PLUGIN_ROOT}/camada` (ou `VANTA_CAMADA`). Dentro do motor, "o plugin" é a pasta `${CLAUDE_PLUGIN_ROOT}/motor`: os scripts são `motor/scripts/validar-plano.mjs`, `descricao-issue.mjs`, `fontes-do-levantamento.mjs` e `validar-projeto.mjs`.

Diga a quem roda a camada usada ("camada: mk-produto/camada, empresa metaKosmos").

## O que é específico da mK

- **Onde entra no fluxo de produto:** depois da Ficha do Projeto aprovada (etapa 3). A Ficha e o `projeto.json` são a entrada; o Mapa do Projeto, se existir, serve de referência visual. Sem Ficha, rode primeiro a skill `ficha-do-projeto`.
- **Servidor de escrita:** o bloco `gestor` da camada. Ordem: o servidor `linear-mk`, se existir na sessão; sem ele, o conector Linear do claude.ai (`gestor.servidor_alternativo`), e só depois de confirmar com `get_workspace` (ou `get_team`) que ele responde pelo workspace metaKosmos (url `linear.app/metakosmos`), antes de qualquer escrita. Quem roda decide qual existe: liste os servidores MCP da sessão e rode `node "${CLAUDE_PLUGIN_ROOT}/motor/scripts/fontes-do-levantamento.mjs" gestor --camada "${CLAUDE_PLUGIN_ROOT}/camada" --na-sessao <prefixos>`. Saída 1 ("não verificável daqui"), outro workspace ou sem confirmação: nada é criado e o motivo vai para quem roda. Nunca o `linear-214`.
- **Time e estado:** time Product, issue nasce em Backlog. As ferramentas do Linear são adiadas: carregue os esquemas com `ToolSearch` antes de usar.
- **Pontos:** escada 1, 2, 3, 5 e 8, com teto de 5 por issue. Acima de 5, fatie por fluxo de quem usa, nunca por camada técnica.
- **Contrato da issue:** os onze campos de `gestor.contrato_campos`, na ordem da camada. Modo é um de quatro: direto, entrevista, brainstorming ou pesquisa. O teste principal é "abro X, faço Y, vejo Z", em palavras de quem usa.
- **Responsável:** quem atribui o que nasce sem dono é o lead do projeto. Ninguém é atribuído sem ordem escrita de quem roda: a sugestão vai no texto da issue, não no campo.
- **Escrita e marca:** as da camada. "mK" com m minúsculo e K maiúsculo (mK Fashion+, mK AI Studio, mK Platform), sem traço longo, sem meia-risca, sem emoji, e "PR 84" em vez de "PR #84". O validador do plano reprova o que sair da regra.
- **Documento de origem:** o Google Doc da Ficha é lido pelo CLI de `fontes.drive.cli` ou pelo servidor de reserva de `fontes.drive`, só leitura. Sem nenhum dos dois, a skill segue só com o `projeto.json` e diz que o Doc não foi lido.
- **Projeto e milestone que ainda não existem:** só são criados na etapa opcional do motor, com o ok de quem roda. Sem o sim, a skill não cria nenhum dos dois.
- **Sem AskUserQuestion na sessão:** pare depois da proposta, devolva as perguntas numeradas e aguarde. Nada é criado por falta de resposta.
- **Registro:** `plano.json` e `criacao.json` ficam na pasta do projeto. Retomada nunca cria de novo o que já tem id.
- **Dono do módulo de produto:** Flávio. Dúvida sobre o contrato da issue ou a escada de pontos vai para ele.
