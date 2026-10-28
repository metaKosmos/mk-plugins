#!/usr/bin/env python3
"""Converte o Markdown do projeto em HTML e, com --subir, cria um Google Doc nativo
pelo gws, com tabelas reais (o Drive converte o HTML no upload).

Só biblioteca padrão do Python 3. Não precisa de python-docx nem de pandoc.

Uso:
  python3 -I gerar-doc.py <entrada.md> --html <saida.html> [--camada <pasta>]
  python3 -I gerar-doc.py <entrada.md> --html <saida.html> [--camada <pasta>] --subir --nome "Projeto X" [--pasta <folderId>]
  python3 -I gerar-doc.py <entrada.md> --html <saida.html> [--camada <pasta>] --atualizar <docId> [--nome "Projeto X"]
  python3 -I gerar-doc.py <entrada.md> --html <saida.html> [--camada <pasta>] --registrar --doc-id <id> --url <link> [--tabelas-doc N] [--descricao-no-drive vN] [--nome "Projeto X"] [--gravar-drive drive.json]

Sem gws: `--via auto` (o padrão) usa o gws se ele estiver no PATH e, se não estiver, o
conector Google Drive do claude.ai (`--via conector` força, `--via gws` exige o gws). No conector o script
NÃO chama o Drive: com --subir imprime `via=conector`, `acao=criar` e os parâmetros do create_file
(`create_file.title`, `.contentMimeType`, `.textContent=@<doc.html>`, `.parentId`) e do update_file que
grava a versão (`update_file.description`), e termina com `subida=pendente`. A skill faz as duas chamadas
ao MCP e volta com `--registrar`, que confere id, url e versão e imprime doc_id, url, versao, tabelas_*.
Pelo conector `--atualizar` é recusado (exit 6, `copia_nova=nao`): o update_file só muda metadados, e
nenhuma ferramenta do conector troca o conteúdo de um arquivo. Criar outro arquivo quebraria "um doc por
projeto", então o script não cria.

Subconjunto de Markdown aceito:
  # H1, ## H2, ### H3 | parágrafo (linha em branco separa) | - item | 1. item
  tabela com pipes (linha 2 é o separador |---|)
  <!-- larguras: 8,62,30 -->  na linha acima da tabela: largura de cada coluna em %
  **negrito**, [texto](https://url), --- (linha horizontal), <br> dentro de célula

Escrita e marca vêm da CAMADA (pasta com camada.json), nunca do código:
  marca.normalizar  troca a variante pela grafia certa antes do lint (o arquivo de entrada é
                    regravado e as trocas saem em `normalizado=N`)
  marca.reprovar    padrões que reprovam o texto
  escrita.travessao_proibido  reprova traço longo e meia-risca
URL nunca é alterada nem reprovada. As expressões são as mesmas de scripts/lib/camada.mjs
(`{{ANTES}}` expande para o prefixo que deixa URL, caminho e e-mail de fora), compiladas com
re.ASCII para que a classe de palavra signifique o mesmo que em JavaScript.
A camada é achada, na ordem, por --camada, pela variável VANTA_CAMADA, por ./camada e por
camada/ ao lado do arquivo de entrada (ou na pasta acima). Sem camada, nenhuma regra de marca
ou de escrita é aplicada e a saída diz `camada=nenhuma`.

O documento do projeto é um arquivo só no Drive. `--subir` cria; `--atualizar <docId>` troca o
conteúdo do MESMO arquivo (mesmo link, nunca uma cópia) e grava a versão na `description` do
arquivo. A versão sai do título do doc.md: a linha logo abaixo do H1 termina em "· v<N>".
Atualizar para uma versão menor que a do arquivo no Drive é recusado (exit 4): é o doc velho
sobrescrevendo o novo. Com projeto.json ao lado do doc.md já trazendo `documento.id`, `--subir`
é recusado (exit 2): o projeto já tem o doc dele, use `--atualizar`.
Limite do Drive: o histórico de versões de um Google Doc não aceita nome pela API. A versão
nomeada fica no nome do arquivo (--nome) e na description.

Upload: erro 5xx do Drive tenta de novo até 3 vezes com espera curta antes de falhar.

Saídas em stdout (linhas chave=valor): camada, normalizado, lint, tabelas_html, e com --subir:
doc_id, url, tabelas_doc, tabelas_ok; com --atualizar também versao_anterior, atualizado e
copia_nova=nao. `versao=` sai sempre que o título traz a versão. Código de saída 0 só se o lint
passa e, no upload, nenhuma tabela se perdeu; 2 uso; 3 tabela perdida; 4 versão que regride;
5 o gws falhou (`erro=` diz por quê; id que o Drive não acha vira "não achei o arquivo <id> no Drive");
6 --atualizar sem gws (o conector não troca conteúdo); 7 --registrar com a description do Drive diferente da versão do doc.md.
"""
import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

