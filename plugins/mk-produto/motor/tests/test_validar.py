"""validar-projeto.mjs: schema, semântica e regras da camada."""
import json
import os
import unittest

from _util import (COMPLETO, EXEMPLO_CAMADA, VAZIO, gravar_json, node, precisa_node, projeto, tmp)


def validar(dados, camada=EXEMPLO_CAMADA):
    caminho = gravar_json(tmp(), "p.json", dados)
    args = [caminho] + (["--camada", camada] if camada else [])
    return node("validar-projeto.mjs", *args, cwd=tmp())


@precisa_node
class TesteValidar(unittest.TestCase):
    def test_exemplos_sao_validos(self):
        for arq in (COMPLETO, VAZIO):
            rc, out, _ = node("validar-projeto.mjs", arq, "--camada", EXEMPLO_CAMADA)
            self.assertEqual(rc, 0, f"{arq}\n{out}")
            self.assertIn("0 erros", out)

    def test_sem_camada_exemplos_validos_com_aviso(self):
        rc, out, _ = validar(projeto(), camada=None)
        self.assertEqual(rc, 0, out)
        self.assertIn("sem camada", out)

    def test_sem_camada_nenhuma_regra_de_marca(self):
        rc, out, _ = validar(projeto(descricao="o FX e a fx loja, com traço \u2014 longo"), camada=None)
        self.assertEqual(rc, 0, out)

    def test_marca_reprovada_pela_camada(self):
        rc, out, _ = validar(projeto(descricao="Projeto do FX para o time."))
        self.assertEqual(rc, 1)
        self.assertIn('projeto.descricao: marca escrita "FX"', out)

    def test_variante_de_produto_reprovada_e_url_preservada(self):
        d = projeto(descricao="Vale para a fx loja e para o fXloja+, não para a URL https://exemplo.com/fxloja.")
        rc, out, _ = validar(d)
        self.assertEqual(rc, 1)
        self.assertIn('escrito "fx loja". A grafia é "fX Loja"', out)
        self.assertIn('escrito "fXloja+". A grafia é "fX Loja+"', out)
        self.assertNotIn("exemplo.com", out)

    def test_grafia_certa_passa(self):
        rc, out, _ = validar(projeto(descricao="Vale para o fX Loja, o fX Loja+ e o fX Pagamentos."))
        self.assertEqual(rc, 0, out)

    def test_travesssao_reprovado_so_se_a_camada_pede(self):
        rc, out, _ = validar(projeto(descricao="um \u2014 outro"))
        self.assertEqual(rc, 1)
        self.assertIn("traço longo ou meia-risca", out)
        rc, out, _ = validar(projeto(descricao="um \u2013 outro"))
        self.assertEqual(rc, 1)

        def liberar(c):
            c["escrita"]["travessao_proibido"] = False
        from _util import copiar_camada
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=liberar)
        rc, out, _ = validar(projeto(descricao="um \u2014 outro"), camada=pasta)
        self.assertEqual(rc, 0, out)

    def test_acento_por_area(self):
        rc, out, _ = validar(projeto(nome="fX Pagamentos: conciliação", acento="#7C3AED"))
        self.assertEqual(rc, 0, out)
        self.assertIn('não bate com "fX Pagamentos"', out)
        self.assertIn("esperado #059669", out)
        rc, out, _ = validar(projeto(nome="fX Pagamentos: conciliação", acento="#059669"))
        self.assertNotIn("não bate", out)

    def test_prefixo_que_vence(self):
        """'Dados:' vence o produto citado depois; sem o prefixo, dois produtos não decidem nada."""
        rc, out, _ = validar(projeto(nome="Dados: teste A/B do fX Loja", acento="#2563EB"))
        self.assertIn('não bate com "Dados"', out)
        self.assertIn("esperado #0EA5E9", out)
        rc, out, _ = validar(projeto(nome="Ponte entre fX Loja e fX Pagamentos", acento="#7C3AED"))
        self.assertNotIn("não bate", out)

    def test_contrato_v1_nao_mudou(self):
        d = projeto()
        d["roadmap"]["itens"][0]["trilha"] = "nao-existe"
        d["capacidades"][0]["itens"][0]["estado"] = "talvez"
        d["campo_novo"] = 1
        rc, out, _ = validar(d)
        self.assertEqual(rc, 1)
        self.assertIn('não existe em roadmap.trilhas', out)
        self.assertIn("fora do permitido", out)
        self.assertIn("campo_novo: campo desconhecido no contrato v1", out)

    def test_estado_nulo_e_roadmap_vazio_com_trilhas_vazias(self):
        d = projeto()
        d["capacidades"][0]["itens"][0]["estado"] = None
        d["roadmap"] = {"trilhas": [], "itens": [], "dependencias": [], "marcos": [], "feriados": []}
        rc, out, _ = validar(d)
        self.assertEqual(rc, 0, out)

    def test_data_inexistente(self):
        rc, out, _ = validar(projeto(prazo="2026-02-31"))
        self.assertEqual(rc, 1)
        self.assertIn("não é uma data real", out)


if __name__ == "__main__":
    unittest.main()
