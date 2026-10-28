# mK Produto

O plugin do fluxo de produto da mK. Cada entrega tem um **template com nome pelo que entrega**: a Ficha do Projeto (etapa 3, priorização de portfólio), o Mapa do Projeto (que atravessa as etapas) e o Esboço, para o formato que ainda não tem molde. Framing (etapa 4) e PRD da Entrega (etapa 5) entram quando forem medidos em uso e se ligam pelo mesmo contrato `projeto.json`.

```
fontes (Linear mK, Granola, Slack, Drive, arquivos locais) ──► Ficha do Projeto ──► Google Doc
                                                                    │
                                                                    ▼
                                                              projeto.json ──► Mapa do Projeto ──► canvas

Ficha aprovada + projeto.json ──► projeto-issues ──► proposta por interface ──(ok)──► issues no Linear mK

pedido sem molde ──► esboco ──► 2 a 3 direções ──► escolha ──► prancha final ──► registro
                                                                     2ª vez do mesmo formato: propõe template
```

## Templates

A lista vive em `camada/templates.json` (contrato `motor/schema/templates.schema.json`, conferido pelo `validar-camada`). Decisão de 20/10/2026: o template ganha o nome pelo que entrega.

| Template | O que entrega | Skill do motor | Skill da mK | Etapa | Estado |
|---|---|---|---|---|---|
| Ficha do Projeto | Google Doc do projeto, com as 13 seções do esqueleto, e o `projeto.json` | `documento-de-projeto` | `ficha-do-projeto` | 3 | pronto |
| Mapa do Projeto | Canvas de 4 pranchas: Conceito, Capacidades, Roadmap e Hipóteses | `visual-de-projeto` | `mapa-do-projeto` | transversal | pronto |
| Painel de Portfólio | Canvas do portfólio, lido do Linear mK | nenhuma | nenhuma | 3 | a trazer |
| Mapa de Processo | Canvas com o desenho de um processo | nenhuma (nasce pelo esboço) | `esboco` | nenhuma | em esboço |
| Linha do Tempo de Fases | Trilha de fases em barras com o bloco "Depois" à direita | nenhuma (SVG pela `esboco`) | `linha-do-tempo` | transversal | em esboço |
| Framing | Documento de framing do projeto | nenhuma | nenhuma | 4 | a construir |
| PRD da Entrega | Documento de requisitos de uma entrega | nenhuma | nenhuma | 5 | a construir |

Estados: `pronto` tem skill do motor; `em esboço` nasceu de um esboço e ainda não tem skill; `a trazer` existe fora do plugin; `a construir` está previsto e nada foi feito.

| Skill | O que faz | Entrada |
|---|---|---|
| `ficha-do-projeto` | Levanta as fontes com subagentes, entrevista só sobre as lacunas e gera o Google Doc da Ficha, mais o `projeto.json` validado | Nome ou id do projeto no Linear mK ("faz a Ficha do 263"), ou uma frase de intenção |
| `mapa-do-projeto` | Monta o canvas (tipo Design) com 4 pranchas | Um `projeto.json`, a Ficha (Google Doc ou .docx) ou um projeto do Linear mK |
| `projeto-issues` | Do projeto aprovado às issues no Linear mK (time Product): confere o que já existe nos repositórios, propõe as issues por interface, pergunta o que as fontes não decidem e só cria depois do ok, cada uma com o contrato de onze campos, pontos de 1 a 5 e dependências | A Ficha do Projeto (Google Doc), o `projeto.json` e o projeto no Linear mK ("quebra o projeto de leads no Linear") |
| `esboco` | Gera 2 a 3 direções de organizar o mesmo conteúdo, pergunta a escolha, constrói a escolhida e registra o formato. Na segunda vez do mesmo formato, propõe virar template | Um pedido de material cujo formato ainda não está claro |
| `linha-do-tempo` | Monta a linha do tempo de fases com o bloco "Depois", lendo `fases[]` e `roadmap.marcos` do `projeto.json` e as cores da camada. Sem data real, escreve "a definir" | Um `projeto.json`, a Ficha ou um projeto do Linear mK ("faz a linha do tempo do 350") |

As skills são finas: apontam para o motor e para a camada, e só dizem o que é da mK (dono do módulo, etapa do fluxo, regras de cor por área). Regra das três: número, nome, data ou cliente sem fonte não entra. Vira `lacunas[]` e aparece no canvas.

## Instalação (quem é do time e não tem o login do David)

Tudo abaixo é na sua máquina, com a sua conta. Nada depende de credencial do David nem de conta no GitHub. O marketplace do repositório público `metaKosmos/mk-plugins` se chama `mk-plugins`, e o mK Produto é um plugin dele.