CSS = """
body{font-family:Arial,Helvetica,sans-serif;font-size:11pt;color:#111111;line-height:1.35}
h1{font-size:22pt;margin:0 0 4pt 0}
h2{font-size:15pt;margin:18pt 0 6pt 0}
h3{font-size:12pt;margin:12pt 0 4pt 0}
p{margin:0 0 8pt 0}
table{border-collapse:collapse;width:100%;margin:6pt 0 10pt 0}
th{background:#F5F5F5;border:1px solid #BBBBBB;padding:4px;text-align:left;vertical-align:top;font-weight:bold}
td{border:1px solid #BBBBBB;padding:4px;vertical-align:top}
a{color:#1155CC}
hr{border:0;border-top:1px solid #E2E2E2}
"""


ANTES = r"(?<![\w/.:@#-])"
URL = re.compile(r"https?://[^\s)>\]|]+")


def expandir(padrao):
    return padrao.replace("{{ANTES}}", ANTES)


def achar_camada(explicito, entrada):
    """Pasta da camada (a que tem camada.json), ou None. Mesma ordem de scripts/lib/camada.mjs."""
    if explicito:
        candidatos = [Path(explicito)]
    else:
        candidatos = []
        if os.environ.get("VANTA_CAMADA"):
            candidatos.append(Path(os.environ["VANTA_CAMADA"]))
        candidatos.append(Path("camada"))
        base = Path(entrada).resolve().parent
        candidatos += [base / "camada", base.parent / "camada"]
    for c in candidatos:
        if (c / "camada.json").is_file():
            return c.resolve()
    return None


def carregar_regras(pasta):
    """Compila as regras da camada: {travessao, reprovar, normalizar}. Pasta None: sem regra."""
    vazio = {"travessao": False, "reprovar": [], "normalizar": []}
    if pasta is None:
        return vazio
    c = json.loads((pasta / "camada.json").read_text(encoding="utf-8"))
    if c.get("versao") != 1:
        raise SystemExit("erro=camada.json: versao deve ser 1")
    marca = c.get("marca", {})

    def comp(r):
        return re.compile(expandir(r["padrao"]), re.A | (re.I if r.get("ignorar_caixa") else 0))

    return {
        "travessao": bool(c.get("escrita", {}).get("travessao_proibido")),
        "reprovar": [(comp(r), r["mensagem"]) for r in marca.get("reprovar", [])],
        "normalizar": [(comp(r), r["para"], r.get("aceitar", [r["para"]])) for r in marca.get("normalizar", [])],
    }


def fora_de_url(texto, f):
    """Aplica f só nos trechos que não são URL."""
    partes = URL.split(texto)
    urls = URL.findall(texto)
    out = []
    for k, parte in enumerate(partes):
        out.append(f(parte))
        if k < len(urls):
            out.append(urls[k])
    return "".join(out)


def normalizar(texto, regras):
    """Corrige a grafia que vem da fonte, pelas regras `marca.normalizar` da camada.
    Não mexe em URL. Devolve (texto novo, lista de trocas "antes -> depois")."""
    trocas = []

    def uma(trecho):
        for regex, para, aceitar in regras["normalizar"]:
            def sub(m):
                if m.group(0) in aceitar:
                    return m.group(0)
                trocas.append(f"{m.group(0)} -> {para}")
                return para
            trecho = regex.sub(sub, trecho)
        return trecho

    return fora_de_url(texto, uma), trocas


def lint(texto, regras):
    """Devolve a lista de problemas de escrita que a camada não aceita. Roda depois de
    normalizar(): reprova o que a normalização não pegou. URL nunca reprova."""
    erros = []
    for n, linha in enumerate(URL.sub("", texto).splitlines(), 1):
        if regras["travessao"] and ("\u2014" in linha or "\u2013" in linha):
            erros.append(f"linha {n}: traço longo ou meia-risca")
        for regex, mensagem in regras["reprovar"]:
            if regex.search(linha):
                erros.append(f"linha {n}: {mensagem}")
        for regex, para, aceitar in regras["normalizar"]:
            for m in regex.finditer(linha):
                if m.group(0) not in aceitar:
                    erros.append(f'linha {n}: escrito "{m.group(0)}" (a grafia é "{para}")')
    return erros


