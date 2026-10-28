---
name: documento-de-projeto
description: Monta o documento de projeto como Google Doc nativo, com tabelas reais, e grava o projeto.json que alimenta a skill visual-de-projeto. Levanta o gestor de tarefas, reuniões, Slack, Drive e arquivos locais em paralelo por subagentes, entrevista só sobre o que as fontes não responderam e nunca inventa dado. Tudo o que é de uma empresa (marca, áreas, fontes habilitadas, esqueleto, nome do arquivo) vem de uma camada, uma pasta com contrato fixo. Use quando pedirem para criar, organizar ou começar o documento de um projeto ("monta o doc do projeto X", "documento do projeto P-123", "organiza esse projeto antes de ir para o gestor de tarefas"), mesmo que só digam o id ou uma frase de intenção.
---

# documento-de-projeto

O processo de produto começa num documento de projeto e continua no gestor de tarefas. Esta skill faz o primeiro passo: levanta as fontes, entrevista e gera o Google Doc. O desdobramento em issues vem depois, a partir do doc, e **não faz parte** desta skill. O visual do projeto é a skill `visual-de-projeto`, que lê o `projeto.json` que esta skill grava.

A skill é genérica. O que é de uma empresa mora na **camada**.

## A camada

Uma pasta com contrato fixo (detalhe em `scripts/lib/camada.mjs` e em `schema/camada.schema.json`):

| Arquivo | Para que serve |
|---|---|
| `camada.json` | obrigatório: nome da empresa, grafias de marca (regex que reprova e que normaliza), tabela área para cor de acento, fontes habilitadas e como acessá-las, padrão do nome do arquivo e pasta do Drive |
| `esqueleto.md` | as seções do documento. Sem ele vale `referencias/esqueleto-padrao.md` |
| `tokens.json` | tokens visuais (usado pela `visual-de-projeto`) |

**Como achar a pasta**, na ordem: o caminho que quem chamou informou, a variável `VANTA_CAMADA`, `./camada/` no diretório atual, `camada/` ao lado da pasta de trabalho ou na pasta acima dela. Achou: **diga a quem roda** numa linha ("camada: <pasta>, empresa <nome>") e valide com `node "${CLAUDE_PLUGIN_ROOT}/scripts/validar-camada.mjs" <pasta>` (exit 0 é obrigatório). Não achou: pare e diga que falta a camada e como informá-la; não improvise marca, fontes nem esqueleto. Exemplo completo e fictício em `${CLAUDE_PLUGIN_ROOT}/exemplos/camada-exemplo/`.

## Entrada

Nome ou id do projeto no gestor de tarefas, ou uma frase de intenção quando o projeto ainda não existe. Opcional: a pasta de trabalho. Sem ela, use `./projeto/<slug-do-projeto>/` no diretório atual e crie. Opcional: uma ou mais pastas locais com o que já foi registrado do projeto (um vault de notas, um repo de registros), que viram a quinta fonte, "Arquivos locais". Opcional: o caminho da camada.

Arquivos que a skill grava na pasta de trabalho:

| Arquivo | O que é |
|---|---|
| `dossie.md` | resultado da etapa A |
| `entrevista.md` | a entrevista da etapa B, uma entrada por pergunta (pergunta, resposta, quem, data) |
| `doc.md` | o documento em Markdown (etapa C) |
| `doc.html` | o HTML gerado, que o Drive converte |
| `projeto.json` | contrato para a `visual-de-projeto` (etapa D) |

## Referências (leia antes de começar)

- **O esqueleto em vigor**: `esqueleto.md` da camada, ou `referencias/esqueleto-padrao.md`. Define as seções, quais são obrigatórias, o que cada uma alimenta no JSON, o formato de citação e as regras de fonte.
- `referencias/levantamento.md` (ao lado deste arquivo): o prompt pronto de cada subagente de fonte, o formato do extrato e o do dossiê.

Caminhos: o plugin é `${CLAUDE_PLUGIN_ROOT}`. Se a variável vier vazia, é o diretório dois níveis acima deste arquivo (`<dir deste SKILL.md>/../..`). Os scripts são `<plugin>/skills/documento-de-projeto/scripts/gerar-doc.py` e `<plugin>/scripts/validar-projeto.mjs`.

## Regras que valem em todas as etapas

