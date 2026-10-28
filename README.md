# mk-plugins

Plugins do Claude Code da mK para quem opera: produto, Linear e o que vier depois. O repositório é público para que qualquer pessoa da mK instale sem conta no GitHub.

## Instalar

```bash
claude plugin marketplace add metaKosmos/mk-plugins
claude plugin install mk-produto@mk-plugins
claude plugin install mk-linear@mk-plugins
```

Passo a passo de cada plugin: [`plugins/mk-produto/README.md`](plugins/mk-produto/README.md) e [`plugins/mk-linear/README.md`](plugins/mk-linear/README.md).

## Regra do repositório

Tudo aqui é público. Por isso:

- Nenhum segredo, chave, token ou ID de documento real entra no repositório.
- Acesso a dado da mK passa pela conta de quem usa: OAuth do Linear, conta `@metakosmos.com.br` no Google, conectores do claude.ai ou o broker autenticado.
- Nome de cliente, número de negócio e conteúdo interno ficam fora. O exemplo usa dado fictício.

Plugin do time de dev (portão SSH, `mk`, `mk-time`) continua no repositório privado `metaKosmos/harness-dev`.
