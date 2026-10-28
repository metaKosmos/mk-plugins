"""PROD-3080, bloqueio 2: o documento sobe sem depender do gws.

Sem o gws no PATH o gerar-doc.py não chama o Drive: prepara o que subir (`via=conector`) e a skill
sobe pelo conector Google Drive do claude.ai; depois `--registrar` confere e imprime as mesmas chaves
que o caminho do gws. A troca de conteúdo no mesmo arquivo (`--atualizar`) NÃO existe pelo conector
(update_file só muda metadados): sem gws o script recusa com exit 6 e nunca cria cópia."""
import json
import os
import unittest

from _util import (EXEMPLO_CAMADA, GERAR_DOC, gravar_json, node, precisa_node, python_isolado, tmp)
from test_versao import URL, ambiente, chamadas, com_documento, doc_md, gravar


def sem_gws(pasta):
    """PATH com uma pasta vazia na frente e nada além dela: `gws` não existe."""
    vazia = os.path.join(pasta, "sem-bin")
    os.makedirs(vazia, exist_ok=True)
    return {"PATH": vazia}


def rodar(pasta, md, *extra, env=None):
    entrada = gravar(pasta, "doc.md", md)
    rc, out, err = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "doc.html"),
                                  "--camada", EXEMPLO_CAMADA, *extra, env=env if env is not None else sem_gws(pasta))
    return rc, out + err


def chaves(out):
    d = {}
    for linha in out.splitlines():
        if "=" in linha and not linha.startswith(" "):
            k, v = linha.split("=", 1)
            d[k] = v
    return d


