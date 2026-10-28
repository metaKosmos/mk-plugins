---
name: linha-do-tempo
description: Linha do Tempo de Fases da mK: trilha horizontal com as fases de um projeto em barras e um bloco "Depois" à direita com os projetos que só começam quando o atual termina. Use ao montar roadmap, fases ou sequência de projetos em material de produto mK, em canvas, documento ou artefato ("faz a linha do tempo do 350", "o que vem depois de terminar o projeto atual", "roadmap em fases"). Para o Gantt em dias úteis com trilhas e dependências, use o Mapa do Projeto.
---

# Linha do Tempo de Fases (mK)

Componente de leitura rápida: 3 a 5 fases em barras sobre um trilho e, à direita, o que vem depois. Nasceu na proposta Priorização do Núcleo de Produto (22/10/2026), aprovada pelo David para reuso, principalmente em roadmap. O estado do template está em `../../camada/templates.json` (hoje "em esboço": a skill existe, o molde fixo no motor não).

Diga a quem roda a camada usada ("camada: mk-produto/camada, empresa metaKosmos").

## Quando usar, e quando não

- **Usa:** sequência curta de fases com data final conhecida, mais uma lista curta de projetos seguintes.
- **Não usa:** roadmap com muitos itens, trilhas por equipe ou dependências. Isso é a prancha Roadmap do Mapa do Projeto (`mapa-do-projeto`), em dias úteis.
- **Sem data real, não desenha.** Fase sem data confirmada entra como "a definir" no rótulo. Nunca estime.

## De onde vêm os dados

| O que aparece | Fonte | Observação |
|---|---|---|
| Nome e número da fase | `fases[]` do `projeto.json` (`n`, `nome`) | A `descricao` fica como apoio abaixo do nome |
| Início e fim da fase | `fases[].duracao`, quando vier como "DD/MM a DD/MM/AAAA" (testado no P-PROD-350) | `duracao` é texto livre. Se não casar com esse formato, use `roadmap.marcos[]` (`data`, `rotulo`) e confira o rótulo com o nome da fase: os rótulos nem sempre coincidem ("Design" para "Casca e Design"). Sem nenhuma das duas, "a definir" e uma `lacunas[]` com `secao: "fases"` |
| Marco intermediário | `roadmap.marcos[]` | Linha tracejada com o rótulo curto |
| Bloco "Depois" | Projetos do Linear mK que dependem do atual ou foram combinados como seguintes | Só pelo servidor de `fontes.linear` da camada, nunca o `linear-214`. Sem fonte, pergunte a quem roda |

Se não houver `projeto.json`, monte o que o pedido trouxer e liste o que faltou, sem preencher.

## Estrutura (SVG inline, viewBox 960 x 170, largura mínima 760 px)

1. **Trilho:** linha horizontal em y=44, de x=10 a x=590, cor `borda_forte`, largura 4, ponta arredondada. As fases ocupam de x=10 a x=560, e o bloco "Depois" fica à direita, a partir de x=640. (O primeiro rascunho dizia trilho até x=950 e "Depois" em x=580, o que se sobrepunha.)
2. **Fases:** uma barra por fase (altura 12, raio 6, y=38), com largura proporcional à duração. A primeira usa o acento cheio. As seguintes usam o mesmo acento com opacidade 1, .75 e .5, para o futuro ficar mais esmaecido. Fase concluída: acento cheio. Fase em risco: contorno na cor `alerta`.
3. **Data:** acima de cada barra (y=22), "até DD/MM", em fonte monoespaçada, 11 px, `texto_suave`. Fase com menos de 8% da janela (como um fechamento de 2 dias) tem o rótulo alinhado à direita da barra, para não colidir com o "depois" no fim do trilho. O "depois" fica centrado sobre o marco final (x=590).
4. **Nome:** abaixo da barra (y=76), numerado ("0. Teste", "1. Porta"), 12 px, peso 700, `texto`.
5. **Apoio:** duas linhas (y=94 e y=112) com detalhe ou responsável, 11 px, `texto_suave`.
6. **Marco intermediário:** linha vertical tracejada (traço `texto`, 1,5, dasharray "3 2") cruzando o trilho, com legenda curta ("20/11: tudo no ar").
7. **Marco final:** círculo de raio 9 com preenchimento `fundo` e contorno no acento, largura 3, em x=590, na passagem para o "Depois".
8. **Bloco "Depois"** (x=640 a 950): um cartão por projeto seguinte, raio 6, preenchimento `superficie`, contorno `borda`. Nome em 12 px `texto`, detalhe em 11 px `texto_suave`. O texto quebra em linhas de até 38 caracteres, sem cortar: o teste cortou o nome "mK Oráculo: módulos de produto e comercial" com 40 caracteres fixos. A altura do cartão cresce com as linhas.

## Cor, fonte e grafia: sempre da camada

- **Cores e fontes:** de `../../camada/tokens.json` (vocabulário claro do mK Orbit: títulos em Anton, corpo em Helvetica Neue). Nada de hex no componente: use as variáveis que o montador injeta a partir dos tokens.
- **Acento:** pela regra de área da `mapa-do-projeto`, na tabela de `../../camada/camada.json`. Material de projeto de uma área usa a cor da área. Material de processo ou interno usa o `acento_padrao`.
- **Máximo:** 5 fases na trilha e 3 cartões em "Depois". Passou disso, divida em dois componentes.
- **Escrita:** português brasileiro com diacríticos, sem traço longo, sem emoji, "mK" com m minúsculo e K maiúsculo, datas em DD/MM.

## Variações

- **Now/Next/Later:** 3 fases com opacidade 1, .75 e .5, e o "Depois" como Later.
- **Por produto:** repita o componente, uma trilha por produto, com a mesma escala de datas entre as trilhas.

## Entrega

- **Envoltório:** título em `h3`, o SVG dentro de uma `div` com `role="img"` e `aria-label`, e uma nota de leitura de uma ou duas frases. O `aria-label` é obrigatório e narra a linha inteira, com as datas.
- **Em canvas:** siga a skill `esboco` (`../esboco/SKILL.md`) para a prancha, com o elemento visual dominante em SVG inline.
- **Segunda vez do mesmo formato:** o esboço propõe promover o formato a template. Quem decide é o David, e mudança no contrato de template passa pelo Flávio, dono do módulo de produto.
