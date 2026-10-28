"""PROD-3072: doc, mapa e Linear apontam a mesma versão do mesmo documento.

Cobre o gerar-doc.py (atualiza o mesmo arquivo do Drive, nunca cria cópia), o bloco `documento`
do projeto.json, o conferir-versao.mjs (doc, canvas e Linear contra a mesma referência) e o
teste principal do ponta a ponta com um gws de mentira."""
import json
import os
import stat
import sys
import unittest

from _util import (EXEMPLO_CAMADA, GERAR_DOC, gravar_json, node, precisa_node, projeto,
                   python_isolado, tmp)

URL = "https://docs.google.com/document/d/DOC1/edit"
OUTRA_URL = "https://docs.google.com/document/d/OUTRO9/edit"

# gws de mentira: grava cada chamada em $GWS_LOG e responde como o Drive responderia.
GWS_FALSO = """#!{python}
import json, os, sys
a = sys.argv[1:]
with open(os.environ["GWS_LOG"], "a", encoding="utf-8") as f:
    f.write(" ".join(a[:3]) + "\\n")
    f.write(json.dumps(a) + "\\n")
if os.environ.get("GWS_FALHA") and a[:2] == ["drive", "files"] and a[2] in os.environ["GWS_FALHA_EM"].split(","):
    print("Using keyring backend: keyring", file=sys.stderr)
    print(os.environ["GWS_FALHA"])
    sys.exit(1)
if a[:3] == ["drive", "files", "create"]:
    print(json.dumps({{"id": "DOC1", "name": "n", "description": "v1", "webViewLink": "{url}"}}))
elif a[:3] == ["drive", "files", "get"]:
    print(json.dumps({{"id": "DOC1", "name": "n", "description": os.environ.get("GWS_DESCRICAO", "v1")}}))
elif a[:3] == ["drive", "files", "update"]:
    print(json.dumps({{"id": "DOC1", "name": "n", "description": "novo", "webViewLink": "{url}"}}))
elif a[:3] == ["docs", "documents", "get"]:
    print(json.dumps({{"body": {{"content": [{{"table": {{}}}}]}}}}))
else:
    sys.exit(9)
"""


def doc_md(versao):
    return f"# Projeto Exemplo | fX Loja\n20/10/2026 · Pessoa que rodou · {versao}\n\n## 0. Ficha\n\n<!-- larguras: 30,70 -->\n| Campo | Valor |\n|---|---|\n| Dono | Pessoa Exemplo |\n"


def ambiente(pasta, descricao="v1"):
    """Pasta com um gws falso na frente do PATH. Devolve (env, caminho do log)."""
    binpasta = os.path.join(pasta, "bin")
    os.makedirs(binpasta)
    gws = os.path.join(binpasta, "gws")
    with open(gws, "w", encoding="utf-8") as f:
        f.write(GWS_FALSO.format(python=sys.executable, url=URL))
    os.chmod(gws, os.stat(gws).st_mode | stat.S_IEXEC)
    log = os.path.join(pasta, "gws.log")
    env = {"PATH": binpasta + os.pathsep + os.environ["PATH"], "GWS_LOG": log, "GWS_DESCRICAO": descricao}
    return env, log


def chamadas(log):
    if not os.path.exists(log):
        return []
    with open(log, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("[")]


def args_do_update(log):
    with open(log, encoding="utf-8") as f:
        linhas = f.read().splitlines()
    for i, l in enumerate(linhas):
        if l == "drive files update":
            return json.loads(linhas[i + 1])
    return None


def gravar(pasta, nome, texto):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


def com_documento(versao="v3", url=URL, rotulo=None, **extra):
    """O completo.json com o bloco `documento` e a fonte que o canvas mostra."""
    d = projeto()
    d["documento"] = {"id": "DOC1", "url": url, "versao": versao, "atualizado_em": "2026-10-20"}
    d["ref"]["fontes"].append({"rotulo": rotulo or f"Documento do projeto, {versao}", "url": url})
    d.update(extra)
    return d


