# vanta. produto

O motor do documento, do visual e das issues de um projeto, mais o esboço para o formato que ainda não existe. Skills ligadas por arquivos, o `projeto.json` e o `plano.json`, uma que explora formatos, e uma **camada** que carrega tudo o que é de uma empresa.

```
fontes ──► documento-de-projeto ──► Google Doc
                  │
                  ▼
            projeto.json ──► visual-de-projeto ──► canvas (4 pranchas)
                  │
                  ▼
  Doc aprovado + projeto.json ──► plano-no-linear ──► plano.json ──(ok de quem roda)──► issues no gestor

        camada/  (camada.json, esqueleto.md, tokens.json, templates.json)  alimenta todas

pedido sem formato claro ──► esboco ──► 2 a 3 direções no canvas ──► escolha ──► prancha final
                               │                                                    │
                               └──── registro de esboços (jsonl, fora do plugin) ◄──┘
                                     2ª vez do mesmo formato: propõe template
```

| Skill | O que faz | Entrada |
|---|---|---|
| `documento-de-projeto` | Levanta as fontes com subagentes, entrevista só sobre as lacunas e gera o Google Doc do projeto, mais o `projeto.json` validado | Nome ou id do projeto, ou uma frase de intenção |
| `visual-de-projeto` | Monta o canvas (tipo Design) com 4 pranchas: Conceito, Capacidades, Roadmap e Hipóteses | Um `projeto.json`, um Google Doc ou .docx existente, ou um projeto do gestor de tarefas |
| `plano-no-linear` | Do plano aprovado às issues: confere por subagente o que já existe nos repositórios, propõe issues por interface (tabela com milestone, título, teste principal, pontos e responsável sugerido), pergunta o que as fontes não decidem e só cria no gestor depois do ok, com dependências ligadas e relatório | O Google Doc aprovado, o `projeto.json` e o projeto no gestor de tarefas, com milestones e lead |
| `esboco` | Modo exploratório: gera 2 a 3 direções de organizar o mesmo conteúdo, lado a lado num canvas, pergunta qual seguir (ou qual mistura), constrói a escolhida na prancha final e registra o formato | Um pedido de material cujo formato ainda não está claro |

Regra das três: número, nome, data ou cliente sem fonte não entra. Vira `lacunas[]` e aparece no canvas. A `plano-no-linear` acrescenta uma: ninguém é atribuído sem ordem explícita, e nada é criado antes do ok.

## A camada

O motor não sabe nada de nenhuma empresa. O que é de uma empresa mora numa pasta com contrato fixo, que a skill recebe.

| Arquivo | Obrigatório | Contrato |
|---|---|---|
| `camada.json` | sim | [`schema/camada.schema.json`](schema/camada.schema.json) |
| `tokens.json` | não | [`schema/tokens.schema.json`](schema/tokens.schema.json). O que faltar vem de [`tokens-padrao.json`](skills/visual-de-projeto/tokens-padrao.json) |
| `esqueleto.md` | não | tabela "As seções" mais as regras de [`esqueleto-padrao.md`](skills/documento-de-projeto/referencias/esqueleto-padrao.md). Sem ele vale o esqueleto padrão |
| `templates.json` | não | [`schema/templates.schema.json`](schema/templates.schema.json): a lista de templates da empresa. Validado pelo `validar-camada.mjs` |

**Campos do `camada.json`:**

