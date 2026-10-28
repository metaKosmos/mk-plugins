"""Fontes do levantamento: o que a sessão alcança (com servidor alternativo) e a escolha salva na máquina."""
import json
import os
import unittest

from _util import PLUGIN, copiar_camada, node, precisa_node, tmp

LINEAR = "mcp__linear-exemplo__"
CONECTOR = "mcp__claude_ai_Linear__"
FATHOM = "mcp__claude_ai_Fathom__"
GRANOLA = "mcp__claude_ai_Granola__"


def camada_com_alternativo(base=None):
    def ajuste(c):
        c["fontes"]["linear"]["servidor_alternativo"] = CONECTOR
        c["fontes"]["linear"]["proibido"] = ["mcp__linear-outra-empresa__"]
    return copiar_camada(os.path.join(base or tmp(), "c"), ajuste=ajuste)


def linha(saida, fonte):
    for l in saida.splitlines():
        if l.startswith(fonte + ":"):
            return l
    return ""


@precisa_node
class TesteDisponiveis(unittest.TestCase):
    def rodar(self, camada, sessao):
        arq = os.path.join(tmp(), "escolhas.json")
        return node("fontes-do-levantamento.mjs", "disponiveis", "--camada", camada,
                    "--na-sessao", ",".join(sessao), env={"VANTA_FONTES_ESCOLHIDAS": arq})

    def test_linear_pelo_servidor_preferido(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [LINEAR, CONECTOR])
        self.assertEqual(rc, 0, out)
        self.assertIn("disponível", linha(out, "linear"))
        self.assertIn(LINEAR, linha(out, "linear"))
        self.assertNotIn(CONECTOR, linha(out, "linear"), "com o preferido na sessão o alternativo não é usado")

    def test_linear_pelo_alternativo_quando_so_ele_responde(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [CONECTOR, GRANOLA])
        self.assertEqual(rc, 0, out)
        l = linha(out, "linear")
        self.assertIn("disponível", l)
        self.assertIn("alternativo", l)
        self.assertIn(CONECTOR, l)
        self.assertIn("workspace", l, "o alternativo só vale depois de confirmar o workspace")

    def test_linear_fora_quando_nenhum_dos_dois_existe(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [GRANOLA])
        self.assertEqual(rc, 0, out)
        self.assertIn("não alcançável", linha(out, "linear"))
        self.assertIn("não verificável daqui", linha(out, "linear"))

    def test_servidor_proibido_na_sessao_nunca_e_escolhido(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), ["mcp__linear-outra-empresa__"])
        self.assertIn("não alcançável", linha(out, "linear"))
        self.assertNotIn("mcp__linear-outra-empresa__", linha(out, "linear"))

    def test_camada_sem_alternativo_ignora_o_conector(self):
        """O exemplo proíbe o conector: sem alternativo declarado ele nunca entra."""
        rc, out, _ = self.rodar(copiar_camada(os.path.join(tmp(), "c")), [CONECTOR])
        self.assertIn("não alcançável", linha(out, "linear"))

    def test_aceita_nome_de_ferramenta_inteiro(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [CONECTOR + "get_team", "mcp__plugin_x_linear-mk__get_issue"])
        self.assertIn(CONECTOR, linha(out, "linear"))

    def test_fonte_desligada_nao_aparece(self):
        def ajuste(c):
            c["fontes"]["slack"]["habilitada"] = False
        camada = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = self.rodar(camada, [LINEAR])
        self.assertEqual(linha(out, "slack"), "")


