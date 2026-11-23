# Guia de conteúdo, layout e schema do mK Oráculo

Para quem conduz ou executa uma mudança pela skill `oraculo-mudanca`. O repositório é `metaKosmos/mk-oraculo`: Next (App Router) com Payload CMS e Postgres. Este guia diz onde as coisas ficam e quais regras valem; os nomes exatos de campo e de arquivo se leem no clone, que é a fonte da verdade. Se o guia e o código discordarem, vale o código, e a diferença vai no relato final.

## Conteúdo, layout ou schema

| O pedido é | Exemplo | Onde se faz | Quem faz |
|---|---|---|---|
| **Conteúdo**: mudar o valor de algo que já tem campo | trocar o resumo de um produto, publicar uma página, subir uma imagem | admin do Oráculo, em `/admin` | quem edita, sem código e sem PR |
| **Layout**: mudar como a tela mostra o que já existe | mostrar o resumo embaixo do título, trocar a ordem de duas seções, virar lista em grade | `src/app/(frontend)/` e `src/components/` | a skill |
| **Schema**: guardar uma informação nova | campo "frase curta" no produto, estado novo numa lista de opções | `src/collections/`, mais migration e tipos | a skill |
| **Schema e layout** | incluir um campo e mostrá-lo na tela | os dois acima, na mesma PR | a skill |

Como decidir: se dá para fazer inteiro pelo admin hoje, é conteúdo. Se a informação já existe e só a apresentação muda, é layout. Se a informação não tem onde ser guardada, é schema.

Atenção a um caso: parte dos textos das landings de produto está escrita no código (arquivo de dados da landing), não no admin. Mudar um texto desses é mudança de código, pequena, e cabe na skill; diga isso a quem pediu, porque a expectativa costuma ser "é só conteúdo".

## Mapa do repositório

| Pasta ou arquivo | O que é |
|---|---|
| `src/collections/` | Um arquivo por collection do Payload: campos, rótulos do admin, acesso. É o schema |
| `src/payload.config.ts` | Lista as collections e configura o admin. Collection nova entra aqui |
| `src/migrations/` | Par `.ts` e `.json` por migration, mais o `index.ts` que as lista. Gerado, não escrito à mão |
| `src/payload-types.ts` | Tipos gerados a partir das collections. Gerado, não escrito à mão |
| `src/app/(frontend)/(app)/` | As telas do hub, uma pasta por módulo (Conhecimento, Design, Oráculo, busca) |
| `src/app/(frontend)/(app)/design/` | Módulo Design. A página do produto fica em `[productSlug]/page.tsx`; as landings de produto, em `_components/landing/` |
| `src/components/` | Componentes compartilhados: a moldura do hub (`shell/`), Design, Conhecimento |
| `src/app/(payload)/` | O admin do Payload. Não se edita |
| `src/seed/` | Carga inicial de dados. `src/seed/data/` é conteúdo e fica fora da skill |
| `tests/unit/` | Testes de unidade (Vitest). Um arquivo por assunto, nomes em português |
| `tests/int/`, `tests/e2e/` | Integração e ponta a ponta. A skill não mexe |

Para achar a tela de um pedido: procure o texto visível na tela dentro de `src/app/(frontend)` e `src/components`; depois leia a `page.tsx` da rota para ver de qual collection ela lê (`payload.find({ collection: ... })`).

## Receita de schema

1. Edite a collection em `src/collections/`. Campo novo é **opcional** (sem `required`), ou tem `defaultValue`. Dê `label` ou `admin.description` em português, dizendo para que serve: é o que quem edita vê no admin.
2. Gere a migration. O nome é curto, em minúsculas, com `_`:

   ```bash
   pnpm payload migrate:create <collection>_<o_que_muda>
   ```

   Isso cria o par `.ts` e `.json` e atualiza o `index.ts`. Não precisa de banco: o comando compara o código com o snapshot da migration anterior.
3. Regenere os tipos:

   ```bash
   pnpm generate:types
   ```