class TesteGerarDocAtualiza(unittest.TestCase):
    def rodar(self, pasta, md, *extra, descricao="v1", falha=None, falha_em="get"):
        env, log = ambiente(pasta, descricao)
        if falha:
            env.update(GWS_FALHA=falha, GWS_FALHA_EM=falha_em)
        entrada = gravar(pasta, "doc.md", md)
        rc, out, err = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "doc.html"),
                                      "--camada", EXEMPLO_CAMADA, *extra, env=env)
        return rc, out + err, log

    def test_subir_cria_e_grava_a_versao_no_arquivo(self):
        pasta = tmp()
        rc, out, log = self.rodar(pasta, doc_md("v1"), "--subir", "--nome", "Projeto Exemplo - v1")
        self.assertEqual(rc, 0, out)
        self.assertIn("versao=v1", out)
        self.assertIn("doc_id=DOC1", out)
        self.assertIn("drive files create", chamadas(log))

    def test_atualizar_troca_o_conteudo_no_mesmo_arquivo_sem_copia(self):
        pasta = tmp()
        rc, out, log = self.rodar(pasta, doc_md("v2"), "--atualizar", "DOC1", "--nome", "Projeto Exemplo - v2")
        self.assertEqual(rc, 0, out)
        self.assertIn("doc_id=DOC1", out)
        self.assertIn(f"url={URL}", out)
        self.assertIn("versao=v2", out)
        self.assertIn("versao_anterior=v1", out)
        self.assertIn("copia_nova=nao", out)
        self.assertIn("tabelas_ok=sim", out)
        c = chamadas(log)
        self.assertNotIn("drive files create", c, "atualizar nunca cria arquivo")
        self.assertIn("drive files update", c)
        a = args_do_update(log)
        self.assertEqual(json.loads(a[a.index("--params") + 1])["fileId"], "DOC1")
        corpo = json.loads(a[a.index("--json") + 1])
        self.assertEqual(corpo["description"], "v2", "a versão fica no arquivo do Drive")
        self.assertEqual(corpo["name"], "Projeto Exemplo - v2")
        self.assertIn("--upload", a)

    def test_atualizar_sem_nome_nao_renomeia(self):
        pasta = tmp()
        rc, out, log = self.rodar(pasta, doc_md("v2"), "--atualizar", "DOC1")
        self.assertEqual(rc, 0, out)
        corpo = json.loads(args_do_update(log)[args_do_update(log).index("--json") + 1])
        self.assertNotIn("name", corpo)

    def test_atualizar_com_id_inexistente_sai_com_erro_legivel_sem_traceback(self):
        # PROD-3072: estourava "RuntimeError: gws falhou (1)" com traceback
        pasta = tmp()
        rc, out, log = self.rodar(pasta, doc_md("v2"), "--atualizar", "NAOEXISTE",
                                  falha='{"error": {"code": 404, "message": "File not found: NAOEXISTE."}}')
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("erro=não achei o arquivo NAOEXISTE no Drive", out)
        self.assertNotIn("drive files update", chamadas(log), "não tentou gravar")

    def test_atualizar_com_outra_falha_do_gws_tambem_sai_com_erro_sem_traceback(self):
        pasta = tmp()
        rc, out, _ = self.rodar(pasta, doc_md("v2"), "--atualizar", "DOC1",
                                falha='{"error": {"code": 403, "message": "The caller does not have permission"}}')
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("erro=", out)
        self.assertIn("403", out)

    def test_subir_com_falha_do_gws_sai_com_erro_sem_traceback(self):
        pasta = tmp()
        rc, out, _ = self.rodar(pasta, doc_md("v1"), "--subir", "--nome", "Projeto Exemplo - v1", falha_em="create",
                                falha='{"error": {"code": 403, "message": "Insufficient Permission"}}')
        self.assertNotEqual(rc, 0, out)
        self.assertNotIn("Traceback", out)
        self.assertIn("erro=", out)
        self.assertIn("403", out)

    def test_atualizar_para_versao_menor_que_a_do_drive_recusa(self):
        pasta = tmp()
        rc, out, log = self.rodar(pasta, doc_md("v2"), "--atualizar", "DOC1", descricao="v3")
        self.assertEqual(rc, 4, out)
        self.assertIn("v2", out)
        self.assertIn("v3", out)
        self.assertNotIn("drive files update", chamadas(log), "recusou antes de gravar")

    def test_atualizar_para_a_mesma_versao_avisa_e_segue(self):
        pasta = tmp()
        rc, out, _ = self.rodar(pasta, doc_md("v2"), "--atualizar", "DOC1", descricao="v2")
        self.assertEqual(rc, 0, out)
        self.assertIn("aviso=mesma versão", out)

    def test_atualizar_sem_versao_no_doc_recusa(self):
        pasta = tmp()
        rc, out, log = self.rodar(pasta, "# T\n20/10/2026 · Pessoa\n\nTexto.\n", "--atualizar", "DOC1")
        self.assertEqual(rc, 2, out)
        self.assertIn("versão", out)
        self.assertEqual(chamadas(log), [])

    def test_subir_com_documento_ja_registrado_recusa_a_copia_nova(self):
        pasta = tmp()
        gravar_json(pasta, "projeto.json", com_documento("v1"))
        rc, out, log = self.rodar(pasta, doc_md("v2"), "--subir", "--nome", "X")
        self.assertEqual(rc, 2, out)
        self.assertIn("--atualizar", out)
        self.assertIn("DOC1", out)
        self.assertEqual(chamadas(log), [], "nada foi criado")

    def test_subir_e_atualizar_juntos_recusam(self):
        pasta = tmp()
        rc, out, _ = self.rodar(pasta, doc_md("v2"), "--subir", "--atualizar", "DOC1", "--nome", "X")
        self.assertEqual(rc, 2, out)


