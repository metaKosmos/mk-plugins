#!/usr/bin/env node
// Valida a pasta de uma camada contra o contrato (schema/camada.schema.json e
// schema/tokens.schema.json) e confere o que o schema não alcança: expressões
// regulares que compilam, grupos nomeados (sintaxe diferente em JS e Python) e
// "para" que o próprio "aceitar" reprovaria. Confere também o templates.json, quando existe
// (nome único, skill que existe no motor, estado coerente, regra de escrita da camada).
//
//   node validar-camada.mjs <pasta da camada>
//   node validar-camada.mjs            (acha a pasta como as outras skills: VANTA_CAMADA, ./camada)
//
// Exit 0: válida. Exit 1: lista de erros. Exit 2: pasta não encontrada.

import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { detectar, validarCamada, lerTemplates } from './lib/camada.mjs';

const arg = process.argv[2];
const dir = arg ?? detectar(null, []);
if (!dir || !existsSync(join(dir, 'camada.json'))) {
  console.error(`camada não encontrada${arg ? ` em ${arg}` : ''}: falta a pasta com camada.json`);
  process.exit(2);
}
const { erros, avisos, camada } = validarCamada(dir);
for (const a of avisos) console.log(`aviso  ${a}`);
for (const e of erros) console.log(`ERRO   ${e}`);
if (!erros.length && camada) {
  const f = camada.fontes ?? {};
  const ligadas = Object.entries(f).filter(([, v]) => v?.habilitada).map(([k]) => k);
  console.log(`empresa: ${camada.empresa.nome}`);
  console.log(`fontes habilitadas: ${ligadas.join(', ') || 'nenhuma'}`);
  console.log(`áreas: ${(camada.areas ?? []).map((a) => `${a.nome} ${a.cor}`).join(', ') || 'nenhuma'}`);
  const tpl = lerTemplates(dir)?.templates;
  console.log(tpl ? `templates: ${tpl.map((x) => `${x.nome} (${x.estado})`).join(', ') || 'nenhum'}` : 'templates: sem templates.json');
}
console.log(erros.length ? `\ninválida: ${erros.length} erro(s), ${avisos.length} aviso(s)` : `\nválida: 0 erros, ${avisos.length} aviso(s)`);
process.exit(erros.length ? 1 : 0);
