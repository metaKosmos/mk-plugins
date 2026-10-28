"""medir-pranchas.mjs: altura estimada, quebra e calibração pelo token de largura do título."""
import json
import os
import unittest

from _util import (COMPLETO, EXEMPLO_CAMADA, VAZIO, copiar_camada, gravar_json, node, precisa_node,
                   projeto, tmp)

TETO = 8000


def plano(dados_ou_arquivo, camada=None):
    if isinstance(dados_ou_arquivo, dict):
        dados_ou_arquivo = gravar_json(tmp(), "p.json", dados_ou_arquivo)
    args = [dados_ou_arquivo, "--json"] + (["--camada", camada] if camada else [])
    rc, out, err = node("medir-pranchas.mjs", *args, cwd=tmp())
    return rc, json.loads(out), err


@precisa_node
class TesteMedidor(unittest.TestCase):
    def test_exemplos_cabem(self):
        for arq in (COMPLETO, VAZIO):
            rc, p, _ = plano(arq, EXEMPLO_CAMADA)
            self.assertEqual(rc, 0)
            self.assertEqual([x["arquivo"] for x in p["pranchas"]],
                             ["Main.dc.html", "Capacidades.dc.html", "Roadmap.dc.html", "Hipoteses.dc.html"])
            self.assertTrue(all(x["hEstimada"] <= TETO for x in p["pranchas"]))

    def test_saida_legivel(self):
        rc, out, _ = node("medir-pranchas.mjs", COMPLETO, "--camada", EXEMPLO_CAMADA, cwd=tmp())
        self.assertEqual(rc, 0)
        self.assertIn("todas cabem", out)
        self.assertIn("cabe  Conceito", out)

    def test_hipoteses_demais_quebram_a_prancha(self):
        d = projeto()
        d["hipoteses"] = [
            {"id": f"H{i}", "hipotese": "Se fizermos uma mudança de exemplo " * 6, "metrica": "métrica de exemplo " * 5,
             "resultado_esperado": "resultado " * 6, "ferramenta": "ferramenta " * 4, "situacao": "a rodar",
             "fonte": "Exemplo fictício"} for i in range(1, 41)]
        rc, p, _ = plano(d, EXEMPLO_CAMADA)
        hip = [x for x in p["pranchas"] if x["molde"] == "Hipoteses"]
        self.assertGreaterEqual(len(hip), 2)
        self.assertEqual(rc, 0)
        self.assertTrue(all(x["h"] <= TETO for x in hip))
        self.assertEqual(hip[1]["arquivo"], "Hipoteses2.dc.html")
        self.assertIn("linhaDe", hip[0]["props"])

    def test_trilhas_demais_quebram_e_avisam(self):
        d = projeto()
        d["roadmap"]["trilhas"] = [{"id": f"t{i}", "nome": f"Trilha {i}", "cor": "#2563EB"} for i in range(14)]
        d["roadmap"]["itens"] = [{"id": f"i{i}", "trilha": f"t{i}", "nome": f"Item {i}", "descricao": "d",
                                  "inicio": "2026-11-02", "dias": 5} for i in range(14)]
        d["roadmap"]["dependencias"] = []
        rc, p, _ = plano(d, EXEMPLO_CAMADA)
        rm = [x for x in p["pranchas"] if x["molde"] == "Roadmap"]
        self.assertEqual(len(rm), 2)
        self.assertTrue(any("14 trilhas" in a for a in p["avisos"]))

    def test_janela_de_mais_de_seis_meses_avisa(self):
        d = projeto()
        d["roadmap"]["janela"] = {"inicio": "2026-11-02", "fim": "2027-08-02"}
        rc, p, _ = plano(d, EXEMPLO_CAMADA)
        self.assertTrue(any("acima de 6 meses" in a for a in p["avisos"]))

    def test_roadmap_sem_itens_nem_trilhas(self):
        d = projeto()
        d["roadmap"] = {"trilhas": [], "itens": [], "dependencias": [], "marcos": [], "feriados": []}
        rc, p, _ = plano(d, EXEMPLO_CAMADA)
        self.assertEqual(rc, 0)
        self.assertEqual(len([x for x in p["pranchas"] if x["molde"] == "Roadmap"]), 1)

    def test_fonte_de_titulo_larga_estima_mais_altura(self):
        """O token titulo_largura_char calibra a estimativa: título mais largo, mais linhas."""
        d = projeto(statement="Uma frase de posicionamento bem longa " * 4, nome="Nome de projeto bem comprido " * 2)
        estreita = copiar_camada(os.path.join(tmp(), "e"), sem_tokens=True)
        larga = copiar_camada(os.path.join(tmp(), "l"), sem_tokens=True)
        with open(os.path.join(larga, "tokens.json"), "w", encoding="utf-8") as f:
            json.dump({"versao": 1, "medidas": {"titulo_largura_char": 0.75}}, f)
        with open(os.path.join(estreita, "tokens.json"), "w", encoding="utf-8") as f:
            json.dump({"versao": 1, "medidas": {"titulo_largura_char": 0.40}}, f)
        h = lambda c: plano(d, c)[1]["pranchas"][0]["hEstimada"]
        self.assertGreater(h(larga), h(estreita))


if __name__ == "__main__":
    unittest.main()