@precisa_node
class TesteDocumentoNoProjeto(unittest.TestCase):
    def validar(self, dados):
        caminho = gravar_json(tmp(), "p.json", dados)
        return node("validar-projeto.mjs", caminho, "--camada", EXEMPLO_CAMADA, cwd=tmp())

    def test_documento_coerente_valida(self):
        rc, out, _ = self.validar(com_documento("v3"))
        self.assertEqual(rc, 0, out)

    def test_versao_fora_do_formato_reprova(self):
        d = com_documento("v3")
        d["documento"]["versao"] = "3"
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("documento.versao", out)

    def test_url_que_nao_e_do_doc_reprova(self):
        d = com_documento("v3")
        d["documento"]["url"] = "https://exemplo.com/outro"
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("documento.url", out)

    def test_id_diferente_do_da_url_reprova(self):
        d = com_documento("v3")
        d["documento"]["id"] = "OUTRO9"
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("documento.id", out)

    def test_mapa_sem_o_link_do_documento_reprova(self):
        d = com_documento("v3")
        d["ref"]["fontes"] = [f for f in d["ref"]["fontes"] if f["url"] != URL]
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("ref.fontes", out)
        self.assertIn(URL, out)

    def test_mapa_que_cita_versao_diferente_da_do_documento_reprova(self):
        # o caso de 20/10: o canvas citava a v2 com o doc em v3
        d = com_documento("v3", rotulo="Documento do projeto, v2")
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("v2", out)
        self.assertIn("v3", out)

    def test_v3_nao_casa_com_v30(self):
        d = com_documento("v3", rotulo="Documento do projeto, v30")
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1, out)

    def test_outro_documento_no_mapa_reprova(self):
        d = com_documento("v3")
        d["ref"]["fontes"].append({"rotulo": "Documento antigo, v2", "url": OUTRA_URL})
        rc, out, _ = self.validar(d)
        self.assertEqual(rc, 1)
        self.assertIn("OUTRO9", out)