@precisa_node
class TesteServidorDoGestor(unittest.TestCase):
    """O servidor de ESCRITA da plano-no-linear: gestor.servidor, senão fontes.linear.servidor; faltando na
    sessão, gestor.servidor_alternativo, senão fontes.linear.servidor_alternativo. Nunca um de `proibido`."""

    def rodar(self, camada, sessao):
        return node("fontes-do-levantamento.mjs", "gestor", "--camada", camada, "--na-sessao", ",".join(sessao))

    def test_preferido_na_sessao_vale_e_o_alternativo_nao_entra(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [LINEAR, CONECTOR])
        self.assertEqual(rc, 0, out)
        self.assertIn(LINEAR, out)
        self.assertNotIn(CONECTOR, out)
        self.assertNotIn("workspace", out)

    def test_so_o_conector_na_sessao_usa_o_alternativo_e_manda_confirmar_o_workspace(self):
        """A máquina do Flávio: sem o servidor da empresa, só o conector do claude.ai."""
        rc, out, _ = self.rodar(camada_com_alternativo(), [CONECTOR + "get_team", CONECTOR + "save_issue"])
        self.assertEqual(rc, 0, out)
        self.assertIn(CONECTOR, out)
        self.assertIn("alternativo", out)
        self.assertIn("get_workspace", out)
        self.assertIn("antes de qualquer escrita", out)

    def test_nenhum_dos_dois_na_sessao_sai_com_1_e_nao_cria(self):
        rc, out, _ = self.rodar(camada_com_alternativo(), [GRANOLA])
        self.assertEqual(rc, 1)
        self.assertIn("não verificável daqui", out)
        self.assertIn("nenhuma issue é criada", out)

    def test_camada_sem_alternativo_nao_usa_o_conector(self):
        rc, out, _ = self.rodar(copiar_camada(os.path.join(tmp(), "c")), [CONECTOR])
        self.assertEqual(rc, 1)
        self.assertNotIn("disponível", out)

    def test_gestor_sem_servidor_cai_no_da_fonte_linear(self):
        def ajuste(c):
            c["gestor"]["servidor"] = None
            c["fontes"]["linear"]["servidor_alternativo"] = CONECTOR
            c["fontes"]["linear"]["proibido"] = []
        rc, out, _ = self.rodar(copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste), [LINEAR])
        self.assertEqual(rc, 0, out)
        self.assertIn(LINEAR, out)

    def test_alternativo_do_gestor_vem_antes_do_da_fonte(self):
        outro = "mcp__plugin_x_linear-alt__"
        def ajuste(c):
            c["gestor"]["servidor_alternativo"] = outro
            c["fontes"]["linear"]["servidor_alternativo"] = CONECTOR
            c["fontes"]["linear"]["proibido"] = []
        camada = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = self.rodar(camada, [CONECTOR, outro])
        self.assertIn(outro, out)
        self.assertNotIn(CONECTOR, out)
        rc, out, _ = self.rodar(camada, [CONECTOR])
        self.assertEqual(rc, 0, out)
        self.assertIn(CONECTOR, out, "sem o alternativo do gestor na sessão, vale o da fonte")

    def test_servidor_de_proibido_nunca_e_escolhido(self):
        def ajuste(c):
            c["gestor"]["proibido"] = [CONECTOR]
            c["fontes"]["linear"]["servidor_alternativo"] = CONECTOR
            c["fontes"]["linear"]["proibido"] = []
        rc, out, _ = self.rodar(copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste), [CONECTOR])
        self.assertEqual(rc, 1)
        self.assertNotIn("disponível", out)

    def test_sem_servidor_de_gestor_nem_de_fonte_pede_o_prefixo(self):
        def ajuste(c):
            c["gestor"]["servidor"] = None
            c["fontes"]["linear"]["servidor"] = None
        rc, out, _ = self.rodar(copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste), [LINEAR])
        self.assertEqual(rc, 1)
        self.assertIn("sem servidor", out)