1. Número, nome de pessoa, nome de cliente, data e valor sem fonte não entram no doc nem no JSON. Viram lacuna.
2. Fonte inacessível é "não verificável daqui", com o motivo, e a skill segue. Nunca "não existe". 404 do Google não é id errado: é arquivo que existe e não foi compartilhado.
3. O resumo automático de reunião às vezes inverte quem deve a entrega. Dono de entrega só vale se conferido na transcrição.
4. **Só a empresa da camada.** Use apenas os servidores e as contas que `camada.json` indica para cada fonte (`servidor` e, na falta dele na sessão, `servidor_alternativo`, seguindo o `como`), mais as fontes extras que quem roda escolheu no chat (etapa A, passo 2), e nunca os que a camada lista em `proibido`. Dado de outra empresa da pessoa que roda a skill não entra, e isso vale também para arquivos locais: um vault pode guardar várias empresas, e só o trecho que cita o projeto ou a empresa dele sobe para o dossiê.
5. A skill só lê as fontes. Não cria issue, não envia mensagem, não compartilha o Doc, não publica canvas, e não escreve no Linear: entrega a linha do documento para o projeto (`conferir-versao.mjs bloco`) e a conferência, e gravar a linha no projeto do Linear é da sincronização.
6. Escrita e marca: as da camada (`escrita`, `marca.regra_texto`). O `gerar-doc.py` normaliza e reprova o que a camada define, e o `validar-projeto.mjs` faz o mesmo no JSON.
7. **Formato único de citação da entrevista:** `decisão de <Nome>, entrevista de DD/MM/AAAA`. É fonte, não vira lacuna. A mesma forma vale no doc e no JSON, e nenhuma outra (nada de "David, 19/10" nem data ISO).
8. Decisão registrada em arquivo local (ADR ou registro de sessão) é fato com fonte, citada com caminho:linha e a data do registro, e **não vira pergunta**. **Decisão dita em transcrição de reunião** (conferida na transcrição, não só no resumo) conta do mesmo jeito: fonte com a reunião, a data e o trecho literal, e **não vira pergunta**. Se um registro contradiz outra fonte, vai para as contradições com a data de cada lado, e a mais recente é a recomendação, salvo indicação contrária no próprio registro. Documento que a busca não achou é "não localizado nas pastas lidas", nunca "não encontrada" nem "não existe".
9. **Premissa contra fonte.** Quando a premissa de quem responde a entrevista contradiz uma fonte, **não decida sozinho**: registre a contradição no doc, na tabela de contradições da seção de lacunas, com as duas versões, cada uma com fonte e data (a da entrevista: `decisão de <Nome>, entrevista de DD/MM/AAAA`), e quem resolve. O texto das outras seções segue a versão que tem fonte documental e marca a divergência com "(ver contradição Cn)".
10. **Autor do documento é quem roda a skill**: o nome informado no pedido ou o da conta autenticada. Nunca o dono do projeto nem o autor de uma fonte.

11. **Um documento por projeto, atualizado no lugar.** O doc de um projeto é um arquivo só no Drive: versão nova troca o conteúdo do mesmo arquivo (mesmo link) e nunca cria cópia. A versão sai do título (`<data> · <autor> · v<N>`, a mesma do nome do arquivo) e o mapa e o Linear citam o mesmo link e a mesma versão. A etapa C diz como, e a D grava o bloco `documento` no `projeto.json`.

## Etapa A: levantamento

1. Ache e valide a camada (acima). Crie a pasta de trabalho. Monte `{{TERMOS}}`: nome do projeto, id, sinônimos óbvios, produto ou área envolvida e qualquer cliente ou pessoa que a entrada já cite.
2. **Escolha das fontes, no chat, antes de disparar qualquer subagente.** A lista padrão é a da camada; quem roda a ajusta, e a sessão nunca instala nem autentica fonte.
   - **Veja o que a sessão alcança.** Liste os servidores MCP que a sessão enxerga (prefixo das ferramentas, adiadas inclusive) e rode `node "${CLAUDE_PLUGIN_ROOT}/scripts/fontes-do-levantamento.mjs" disponiveis --camada <pasta> --na-sessao <prefixos separados por vírgula>`. Ele diz, por fonte habilitada e por fonte extra já salva, se está disponível e qual servidor vale. **Linear é disponível quando `servidor` ou `servidor_alternativo` responde**; a lista mostra qual será usado, e o alternativo só lê depois de confirmar o workspace (ver `como`). Fonte que nenhum servidor alcança é "não alcançável": entra no dossiê como "não verificável daqui" e a skill segue.
   - **Mostre a lista a quem roda** em tabela curta (fonte, estado, servidor) e pergunte duas coisas, de uma vez: quais dessas fontes valem para este projeto (as ausentes ficam como não verificáveis; as que a pessoa dispensar viram "não aplicável: dispensada por quem roda"), e se ela quer incluir uma fonte extra que tem (por exemplo, o Fathom). Sem AskUserQuestion, use as fontes padrão e as extras já salvas, e diga numa linha que a lista não foi confirmada.
   - **Fonte extra nova**: confirme o nome e o prefixo do servidor (os que a sessão mostra, por exemplo `mcp__claude_ai_Fathom__`) e grave com `fontes-do-levantamento.mjs incluir --camada <pasta> --nome <nome> --servidor <prefixo>`. A escolha fica na máquina de quem roda, fora do plugin (`fontes-do-levantamento.mjs caminho` diz onde), por empresa, e vale nos próximos levantamentos; `remover` desfaz. O script recusa servidor que a camada proíbe. Fonte extra salva que a sessão não alcança é "não verificável daqui", não erro. A fonte extra tem subagente próprio, em `levantamento.md`.
