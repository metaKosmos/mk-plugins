// Validador mínimo de JSON Schema (o subconjunto que os contratos do plugin usam):
// type, enum, const, pattern, minLength, minimum, minItems, items, required, properties,
// additionalProperties:false, anyOf e $ref local. Sem dependências.

function resolver(ref, raiz) {
  return ref
    .replace(/^#\//, '')
    .split('/')
    .reduce((no, parte) => no?.[parte], raiz);
}

function tipoDe(valor) {
  if (valor === null) return 'null';
  if (Array.isArray(valor)) return 'array';
  if (Number.isInteger(valor)) return 'integer';
  return typeof valor;
}

function confere(valor, tipo) {
  const t = tipoDe(valor);
  return t === tipo || (tipo === 'number' && t === 'integer');
}

export function caminho(base, chave) {
  if (typeof chave === 'number') return `${base}[${chave}]`;
  return base ? `${base}.${chave}` : chave;
}

export function validarSchema(valor, esquema, raiz, onde, erros) {
  if (esquema.$ref) esquema = resolver(esquema.$ref, raiz);
  const rotulo = onde || '(raiz)';

  if (esquema.anyOf) {
    const tentativas = esquema.anyOf.map((alt) => {
      const e = [];
      validarSchema(valor, alt, raiz, onde, e);
      return { alt, e };
    });
    if (tentativas.some((t) => !t.e.length)) return;
    // nenhuma serve: conta os erros da alternativa que tem o tipo do valor (a mais provável)
    const doTipo = tentativas.find((t) => [t.alt.type].flat().includes(tipoDe(valor))) ?? tentativas[0];
    erros.push(...doTipo.e);
    return;
  }

  if (esquema.const !== undefined && valor !== esquema.const) {
    erros.push(`${rotulo}: deve ser ${JSON.stringify(esquema.const)}`);
    return;
  }
  if (esquema.enum && !esquema.enum.includes(valor)) {
    erros.push(`${rotulo}: "${valor}" fora do permitido (${esquema.enum.join(' | ')})`);
    return;
  }
  if (esquema.type) {
    const tipos = Array.isArray(esquema.type) ? esquema.type : [esquema.type];
    if (!tipos.some((t) => confere(valor, t))) {
      erros.push(`${rotulo}: esperava ${tipos.join(' ou ')}, veio ${tipoDe(valor)}`);
      return;
    }
  }
  if (typeof valor === 'string') {
    // texto só com espaço é vazio: o que conta é o que sobra depois do trim
    if (esquema.minLength && valor.trim().length < esquema.minLength) erros.push(`${rotulo}: vazio`);
    if (esquema.pattern && !new RegExp(esquema.pattern).test(valor)) {
      erros.push(`${rotulo}: "${valor}" não segue o formato esperado`);
    }
  }
  if (typeof valor === 'number' && esquema.minimum !== undefined && valor < esquema.minimum) {
    erros.push(`${rotulo}: ${valor} é menor que o mínimo ${esquema.minimum}`);
  }
  if (Array.isArray(valor) && esquema.minItems !== undefined && valor.length < esquema.minItems) {
    erros.push(`${rotulo}: precisa de pelo menos ${esquema.minItems} item(ns), veio ${valor.length}`);
  }
  if (Array.isArray(valor) && esquema.items) {
    valor.forEach((item, i) => validarSchema(item, esquema.items, raiz, caminho(onde, i), erros));
  }
  if (valor && typeof valor === 'object' && !Array.isArray(valor)) {
    for (const obrigatorio of esquema.required ?? []) {
      if (valor[obrigatorio] === undefined) {
        erros.push(`${caminho(onde, obrigatorio)}: campo obrigatório ausente`);
      }
    }
    const props = esquema.properties ?? {};
    for (const [chave, sub] of Object.entries(valor)) {
      if (props[chave]) validarSchema(sub, props[chave], raiz, caminho(onde, chave), erros);
      else if (esquema.additionalProperties === false) {
        erros.push(`${caminho(onde, chave)}: campo desconhecido no contrato v1`);
      }
    }
  }
}