VERSAO_TITULO = re.compile(r"·\s*(v[1-9]\d*)\s*$")
VERSAO_ARQUIVO = re.compile(r"\bv([1-9]\d*)\b")


def versao_do_doc(md):
    """Versão do título: a linha logo abaixo do H1 termina em '· v<N>'. None se não houver."""
    linhas = md.splitlines()
    for i, l in enumerate(linhas):
        if re.match(r"#\s", l.strip()):
            abaixo = next((x.strip() for x in linhas[i + 1:] if x.strip()), "")
            m = VERSAO_TITULO.search(abaixo)
            return m.group(1) if m else None
    return None


def documento_registrado(entrada):
    """Id do doc que o projeto.json ao lado do doc.md já registra em `documento`, ou None."""
    arq = Path(entrada).resolve().parent / "projeto.json"
    if not arq.is_file():
        return None
    try:
        return (json.loads(arq.read_text(encoding="utf-8")).get("documento") or {}).get("id")
    except (OSError, ValueError, AttributeError):
        return None


def inline(txt):
    t = html.escape(txt, quote=True)
    t = t.replace("&lt;br&gt;", "<br>")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s\"'<>]+)\)", r'<a href="\2">\1</a>', t)
    return t


def celulas(linha):
    linha = linha.strip()
    if linha.startswith("|"):
        linha = linha[1:]
    if linha.endswith("|"):
        linha = linha[:-1]
    return [c.strip() for c in linha.split("|")]


def converter(md):
    out = []
    linhas = md.splitlines()
    i = 0
    larguras = None
    n_tabelas = 0
    while i < len(linhas):
        l = linhas[i]
        s = l.strip()
        if not s:
            i += 1
            continue
        m = re.match(r"<!--\s*larguras:\s*([\d.,\s]+)-->", s)
        if m:
            larguras = [float(x) for x in m.group(1).split(",") if x.strip()]
            i += 1
            continue
        if s.startswith("<!--"):
            i += 1
            continue
        m = re.match(r"(#{1,3})\s+(.*)", s)
        if m:
            k = len(m.group(1))
            out.append(f"<h{k}>{inline(m.group(2))}</h{k}>")
            i += 1
            continue
        if s == "---":
            out.append("<hr>")
            i += 1
            continue
        if s.startswith("|"):
            bloco = []
            while i < len(linhas) and linhas[i].strip().startswith("|"):
                bloco.append(linhas[i])
                i += 1
            cab = celulas(bloco[0])
            corpo = [celulas(b) for b in bloco[1:] if not re.fullmatch(r"[\s|:\-]+", b)]
            n = len(cab)
            larg = larguras if larguras and len(larguras) == n else None
            larguras = None
            h = ['<table style="width:100%;border-collapse:collapse">']
            if larg:
                h.append("<colgroup>" + "".join(f'<col style="width:{w}%">' for w in larg) + "</colgroup>")
            h.append("<tr>" + "".join(
                f'<th style="width:{larg[j]}%">{inline(c)}</th>' if larg else f"<th>{inline(c)}</th>"
                for j, c in enumerate(cab)) + "</tr>")
            for r in corpo:
                r = (r + [""] * n)[:n]
                h.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            h.append("</table>")
            out.append("".join(h))
            n_tabelas += 1
            continue
        if re.match(r"[-*]\s+", s) or re.match(r"\d+\.\s+", s):
            ordenada = bool(re.match(r"\d+\.\s+", s))
            itens = []
            while i < len(linhas) and re.match(r"\s*([-*]|\d+\.)\s+", linhas[i]):
                itens.append(re.sub(r"^\s*([-*]|\d+\.)\s+", "", linhas[i]))
                i += 1
            tag = "ol" if ordenada else "ul"
            out.append(f"<{tag}>" + "".join(f"<li>{inline(x)}</li>" for x in itens) + f"</{tag}>")
            continue
        par = []
        while i < len(linhas) and linhas[i].strip() and not re.match(
                r"\s*(#{1,3}\s|\||[-*]\s|\d+\.\s|---$|<!--)", linhas[i]):
            par.append(linhas[i].strip())
            i += 1
        if not par:  # linha que casou nenhum bloco e nenhum parágrafo: evita laço infinito
            par = [s]
            i += 1
        out.append(f"<p>{inline(' '.join(par))}</p>")
    corpo = "\n".join(out)
    doc = (f'<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head>'
           f"<body>\n{corpo}\n</body></html>")
    return doc, n_tabelas