3. **Defina as pastas locais**, se `fontes.locais.habilitada`. Use as que quem roda indicou, depois as de `fontes.locais.pastas`. Sem nenhuma, olhe o diretório atual e, se ele estiver num repositório git, a raiz (`git rev-parse --show-toplevel`): se existir alguma das pastas de `fontes.locais.marcadores`, essa raiz é uma pasta local detectada. Use-a por padrão e **diga isso a quem roda** numa linha ("li o vault em <pasta>, detectado pelas pastas decisions/ e sessions/; diga se não quiser"). Sem pasta indicada, fixa nem detectada, a fonte fica como "não aplicável" no dossiê e a skill segue com as outras. Pasta indicada que não abre é "não verificável daqui", com o erro.
4. **Numa única mensagem**, dispare os subagentes em paralelo (ferramenta Agent), um por fonte habilitada que quem roda manteve e por fonte extra escolhida, e escreva em cada prompt o servidor que o passo 2 definiu ("Servidor a usar: <prefixo>"). O prompt de cada um está em `referencias/levantamento.md`: copie as "Regras comuns" e o bloco da fonte e preencha os campos da tabela do arquivo (`{{EMPRESA}}`, `{{ACESSO}}` com o bloco da fonte na camada, `{{ESQUELETO}}`, `{{OBRIGATORIAS}}` e os demais). Não resuma os prompts: eles carregam as regras anti-invenção.
5. Quando todos voltarem, monte `dossie.md` no formato de `levantamento.md`: fatos agrupados por seção do esqueleto (F1, F2...) com fonte, lacunas por seção, contradições e não verificável. Carimbe o `ref:` com a data de hoje no cabeçalho. A tabela de fontes registra **quais pastas locais foram lidas e quais não estavam acessíveis** (não verificável daqui).
6. Termos novos que um subagente achou e outro não buscou: uma segunda rodada curta, só deles, só nas fontes que ainda não os viram. **A segunda rodada local é opcional**: se a primeira já cobriu os ids relacionados que o gestor de tarefas revelou (pai, filho, absorvido, duplicado), dispense-a e **diga no dossiê** ("Segunda rodada local: dispensada, a primeira cobriu os ids relacionados (<lista>)"). Se faltou algum id, faça-a só para ele e diga também.
7. Cruze os extratos antes de promover qualquer lacuna a pergunta: o fato pode estar numa fonte que outro subagente leu, e decisão registrada em arquivo local ou dita em reunião já responde a lacuna.
8. Subagente que falhou ou voltou vazio por erro de ferramenta: registre a fonte como "não verificável daqui" com o erro exato e continue. Uma fonte fora do ar não para a skill.

## Etapa B: entrevista (método do grilling, adaptado)

Método de `mattpocock-skills:grilling` (se a skill existir; senão, o que segue basta): rodadas de perguntas numeradas, cada uma com resposta recomendada, até a fronteira esvaziar. Adaptações desta skill:

- **Só pergunta o que o dossiê não respondeu.** Fato que está em reunião, thread, issue ou documento nunca vira pergunta. O que existe com fonte vai direto para o doc.
- **Quem pergunta é o que falta numa seção obrigatória** (as marcadas no esqueleto), mais contradições que só o dono do projeto resolve.
- **Antes de perguntar, confira os arquivos locais e as transcrições.** Se a decisão que a pergunta pediria já está registrada em ADR ou registro de sessão, numa proposta em disco ou dita numa reunião (transcrição), não pergunte: cite no doc, com caminho:linha e a data do registro, ou com a reunião, a data e o trecho. Pergunta só sobrevive se a busca foi feita e não achou, ou se achou registros que se contradizem sem um deles declarar que vale (aí a pergunta mostra os dois lados, com as datas, e recomenda o mais recente).
- **Fatos são trabalho seu, decisões são de quem responde.** Se a lacuna se resolve lendo outra fonte, mande um subagente buscar. Pergunte só o que é decisão ou conhecimento que não está escrito em lugar nenhum.

### O arquivo `entrevista.md`

**Antes de perguntar qualquer coisa, leia `<pasta de trabalho>/entrevista.md` se ele existir** (reexecução ou retomada): pergunta já respondida não se repete, e a resposta de lá é fonte. Cada resposta nova é gravada no arquivo **na hora**, uma entrada por pergunta:

```
## Q3 - título curto
- Data: DD/MM/AAAA
- Quem respondeu: <Nome>
- Pergunta: <o corpo da pergunta>
- Recomendada: <a resposta recomendada, com o porquê>
- Resposta: <o que a pessoa respondeu, literal>
- Citação: decisão de <Nome>, entrevista de DD/MM/AAAA
```

A resposta "registrar como lacuna" também entra (`Resposta: registrar como lacuna`) e vira item da seção de lacunas. Os ids Q1, Q2... são contínuos entre rodadas e entre execuções.

Como conduzir:

