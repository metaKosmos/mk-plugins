"""A camada: contrato, achado da pasta e tokens."""
import json
import os
import shutil
import unittest

from _util import (EXEMPLO_CAMADA, PLUGIN, COMPLETO, copiar_camada, gravar_json, node,
                   precisa_node, tmp)


@precisa_node
class TesteCamada(unittest.TestCase):
    def test_exemplo_e_valido(self):
        rc, out, _ = node("validar-camada.mjs", EXEMPLO_CAMADA)
        self.assertEqual(rc, 0, out)
        self.assertIn("válida: 0 erros", out)
        self.assertIn("empresa: Fábrica Exemplo", out)

    def test_camada_sem_campo_obrigatorio_reprova(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c.pop("empresa"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("empresa: campo obrigatório ausente", out)

    def test_regex_invalida_reprova(self):
        def ajuste(c):
            c["marca"]["reprovar"][0]["padrao"] = "(abre"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("marca.reprovar[0].padrao: expressão regular inválida", out)

    def test_grupo_nomeado_reprova(self):
        def ajuste(c):
            c["marca"]["reprovar"][0]["padrao"] = "(?<marca>FX)"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("grupo nomeado", out)

    def test_cor_de_area_fora_do_formato_reprova(self):
        def ajuste(c):
            c["areas"][1]["cor"] = "azul"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("areas[1].cor", out)

    def test_token_fora_do_contrato_reprova(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"))
        with open(os.path.join(pasta, "tokens.json"), encoding="utf-8") as f:
            t = json.load(f)
        t["cores"]["texto"] = "preto"
        t["cores"]["inventada"] = "#000000"
        gravar_json(pasta, "tokens.json", t)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("tokens.cores.texto", out)
        self.assertIn("tokens.cores.inventada: campo desconhecido", out)

    def test_servidor_alternativo_da_fonte_valida(self):
        def ajuste(c):
            c["fontes"]["linear"]["servidor_alternativo"] = "mcp__claude_ai_Linear__"
            c["fontes"]["linear"]["proibido"] = ["mcp__linear-outra-empresa__"]
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 0, out)
        self.assertIn("válida: 0 erros", out)

    def test_servidor_alternativo_que_a_propria_fonte_proibe_reprova(self):
        """O exemplo proíbe mcp__claude_ai_Linear__: declará-lo também como alternativo é contradição."""
        def ajuste(c):
            c["fontes"]["linear"]["servidor_alternativo"] = "mcp__claude_ai_Linear__"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("fontes.linear.servidor_alternativo", out)
        self.assertIn("proibido", out)

    def test_servidor_que_a_propria_fonte_proibe_reprova(self):
        def ajuste(c):
            c["fontes"]["linear"]["proibido"].append(c["fontes"]["linear"]["servidor"])
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("fontes.linear.servidor", out)

    def test_servidor_alternativo_que_nao_e_texto_reprova(self):
        def ajuste(c):
            c["fontes"]["linear"]["servidor_alternativo"] = 7
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("fontes.linear.servidor_alternativo", out)

    def test_gestor_aceita_servidor_alternativo(self):
        def ajuste(c):
            c["gestor"]["servidor_alternativo"] = "mcp__claude_ai_Linear__"
            c["gestor"]["proibido"] = ["mcp__linear-outra-empresa__"]
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 0, out)

    def test_gestor_alternativo_que_a_camada_proibe_reprova(self):
        """Sem proibido próprio, vale o da fonte linear, que no exemplo proíbe o conector."""
        def ajuste(c):
            c["gestor"]["servidor_alternativo"] = "mcp__claude_ai_Linear__"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.servidor_alternativo", out)
        self.assertIn("proibido", out)

    def test_gestor_servidor_que_a_camada_proibe_reprova(self):
        def ajuste(c):
            c["gestor"]["proibido"] = [c["gestor"]["servidor"]]
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.servidor", out)

    def test_pasta_sem_camada_json_sai_com_2(self):
        rc, _, err = node("validar-camada.mjs", tmp())
        self.assertEqual(rc, 2)
        self.assertIn("camada não encontrada", err)

    def test_achado_da_camada(self):
        """--camada, VANTA_CAMADA, ./camada e camada/ ao lado do projeto.json."""
        base = tmp()
        copiar_camada(os.path.join(base, "camada"))
        with open(COMPLETO, encoding="utf-8") as f:
            proj = gravar_json(base, "projeto.json", json.load(f))
        alvo = os.path.realpath(os.path.join(base, "camada"))

        def usada(saida):
            for linha in saida.splitlines():
                if linha.startswith("camada /"):
                    return os.path.realpath(linha[len("camada "):])
            return None

        outro = tmp()  # cwd sem camada, para só valer o que o teste liga
        rc, out, _ = node("validar-projeto.mjs", proj, cwd=outro)
        self.assertEqual(usada(out), alvo, "ao lado do projeto.json")

        rc, out, _ = node("validar-projeto.mjs", COMPLETO, cwd=base)
        self.assertEqual(usada(out), alvo, "./camada no diretório atual")

        rc, out, _ = node("validar-projeto.mjs", COMPLETO, cwd=outro, env={"VANTA_CAMADA": alvo})
        self.assertEqual(usada(out), alvo, "VANTA_CAMADA")

        rc, out, _ = node("validar-projeto.mjs", COMPLETO, "--camada", EXEMPLO_CAMADA, cwd=outro,
                          env={"VANTA_CAMADA": alvo})
        self.assertEqual(usada(out), os.path.realpath(EXEMPLO_CAMADA), "--camada vence a variável")

        rc, out, _ = node("validar-projeto.mjs", COMPLETO, cwd=outro)
        self.assertIsNone(usada(out))
        self.assertIn("sem camada", out)

    def test_camada_invalida_barra_o_validador_de_projeto(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c.pop("fontes"))
        rc, out, err = node("validar-projeto.mjs", COMPLETO, "--camada", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("camada inválida", err)

    def test_tokens_da_camada_sobrescrevem_o_padrao_e_o_resto_vem_do_padrao(self):
        rc, out, _ = node("medir-pranchas.mjs", COMPLETO, "--camada", EXEMPLO_CAMADA)
        self.assertIn("0.42 de largura", out, "tokens da camada")
        sem = copiar_camada(os.path.join(tmp(), "c"), sem_tokens=True)
        rc, out, _ = node("medir-pranchas.mjs", COMPLETO, "--camada", sem)
        self.assertIn("0.58 de largura", out, "padrão neutro do motor")


if __name__ == "__main__":
    unittest.main()
