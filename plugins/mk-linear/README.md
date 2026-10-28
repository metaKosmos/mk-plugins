# mK Linear

O Linear da mK como servidor do Claude Code (`linear-mk`). O login fica guardado só na máquina de quem instala.

## Por que existe

O conector do Linear no claude.ai fica preso à conta do claude.ai. Se a conta for compartilhada, quem entrar nela usa o Linear de quem autorizou. O servidor deste plugin guarda o login na máquina, então uma conta compartilhada não o herda.

O mK Produto procura este servidor primeiro (`camada/camada.json`) e só depois o conector do claude.ai.

## Instalar

```bash
claude plugin marketplace add metaKosmos/mk-plugins
claude plugin install mk-linear@mk-plugins
```

Depois, na caixa de prompt do Claude Code, digite `/reload-plugins` e em seguida `/mcp`. Escolha `linear-mk` e entre com a sua conta do Linear da mK.

Conferência: peça ao Claude "em qual workspace do Linear estou conectado". A resposta certa é `metaKosmos`.

## Limites

- O login vence com o tempo. Quando o Linear pedir de novo, renove por `/mcp`.
- O plugin só liga o servidor. Quem decide o que ler e criar são as skills que o usam, como as do mK Produto.
- É o workspace da conta que você autorizar. Entre sempre com a conta da mK.