1. Da tabela "Lacunas por seção" do dossiê, menos o que `entrevista.md` já respondeu, monte a **fronteira**: as perguntas cuja resposta não depende de outra pergunta ainda aberta. Pergunta que depende de outra espera a rodada seguinte.
2. Cada pergunta tem: número, título curto, o corpo e a **resposta recomendada**. A recomendação sai da evidência do dossiê (a fonte mais recente, o dono mais citado, o valor mais comum). Quando não há base para recomendar, a recomendada é "Registrar como lacuna e seguir". Redija de modo que "sim" aceite a recomendação.
3. **Mande por AskUserQuestion, até 4 perguntas por chamada.** Cada pergunta: texto "Q3 - título: corpo", 2 a 4 opções, a recomendada primeiro e com "(Recomendado)" no rótulo, as outras vindas do dossiê (por exemplo os dois lados de uma contradição) e a opção de registrar como lacuna. "Outro" já existe. Se a fronteira tiver mais de 4 perguntas, divida em chamadas seguidas da mesma rodada.
4. Grave cada resposta em `entrevista.md` (formato acima), com a citação já escrita.
5. **Recalcule a fronteira com as respostas, e confira cada resposta contra o dossiê:** resposta cuja premissa contradiz uma fonte não é aceita calada (regra 9). Resposta nova pode abrir pergunta nova. Repita até a fronteira esvaziar.
6. Termina quando toda seção obrigatória tem conteúdo com fonte ou lacuna registrada. Feche com uma última pergunta de confirmação ("Gero o doc com isto?", recomendada "Sim, gerar"). Não gere o documento antes da confirmação.

Perguntas que quase sempre sobram, quando o dossiê não as responde: hipóteses e a métrica de cada uma, o critério de pronto, o que está fora de escopo, quem é o dono e o prazo final, e quem revisa. Pasta do Drive de destino só se o dossiê achou uma pasta do projeto e a camada não fixa `documento.pasta_drive_id`.

### Quando você roda dentro de um subagente sem AskUserQuestion

Cheque com `ToolSearch` (`select:AskUserQuestion`). Se a ferramenta não existe, ninguém pergunta por você: faça a conta da fronteira (depois de ler `entrevista.md`, se existir) e siga **um** destes dois caminhos.

**Sobrou pergunta.** Pare depois da etapa A e devolva à sessão que te chamou, nesta ordem:

1. o caminho do `dossie.md` e um resumo de 5 linhas (fontes consultadas, quais são não verificáveis, quantas lacunas obrigatórias);
2. as perguntas da etapa B, numeradas, cada uma com a resposta recomendada e o porquê (a evidência do dossiê), **no máximo 8** (as que mais mudam o documento; as demais viram lacuna registrada, sem pergunta):

```
**Q1** - **<título>**: <corpo, com as opções quando houver>

Recomendada: <resposta recomendada, e o porquê>

---
```

3. a frase "Aguardo as respostas para seguir da etapa C".

A sessão principal leva as perguntas, agrupa até 4 por chamada, e te devolve as respostas. **O caminho é retomar o mesmo agente por `SendMessage`** com as respostas numeradas: ele mantém o dossiê no contexto e não refaz a etapa A. Chamar a skill de novo com a pasta de trabalho é o plano B, e ele se apoia em `entrevista.md` e `dossie.md`. Ao receber, grave em `entrevista.md` (a sessão que te chamou é quem respondeu: cite o nome que ela informar), **não refaça a etapa A**, recalcule a fronteira (resposta nova pode abrir pergunta nova: devolva essa rodada do mesmo jeito) e, quando a fronteira esvaziar, siga para a etapa C.

**Não sobrou pergunta.** Não pare. Siga direto para a etapa C e a D. A confirmação final ("Gero o doc com isto?") não existe sem a ferramenta: ela vira a seção **"Resumo do que será gerado"** no relatório final (seções do doc, lacunas abertas, contradições registradas, o que veio de entrevista e o que veio de fonte), escrita **antes** de gerar e repetida no relatório.

## Etapa C: documento

1. **Releia `entrevista.md` inteiro** antes de escrever uma linha do documento: toda resposta dada é fonte e entra com a citação do arquivo. Depois escreva `doc.md` seguindo o esqueleto em vigor: título, seções, omitindo seção opcional sem fonte. Use o subconjunto de Markdown do `gerar-doc.py`: `#`, `##`, `###`, parágrafo, lista com `-`, tabela com pipes, `<!-- larguras: 8,52,40 -->` na linha acima de cada tabela (larguras em %, uma por coluna, somando 100), `**negrito**`, `[texto](url)`, `<br>` dentro de célula, `---`. Lista numerada vira marcador no Google Doc: se a ordem importa, escreva o número no texto.
2. Confira antes de gerar: toda afirmação factual tem link, caminho:linha com a data do registro (arquivo local), reunião com data e trecho, ou `decisão de <Nome>, entrevista de DD/MM/AAAA`; dado sem fonte virou "A definir (Ln)" com a lacuna Ln na seção de lacunas; nada de dono vindo só do resumo sem a marca; a seção de hipóteses existe (com a tabela ou com "Sem hipóteses registradas. Lacuna: ..."); toda contradição, inclusive a de premissa contra fonte, está na tabela de contradições com as duas versões e as datas; o autor do título é quem roda a skill.
3. Confira a conta do Google que vai criar o Doc: `gws auth status` (ou o CLI de `fontes.drive.cli`). O Doc nasce na conta autenticada. Se `fontes.drive.conta_dominio` existe e a conta é de outro domínio, pare e avise, em vez de criar fora da organização. **Sem o gws** (`command -v gws` vazio): o caminho é o conector Google Drive (`fontes.drive.servidor`), descrito em "Sem o gws" abaixo; pule esta conferência e confira a conta pelo dono que o próprio `create_file` devolver.
4. Gere o HTML, valide a escrita e suba convertido, num único comando:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/documento-de-projeto/scripts/gerar-doc.py" "<pasta>/doc.md" \
  --camada "<pasta da camada>" \
  --html "<pasta>/doc.html" --subir \
  --nome "<nome do arquivo>" [--pasta <folderId do Drive>]