| Campo | O que é |
|---|---|
| `versao` | sempre `1` |
| `empresa.nome` | a empresa dona do projeto: dado de outra empresa não entra no levantamento |
| `empresa.rotulo_canvas` | texto curto que abre o kicker e o rodapé das pranchas (opcional) |
| `escrita.travessao_proibido`, `idioma`, `regras` | traço longo e meia-risca reprovados (ou não), idioma, regras em prosa para os subagentes |
| `marca.regra_texto` | a regra de grafia em prosa, que abre o prompt de cada subagente |
| `marca.preservar_caixa` | palavras de marca que a caixa alta do canvas mantém na grafia certa |
| `marca.reprovar[]` | `padrao` (regex), `ignorar_caixa`, `mensagem`: o texto que casa é reprovado |
| `marca.normalizar[]` | `padrao`, `ignorar_caixa`, `para`, `aceitar[]`: a variante vira `para`; o que casa e não está em `aceitar` é reprovado |
| `areas[]` | `nome`, `cor`, `padrao`, `vence_no_prefixo`: tabela área ou produto para a cor de acento |
| `acento_padrao` | cor quando nenhuma área casa |
| `fontes.linear`, `granola`, `slack` | `habilitada`, `servidor` (prefixo das ferramentas MCP), `servidor_alternativo`, `proibido[]`, `como` |
| `gestor` | opcional, para a `plano-no-linear`: `servidor` do MCP (nulo: vale `fontes.linear.servidor`), `servidor_alternativo` (nulo: vale `fontes.linear.servidor_alternativo`; só quando o servidor escolhido não existe na sessão, com o workspace confirmado antes de escrever), `proibido[]`, `time`, `estado_inicial` (padrão Backlog), `escada_pontos` (padrão 1, 2, 3, 5, 8), `teto_pontos` (padrão 5, precisa estar na escada), `contrato_campos` (os onze rótulos da descrição, em ordem), `termos_mecanismo[]`, `labels[]`, `quem_atribui`. Sem o bloco valem os padrões neutros |
| `fontes.drive` | `habilitada`, `cli` (ex.: gws), `conta_dominio`, `servidor` (o conector Google Drive que a skill usa quando o `cli` não está no PATH: cria o Doc, mas não troca o conteúdo de um Doc existente), `como` |
| `fontes.locais` | `habilitada`, `pastas[]` fixas, `marcadores[]` que denunciam um vault de notas na raiz de um repositório |
| `documento.nome_arquivo` | padrão do nome do Google Doc, com `{produto}`, `{nome}`, `{versao}`, `{data}` |
| `documento.pasta_drive_id` | pasta do Drive de destino (nulo: raiz do Drive de quem roda) |
| `canvas.type_url` | link do tipo Design de Artifact da conta (nulo: a skill descobre) |
| `esbocos.registro` | arquivo `.jsonl` do registro de esboços, fora do cache do plugin (`~` vale a pasta do usuário). Nulo: `~/.config/vanta-produto/esbocos.jsonl` |
| `esbocos.similaridade_minima` | de 0,1 a 1: pontuação a partir da qual duas estruturas são "formato parecido" (padrão 0,6) |

**`templates.json`** é `{ "versao": 1, "templates": [...] }`. Cada template tem o nome pelo que entrega:

| Campo | O que é |
|---|---|
| `nome` | nome pelo que o template entrega, único na lista |
| `entrega` | o que sai dele, em uma frase |
| `skill_do_motor` | a skill do motor que o produz (pasta em `skills/`), ou `null` quando ainda não há |
| `etapa` | etapa do fluxo (número), um rótulo como `transversal`, ou `null` |
| `estado` | `pronto` (exige skill), `em esboço`, `a trazer` ou `a construir` |
| `estrutura` | opcional: os blocos do molde. É o que o esboço usa para reconhecer um template nascido dele |

O validador confere o contrato, nome único, que a skill existe no motor, que `pronto` tem skill e a regra de escrita e de marca da camada nos textos.

Nos padrões, `{{ANTES}}` expande para o prefixo que deixa URL, caminho, e-mail e `#hash` de fora. Os padrões rodam em JavaScript (validador, montador) e em Python (`gerar-doc.py`, com `re.ASCII`): fique na sintaxe comum, sem grupo nomeado. Para um produto com sufixo (`Produto+`), escreva duas regras em ordem, a do sufixo primeiro e a sem sufixo com `(?!\s?\+)`; o exemplo faz isso.