@precisa_node
class TesteEscolhaSalva(unittest.TestCase):
    def setUp(self):
        self.base = tmp()
        self.arq = os.path.join(self.base, "casa", "fontes-escolhidas.json")
        self.env = {"VANTA_FONTES_ESCOLHIDAS": self.arq}
        self.camada = camada_com_alternativo(self.base)

    def incluir(self, camada=None, nome="Fathom", servidor=FATHOM, *extra):
        return node("fontes-do-levantamento.mjs", "incluir", "--camada", camada or self.camada,
                    "--nome", nome, "--servidor", servidor, *extra, env=self.env)

    def ler(self, camada=None):
        rc, out, _ = node("fontes-do-levantamento.mjs", "ler", "--camada", camada or self.camada, env=self.env)
        self.assertEqual(rc, 0, out)
        return json.loads(out)

    def test_incluir_grava_fora_do_plugin_e_le_de_volta(self):
        rc, out, err = self.incluir()
        self.assertEqual(rc, 0, out + err)
        self.assertTrue(os.path.exists(self.arq))
        self.assertFalse(os.path.realpath(self.arq).startswith(os.path.realpath(PLUGIN)))
        self.assertEqual([(e["nome"], e["servidor"]) for e in self.ler()], [("Fathom", FATHOM)])

    def test_a_escolha_e_de_uma_empresa_so(self):
        self.incluir()
        outra = copiar_camada(os.path.join(self.base, "outra"), ajuste=lambda c: c["empresa"].update(nome="Outra Empresa"))
        self.assertEqual(self.ler(outra), [])

    def test_incluir_de_novo_troca_em_vez_de_duplicar(self):
        self.incluir()
        self.incluir(None, "Fathom", FATHOM, "--como", "só reuniões do time")
        extras = self.ler()
        self.assertEqual(len(extras), 1)
        self.assertEqual(extras[0]["como"], "só reuniões do time")

    def test_recusa_servidor_que_a_camada_proibe(self):
        rc, out, _ = self.incluir(None, "Outro Linear", "mcp__linear-outra-empresa__")
        self.assertEqual(rc, 1)
        self.assertIn("proíbe", out)
        self.assertFalse(os.path.exists(self.arq))

    def test_recusa_o_que_ja_e_fonte_padrao(self):
        rc, out, _ = self.incluir(None, "Linear", CONECTOR)
        self.assertEqual(rc, 1)
        self.assertIn("já é fonte padrão", out)

    def test_recusa_prefixo_malformado(self):
        rc, out, _ = self.incluir(None, "Fathom", "fathom")
        self.assertEqual(rc, 1)
        self.assertIn("prefixo", out)

    def escrever_a_mao(self, conteudo):
        os.makedirs(os.path.dirname(self.arq), exist_ok=True)
        with open(self.arq, "w", encoding="utf-8") as f:
            json.dump(conteudo, f)

    def nome_da_empresa(self):
        with open(os.path.join(self.camada, "camada.json"), encoding="utf-8") as f:
            return json.load(f)["empresa"]["nome"]

    def test_empresa_sem_extras_no_arquivo_editado_a_mao_nao_derruba_o_incluir(self):
        self.escrever_a_mao({"versao": 1, "empresas": {self.nome_da_empresa(): {}}})
        rc, out, err = self.incluir()
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("TypeError", err)
        self.assertEqual([e["nome"] for e in self.ler()], ["Fathom"])

    def test_empresa_sem_extras_le_vazio_e_remover_diz_que_nao_esta_salva(self):
        self.escrever_a_mao({"versao": 1, "empresas": {self.nome_da_empresa(): {}}})
        self.assertEqual(self.ler(), [])
        rc, out, err = node("fontes-do-levantamento.mjs", "remover", "--camada", self.camada, "--nome", "Fathom", env=self.env)
        self.assertEqual(rc, 1, out + err)
        self.assertIn("não está salva", out)
        self.assertNotIn("TypeError", err)

    def test_extra_sem_servidor_vira_aviso_claro_e_nao_undefined(self):
        self.escrever_a_mao({"versao": 1, "empresas": {self.nome_da_empresa(): {"extras": [{"nome": "Fathom"}]}}})
        rc, out, err = node("fontes-do-levantamento.mjs", "disponiveis", "--camada", self.camada,
                            "--na-sessao", LINEAR, env=self.env)
        self.assertEqual(rc, 0, out + err)
        self.assertNotIn("undefined", out)
        l = linha(out, "extra Fathom")
        self.assertIn("sem servidor", l)
        self.assertIn(self.arq, l)

    def test_recusa_prefixo_com_dois_sublinhados_no_meio(self):
        """mcp__a__b__ nunca é reconhecido na sessão: a fonte ficaria sempre não alcançável."""
        rc, out, _ = self.incluir(None, "Fathom", "mcp__a__b__")
        self.assertEqual(rc, 1)
        self.assertIn("prefixo", out)
        self.assertIn("mcp__<servidor>__", out)
        self.assertFalse(os.path.exists(self.arq))

    def test_prefixo_com_sublinhado_simples_continua_valendo(self):
        rc, out, err = self.incluir(None, "Fathom", "mcp__plugin_x_fathom-2__")
        self.assertEqual(rc, 0, out + err)

    def test_remover(self):
        self.incluir()
        rc, out, _ = node("fontes-do-levantamento.mjs", "remover", "--camada", self.camada, "--nome", "fathom", env=self.env)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.ler(), [])

    def test_extra_salva_aparece_nas_disponiveis_e_ausente_fica_nao_verificavel(self):
        self.incluir()
        def disp(sessao):
            return node("fontes-do-levantamento.mjs", "disponiveis", "--camada", self.camada,
                        "--na-sessao", ",".join(sessao), env=self.env)[1]
        com = linha(disp([LINEAR, FATHOM]), "extra Fathom")
        self.assertIn("disponível", com)
        self.assertIn(FATHOM, com)
        sem = linha(disp([LINEAR]), "extra Fathom")
        self.assertIn("não alcançável", sem)
        self.assertIn("não verificável daqui", sem)

    def test_arquivo_ilegivel_nao_e_sobrescrito(self):
        os.makedirs(os.path.dirname(self.arq))
        with open(self.arq, "w", encoding="utf-8") as f:
            f.write("{ não é json")
        rc, out, err = self.incluir()
        self.assertEqual(rc, 1)
        self.assertIn("ilegível", out + err)
        with open(self.arq, encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ não é json")

    def test_sem_variavel_o_arquivo_vai_para_a_pasta_do_usuario(self):
        casa = tmp()
        rc, out, _ = node("fontes-do-levantamento.mjs", "caminho", env={"HOME": casa, "USERPROFILE": casa, "VANTA_FONTES_ESCOLHIDAS": ""})
        self.assertEqual(rc, 0, out)
        self.assertTrue(out.strip().startswith(casa), out)
        self.assertFalse(out.strip().startswith(PLUGIN))


if __name__ == "__main__":
    unittest.main()
