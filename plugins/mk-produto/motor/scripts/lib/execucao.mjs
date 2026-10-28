// Execução direta de um script .mjs. O guarda `if (executadoDiretamente(import.meta.url)) { ... }`
// deixa o módulo importável (testes, outros scripts) sem rodar o CLI.
//
// Comparar `fileURLToPath(import.meta.url) === process.argv[1]` não serve: o Node resolve o symlink
// do módulo principal (import.meta.url sai com o caminho real) e argv[1] fica com o que foi digitado.
// Com /var -> /private/var do mktemp no macOS, ou HOME por symlink, os dois diferem, o guarda dá
// falso e o script termina com exit 0 e sem saída, um falso verde. Aqui os dois lados são resolvidos.
import { realpathSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

function real(caminho) {
  try {
    return realpathSync(caminho);
  } catch {
    return caminho; // não existe (ex.: `node -e`): compara como veio
  }
}

/** `true` quando o módulo cujo `import.meta.url` é `urlDoModulo` é o script que o Node executou. */
export function executadoDiretamente(urlDoModulo, argv1 = process.argv[1]) {
  if (!argv1) return false;
  return real(fileURLToPath(urlDoModulo)) === real(argv1);
}