**Como a skill acha a pasta**, na ordem: `--camada <pasta>`, a variável `VANTA_CAMADA`, `./camada/` e `camada/` ao lado do arquivo de entrada (ou na pasta acima dele). Sem camada, o motor roda no padrão neutro e **sem regra de marca**, e diz isso.

Exemplo completo e fictício: [`exemplos/camada-exemplo/`](exemplos/camada-exemplo/).

## Tokens visuais

Os moldes não têm cor, fonte nem marca no código. Leem CSS variables (`--vp-fonte-titulo`, `--vp-texto`, `--vp-borda`, `--vp-raio`...) que o `montar-canvas.mjs` injeta de `tokens.json`, mais as palavras de marca que a caixa alta preserva e o `titulo_largura_char` que calibra o medidor. O padrão do motor é neutro: system-ui, cinzas, acento `#7C3AED`.

## Contrato

O `projeto.json` (v1) está em [`schema/projeto.schema.json`](schema/projeto.schema.json). Dois exemplos em `exemplos/projeto/`: `vazio.json` (listas vazias, estado vazio explícito) e `completo.json` (projeto fictício, rotulado como exemplo).

O `plano.json` (v1), a proposta de issues da `plano-no-linear`, está em [`schema/plano.schema.json`](schema/plano.schema.json). Cada issue traz o contrato de onze campos (`modo`: direto, entrevista, brainstorming ou pesquisa; `fluxo`; `repos[]`; `pode_mexer_em[]`; `resultado`; `entrega[]`, o checklist; `teste_principal`, abro X, faço Y, vejo Z; `portao`; `fora`; `se_nunca_for_feita`; `contexto`), mais `id_local`, `titulo` (`<Superfície>: <o que o usuário faz>`), `milestone`, `pontos`, `responsavel` (só com `responsavel_autorizado` e `autorizado_por`), `responsavel_sugerido`, `bloqueia[]` e `relacionada[]`. Fora das issues: `ref`, `milestones[]` como o gestor devolve (ou `novo: true`, quando a proposta inclui criar projeto e milestone, só depois do ok), `conferencia[]` (estado, `repo`, `caminho:linha` e SHA), `nao_viram_issue[]` e `lacunas[]`. Exemplo fictício em `exemplos/plano/completo.json`.

## Scripts (Node, sem dependências; Python 3 só o que usa o gws)

```bash
node scripts/validar-camada.mjs <pasta da camada>                          # exit 0, ou lista de erros
node scripts/validar-projeto.mjs <projeto.json> [--camada <pasta>]         # exit 0, ou lista de erros e exit 1
node scripts/fontes-do-levantamento.mjs disponiveis --camada <pasta> --na-sessao <servidores>   # fontes que a sessão alcança (servidor ou alternativo); `gestor` dá o servidor de escrita da plano-no-linear; também ler, incluir, remover, caminho
node scripts/medir-pranchas.mjs <projeto.json> [--camada <pasta>]          # altura estimada por prancha e plano de quebra
node scripts/montar-canvas.mjs <projeto.json> "<título>" <pasta> [--camada <pasta>]   # monta project/ pronto para publicar
node scripts/validar-plano.mjs <plano.json> [--camada <pasta>]             # exit 0, ou lista de erros e exit 1
node scripts/descricao-issue.mjs <plano.json> [--id <id_local>] [--json | --estrutura] [--camada <pasta>]   # descrição de cada issue, no formato do contrato (--estrutura: projeto e milestones novos)
node scripts/montar-esboco.mjs <esboco.json> <pasta> [--camada <pasta>]    # monta o canvas do esboço (direções e prancha final)
node scripts/esbocos.mjs consultar|registrar|promover|comparar ...         # registro de esboços e templates em esboço
python3 -I skills/documento-de-projeto/scripts/gerar-doc.py <doc.md> --html <doc.html> [--camada <pasta>] [--subir --nome ...]
python3 -I skills/documento-de-projeto/scripts/gerar-doc.py <doc.md> --html <doc.html> --atualizar <docId> [--nome ...]   # troca o conteúdo do mesmo doc, sem cópia; recusa versão menor
node scripts/conferir-versao.mjs conferir <projeto.json> [--doc doc.md] [--canvas dados/projeto.json] [--linear texto.txt] [--drive arquivo.json]   # doc, mapa, Linear e Drive na mesma versão (grave o arquivo do Drive com `gws ... 2>/dev/null`, não `2>&1`)
node scripts/conferir-versao.mjs bloco <projeto.json>                      # a linha do documento para a descrição do projeto no Linear
python3 -I scripts/docx-para-texto.py <arquivo.docx>
```