class TesteSubirSemGws(unittest.TestCase):
    def test_subir_sem_gws_prepara_o_conector_em_vez_de_abortar(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "Projeto Exemplo - v1")
        self.assertEqual(rc, 0, out)
        k = chaves(out)
        self.assertEqual(k["via"], "conector")
        self.assertEqual(k["acao"], "criar")
        self.assertEqual(k["create_file.title"], "Projeto Exemplo - v1")
        self.assertEqual(k["create_file.contentMimeType"], "text/html")
        self.assertEqual(k["create_file.textContent"], "@" + os.path.realpath(os.path.join(pasta, "doc.html")))
        self.assertEqual(k["update_file.description"], "v1", "a versão vai na description, depois do create")
        self.assertEqual(k["versao"], "v1")
        self.assertEqual(k["subida"], "pendente")
        self.assertNotIn("doc_id", k, "nada foi criado ainda: não há id")
        self.assertNotIn("erro", k)
        self.assertTrue(os.path.isfile(os.path.join(pasta, "doc.html")))

    def test_pasta_vira_parentId(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X - v1", "--pasta", "PASTA123")
        self.assertEqual(rc, 0, out)
        self.assertEqual(chaves(out)["create_file.parentId"], "PASTA123")

    def test_sem_pasta_nao_imprime_parentId(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X - v1")
        self.assertNotIn("create_file.parentId", chaves(out))

    def test_o_lint_continua_valendo_no_conector(self):
        pasta = tmp()
        rc, out = rodar(pasta, "# T\n20/10/2026 · P · v1\n\nTexto — com traço.\n", "--subir", "--nome", "X - v1")
        self.assertEqual(rc, 1, out)
        self.assertIn("lint=FALHOU", out)
        self.assertNotIn("via=conector", out)

    def test_nome_sem_a_versao_do_titulo_avisa(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v2"), "--subir", "--nome", "Projeto Exemplo")
        self.assertEqual(rc, 0, out)
        self.assertIn("aviso=o nome do arquivo não traz a versão v2", out)

    def test_nome_com_a_versao_nao_avisa(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v2"), "--subir", "--nome", "Projeto Exemplo - v2")
        self.assertNotIn("aviso=o nome", out)

    def test_subir_exige_nome_tambem_no_conector(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir")
        self.assertEqual(rc, 2, out)
        self.assertIn("--subir exige --nome", out)

    def test_projeto_com_documento_registrado_recusa_a_copia_tambem_no_conector(self):
        pasta = tmp()
        gravar_json(pasta, "projeto.json", com_documento("v1"))
        rc, out = rodar(pasta, doc_md("v2"), "--subir", "--nome", "X - v2")
        self.assertEqual(rc, 2, out)
        self.assertIn("--atualizar", out)
        self.assertNotIn("create_file", out, "nada para criar")

    def test_subir_sem_versao_no_titulo_segue_sem_description(self):
        pasta = tmp()
        rc, out = rodar(pasta, "# T\n\nTexto.\n", "--subir", "--nome", "T")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("update_file.description", chaves(out))


class TesteAtualizarSemGws(unittest.TestCase):
    def test_recusa_com_exit_6_e_nao_cria_copia(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v2"), "--atualizar", "DOC1", "--nome", "Projeto Exemplo - v2")
        self.assertEqual(rc, 6, out)
        k = chaves(out)
        self.assertEqual(k["via"], "conector")
        self.assertEqual(k["atualizado"], "nao")
        self.assertEqual(k["copia_nova"], "nao")
        self.assertIn("update_file só muda metadados", k["erro"])
        self.assertIn("gws", k["erro"])
        self.assertNotIn("create_file.title", k, "atualizar nunca cai em criar")
        self.assertNotIn("subida", k)

    def test_o_html_sai_mesmo_assim_para_quem_troca_o_conteudo_a_mao(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v2"), "--atualizar", "DOC1")
        self.assertEqual(rc, 6, out)
        self.assertTrue(os.path.isfile(os.path.join(pasta, "doc.html")))
        self.assertEqual(chaves(out)["html"], os.path.realpath(os.path.join(pasta, "doc.html")))

    def test_sem_versao_no_titulo_continua_exit_2(self):
        pasta = tmp()
        rc, out = rodar(pasta, "# T\n20/10/2026 · Pessoa\n\nTexto.\n", "--atualizar", "DOC1")
        self.assertEqual(rc, 2, out)
        self.assertIn("versão", out)


class TesteEscolhaDoCaminho(unittest.TestCase):
    def test_com_gws_no_path_o_padrao_continua_sendo_o_gws(self):
        pasta = tmp()
        env, log = ambiente(pasta)
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X - v1", env=env)
        self.assertEqual(rc, 0, out)
        self.assertIn("doc_id=DOC1", out)
        self.assertNotIn("via=conector", out)
        self.assertIn("drive files create", chamadas(log))

    def test_via_conector_forca_o_conector_mesmo_com_gws(self):
        pasta = tmp()
        env, log = ambiente(pasta)
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X - v1", "--via", "conector", env=env)
        self.assertEqual(rc, 0, out)
        self.assertEqual(chaves(out)["via"], "conector")
        self.assertEqual(chamadas(log), [], "o gws não foi chamado")

    def test_via_gws_sem_gws_continua_recusando(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X - v1", "--via", "gws")
        self.assertEqual(rc, 2, out)
        self.assertIn("erro=gws não encontrado no PATH", out)

    def test_via_invalida_e_recusada(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--subir", "--nome", "X", "--via", "outro")
        self.assertEqual(rc, 2)

    def test_so_html_sem_subir_nao_muda(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"))
        self.assertEqual(rc, 0, out)
        self.assertNotIn("via=", out)


class TesteRegistrar(unittest.TestCase):
    def registrar(self, pasta, md, *extra):
        return rodar(pasta, md, "--registrar", "--doc-id", "DOC1", "--url", URL, *extra)

    def test_registra_com_as_mesmas_chaves_do_caminho_do_gws(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, doc_md("v1"), "--tabelas-doc", "1")
        self.assertEqual(rc, 0, out)
        k = chaves(out)
        self.assertEqual(k["doc_id"], "DOC1")
        self.assertEqual(k["url"], URL)
        self.assertEqual(k["versao"], "v1")
        self.assertEqual(k["tabelas_html"], "1")
        self.assertEqual(k["tabelas_doc"], "1")
        self.assertEqual(k["tabelas_ok"], "sim")
        self.assertEqual(k["via"], "conector")

    def test_sem_contagem_de_tabelas_diz_nao_verificavel_e_nao_reprova(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, doc_md("v1"))
        self.assertEqual(rc, 0, out)
        self.assertEqual(chaves(out)["tabelas_ok"], "nao_verificavel")
        self.assertNotIn("tabelas_doc", chaves(out))

    def test_tabela_perdida_no_doc_reprova_com_exit_3(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, doc_md("v1"), "--tabelas-doc", "0")
        self.assertEqual(rc, 3, out)
        self.assertEqual(chaves(out)["tabelas_ok"], "NAO")

    def test_url_que_nao_e_do_id_recusa(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--registrar", "--doc-id", "OUTRO9", "--url", URL)
        self.assertEqual(rc, 2, out)
        self.assertIn("a url não é do documento OUTRO9", out)

    def test_url_do_conector_com_parametros_e_normalizada_para_edit(self):
        pasta = tmp()
        alvo = os.path.join(pasta, "drive.json")
        sujo = "https://docs.google.com/document/d/DOC1/edit?usp=drivesdk&ouid=123456789012345678901"
        rc, out = rodar(pasta, doc_md("v1"), "--registrar", "--doc-id", "DOC1", "--url", sujo,
                        "--nome", "X - v1", "--gravar-drive", alvo)
        self.assertEqual(rc, 0, out)
        self.assertEqual(chaves(out)["url"], URL)
        self.assertNotIn("usp=", out)
        self.assertNotIn("ouid", out)
        with open(alvo, encoding="utf-8") as f:
            self.assertEqual(json.load(f)["id"], "DOC1")

    def test_variacoes_de_url_sem_edit_viram_edit(self):
        for variacao in ["https://docs.google.com/document/d/DOC1",
                         "https://docs.google.com/document/d/DOC1/",
                         "https://docs.google.com/document/d/DOC1/view",
                         "https://docs.google.com/document/d/DOC1/edit#heading=h.abc",
                         "https://docs.google.com/document/d/DOC1?usp=sharing",
                         "https://docs.google.com/document/u/0/d/DOC1/edit"]:
            with self.subTest(url=variacao):
                rc, out = rodar(tmp(), doc_md("v1"), "--registrar", "--doc-id", "DOC1", "--url", variacao)
                self.assertEqual(rc, 0, out)
                self.assertEqual(chaves(out)["url"], URL)

    def test_url_normalizada_nao_confunde_id_que_so_comeca_igual(self):
        rc, out = rodar(tmp(), doc_md("v1"), "--registrar", "--doc-id", "DOC1",
                        "--url", "https://docs.google.com/document/d/DOC12/edit?usp=drivesdk")
        self.assertEqual(rc, 2, out)

    def test_id_divergente_com_url_suja_continua_exit_2(self):
        rc, out = rodar(tmp(), doc_md("v1"), "--registrar", "--doc-id", "OUTRO9",
                        "--url", "https://docs.google.com/document/d/DOC1/edit?usp=drivesdk&ouid=1")
        self.assertEqual(rc, 2, out)
        self.assertIn("a url não é do documento OUTRO9", out)

    def test_url_que_nao_e_de_google_doc_recusa(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--registrar", "--doc-id", "DOC1", "--url", "https://exemplo.com/DOC1")
        self.assertEqual(rc, 2, out)

    def test_registrar_exige_id_e_url(self):
        pasta = tmp()
        rc, out = rodar(pasta, doc_md("v1"), "--registrar")
        self.assertEqual(rc, 2, out)
        self.assertIn("--registrar exige --doc-id e --url", out)

    def test_description_do_drive_diferente_da_versao_do_doc_reprova(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, doc_md("v2"), "--descricao-no-drive", "v1")
        self.assertEqual(rc, 7, out)
        self.assertIn("o Drive está em v1 e o doc.md é v2", out)

    def test_description_do_drive_igual_passa(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, doc_md("v2"), "--descricao-no-drive", "v2")
        self.assertEqual(rc, 0, out)

    def test_registrar_sem_versao_no_titulo_recusa(self):
        pasta = tmp()
        rc, out = self.registrar(pasta, "# T\n20/10/2026 · Pessoa\n\nTexto.\n")
        self.assertEqual(rc, 2, out)
        self.assertIn("versão", out)

    def test_registrar_com_id_diferente_do_registrado_no_projeto_recusa(self):
        # o projeto já tem o doc DOC1; um id novo é uma cópia
        pasta = tmp()
        gravar_json(pasta, "projeto.json", com_documento("v1"))
        rc, out = rodar(pasta, doc_md("v2"), "--registrar", "--doc-id", "NOVO7",
                        "--url", "https://docs.google.com/document/d/NOVO7/edit")
        self.assertEqual(rc, 2, out)
        self.assertIn("copia_nova=sim", out)
        self.assertIn("DOC1", out)

    def test_registrar_com_o_mesmo_id_do_projeto_passa(self):
        pasta = tmp()
        gravar_json(pasta, "projeto.json", com_documento("v1"))
        rc, out = self.registrar(pasta, doc_md("v1"))
        self.assertEqual(rc, 0, out)

    def test_grava_o_drive_json_que_o_conferir_le(self):
        pasta = tmp()
        alvo = os.path.join(pasta, "drive.json")
        rc, out = self.registrar(pasta, doc_md("v1"), "--nome", "Projeto Exemplo - v1", "--gravar-drive", alvo)
        self.assertEqual(rc, 0, out)
        with open(alvo, encoding="utf-8") as f:
            d = json.load(f)
        self.assertEqual(d, {"id": "DOC1", "name": "Projeto Exemplo - v1", "description": "v1"})


@precisa_node
class TesteCaminhoInteiroSemGws(unittest.TestCase):
    def test_preparar_registrar_validar_e_conferir_o_drive(self):
        pasta = tmp()
        md = doc_md("v1")
        rc, out = rodar(pasta, md, "--subir", "--nome", "Projeto Exemplo - v1")
        self.assertEqual(rc, 0, out)
        # a skill sobe pelo conector (aqui simulado) e devolve id e link
        alvo = os.path.join(pasta, "drive.json")
        rc, out = rodar(pasta, md, "--registrar", "--doc-id", "DOC1", "--url", URL, "--tabelas-doc", "1",
                        "--nome", "Projeto Exemplo - v1", "--descricao-no-drive", "v1", "--gravar-drive", alvo)
        self.assertEqual(rc, 0, out)
        k = chaves(out)
        # o bloco `documento` do projeto.json sai das chaves, como no caminho do gws
        dados = com_documento(k["versao"], url=k["url"])
        dados["documento"]["id"] = k["doc_id"]
        caminho = gravar_json(pasta, "projeto.json", dados)
        rc, out, _ = node("validar-projeto.mjs", caminho, "--camada", EXEMPLO_CAMADA, cwd=tmp())
        self.assertEqual(rc, 0, out)
        rc, out, _ = node("conferir-versao.mjs", "conferir", caminho, "--doc", os.path.join(pasta, "doc.md"),
                          "--drive", alvo, cwd=tmp())
        self.assertEqual(rc, 0, out)


class TesteSkillSemGws(unittest.TestCase):
    """O que a skill promete a quem roda sem o gws tem de estar escrito na seção."""

    def secao(self):
        arq = os.path.join(os.path.dirname(GERAR_DOC), "..", "SKILL.md")
        with open(arq, encoding="utf-8") as f:
            texto = f.read()
        ini = texto.index("**Sem o gws: pelo conector")
        return texto[ini:texto.index("5. O Doc nasce privado")]

    def test_diz_que_bloco_continuo_de_tabela_e_uma_tabela_so(self):
        s = self.secao()
        self.assertIn("linha de cabeçalho vazia", s)
        self.assertIn("`|  |  |`", s)
        self.assertIn("não duas", s)

    def test_diz_que_sem_o_conector_nao_ha_caminho(self):
        self.assertIn("não há caminho sem o gws", self.secao())

    def test_diz_que_a_url_sai_normalizada(self):
        self.assertIn("usp=drivesdk", self.secao())


if __name__ == "__main__":
    unittest.main()
