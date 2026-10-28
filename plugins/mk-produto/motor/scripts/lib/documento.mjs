// O documento de projeto é um só no Drive, e doc, mapa (canvas) e Linear citam o mesmo link e
// a mesma versão dele. Aqui mora o que os scripts compartilham sobre isso: ler o bloco
// `documento` do projeto.json, a versão do título do doc.md, o bloco de texto do Linear e as
// conferências. Nada aqui fala com o Drive nem com o Linear.

export const RE_VERSAO = /^v[1-9]\d*$/;
const RE_LINK_DOC = /https:\/\/docs\.google\.com\/document\/d\/([\w-]+)[^\s)>\]]*/g;

export function idDaUrl(url) {
  const m = /^https:\/\/docs\.google\.com\/document\/d\/([\w-]+)(?:[/?#].*)?$/.exec(url ?? '');
  return m ? m[1] : null;
}

/** `v3` casa em "Documento, v3" e não casa em "v30" nem em "v3x". */
export function citaVersao(texto, versao) {
  return new RegExp(`(?<![\\w])${versao}(?![\\w])`, 'i').test(texto ?? '');
}

/** Versão do título do doc.md: a linha logo abaixo do H1, "<data> · <autor> · v<N>". */
export function versaoDoDoc(md) {
  const linhas = md.split(/\r?\n/);
  const i = linhas.findIndex((l) => /^#\s/.test(l.trim()));
  if (i < 0) return null;
  const abaixo = linhas.slice(i + 1).find((l) => l.trim());
  const m = abaixo ? /·\s*(v[1-9]\d*)\s*$/.exec(abaixo.trim()) : null;
  return m ? m[1] : null;
}

export function dataBr(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '');
  return m ? `${m[3]}/${m[2]}/${m[1]}` : null;
}

/** A linha que vai na descrição do projeto no Linear. */
export function blocoLinear(doc) {
  const quando = dataBr(doc.atualizado_em);
  return `Documento do projeto: ${doc.url} (${doc.versao}${quando ? `, atualizado em ${quando}` : ''})`;
}

/**
 * Confere o que o projeto.json diz de si mesmo: o bloco `documento` é coerente (o id é o da
 * URL) e o mapa cita, em `ref.fontes`, o link do doc com a versão e nenhum outro doc.
 * Sem `documento`, não há o que conferir aqui (devolve []).
 */
export function errosDoProjeto(d) {
  const doc = d?.documento;
  if (!doc) return [];
  const erros = [];
  const idUrl = idDaUrl(doc.url);
  if (!idUrl) erros.push(`documento.url: "${doc.url}" não é o link de um Google Doc (docs.google.com/document/d/<id>)`);
  else if (idUrl !== doc.id) erros.push(`documento.id: "${doc.id}" não é o id do documento da url ("${idUrl}")`);
  const fontes = d.ref?.fontes ?? [];
  const doDoc = fontes.filter((f) => idDaUrl(f?.url) === (idUrl ?? doc.id));
  if (!doDoc.length) {
    erros.push(`ref.fontes: falta a fonte do documento (${doc.url}): o mapa precisa citar o mesmo link`);
  } else if (!doDoc.some((f) => f.url === doc.url && citaVersao(f.rotulo, doc.versao))) {
    const achada = doDoc.map((f) => `"${f.rotulo}"`).join(', ');
    erros.push(`ref.fontes: a fonte do documento precisa citar ${doc.versao} e o link ${doc.url}, mas diz ${achada}`);
  }
  for (const f of fontes) {
    const id = idDaUrl(f?.url);
    if (id && id !== (idUrl ?? doc.id)) {
      erros.push(`ref.fontes: cita outro documento (${id}, "${f.rotulo}") e o mapa tem um só (${idUrl ?? doc.id})`);
    }
  }
  return erros;
}

/**
 * O texto do projeto no Linear: toda linha que cita um Google Doc cita o do projeto, com a
 * versão dele. Devolve os erros.
 */
export function errosDoLinear(texto, doc) {
  const erros = [];
  const linhas = (texto ?? '').split(/\r?\n/).filter((l) => new RegExp(RE_LINK_DOC.source).test(l));
  if (!linhas.length) return [`o projeto não cita o documento (${doc.url})`];
  for (const l of linhas) {
    for (const m of l.matchAll(new RegExp(RE_LINK_DOC.source, 'g'))) {
      if (m[1] !== doc.id) erros.push(`cita outro documento (${m[1]}), o do projeto é ${doc.id}: "${l.trim()}"`);
    }
  }
  const certas = linhas.filter((l) => l.includes(doc.url) || idDaLinha(l) === doc.id);
  if (!certas.length) erros.push(`o projeto não cita o documento do projeto (${doc.url})`);
  else if (!certas.some((l) => citaVersao(l, doc.versao))) {
    erros.push(`o link está certo mas a versão não é ${doc.versao}: "${certas[0].trim()}"`);
  } else {
    // uma linha certa não salva as outras: linha com o link e outra versão convive com a nova e engana quem lê
    for (const l of certas) {
      const velha = (l.match(/(?<![\w])v[1-9]\d*(?![\w])/gi) ?? []).find((v) => v.toLowerCase() !== doc.versao);
      if (velha && !citaVersao(l, doc.versao)) {
        erros.push(`linha com o link do documento em ${velha.toLowerCase()} e o documento está em ${doc.versao}: "${l.trim()}"`);
      }
    }
  }
  return erros;
}

function idDaLinha(l) {
  const m = new RegExp(RE_LINK_DOC.source).exec(l);
  return m ? m[1] : null;
}