def so_json(saida):
    """O gws imprime 'Using keyring backend' antes do JSON."""
    ini = saida.find("{")
    if ini < 0:
        raise RuntimeError(f"gws não devolveu JSON: {saida[:300]}")
    return json.loads(saida[ini:])


class GwsErro(RuntimeError):
    """O gws falhou. `saida` é o que ele escreveu, para quem precisa distinguir 404 de 403."""

    def __init__(self, msg, saida=""):
        super().__init__(msg)
        self.saida = saida


NAO_ACHOU = re.compile(r"\b404\b|notFound|File not found", re.I)

TRANSITORIO = re.compile(r"\b5\d\d\b|backendError|internalError|Internal (Server )?Error|Service Unavailable", re.I)


def gws(args, cwd, tentativas=3, espera=2.0):
    # O gws recusa --upload fora do diretório atual: roda sempre na pasta do HTML.
    # Erro 5xx do Drive é transitório: tenta de novo (até `tentativas`, espera crescente).
    # Erro que não é 5xx (auth, 403, 404) falha na hora.
    for k in range(1, tentativas + 1):
        r = subprocess.run(["gws", *args], capture_output=True, text=True, cwd=cwd)
        if r.returncode == 0:
            if k > 1:
                print(f"tentativas={k}")
            return so_json(r.stdout)
        msg = f"gws falhou ({r.returncode}): {r.stdout[-400:]} {r.stderr[-400:]}"
        if k == tentativas or not TRANSITORIO.search(r.stdout + r.stderr):
            raise GwsErro(msg + (f" [após {k} tentativas]" if k > 1 else ""), r.stdout + r.stderr)
        print(f"aviso=erro transitório do Drive, nova tentativa {k + 1} de {tentativas}", file=sys.stderr)
        time.sleep(espera * k)