```

**Nome do arquivo no Drive:** o padrão de `documento.nome_arquivo` da camada (campos `{produto}`, `{nome}`, `{versao}`, `{data}`, data em DD/MM/AAAA). Se quem rodou pediu outro nome, **o pedido vence**: passe-o em `--nome` como veio. **Pasta:** `--pasta` com o que quem rodou indicou; na falta, `documento.pasta_drive_id` da camada; na falta, a raiz.

Saída esperada, uma chave por linha: `lint=ok`, `tabelas_html=N`, `doc_id=...`, `url=https://docs.google.com/document/d/.../edit`, `tabelas_doc=N`, `tabelas_ok=sim`. O código de saída é 0 só se o lint passou e o número de tabelas no Doc é o do HTML. Antes do lint, o script **normaliza a grafia** definida em `marca.normalizar` da camada (no texto, não em URL): cada troca sai em `normalizado=N` com a lista "antes -> depois", e o `doc.md` é regravado igual ao que sobe (o `projeto.json` sai desse texto). O lint reprova o que sobrar de `marca.reprovar`, de `marca.normalizar` fora de `aceitar` e, se a camada pedir (`escrita.travessao_proibido`), traço longo e meia-risca. URL nunca é alterada nem reprovada. Se `lint=FALHOU`, corrija o `doc.md` nas linhas apontadas e rode de novo. Sem camada, o script avisa e só converte.

Erro 5xx transitório do Drive no upload: o script tenta de novo até 3 vezes, com espera curta e crescente, e imprime `tentativas=N` quando precisou. Só falha se as 3 falharem; erro que não é 5xx (auth, 403, 404) falha na hora. Se `tabelas_ok=NAO`, não entregue: abra o Doc, descubra qual tabela se perdeu e refaça o `doc.md`.

O comando equivalente, sem o script, é o que o script executa por baixo (a tabela vira tabela de verdade, com cabeçalho cinza, bordas, larguras e links preservados):

```bash
cd "<pasta>"   # o gws só aceita --upload de dentro do diretório atual
gws drive files create \
  --json '{"name":"<nome do doc>","mimeType":"application/vnd.google-apps.document"}' \
  --upload doc.html --upload-content-type text/html \
  --params '{"fields":"id,name,webViewLink","supportsAllDrives":true}'
```

O Drive converte o HTML em Google Doc nativo no upload (por isso `mimeType` é `application/vnd.google-apps.document`). Para conferir tabelas depois: `gws docs documents get --params '{"documentId":"<id>"}'` e contar os elementos `table` em `body.content`. O gws imprime `Using keyring backend: keyring` antes do JSON: descarte essa linha. Não use `python-docx` nem `pandoc`: não estão instalados na máquina padrão e o caminho por HTML dispensa os dois.

**Reexecução (o projeto já tem doc):** se `<pasta>/projeto.json` existe e traz `documento.id`, ou quem rodou informou o link do doc, **não crie outro arquivo**. Se o projeto também tem canvas, aplique antes os comentários do canvas que resolvem lacunas (seção "Resolver lacunas pelos comentários do canvas" da `visual-de-projeto`), para que o `doc.md` novo e o mapa saiam do mesmo `projeto.json`. Suba com `--atualizar <documento.id>` no lugar de `--subir`, com a versão nova no título do `doc.md` (v1 vira v2) e o `--nome` com a versão nova:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/documento-de-projeto/scripts/gerar-doc.py" "<pasta>/doc.md" \
  --camada "<pasta da camada>" --html "<pasta>/doc.html" \
  --atualizar "<documento.id>" --nome "<nome do arquivo com a versão nova>"