@precisa_node
class TesteConferirVersao(unittest.TestCase):
    def preparar(self, doc_versao="v3", **kw):
        pasta = tmp()
        proj = gravar_json(pasta, "projeto.json", com_documento("v3"))
        doc = gravar(pasta, "doc.md", doc_md(doc_versao))
        return pasta, proj, doc

    def conferir(self, *args):
        return node("conferir-versao.mjs", "conferir", *args, cwd=tmp())

    def test_tudo_na_mesma_versao_passa(self):
        pasta, proj, doc = self.preparar()
        canvas = gravar_json(pasta, "dados.json", com_documento("v3"))
        rc, bloco, _ = node("conferir-versao.mjs", "bloco", proj, cwd=tmp())
        self.assertEqual(rc, 0, bloco)
        linear = gravar(pasta, "linear.txt", "Resumo do projeto.\n\n" + bloco)
        rc, out, _ = self.conferir(proj, "--doc", doc, "--canvas", canvas, "--linear", linear)
        self.assertEqual(rc, 0, out)
        self.assertIn("documento=DOC1", out)
        self.assertIn("versao=v3", out)
        self.assertIn("doc=ok", out)
        self.assertIn("canvas=ok", out)
        self.assertIn("linear=ok", out)

    def test_bloco_do_linear_traz_link_versao_e_data(self):
        _, proj, _ = self.preparar()
        rc, out, _ = node("conferir-versao.mjs", "bloco", proj, cwd=tmp())
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), f"Documento do projeto: {URL} (v3, atualizado em 20/10/2026)")

    def test_canvas_com_a_versao_velha_reprova(self):
        pasta, proj, doc = self.preparar()
        canvas = gravar_json(pasta, "dados.json", com_documento("v2"))
        rc, out, _ = self.conferir(proj, "--doc", doc, "--canvas", canvas)
        self.assertEqual(rc, 1, out)
        self.assertIn("canvas", out)
        self.assertIn("v2", out)
        self.assertIn("v3", out)

    def test_doc_em_versao_diferente_do_projeto_reprova(self):
        _, proj, doc = self.preparar(doc_versao="v4")
        rc, out, _ = self.conferir(proj, "--doc", doc)
        self.assertEqual(rc, 1, out)
        self.assertIn("doc", out)
        self.assertIn("v4", out)

    def test_linear_com_link_ou_versao_velha_reprova(self):
        pasta, proj, doc = self.preparar()
        velho = gravar(pasta, "l1.txt", f"Documento do projeto: {URL} (v2, atualizado em 10/10/2026)\n")
        rc, out, _ = self.conferir(proj, "--doc", doc, "--linear", velho)
        self.assertEqual(rc, 1, out)
        self.assertIn("linear", out)
        self.assertIn("v2", out)
        outro = gravar(pasta, "l2.txt", f"Documento do projeto: {OUTRA_URL} (v3, atualizado em 20/10/2026)\n")
        rc, out, _ = self.conferir(proj, "--doc", doc, "--linear", outro)
        self.assertEqual(rc, 1, out)
        self.assertIn("OUTRO9", out)

    def test_linear_sem_o_documento_reprova(self):
        pasta, proj, doc = self.preparar()
        vazio = gravar(pasta, "l.txt", "Projeto sem link do documento.\n")
        rc, out, _ = self.conferir(proj, "--doc", doc, "--linear", vazio)
        self.assertEqual(rc, 1, out)
        self.assertIn("linear", out)

    def test_drive_com_versao_diferente_reprova(self):
        pasta, proj, doc = self.preparar()
        drive = gravar_json(pasta, "drive.json", {"id": "DOC1", "name": "n", "description": "v2"})
        rc, out, _ = self.conferir(proj, "--doc", doc, "--drive", drive)
        self.assertEqual(rc, 1, out)
        self.assertIn("drive", out)
        certo = gravar_json(pasta, "drive2.json", {"id": "DOC1", "name": "n", "description": "v3"})
        rc, out, _ = self.conferir(proj, "--doc", doc, "--drive", certo)
        self.assertEqual(rc, 0, out)
        self.assertIn("drive=ok", out)

    def test_linear_com_duas_linhas_do_mesmo_link_uma_em_v1_e_outra_em_v2_reprova(self):
        # o caso do testador: bastava uma linha certa para o exit 0
        pasta, proj, doc = self.preparar()
        misto = gravar(pasta, "l.txt", f"Documento do projeto: {URL} (v3, atualizado em 20/10/2026)\n"
                                       f"Documento do projeto: {URL} (v2, atualizado em 10/10/2026)\n")
        rc, out, _ = self.conferir(proj, "--doc", doc, "--linear", misto)
        self.assertEqual(rc, 1, out)
        self.assertIn("ERRO   linear", out)
        self.assertIn("v2", out)
        self.assertNotIn("linear=ok", out)

    def test_linear_com_duas_linhas_do_link_ambas_na_versao_certa_passa(self):
        # controle positivo: duas citações do mesmo link na versão certa não reprovam
        pasta, proj, doc = self.preparar()
        duas = gravar(pasta, "l.txt", f"Documento do projeto: {URL} (v3, atualizado em 20/10/2026)\n"
                                      f"Recursos: {URL} (v3)\n")
        rc, out, _ = self.conferir(proj, "--doc", doc, "--linear", duas)
        self.assertEqual(rc, 0, out)

    def test_drive_com_o_stderr_do_gws_misturado_ainda_confere(self):
        # `2>&1` põe "Using keyring backend" antes do JSON: o conferir ignora o que vem antes do primeiro {
        pasta, proj, doc = self.preparar()
        sujo = gravar(pasta, "drive.json", 'Using keyring backend: keyring\n{"id": "DOC1", "name": "n", "description": "v3"}\n')
        rc, out, _ = self.conferir(proj, "--doc", doc, "--drive", sujo)
        self.assertEqual(rc, 0, out)
        self.assertIn("drive=ok", out)

    def test_drive_sem_json_nenhum_continua_ilegivel(self):
        pasta, proj, doc = self.preparar()
        sem = gravar(pasta, "drive.json", "Using keyring backend: keyring\n")
        rc, out, err = self.conferir(proj, "--doc", doc, "--drive", sem)
        self.assertEqual(rc, 1, out)
        self.assertIn("JSON ilegível", out + err)

    def test_projeto_sem_documento_reprova(self):
        pasta = tmp()
        proj = gravar_json(pasta, "projeto.json", projeto())
        rc, out, _ = self.conferir(proj)
        self.assertEqual(rc, 1)
        self.assertIn("documento", out)