def atualizar(a, caminho, versao):
    """Troca o conteúdo do Google Doc `a.atualizar` pelo HTML, no mesmo arquivo (mesmo link)."""
    if not shutil.which("gws"):
        print("erro=gws não encontrado no PATH")
        return 2
    id_ = a.atualizar
    try:
        atual = gws(["drive", "files", "get", "--params", json.dumps(
            {"fileId": id_, "fields": "id,name,description", "supportsAllDrives": True})], caminho.parent)
    except GwsErro as e:
        if NAO_ACHOU.search(e.saida):
            print(f"erro=não achei o arquivo {id_} no Drive: confira o id em documento.id do projeto.json (ou suba com --subir se o projeto ainda não tem doc)")
            return 5
        raise
    m = VERSAO_ARQUIVO.search(atual.get("description") or "")
    anterior = f"v{m.group(1)}" if m else None
    print(f"versao_anterior={anterior or 'desconhecida'}")
    if anterior and int(versao[1:]) < int(anterior[1:]):
        print(f"erro=o arquivo do Drive está em {anterior} e este doc.md é {versao}: atualizar sobrescreveria o novo com o velho")
        return 4
    if anterior == versao:
        print(f"aviso=mesma versão ({versao}): o conteúdo é trocado, mas ninguém verá versão nova no histórico")
    corpo = {"description": versao}
    if a.nome:
        corpo["name"] = a.nome
    novo = gws(["drive", "files", "update",
                "--params", json.dumps({"fileId": id_, "fields": "id,name,description,webViewLink", "supportsAllDrives": True}),
                "--json", json.dumps(corpo),
                "--upload", caminho.name, "--upload-content-type", "text/html"], caminho.parent)
    print(f"doc_id={novo.get('id', id_)}")
    print(f"url={novo.get('webViewLink', '')}")
    print("atualizado=sim")
    print("copia_nova=nao")
    lido = gws(["docs", "documents", "get", "--params", json.dumps({"documentId": id_})], caminho.parent)
    n_doc = sum(1 for e in lido["body"]["content"] if "table" in e)
    n_html = len(re.findall(r"<table", caminho.read_text(encoding="utf-8")))
    print(f"tabelas_doc={n_doc}")
    ok = n_doc == n_html
    print(f"tabelas_ok={'sim' if ok else 'NAO'}")
    return 0 if ok else 3


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entrada")
    ap.add_argument("--html", required=True)
    ap.add_argument("--subir", action="store_true")
    ap.add_argument("--nome")
    ap.add_argument("--pasta")
    ap.add_argument("--camada")
    ap.add_argument("--atualizar", metavar="DOC_ID", help="troca o conteúdo deste Google Doc no lugar, sem criar cópia")
    ap.add_argument("--via", choices=["auto", "gws", "conector"], default="auto",
                    help="auto: gws se estiver no PATH, senão o conector Google Drive do claude.ai")
    ap.add_argument("--registrar", action="store_true",
                    help="depois da subida pelo conector: confere id, url e versão e imprime as chaves do documento")
    ap.add_argument("--doc-id", help="--registrar: o id que o conector devolveu")
    ap.add_argument("--url", help="--registrar: o link que o conector devolveu")
    ap.add_argument("--tabelas-doc", type=int, help="--registrar: quantas tabelas o Doc criado tem")
    ap.add_argument("--descricao-no-drive", help="--registrar: a description que o Drive devolveu depois do update_file")
    ap.add_argument("--gravar-drive", metavar="ARQUIVO", help="--registrar: grava {id,name,description} para o conferir-versao --drive")
    a = ap.parse_args()
    if a.subir and a.atualizar:
        print("erro=--subir cria um arquivo e --atualizar troca o de um existente: escolha um")
        return 2
    if a.registrar and (a.subir or a.atualizar):
        print("erro=--registrar vem depois da subida e não se combina com --subir nem --atualizar")
        return 2
    if a.registrar and not (a.doc_id and a.url):
        print("erro=--registrar exige --doc-id e --url (o que o create_file do conector devolveu)")
        return 2

    pasta_camada = achar_camada(a.camada, a.entrada)
    regras = carregar_regras(pasta_camada)
    print(f"camada={pasta_camada if pasta_camada else 'nenhuma (sem regras de marca e de escrita)'}")
    md = Path(a.entrada).read_text(encoding="utf-8")
    md, trocas = normalizar(md, regras)
    if trocas:
        Path(a.entrada).write_text(md, encoding="utf-8")  # doc.md fica igual ao que sobe
        print(f"normalizado={len(trocas)}")
        for t in trocas:
            print("  " + t)
    erros = lint(md, regras)
    if erros:
        print("lint=FALHOU")
        for e in erros:
            print("  " + e)
        return 1
    print("lint=ok")
    versao = versao_do_doc(md)
    if versao:
        print(f"versao={versao}")
    if a.atualizar and not versao:
        print("erro=o título do doc.md não traz a versão: a linha abaixo do # termina em '· v<N>' (ex.: 20/10/2026 · Fulano · v3)")
        return 2
    registrado = None if a.atualizar else documento_registrado(a.entrada)
    if a.subir and registrado:
        print(f"erro=o projeto.json ao lado já registra o documento {registrado}: use --atualizar {registrado}, não crie cópia")
        return 2
    doc, n_html = converter(md)
    caminho = Path(a.html).resolve()
    caminho.write_text(doc, encoding="utf-8")
    print(f"html={caminho}")
    print(f"tabelas_html={n_html}")
    if a.registrar:
        return registrar(a, md, versao, n_html)
    if not a.subir and not a.atualizar:
        return 0
    if a.subir and not a.nome:
        print("erro=--subir exige --nome")
        return 2
    via = a.via
    if via == "auto":
        via = "gws" if shutil.which("gws") else "conector"
    if via == "conector":
        return preparar_conector(a, caminho, versao)
    if not shutil.which("gws"):
        print("erro=gws não encontrado no PATH")
        return 2
    try:
        return atualizar(a, caminho, versao) if a.atualizar else subir(a, caminho, versao, n_html)
    except (RuntimeError, ValueError) as e:  # GwsErro é RuntimeError; ValueError é JSON ilegível do gws
        print("erro=" + " ".join(str(e).split()))
        return 5


DOC_URL = re.compile(r"^https://docs\.google\.com/document/(?:u/\d+/)?d/([\w-]+)(?:[/?#].*)?$")