```

Saída esperada, além das chaves do `--subir`: `versao=v2`, `versao_anterior=v1`, `atualizado=sim`, `copia_nova=nao`, e o mesmo `url=` do registro. O script recusa o que repete o erro de 20/10: versão menor que a do arquivo no Drive (exit 4, o doc velho sobrescreveria o novo), título sem versão (exit 2) e `--subir` com `documento.id` já registrado ao lado do `doc.md` (exit 2). **Limite do Drive:** a API não nomeia a versão no histórico do Google Doc (só a interface faz isso). A versão nomeada fica no nome do arquivo e na `description` do arquivo; diga a quem roda que o nome no histórico é manual, se ele quiser.

**Sem o gws: pelo conector Google Drive do claude.ai.** Se quem roda também não tem o conector Google Drive no claude.ai (as ferramentas `create_file` e `update_file` não aparecem), **não há caminho sem o gws**: pare, diga isso e peça que ele autentique o gws ou conecte o Drive no claude.ai. O mesmo comando, sem mudar nada: com `--via auto` (o padrão) o script vê que o gws não está no PATH, valida o texto, gera o HTML e **não sobe**: imprime `via=conector`, `acao=criar`, os parâmetros e `subida=pendente`. A decisão (nome, versão, recusa de cópia quando o projeto já tem doc) é do script; a chamada ao MCP é sua, nesta ordem:

1. Leia o arquivo de `create_file.textContent=@<caminho>` (o `doc.html` inteiro) e chame `create_file` com `title`, `textContent` (o HTML lido), `contentMimeType=text/html` e, se veio, `parentId`. **Não** passe `disableConversionToGoogleType`: o padrão do conector converte HTML em Google Doc. Guarde o `id` e o link (`webViewLink`) da resposta.
2. Se veio `update_file.description`, chame `update_file` com o `fileId` do passo 1 e `description` igual a esse valor (o `create_file` não tem campo de description: a versão entra por aqui).
3. Conte as tabelas do Doc criado com `read_file_content` do `fileId`. O conector mostra cada tabela com uma linha de cabeçalho vazia (`|  |  |`), a linha separadora e só depois as linhas da tabela. **Cada bloco de linhas com pipe sem linha em branco no meio é uma tabela, não duas**: a linha vazia do começo não abre uma tabela nova. Exemplo, uma tabela só:

```
|  |  |
| --- | --- |
| Campo | Valor |
| Dono | Pessoa Exemplo |
```

Duas tabelas são dois blocos separados por texto ou linha em branco. Se não der para contar com segurança, não passe a contagem. Depois rode o mesmo comando com `--registrar --doc-id <id> --url <link como o conector devolveu> [--tabelas-doc N] --nome "<nome>" --gravar-drive "<pasta>/drive.json"`. Saem `doc_id=`, `url=`, `versao=` e `tabelas_ok=` (`nao_verificavel` quando você não passou a contagem: abra o link e confira as tabelas a olho antes de entregar). O `url=` sai normalizado para `https://docs.google.com/document/d/<id>/edit` (o conector devolve `?usp=drivesdk&ouid=<número>` no fim: não o grave no `projeto.json`). O `drive.json` alimenta `conferir-versao.mjs ... --drive` da etapa D, no lugar da resposta do gws.

O que o conector **não** faz, e o script recusa com exit 6 em vez de contornar: `--atualizar` sem gws. O `update_file` do conector só muda metadados (`title`, `description`, `parentId`, `starred`, `readOnly`...), não tem parâmetro de conteúdo, e nenhuma outra ferramenta dele troca o conteúdo de um arquivo. Criar outro Doc quebraria "um documento por projeto, atualizado no lugar". Reexecução sem gws: diga a quem roda que ou ele autentica o gws (aí `--atualizar` funciona como acima), ou troca o conteúdo do Doc à mão (abrir o `doc.html`, copiar tudo, colar no Doc) e você ajusta só o nome e a `description` com `update_file`. Nunca suba uma cópia.

5. O Doc nasce privado, na conta de quem rodou. Não compartilhe: entregue o link e diga que o compartilhamento é decisão da pessoa.

## Etapa D: projeto.json

Grave `<pasta de trabalho>/projeto.json` a partir do **doc final** (não do dossiê: o que ficou de fora do doc por falta de fonte fica de fora do JSON). Contrato v1, que a `visual-de-projeto` lê:

```json
{
  "versao": 1,
  "ref": { "data": "AAAA-MM-DD", "fontes": [{ "rotulo": "", "url": "" }] },
  "documento": { "id": "", "url": "", "versao": "v1", "atualizado_em": "AAAA-MM-DD" },
  "projeto": { "nome": "", "linear_id": "", "linear_url": "", "kicker": "", "statement": "", "destaque": "", "descricao": "", "acento": "#7C3AED", "dono": "", "prazo": "AAAA-MM-DD|null", "status": "" },
  "kpis": [{ "valor": "", "rotulo": "", "invertido": false, "fonte": "" }],
  "fontes_dados": [{ "nome": "", "papel": "", "descricao": "", "cor": "" }],
  "fases": [{ "n": 1, "nome": "", "duracao": "", "descricao": "", "gate": "" }],
  "capacidades": [{ "grupo": "", "itens": [{ "nome": "", "descricao": "", "estado": "no go-live|depois|fora|null" }] }],
  "hipoteses": [{ "id": "H1", "hipotese": "", "metrica": "", "resultado_esperado": "", "ferramenta": "", "situacao": "", "fonte": "" }],
  "roadmap": {
    "janela": { "inicio": "AAAA-MM-DD", "fim": "AAAA-MM-DD" },
    "trilhas": [{ "id": "", "nome": "", "cor": "" }],
    "itens": [{ "id": "", "trilha": "", "nome": "", "descricao": "", "inicio": "AAAA-MM-DD", "dias": 5, "entregas": [{ "data": "", "texto": "" }] }],
    "dependencias": [{ "de": "", "para": "", "trava": "" }],
    "marcos": [{ "data": "", "rotulo": "", "cor": "" }],
    "feriados": ["AAAA-MM-DD"]
  },
  "lacunas": [{ "secao": "", "o_que_falta": "", "depende_de": "" }]
}
```