O teto de uma prancha no canvas é 8000 px. O medidor aponta a quebra antes de publicar: o canvas corta sem aviso. O medidor lê o `projeto.json`, então no esboço não há medidor: a altura vem da captura (que vence qualquer estimativa), e o montador recusa `h` acima do teto.

## O esboço e o registro

A skill `esboco` pergunta a escolha entre direções, não entre cores: cada direção muda a ordem, o foco ou o que abre o material. Para material de produto ou de processo o leitor é visual por padrão (`leitor` do `esboco.json`, que só vira `textual` se quem pediu declarou): cada direção declara um **elemento visual dominante** (`fluxograma`, `diagrama-de-blocos`, `linha-do-tempo`, `matriz`, `grafico`, `mapa-de-jornada` ou `amostras-de-design`), cada bloco declara o seu `visual` (`texto` é o que só apoia) e as direções diferem no dominante, não só na ordem dos blocos. O montador reprova direção sem bloco visual, sem dominante, com dominante repetido, gráfico sem `fonte` e fragmento sem `<svg>`.

Depois da escolha, o formato vai para o registro (`esbocos.jsonl`, uma linha por esboço: `{versao, data, empresa, pedido, leitor, direcao: {rotulo, nome, privilegia, visual_dominante}, estrutura, visuais, canvas}`), fora da pasta do plugin para sobreviver à atualização. Cada empresa só lê as próprias linhas. Linha antiga, sem `visuais`, continua valendo.

**Formato parecido** é decidido pela estrutura (a lista ordenada de blocos), não pelo texto do pedido: dois blocos casam quando as palavras deles, sem acento, caixa, artigo e plural, se parecem pelo menos 50%. A pontuação é 0,7 x (blocos casados / blocos distintos nas duas listas) + 0,3 x (fração dos casados na mesma ordem), multiplicada por 0,4 + 0,6 x (fração dos casados com o mesmo elemento visual) quando os dois lados têm visuais, e vale como parecido com 0,6 ou mais e ao menos 3 blocos em comum: mesmos blocos com visuais diferentes não são o mesmo formato. Na segunda ocorrência o esboço propõe promover o formato a template (nome, molde, contrato) e, com o OK, lista-o em `templates.json` com estado `em esboço`.

## Testes

```bash
python3 -m unittest discover -s plugins/vanta-produto/tests
```

Cobrem a camada (contrato, achado da pasta e bloco `gestor`), o `templates.json`, o validador e o gerador de doc contra a camada de exemplo, o validador do plano e o gerador de descrição de issue, o medidor, os moldes renderizados com tokens neutros e com os da camada de exemplo (nenhuma cor, fonte ou marca residual no código), o registro de esboços (jsonl lido e escrito, isolamento por empresa, formato parecido, segunda ocorrência, promoção), o montador do canvas do esboço, e que o motor não carrega nome de empresa.

## Usar numa empresa

1. Crie a pasta da camada (comece copiando `exemplos/camada-exemplo/`) e valide com `validar-camada.mjs`.
2. Instale o plugin (`claude plugin install vanta-produto@vanta`) e informe a camada: `VANTA_CAMADA=<pasta>` ou `--camada`.
3. Sem instalar o plugin do marketplace, a empresa guarda uma **cópia fixada** do motor (a pasta do plugin) e anota o SHA de origem. Mudança no motor se faz aqui, e a cópia é refeita a partir do novo SHA.
