"""templates.json: contrato e o que o schema não alcança (nome único, skill existente, estado coerente, escrita)."""
import json
import os
import unittest

from _util import EXEMPLO_CAMADA, copiar_camada, node, precisa_node, tmp


def com_templates(mudanca):
    """Camada de exemplo com o templates.json alterado por `mudanca(dict)`."""
    pasta = copiar_camada(os.path.join(tmp(), "c"))
    arq = os.path.join(pasta, "templates.json")
    with open(arq, encoding="utf-8") as f:
        t = json.load(f)
    mudanca(t)
    with open(arq, "w", encoding="utf-8") as f:
        json.dump(t, f, ensure_ascii=False, indent=2)
    return pasta


@precisa_node
class TesteTemplates(unittest.TestCase):
    def test_exemplo_lista_os_templates(self):
        rc, out, _ = node("validar-camada.mjs", EXEMPLO_CAMADA)
        self.assertEqual(rc, 0, out)
        self.assertIn("Ficha do Projeto (pronto)", out)
        self.assertIn("Resumo de Entrega (em esboço)", out)

    def test_camada_sem_templates_json_continua_valida(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"))
        os.remove(os.path.join(pasta, "templates.json"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 0, out)
        self.assertIn("sem templates.json", out)

    def test_estado_fora_do_contrato_reprova(self):
        pasta = com_templates(lambda t: t["templates"][0].update(estado="quase pronto"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("templates.templates[0].estado", out)

    def test_campo_obrigatorio_ausente_reprova(self):
        pasta = com_templates(lambda t: t["templates"][1].pop("entrega"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("templates.templates[1].entrega: campo obrigatório ausente", out)

    def test_campo_desconhecido_reprova(self):
        pasta = com_templates(lambda t: t["templates"][0].update(cor="azul"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("campo desconhecido", out)

    def test_nome_repetido_reprova_mesmo_com_outra_caixa(self):
        pasta = com_templates(lambda t: t["templates"][1].update(nome="ficha do projeto"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("repetido", out)

    def test_skill_que_nao_existe_no_motor_reprova(self):
        pasta = com_templates(lambda t: t["templates"][0].update(skill_do_motor="skill-fantasma"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn('a skill "skill-fantasma" não existe no motor', out)

    def test_pronto_sem_skill_reprova(self):
        pasta = com_templates(lambda t: t["templates"][0].update(skill_do_motor=None))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn('"pronto" pede skill_do_motor', out)

    def test_skill_com_estado_que_nao_e_pronto_avisa_sem_reprovar(self):
        pasta = com_templates(lambda t: t["templates"][2].update(skill_do_motor="esboco"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 0, out)
        self.assertIn("aviso", out)

    def test_travessao_e_marca_do_nome_reprovam_pela_regra_da_camada(self):
        def ajuste(t):
            t["templates"][0]["nome"] = "Ficha — do FX"
        pasta = com_templates(ajuste)
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("templates.templates[0].nome: traço longo", out)
        self.assertIn('A grafia é "fX"', out)

    def test_json_ilegivel_reprova_sem_quebrar(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"))
        with open(os.path.join(pasta, "templates.json"), "w", encoding="utf-8") as f:
            f.write("{ nao e json")
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("templates.json: ilegível", out)

    def test_similaridade_minima_acima_de_1_reprova(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["esbocos"].update(similaridade_minima=1.5))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("esbocos.similaridade_minima", out)


if __name__ == "__main__":
    unittest.main()