Regras do contrato: lista vazia é válida; campo obrigatório é só `versao`, `ref.data` e `projeto.nome`; `null` é "desconhecido" e aparece como "a definir"; o JSON Schema completo está em `<plugin>/schema/projeto.schema.json`.

De onde sai cada campo (as seções citadas são as do esqueleto padrão; a tabela "Alimenta no `projeto.json`" do esqueleto em vigor manda):

| Campo | Origem |
|---|---|
| `ref.data`, `ref.fontes` | data de hoje; as fontes citadas no doc, mais **a fonte do próprio Doc**: `url` igual a `documento.url` e rótulo que cita a versão (`Documento do projeto, v2`). Só um documento: o link de uma versão antiga sai |
| `documento` | `id` e `url` do `doc_id=` e `url=` que o `gerar-doc.py` imprimiu, `versao` do `versao=` (o `v<N>` do título), `atualizado_em` a data de hoje. Reexecução: o mesmo `id` e a mesma `url`, só a versão e a data mudam |
| `projeto.nome`, `linear_id`, `linear_url`, `dono`, `prazo`, `status` | seção 0. Dono ou prazo sem fonte: `null` e uma lacuna que cita "dono" ou "prazo". Dono ou prazo vindo da entrevista **tem fonte**: no doc a marca é `decisão de <Nome>, entrevista de DD/MM/AAAA`, vale como fonte e não abre lacuna |
| `projeto.kicker` | linha curta acima do título no visual: "<produto ou área> · <tipo ou prioridade>" (seções 0 e 4). Quando só existe o time (sem tipo nem prioridade com fonte): "<produto ou área> · <time>". Sem produto nem time, `null` |
| `projeto.statement`, `destaque` | frase do objetivo (seção 4) e o trecho dela que merece destaque. `destaque` é substring literal do `statement` |
| `projeto.descricao` | resumo (seção 1), 2 a 3 frases |
| `projeto.acento` | A área ou o produto decide, pelo prefixo ou pelo nome do projeto, na tabela `areas` da camada (a cor da área que casar). Sem área que case, `acento_padrao` da camada. Só muda se quem roda pediu outra cor. O `validar-projeto.mjs` avisa quando o acento não bate |
| `kpis` | indicadores com número e fonte (seções 1 e 7). `invertido: true` quando menor é melhor. Sem número com fonte: `[]` e lacuna `kpis` |
| `fontes_dados` | sistemas e dados em que o projeto se apoia (seções 2, 3 e 7). Sem dado: `[]` |
| `fases` | seção 8: `n`, `nome`, `duracao` (texto do período), `descricao` (o porquê), `gate` (o portão). Sem fase: `[]` e lacuna `fases` |
| `capacidades` | seção 6: `grupo` é a frente, `itens` são as entregas. `estado`: `no go-live` (entra na entrega), `depois` (previsto para fase posterior), `fora` (item da lista de fora de escopo). **`estado: null` é válido e quer dizer "nenhuma fonte diz o estado"**: a capacidade entra, aparece como "a definir" no visual, e a lacuna `capacidades` registra o que falta. Nunca invente o estado para evitar o `null` |
| `hipoteses` | seção 5, uma linha da tabela por item, `fonte` com o link. Sem hipótese: `[]` e lacuna `hipoteses` |
| `roadmap.trilhas` | uma por frente ou por responsável (seções 6 e 10); `id` curto, sem espaço. **Só existe trilha onde há item de roadmap**: se `roadmap.itens` fica vazio, `trilhas` também pode (e costuma) ficar `[]`. O validador aceita trilha sem item, mas só declare as que têm |
| `roadmap.itens` | fases e ações de data conhecida (seções 8 e 11). `inicio` AAAA-MM-DD e `dias` em **dias úteis**, só quando as duas pontas têm fonte. Item sem data com fonte fica fora e vira lacuna `roadmap`. **Sem data de início com fonte: `itens: []`, `trilhas: []`, `janela` omitida, e só `marcos` (se houver) e a lacuna `roadmap`.** O visual mostra os marcos e a lacuna, não uma linha do tempo inventada |
| `roadmap.dependencias`, `marcos` | só o que uma fonte declara: portão entre fases, prazo final, marco intermediário |
| `roadmap.janela` | do primeiro `inicio` ao último prazo do roadmap. Sem `inicio` com fonte, omita |
| `roadmap.feriados` | feriados nacionais de dia útil dentro da janela. Sem como conferir num calendário: `[]` |
| `lacunas` | as da seção de lacunas que deixaram algo vazio no JSON. `secao` é uma destas chaves: `projeto`, `kpis`, `fontes_dados`, `fases`, `capacidades`, `hipoteses`, `roadmap` (tabela no fim do esqueleto) |