def preparar_conector(a, caminho, versao):
    """Sem gws: não chama o Drive. Imprime o que a skill passa ao conector Google Drive do claude.ai
    (create_file e, com o id devolvido, update_file para a description) e para aqui. A decisão
    (nome, versão, recusa de cópia) é toda tomada aqui, em código; a chamada ao MCP é da skill."""
    print("via=conector")
    if a.atualizar:
        # O update_file do conector só muda metadados (title, description, parentId...): não tem
        # parâmetro de conteúdo, e nenhuma outra ferramenta do conector troca o conteúdo de um
        # arquivo. Criar outro arquivo quebraria o contrato de um doc por projeto (mesmo id e link).
        print(f"html={caminho}")
        print("atualizado=nao")
        print("copia_nova=nao")
        print("erro=sem o gws não dá para trocar o conteúdo do mesmo arquivo: o conector Google Drive do claude.ai "
              "(update_file só muda metadados) não aceita conteúdo novo. Não crio cópia: autentique o gws "
              f"e rode --atualizar {a.atualizar} de novo, ou troque o conteúdo do Doc à mão com o html acima")
        return 6
    print("acao=criar")
    print(f"create_file.title={a.nome}")
    print("create_file.contentMimeType=text/html")
    print(f"create_file.textContent=@{caminho}")
    if a.pasta:
        print(f"create_file.parentId={a.pasta}")
    if versao:
        print(f"update_file.description={versao}")
        if not re.search(rf"\b{re.escape(versao)}\b", a.nome):
            print(f"aviso=o nome do arquivo não traz a versão {versao}: a versão fica só na description")
    print("subida=pendente")
    return 0


def registrar(a, md, versao, n_html):
    """Depois da subida pelo conector: confere id, url e versão e imprime as chaves que o caminho do
    gws imprime (doc_id, url, versao, tabelas_*), para a etapa D gravar o bloco `documento`."""
    print("via=conector")
    if not versao:
        print("erro=o título do doc.md não traz a versão: a linha abaixo do # termina em '· v<N>' (ex.: 20/10/2026 · Fulano · v3)")
        return 2
    m = DOC_URL.match(a.url.strip())
    if not m or m.group(1) != a.doc_id:
        print(f"erro=a url não é do documento {a.doc_id}: esperado https://docs.google.com/document/d/{a.doc_id}/...")
        return 2
    # O conector devolve o link com ?usp=drivesdk&ouid=<número da conta>: o link do documento é só o /edit.
    a.url = f"https://docs.google.com/document/d/{a.doc_id}/edit"
    registrado = documento_registrado(a.entrada)
    if registrado and registrado != a.doc_id:
        print("copia_nova=sim")
        print(f"erro=o projeto.json ao lado já registra o documento {registrado} e o conector criou {a.doc_id}: "
              f"é uma cópia. Apague a cópia (trash_file) e atualize o {registrado}")
        return 2
    if a.descricao_no_drive is not None and a.descricao_no_drive.strip() != versao:
        print(f"erro=o Drive está em {a.descricao_no_drive.strip() or 'sem versão'} e o doc.md é {versao}: "
              "refaça o update_file da description")
        return 7
    print(f"doc_id={a.doc_id}")
    print(f"url={a.url}")
    print(f"tabelas_html={n_html}")
    if a.gravar_drive:
        Path(a.gravar_drive).write_text(json.dumps(
            {"id": a.doc_id, "name": a.nome or "", "description": a.descricao_no_drive or versao},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"drive_json={Path(a.gravar_drive).resolve()}")
    if a.tabelas_doc is None:
        print("tabelas_ok=nao_verificavel")
        return 0
    print(f"tabelas_doc={a.tabelas_doc}")
    ok = a.tabelas_doc == n_html
    print(f"tabelas_ok={'sim' if ok else 'NAO'}")
    return 0 if ok else 3


def subir(a, caminho, versao, n_html):
    corpo = {"name": a.nome, "mimeType": "application/vnd.google-apps.document"}
    if versao:
        corpo["description"] = versao
    if a.pasta:
        corpo["parents"] = [a.pasta]
    criado = gws(["drive", "files", "create", "--json", json.dumps(corpo),
                  "--upload", caminho.name, "--upload-content-type", "text/html",
                  "--params", json.dumps({"fields": "id,name,webViewLink", "supportsAllDrives": True})], caminho.parent)
    doc_id = criado["id"]
    print(f"doc_id={doc_id}")
    print(f"url={criado.get('webViewLink', '')}")
    lido = gws(["docs", "documents", "get", "--params", json.dumps({"documentId": doc_id})], caminho.parent)
    n_doc = sum(1 for e in lido["body"]["content"] if "table" in e)
    print(f"tabelas_doc={n_doc}")
    ok = n_doc == n_html
    print(f"tabelas_ok={'sim' if ok else 'NAO'}")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