4. Leia a função `up` da migration gerada. Ela deve só acrescentar (`ADD COLUMN`, `CREATE TABLE`, `ADD VALUE`). Se aparecer `DROP`, `RENAME`, `SET DATA TYPE` ou `NOT NULL` sem valor padrão, a mudança é destrutiva: pare.
5. Commite juntos: a collection, o par da migration, o `index.ts` e o `payload-types.ts`.

Por que a migration é obrigatória: em desenvolvimento o Payload ajusta o banco sozinho, sem migration. Coluna criada assim nunca chega ao stage, o app passa a consultar o que não existe e o login cai. Já aconteceu. O deploy do stage aplica as migrations pendentes sozinho; sem migration na PR, a mudança de schema não existe lá.

Não rode `pnpm payload migrate` nesta máquina contra banco que não seja o local.

## Receita de layout

1. Ache o componente da tela e leia os vizinhos: classes de CSS, componentes já usados, como o dado chega.
2. Reaproveite o que existe. Cor, espaçamento e tipografia vêm dos tokens e das classes já presentes no CSS do módulo; não escreva cor ou medida solta se já há um token.
3. O dado é lido no servidor, na `page.tsx`, e passado ao componente. Campo novo opcional pode estar vazio: a tela precisa ficar correta sem ele (não mostra o bloco, em vez de mostrar um rótulo sem valor).
4. A tela se ajusta a tablet e celular sem rolagem de lado. Mudou a largura de um bloco, confira os dois.
5. Texto de interface em português, com a grafia da marca: "mK" com m minúsculo e K maiúsculo (mK Fashion+, mK AI Studio, mK Platform), sem travessão e sem emoji.

## Teste por mudança

Toda mudança de código ganha teste em `tests/unit/`. O teste diz, em português, o comportamento de quem usa, não o detalhe de implementação.

- **Schema:** o campo existe na collection, com o tipo certo, e é opcional.
- **Layout:** o componente, renderizado com `renderToStaticMarkup`, mostra o campo quando há valor e não mostra o bloco quando não há.
- **Lógica:** função pura testada direto.

Siga o estilo dos testes vizinhos do mesmo módulo (por exemplo os `design-landing-*.test.ts`).

## O que roda, e o que cada coisa prova

| Comando | Prova | Precisa de banco |
|---|---|---|
| `pnpm typecheck` | os tipos fecham, inclusive com o campo novo | não |
| `pnpm lint` | o padrão do código | não |
| `pnpm test:unit` | o comportamento descrito nos testes | não |
| `pnpm payload migrate:create` | a migration foi gerada | não |
| `pnpm dev` e abrir a tela | a tela de verdade, com dado | sim |
| CI da PR | tudo acima, mais o build | roda no GitHub |

O script `oraculo-conferir.mjs mudanca --rodar` roda os três primeiros e confere as regras deste guia (migration presente e só acrescenta, tipos regenerados, teste presente, nada fora do alcance).

Sem banco local não se vê a tela nesta máquina. Diga isso no relato, sem maquiar: "tela não conferida aqui". Na primeira vez que roda, o `pnpm dev` pode parar com um aviso de versão do Next; rode de novo.

## Fora do alcance da skill

Pedido que precise mexer nestes pontos para, e vai para o David:

- login e sessão (`src/auth/`, autenticação em `src/lib/`);
- regras de acesso (`src/access/`, `src/lib/knowledge-access/`) e o bloco `access` de uma collection;
- CI e deploy (`.github/`, `scripts/`, `docs/deploy*`, `Dockerfile`, `docker-compose.yml`, `ecosystem.config.cjs`, `next.config.ts`);
- variáveis de ambiente (`.env*`);
- dependências (`package.json`, `pnpm-lock.yaml`);
- conteúdo de carga (`src/seed/data/`);
- qualquer migration destrutiva.

## Depois da PR

A PR não muda o stage. O caminho é: CI verde, revisão, merge na `main` e o workflow de deploy rodado por quem tem permissão; é ele que aplica a migration e troca a versão no ar. O teste principal em stage é do David. A skill termina na PR aberta, com o CI verde e o relato do que foi e do que não foi conferido.