@precisa_node
class TestePrincipal(unittest.TestCase):
    """Atualizo o doc de um projeto para uma versão nova, rodo o mapa e vejo o mesmo link e a
    mesma versão no doc, no canvas e no Linear, sem cópia nova no Drive."""

    def test_v1_para_v2_no_mesmo_arquivo_e_o_mapa_acompanha(self):
        pasta = tmp()
        env, log = ambiente(pasta)

        def gerar(md, *extra):
            entrada = gravar(pasta, "doc.md", md)
            return python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "doc.html"),
                                  "--camada", EXEMPLO_CAMADA, *extra, env=env)

        # v1: nasce um arquivo
        rc, out, err = gerar(doc_md("v1"), "--subir", "--nome", "Projeto Exemplo")
        self.assertEqual(rc, 0, out + err)
        # mapa e Linear em v1
        proj = com_documento("v1")
        caminho = gravar_json(pasta, "projeto.json", proj)
        canvas = os.path.join(pasta, "canvas")
        rc, out, err = node("montar-canvas.mjs", caminho, "Projeto Exemplo", canvas, "--camada", EXEMPLO_CAMADA, cwd=pasta)
        self.assertEqual(rc, 0, out + err)
        dados = os.path.join(canvas, "project", "dados", "projeto.json")
        rc, bloco, _ = node("conferir-versao.mjs", "bloco", caminho, cwd=pasta)
        linear = gravar(pasta, "linear.txt", bloco)
        doc = os.path.join(pasta, "doc.md")
        rc, out, _ = node("conferir-versao.mjs", "conferir", caminho, "--doc", doc, "--canvas", dados, "--linear", linear, cwd=pasta)
        self.assertEqual(rc, 0, out)

        # v2 no doc: o mesmo arquivo é atualizado, sem cópia
        rc, out, err = gerar(doc_md("v2"), "--atualizar", "DOC1", "--nome", "Projeto Exemplo")
        self.assertEqual(rc, 0, out + err)
        self.assertIn("copia_nova=nao", out)
        self.assertEqual(chamadas(log).count("drive files create"), 1, "um único create, o da v1")
        self.assertEqual(chamadas(log).count("drive files update"), 1)

        # o mapa ainda diz v1: a conferência pega, antes de alguém abrir o link velho
        rc, out, _ = node("conferir-versao.mjs", "conferir", caminho, "--doc", doc, "--canvas", dados, "--linear", linear, cwd=pasta)
        self.assertEqual(rc, 1, out)
        self.assertIn("v1", out)
        self.assertIn("v2", out)

        # roda o mapa em v2 e atualiza o bloco do Linear
        caminho = gravar_json(pasta, "projeto.json", com_documento("v2"))
        rc, out, err = node("montar-canvas.mjs", caminho, "--so-dados", canvas, "--camada", EXEMPLO_CAMADA, cwd=pasta)
        self.assertEqual(rc, 0, out + err)
        rc, bloco, _ = node("conferir-versao.mjs", "bloco", caminho, cwd=pasta)
        linear = gravar(pasta, "linear.txt", bloco)
        rc, out, _ = node("conferir-versao.mjs", "conferir", caminho, "--doc", doc, "--canvas", dados, "--linear", linear, cwd=pasta)
        self.assertEqual(rc, 0, out)
        self.assertIn("versao=v2", out)
        self.assertIn(f"link={URL}", out)


if __name__ == "__main__":
    unittest.main()
