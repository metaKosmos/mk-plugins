#!/usr/bin/env node
// Conferência da skill oraculo-mudanca. Roda dentro de um clone do mk-oraculo.
// Sem dependências: só Node e git. Funciona em Windows, macOS e Linux.
//
//   node oraculo-conferir.mjs preparo [--repo <pasta>] [--json]
//       a máquina e o clone estão prontos para uma mudança?
//   node oraculo-conferir.mjs mudanca [--repo <pasta>] [--base <ref>] [--rodar] [--json]
//       a mudança em curso respeita as regras do guia? --rodar executa também
//       typecheck, lint e testes de unidade.
//
// Saída 0: nada reprovado. Saída 1: há item "reprovado". Saída 2: uso errado.
import { execSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import net from 'node:net'
import path from 'node:path'

const args = process.argv.slice(2)
const modo = args[0]
const opt = (nome) => {
  const i = args.indexOf(nome)
  return i >= 0 ? args[i + 1] : undefined
}
const tem = (nome) => args.includes(nome)
const repo = path.resolve(opt('--repo') ?? '.')
const itens = []
const marca = (estado, nome, detalhe) => itens.push({ estado, nome, detalhe })
const ok = (n, d) => marca('ok', n, d)
const aviso = (n, d) => marca('aviso', n, d)
const reprovado = (n, d) => marca('reprovado', n, d)

function sh(cmd, { permiteFalha = true } = {}) {
  try {
    return execSync(cmd, { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
  } catch (e) {
    if (!permiteFalha) throw e
    return null
  }
}

function ehOraculo() {
  const pkg = path.join(repo, 'package.json')
  if (!existsSync(pkg) || !existsSync(path.join(repo, 'src', 'payload.config.ts'))) return false
  const remoto = sh('git remote get-url origin') ?? ''
  return /mk-oraculo(\.git)?$/i.test(remoto)
}

function portaAberta(host, porta) {
  return new Promise((resolve) => {
    const s = net.connect({ host, port: porta })
    const fim = (v) => {
      s.destroy()
      resolve(v)
    }
    s.setTimeout(1500, () => fim(false))
    s.on('connect', () => fim(true))
    s.on('error', () => fim(false))
  })
}

async function preparo() {
  if (!ehOraculo()) {
    reprovado('clone do mk-oraculo', `${repo} não é um clone do metaKosmos/mk-oraculo`)
    return
  }
  ok('clone do mk-oraculo', repo)

  const [maior, menor] = process.versions.node.split('.').map(Number)
  if (maior > 20 || (maior === 20 && menor >= 9)) ok('node', process.versions.node)
  else reprovado('node', `${process.versions.node}; o Oráculo pede 20.9 ou mais (22 recomendado)`)

  const pnpm = sh('pnpm --version')
  if (pnpm) ok('pnpm', pnpm)
  else reprovado('pnpm', 'não encontrado; instale com: npm install -g pnpm@10')

  if (sh('gh auth status') !== null) ok('gh', 'autenticado')
  else reprovado('gh', 'GitHub CLI ausente ou sem login; rode: gh auth login')

  const podeEscrever = sh('gh api repos/metaKosmos/mk-oraculo --jq .permissions.push')
  if (podeEscrever === 'true') ok('escrita no repositório', 'push liberado')
  else if (podeEscrever === 'false')
    reprovado('escrita no repositório', 'a conta só lê; peça o papel Write no mk-oraculo')
  else aviso('escrita no repositório', 'não foi possível conferir')

  const assina = sh('git config --get commit.gpgsign')
  const chave = sh('git config --get user.signingkey')
  if (assina === 'true' && chave) ok('commit assinado', `formato ${sh('git config --get gpg.format') ?? 'gpg'}`)
  else reprovado('commit assinado', 'commit.gpgsign não está ligado; veja "Primeira contribuição" no README do mk-oraculo')

  const email = sh('git config --get user.email') ?? ''
  const nome = sh('git config --get user.name') ?? ''
  if (!email || !nome || /exemplo\.com|example\.com|^seu[- ]/i.test(email) || /^seu nome$/i.test(nome))
    reprovado('autor do commit', 'user.name ou user.email vazio ou ainda com o texto de exemplo')
  else ok('autor do commit', 'configurado')

  const sujo = sh('git status --porcelain')
  if (sujo) aviso('pasta de trabalho', 'há mudança sem commit; confirme com quem roda se é para seguir por cima')
  else ok('pasta de trabalho', 'limpa')

  const ramo = sh('git rev-parse --abbrev-ref HEAD')
  if (ramo === 'main') aviso('branch', 'você está na main; a skill cria a branch da mudança antes de editar')
  else ok('branch', ramo)

  if (existsSync(path.join(repo, 'node_modules'))) ok('dependências', 'node_modules presente')
  else aviso('dependências', 'faltam; rode: pnpm install --frozen-lockfile')

  const env = path.join(repo, '.env.local')
  if (!existsSync(env)) {
    aviso('.env.local', 'ausente; copie o .env.example e gere um PAYLOAD_SECRET (README, Setup local)')
    aviso('banco local', 'não conferido sem o .env.local')
    return
  }
  ok('.env.local', 'presente')
  const uri = readFileSync(env, 'utf8').match(/^DATABASE_URI=(.+)$/m)?.[1]?.trim()
  let alvo = null
  try {
    alvo = new URL(uri)
  } catch {
    /* sem URI válida */
  }
  if (!alvo) {
    aviso('banco local', 'DATABASE_URI ausente ou inválida no .env.local')
  } else if (!['localhost', '127.0.0.1', '::1'].includes(alvo.hostname)) {
    reprovado('banco local', 'DATABASE_URI aponta para fora da máquina; nunca rode o dev contra o banco do stage')
  } else if (await portaAberta(alvo.hostname, Number(alvo.port || 5432))) {
    ok('banco local', 'responde; dá para subir o app e conferir a tela')
  } else {
    aviso('banco local', 'não responde; typecheck, lint, testes e migration rodam, mas a tela não será conferida aqui')
  }
}

const PROIBIDO = [
  [/^\.github\//, 'CI e deploy'],
  [/^scripts\//, 'scripts de deploy'],
  [/^docs\/deploy/, 'documentação de deploy'],
  [/^src\/auth\//, 'login'],
  [/^src\/access\//, 'regras de acesso'],
  [/^src\/lib\/(oraculoAuth|getUser)\./, 'autenticação'],
  [/^src\/lib\/knowledge-access\//, 'regras de acesso'],
  [/^(Dockerfile|docker-compose\.yml|ecosystem\.config\.cjs|next\.config\.ts)$/, 'infraestrutura'],
  [/^\.env/, 'variáveis de ambiente'],
  [/^(package\.json|pnpm-lock\.yaml)$/, 'dependências'],
  [/^src\/seed\/data\//, 'conteúdo (é pelo admin)'],
]

function corpoDoUp(texto) {
  const i = texto.indexOf('export async function up')
  const j = texto.indexOf('export async function down')
  return i >= 0 ? texto.slice(i, j > i ? j : undefined) : texto
}

function mudanca() {
  if (!ehOraculo()) {
    reprovado('clone do mk-oraculo', `${repo} não é um clone do metaKosmos/mk-oraculo`)
    return
  }
  const base = opt('--base') ?? 'origin/main'
  const raiz = sh(`git merge-base ${base} HEAD`)
  if (!raiz) {
    reprovado('base da comparação', `não achei ${base}; rode: git fetch origin main`)
    return
  }
  const lista = new Set()
  for (const l of (sh(`git diff --name-only ${raiz}`) ?? '').split('\n')) if (l) lista.add(l)
  for (const l of (sh('git ls-files --others --exclude-standard') ?? '').split('\n')) if (l) lista.add(l)
  const arquivos = [...lista].sort()
  if (arquivos.length === 0) {
    aviso('arquivos mudados', 'nenhum; ainda não há mudança para conferir')
    return
  }
  ok('arquivos mudados', `${arquivos.length} em relação a ${base}`)

  const fora = []
  for (const a of arquivos) for (const [re, motivo] of PROIBIDO) if (re.test(a)) fora.push(`${a} (${motivo})`)
  if (fora.length) reprovado('fora do alcance da skill', fora.join('; '))
  else ok('fora do alcance da skill', 'nenhum arquivo')

  const schema = arquivos.filter((a) => /^src\/collections\//.test(a) || a === 'src/payload.config.ts')
  const migTs = arquivos.filter((a) => /^src\/migrations\/\d{8}_\d{6}_.+\.ts$/.test(a))
  const migJson = arquivos.filter((a) => /^src\/migrations\/\d{8}_\d{6}_.+\.json$/.test(a))
  const layout = arquivos.filter((a) => /^src\/(app\/\(frontend\)|components)\//.test(a))
  const testes = arquivos.filter((a) => /^tests\//.test(a))
  const tipo = schema.length && layout.length ? 'schema e layout' : schema.length ? 'schema' : layout.length ? 'layout' : 'outro'
  ok('tipo da mudança', tipo)

  if (schema.length) {
    if (migTs.length === 0) reprovado('migration', 'mudou collection e não há migration; rode: pnpm payload migrate:create <nome>')
    else if (migTs.length > 1) aviso('migration', `${migTs.length} migrations na mesma mudança; o normal é uma`)
    else ok('migration', migTs[0])
    for (const ts of migTs)
      if (!migJson.includes(ts.replace(/\.ts$/, '.json'))) reprovado('snapshot da migration', `falta o .json par de ${ts}`)
    if (migTs.length && !arquivos.includes('src/migrations/index.ts'))
      reprovado('índice das migrations', 'src/migrations/index.ts não mudou')
    if (!arquivos.includes('src/payload-types.ts'))
      reprovado('tipos do Payload', 'src/payload-types.ts não mudou; rode: pnpm generate:types')
    else ok('tipos do Payload', 'regenerados')
  } else if (migTs.length) {
    aviso('migration', 'há migration sem mudança em collection; confira se é intencional')
  }

  for (const ts of migTs) {
    const up = corpoDoUp(readFileSync(path.join(repo, ts), 'utf8'))
    const riscos = []
    if (/DROP\s+(TABLE|COLUMN|TYPE)/i.test(up)) riscos.push('apaga tabela, coluna ou tipo')
    if (/SET\s+DATA\s+TYPE/i.test(up)) riscos.push('muda o tipo de uma coluna')
    if (/\bRENAME\b/i.test(up)) riscos.push('renomeia')
    if (/\bSET\s+NOT\s+NULL\b/i.test(up) || /ADD\s+COLUMN[^;]*NOT\s+NULL(?![^;]*DEFAULT)/i.test(up))
      riscos.push('coluna obrigatória sem valor padrão')
    if (/\b(DELETE\s+FROM|TRUNCATE)\b/i.test(up)) riscos.push('apaga dado')
    if (riscos.length) reprovado('migration destrutiva', `${ts}: ${riscos.join(', ')}. Pare e leve ao David antes de seguir`)
    else ok('migration só acrescenta', ts)
  }

  if ((schema.length || layout.length) && testes.length === 0)
    reprovado('teste da mudança', 'mudou código e nenhum arquivo em tests/ mudou; todo comportamento novo ganha teste')
  else if (testes.length) ok('teste da mudança', testes.join(', '))

  if (tem('--rodar')) {
    for (const [nome, cmd] of [
      ['typecheck', 'pnpm typecheck'],
      ['lint', 'pnpm lint'],
      ['testes de unidade', 'pnpm test:unit'],
    ]) {
      try {
        execSync(cmd, { cwd: repo, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] })
        ok(nome, 'passou')
      } catch (e) {
        const saida = `${e.stdout ?? ''}${e.stderr ?? ''}`.trim().split('\n').slice(-25).join('\n')
        reprovado(nome, `falhou:\n${saida}`)
      }
    }
  } else {
    aviso('typecheck, lint e testes', 'não rodados; use --rodar')
  }
}

if (modo === 'preparo') await preparo()
else if (modo === 'mudanca') mudanca()
else {
  console.error('uso: oraculo-conferir.mjs preparo|mudanca [--repo <pasta>] [--base <ref>] [--rodar] [--json]')
  process.exit(2)
}

const reprovados = itens.filter((i) => i.estado === 'reprovado').length
if (tem('--json')) {
  console.log(JSON.stringify({ modo, repo, aprovado: reprovados === 0, itens }, null, 2))
} else {
  for (const i of itens) console.log(`[${i.estado}] ${i.nome}: ${i.detalhe}`)
  console.log(reprovados === 0 ? '\nresultado: aprovado' : `\nresultado: ${reprovados} item(ns) reprovado(s)`)
}
process.exit(reprovados === 0 ? 0 : 1)
