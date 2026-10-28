// CSS variables (--vp-*) e o bloco <style>/<link> que cada prancha leva, a partir dos tokens.
// Compartilhado pelo montar-canvas.mjs (moldes do projeto) e pelo montar-esboco.mjs (pranchas do esboço).

export const VAR = {
  '--vp-fonte-titulo': (t) => t.fontes.titulo.familia,
  '--vp-titulo-peso': (t) => t.fontes.titulo.peso,
  '--vp-titulo-caixa': (t) => t.fontes.titulo.caixa,
  '--vp-fonte-corpo': (t) => t.fontes.corpo.familia,
  '--vp-corpo-peso': (t) => t.fontes.corpo.peso,
  '--vp-fundo': (t) => t.cores.fundo,
  '--vp-texto': (t) => t.cores.texto,
  '--vp-texto-suave': (t) => t.cores.texto_suave,
  '--vp-borda': (t) => t.cores.borda,
  '--vp-borda-forte': (t) => t.cores.borda_forte,
  '--vp-superficie': (t) => t.cores.superficie,
  '--vp-linha-leve': (t) => t.cores.linha_leve,
  '--vp-apagado': (t) => t.cores.apagado,
  '--vp-inverso': (t) => t.cores.inverso,
  '--vp-alerta': (t) => t.cores.alerta,
  '--vp-acento': (t) => t.cores.acento,
  '--vp-raio': (t) => t.raio.card,
  '--vp-raio-grande': (t) => t.raio.grande
};

export const esc = (x) => String(x).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');

export function blocoDeTokens(t) {
  const linhas = [];
  for (const [nome, f] of Object.entries(VAR)) {
    const v = String(f(t));
    if (/[;{}<>]/.test(v)) throw new Error(`token ${nome}: valor com caractere proibido (; { } < >): ${v}`);
    linhas.push(`${nome}:${v}`);
  }
  const urls = [...new Set([t.fontes.titulo.url, t.fontes.corpo.url].filter(Boolean))];
  const links = urls.length
    ? ['<link rel="preconnect" href="https://fonts.googleapis.com">', ...urls.map((u) => `<link rel="stylesheet" href="${esc(u)}">`)].join('\n') + '\n'
    : '';
  return `${links}<style>\n:root{${linhas.join(';')}}\n</style>`;
}