**1. Confira o que você já tem.**

```bash
claude plugin marketplace list     # procure "mk-plugins"
claude plugin list                 # procure mk-produto e mk-linear
```

Se o `mk-produto` já aparece como `enabled` (inclusive com `Scope: managed`, instalado pela organização), pule para o passo 4. Se ele veio do marketplace antigo `metakosmos` (repositório `metaKosmos/harness-dev`), desinstale com `claude plugin uninstall mk-produto@metakosmos` e `claude plugin uninstall mk-linear@metakosmos` antes de seguir.

**2. Adicione o marketplace.** O repositório é público: não precisa de conta no GitHub nem de `gh`.

```bash
claude plugin marketplace add metaKosmos/mk-plugins
```

Já tinha adicionado antes? Traga a versão nova com `claude plugin marketplace update mk-plugins`.

**3. Instale o plugin e recarregue.**

```bash
claude plugin install mk-produto@mk-plugins
claude plugin install mk-linear@mk-plugins
```

O `mk-linear` liga o Linear da mK como servidor na sua máquina, com o login guardado só nela. Use-o quando a sua conta do claude.ai for compartilhada ou quando você não quiser deixar o Linear nos conectores. Sem ele, a skill usa o conector do claude.ai.

Depois, na caixa de prompt do Claude Code, digite `/reload-plugins` e em seguida `/mcp`: escolha `linear-mk` e entre com a sua conta do Linear da mK. `claude plugin list` precisa mostrar `mk-produto` e `mk-linear` como `enabled`.

**4. Conecte os conectores do claude.ai.** Em claude.ai, Configurações, Conectores, conecte com a conta da mK (`@metakosmos.com.br`):

| Conector | Para que o mK Produto usa | Sem ele |
|---|---|---|
| Linear (plugin `mk-linear` ou conector) | levantar o projeto e criar as issues (`projeto-issues`), só no workspace metaKosmos | a fonte vira "não verificável daqui" e nenhuma issue é criada |
| Google Drive | ler e gerar a Ficha do Projeto, na conta `@metakosmos.com.br` | sem ele e sem o `gws`, a Ficha não chega ao Drive; com o conector, o Doc é criado, mas as versões seguintes pedem o `gws` |
| Granola e Slack | levantar o que foi dito sobre o projeto | a fonte vira "não verificável daqui" e a skill segue com as outras |

O conector Linear do claude.ai, usado quando o `mk-linear` não está instalado, enxerga todos os workspaces da sua conta. A skill confere com `get_workspace` que ele responde pelo metaKosmos (`linear.app/metakosmos`) antes de ler ou escrever, e para se for outro. Se o conector pedir login, conclua pelo `/mcp` dentro do Claude Code.

**5. `gws`: opcional para criar, necessário para atualizar.** Com o CLI `gws` autenticado na conta `@metakosmos.com.br` (`gws auth status`), a Ficha é criada e atualizada no Drive por ele. Sem o `gws`, o documento é criado pelo conector Google Drive do claude.ai (`fontes.drive` em `camada/camada.json`), mas o conector não atualiza o conteúdo: as versões seguintes precisam do `gws`, ou você cola o conteúdo à mão no mesmo Doc. Se só vai criar a primeira versão, não precisa instalar o `gws`.

**6. Confira.** Abra o Claude Code numa pasta qualquer e peça: "faz a Ficha do projeto de captação e gestão de leads". Antes de levantar, a skill mostra a tabela das fontes que a sua sessão alcança (Linear, Granola, Slack, Drive, arquivos locais) e pergunta quais valem para o projeto. Linear aparecendo como disponível pelo conector do claude.ai é o esperado na sua máquina. Fonte ausente fica "não verificável daqui", e a skill segue.

Para quebrar o projeto em issues depois da Ficha aprovada: "quebra o projeto de leads no Linear". A skill propõe as issues por interface e só cria depois do seu ok.

Dúvida ou travou num passo: Flávio, dono do módulo de produto.

## Estrutura

| Pasta | O que é |
|---|---|
| `motor/` | Cópia fixada do plugin `vanta-produto`: skills genéricas, schema, scripts, moldes e testes. Não é plugin aninhado (sem `.claude-plugin`). Não se edita aqui |
| `camada/` | O que é da mK: `camada.json` (grafia, cores por área, fontes do levantamento, `gestor` do Linear, nome do arquivo, tipo Design, registro de esboços), `tokens.json` (vocabulário claro do mK Orbit), `esqueleto.md` (13 seções) e `templates.json` (a lista de templates) |
| `skills/` | `ficha-do-projeto`, `mapa-do-projeto`, `projeto-issues` e `esboco`, que chamam o motor com a camada |
| `scripts/sincronizar-motor.sh` | Atualiza `motor/` a partir de um clone do vanta-plugins |

