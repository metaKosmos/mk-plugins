---
name: oraculo-mudanca
description: Mudança de layout ou de schema no mK Oráculo (repositório metaKosmos/mk-oraculo), conduzida em loop a partir de um pedido em linguagem natural. A skill entende o pedido, devolve o plano em palavras de quem usa, executa com um subagente, testa com outro, repete até passar e abre a PR. Use quando pedirem para incluir, tirar de lugar ou reorganizar um campo, uma seção, uma coluna ou um bloco numa tela do Oráculo ("inclui um campo na landing do produto", "mostra o responsável no card do curso", "adiciona um campo de data no design system"). Não é para editar conteúdo (texto, imagem, registro): isso é pelo admin do Oráculo.
---

# Mudança no Oráculo (mK)

Quem roda descreve a mudança e não escreve código. Você conduz: plano, execução, teste e PR. O guia de conteúdo, layout e schema está em `referencias/guia-do-oraculo.md`. Leia-o inteiro antes do passo 2.

O script de conferência é `${CLAUDE_PLUGIN_ROOT}/scripts/oraculo-conferir.mjs`. Rode-o sempre de dentro do clone do `mk-oraculo`.

## Regras que não cedem

- **Conteúdo é pelo admin.** Trocar texto, imagem ou registro que já tem campo no admin não é desta skill. Diga onde editar (`/admin`, a collection e o campo) e pare.
- **Fora do alcance:** login, regras de acesso, deploy, CI, variáveis de ambiente e dependências. A lista exata está no guia e no script. Pedido que precise disso vai para o David, com o motivo.
- **Migration só acrescenta.** Apagar, renomear, mudar tipo ou tornar obrigatório um campo que já existe é destrutivo: o script reprova. Pare e leve ao David.
- **Nunca o banco do stage.** O `.env.local` aponta para banco local ou para nenhum. Nada de `pnpm dev` nem `pnpm payload migrate` contra o stage.
- **Stage não é seu.** A skill não roda o workflow `deploy-stage` nem faz merge. Ela entrega a PR com o CI verde; quem publica e confere em stage é o David.
- **Commit assinado.** Sem `commit.gpgsign` ligado, nada é commitado.
- **Sem invenção.** Nome de campo, texto de rótulo ou posição que o pedido não diz vira pergunta, não palpite.

## O loop

### 1. Preparo

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/oraculo-conferir.mjs" preparo
```

Item `reprovado`: pare, diga a quem roda o que falta e como resolver, um item por vez. Item `aviso`: diga e siga. Se a pasta atual não for um clone do `mk-oraculo`, pergunte onde ele está antes de qualquer outra coisa (o passo a passo de clonar está no README do repositório, seção "Primeira contribuição").

Se "banco local" veio como aviso, avise já: a mudança será testada por typecheck, lint, testes de unidade e migration, mas a tela não será vista nesta máquina.

### 2. Entender e devolver o plano

Classifique o pedido pela tabela "Conteúdo, layout ou schema" do guia. Ache no código a tela e a collection envolvidas (o guia diz onde procurar; leia os arquivos, não presuma).

Devolva o plano em palavras de quem usa, curto:

- o que muda na tela, e onde;
- se muda o schema: qual campo, de que tipo, opcional, com que rótulo no admin;
- o que **não** muda;
- o teste principal, na forma "abro X, faço Y, vejo Z".

Pergunte só o que o pedido não decide (rótulo, posição, tipo do campo). Com `AskUserQuestion` na sessão, use-o; sem ele, devolva as perguntas numeradas e aguarde. Não edite nada antes do ok.

Peça também o id da issue no Linear, se houver (por exemplo `PROD-1234`). Sem issue, siga sem.

### 3. Branch

A partir da `main` atualizada:

```bash
git switch main
git pull --ff-only
git switch -c <usuario>/<issue-em-minusculas>-<resumo-curto>
```

`<usuario>` é o login do GitHub de quem roda (`gh api user --jq .login`). Sem issue, só `<usuario>/<resumo-curto>`.

### 4. Executar

Chame o subagente `oraculo-executor` (do plugin `mk-produto`) com: o plano aprovado, o teste principal, os arquivos que você achou no passo 2 e o caminho do guia. Ele edita, gera migration e tipos quando há schema, escreve o teste e devolve a lista do que mudou. Sem a ferramenta de subagentes na sessão, faça você mesmo seguindo `agents/oraculo-executor.md`.

### 5. Testar

Chame o subagente `oraculo-testador` com o plano e o teste principal, **sem** o relato do executor: ele confere pelo diff e pelo script, não pela palavra de quem fez. Ele roda:

```bash
node "${CLAUDE_PLUGIN_ROOT}/scripts/oraculo-conferir.mjs" mudanca --rodar
```

e, com banco local, sobe o app e confere a tela. Devolve `aprovado` ou a lista de falhas.

### 6. Repetir

Reprovou: devolva as falhas ao executor e volte ao passo 4. No máximo **três voltas**. Na terceira reprovação, pare, mostre o que falhou e o que foi tentado, e pergunte a quem roda se continua ou se leva ao David. Nunca apague, pule ou afrouxe um teste para passar.

### 7. Commit

Um commit, com a issue na frente quando houver, no padrão do repositório:

```bash
git add -A
git commit -m "PROD-1234: <o que muda, em palavras de quem usa>"
```

O gerenciador de senhas pede autorização para assinar; avise quem roda. Confira com `git cat-file commit HEAD` que há a linha `gpgsig`.

### 8. PR

Abra a PR com a skill `pr` do plugin `mk-time`. Passe a ela o título, o resumo do que muda, o teste principal e o que foi e o que não foi conferido nesta máquina.

Sem a skill `pr` na sessão: diga que ela falta e pergunte se abre direto. Com o sim:

```bash
git push -u origin HEAD
gh pr create --fill
```

Depois acompanhe o CI (`gh pr checks --watch`). CI vermelho por causa da mudança volta ao passo 4 e conta como uma volta.

### 9. Entregar

Feche com um relato curto:

- link da PR e estado do CI;
- o que mudou, em uma frase;
- o que foi conferido aqui e o que **não** foi (a tela, se não havia banco);
- o que falta e de quem é: revisão e publicação em stage são do David. Se a mudança tem migration, diga que o deploy a aplica sozinho;
- a mensagem pronta para o canal de revisão, no formato do time:

```text
mK Oráculo - <o que muda, em uma frase>
Urgencia: <Baixa, Média ou Alta>
PR : <link>
```

Não diga "pronto em stage": a skill não publica.

## Dono

David é o dono do mK Oráculo. Pedido fora do alcance, migration destrutiva e dúvida de arquitetura vão para ele.