Valide, sem pular:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/validar-projeto.mjs" "<pasta>/projeto.json" --camada "<pasta da camada>"
```

Exit 0 é obrigatório. O validador reprova o mapa que cita outra versão ou outro link que não o de `documento` (`ref.fontes`). Confira também o doc contra o `projeto.json`:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/conferir-versao.mjs" conferir "<pasta>/projeto.json" --doc "<pasta>/doc.md"
```

Para conferir também o arquivo do Drive, grave a resposta do gws e passe em `--drive`. **Grave só o stdout: `2>/dev/null`, nunca `2>&1`.** O gws escreve "Using keyring backend: keyring" no stderr, e `2>&1` põe essa linha dentro do arquivo (o conferir tolera o que vem antes do primeiro `{`, mas não conte com isso):

```bash
gws drive files get --params '{"fileId":"<id>","fields":"id,name,description","supportsAllDrives":true}' 2>/dev/null > "<pasta>/drive.json"
node "${CLAUDE_PLUGIN_ROOT}/scripts/conferir-versao.mjs" conferir "<pasta>/projeto.json" --doc "<pasta>/doc.md" --drive "<pasta>/drive.json"
```

No texto do Linear passado em `--linear`, toda linha que cita o link do documento precisa estar na versão atual: uma linha em v2 convivendo com outra em v3 reprova.

Se `gerar-doc.py --atualizar` ou `--subir` falhar no gws, a saída traz `erro=` e o exit é 5 (sem traceback). Sem gws, `--atualizar` sai com 6 e `--registrar` com a description do Drive diferente da versão do `doc.md` sai com 7. `não achei o arquivo <id> no Drive` é o id errado ou sem acesso: confira `documento.id` no `projeto.json`.

Erro: corrija o campo citado e rode de novo. Aviso do tipo "desconhecido sem lacuna" ou "vazio sem lacuna": acrescente a lacuna. O validador também reprova as grafias e a escrita que a camada define.

## O que devolver

Responda com isto, nada além:

| Item | Conteúdo |
|---|---|
| Camada | a pasta usada e o nome da empresa |
| Documento | o link do Google Doc, a versão (`versao=`), se foi criado ou atualizado no lugar (`copia_nova=nao`) e o resultado `tabelas_ok`. Doc atualizado: a linha para o projeto do Linear (`node scripts/conferir-versao.mjs bloco <pasta>/projeto.json`), para a sincronização gravar |
| `projeto.json` | caminho absoluto e "válido" (ou os avisos que sobraram) |
| Fontes | quantas consultadas, as não verificáveis com o motivo, e a linha da segunda rodada local (dispensada ou feita) |
| Lacunas | a lista de lacunas do doc, numerada |
| Contradições | as registradas no doc, com as duas versões e as datas |
| Entrevista | o caminho de `entrevista.md`, quais perguntas foram feitas e quais lacunas a pessoa mandou registrar. Sem AskUserQuestion e sem pergunta sobrando: a seção "Resumo do que será gerado" no lugar da confirmação |
| Próximo passo | `visual-de-projeto` com o `projeto.json`, e o desdobramento no gestor de tarefas a partir do doc |

## Antiobjetivos (a skill falhou, mesmo funcionando)

- Segundo arquivo no Drive para a mesma frente (versão nova que vira cópia) ou mapa que cita versão ou link diferente do doc.
- Doc ou JSON com número, prazo, cliente ou pessoa sem fonte.
- Entrevista que pergunta o que já estava numa reunião, thread, issue, documento, ADR ou transcrição.
- Doc gerado sem reler `entrevista.md`, ou reexecução que repete pergunta já respondida lá.
- Premissa de quem respondeu contra uma fonte aceita calada, sem as duas versões no doc.
- Dono de entrega tirado do resumo de reunião sem conferir a transcrição.
- Fonte inacessível tratada como "não existe", ou skill que para por causa dela.
- Subagente sem AskUserQuestion que para depois da etapa A sem ter pergunta sobrando.
- Documento ou decisão registrada em arquivo local dada como "não encontrada".
- Nome, número ou cliente de outra empresa vindo de um arquivo local para o dossiê, o doc ou o JSON.
- Seção de hipóteses ausente ou preenchida com hipótese inventada.
- Autor do documento que não é quem rodou a skill.
- Grafia de marca ou escrita que a camada reprova.
- Qualquer marca, cor, servidor ou nome de empresa no motor em vez de na camada.