## De onde vem o motor

`motor/ORIGEM.json` registra o repositório, o caminho, o SHA e a versão de origem e a data da cópia. O motor é do VANTA (214); a mK usa uma cópia, então o time não precisa de acesso ao marketplace da 214. Decisão de 20/10/2026.

Corrigir o motor exige duas PRs: uma no vanta-plugins e outra de sincronização aqui. Sem a sincronização, a mK fica na versão anterior, e o SHA no `ORIGEM.json` mostra a defasagem.

## Como atualizar o motor

```bash
scripts/sincronizar-motor.sh <clone do vanta-plugins> <ref>
```

O script lista os arquivos que mudam, troca `motor/` pela versão daquele ref e regrava o `ORIGEM.json`. Com o mesmo SHA, a mudança é zero. Depois: valide a camada e rode a suíte do motor.

```bash
node motor/scripts/validar-camada.mjs camada
node motor/scripts/validar-plano.mjs motor/exemplos/plano/completo.json --camada camada
(cd motor && python3 -m unittest discover -s tests)
```

A suíte roda de dentro de `motor/`: um teste confere o comportamento sem camada, e a pasta `camada/` ao lado de `motor/` seria achada pelo caminho padrão.

## Scripts do motor com a camada da mK

```bash
node motor/scripts/validar-projeto.mjs <projeto.json> --camada camada
node motor/scripts/medir-pranchas.mjs <projeto.json> --camada camada
node motor/scripts/montar-canvas.mjs <projeto.json> "<nome do projeto>" <pasta> --camada camada
node motor/scripts/montar-esboco.mjs <esboco.json> <pasta> --camada camada
node motor/scripts/esbocos.mjs consultar|registrar|promover|comparar ... --camada camada
```

## Registro de esboços

Cada esboço escolhido vira uma linha em `~/.config/vanta-produto/esbocos.jsonl` (padrão do motor; `esbocos.registro` no `camada.json` está nulo). O arquivo fica fora da pasta do plugin, então sobrevive à atualização dele, e é uma cópia por máquina. A skill consulta o registro antes de gerar as direções e, se o formato já foi usado, mostra-o como uma das direções. "Formato parecido" é decidido pela estrutura (a lista de blocos), não pelo texto do pedido: pontuação de 0,6 ou mais e ao menos 3 blocos em comum. Detalhe da conta em `motor/README.md`.

## Dono

Flávio é o dono do módulo de produto na mK, incluindo o template de PRD e a priorização com os líderes. Mudança no esqueleto ou no contrato passa por ele.

## Histórico

- **0.4.1:** motor em `c220221` (vanta-produto 0.4.1): sem o `gws`, o Doc da Ficha é criado pelo conector Google Drive do claude.ai (`--via conector`, depois `--registrar`); atualizar o conteúdo continua pedindo o `gws`. Os validadores deixam de sair calados quando o caminho do plugin passa por symlink.
- **0.4.0:** skill `projeto-issues` (issues no Linear mK a partir do plano aprovado) e bloco `gestor` na camada (Product, Backlog, escada 1-2-3-5-8, teto 5, conector do claude.ai como alternativo com o workspace confirmado). Passo a passo de instalação para o time. Motor em `1b721a1` (vanta-produto 0.4.0): `plano-no-linear`, contrato de onze campos, versão do documento, fontes do levantamento escolhidas por sessão, lacunas por comentário no canvas.
- **0.3.2:** moldes do visual buscam o dado sem cache (`cache: 'no-store'`), e há teste que reprova o contrário. Motor em `9d6b7a8` (vanta-produto 0.2.2).
- **0.3.1:** esboço com elemento visual: leitor visual por padrão, elemento visual dominante por direção e `visual` por bloco, e o montador reprova direção só com texto. Acento da camada para material de processo ou interno. Motor em `56d43cd` (vanta-produto 0.2.1).
- **0.3.0:** templates com nome pelo que entregam (`camada/templates.json`). `projeto-doc` vira `ficha-do-projeto` e `projeto-visual` vira `mapa-do-projeto`. Skill nova `esboco`. Motor em `5c758e1` (vanta-produto 0.2.0).
- **0.2.0:** substitui o plugin `mk-projeto` (0.1.0), que tinha o motor e a camada juntos. O que era genérico foi para o motor, e o que era da mK ficou em `camada/`.
