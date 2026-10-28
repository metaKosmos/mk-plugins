"""gerar-doc.py: normalização, lint e HTML, sempre contra a camada (sem subir nada)."""
import importlib.util
import json
import os
import subprocess
import unittest

from _util import (EXEMPLO_CAMADA, GERAR_DOC, NODE, PLUGIN, copiar_camada, precisa_node,
                   python_isolado, tmp)

spec = importlib.util.spec_from_file_location("gerar_doc", GERAR_DOC)
gerar_doc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gerar_doc)

DOC = """# Projeto Exemplo | fX Loja
20/10/2026 · Pessoa que rodou · v1

## 0. Ficha

<!-- larguras: 30,70 -->
| Campo | Valor |
|---|---|
| Dono | Pessoa Exemplo, decisão de Pessoa Exemplo, entrevista de 19/10/2026 |
| Produto | fx loja e FXLOJA+ |

Link: https://exemplo.com/fxloja e a marca fX.
"""


def gravar(pasta, texto):
    caminho = os.path.join(pasta, "doc.md")
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)
    return caminho


class TesteGerarDoc(unittest.TestCase):
    def test_normaliza_reprova_o_resto_e_preserva_url(self):
        pasta = tmp()
        entrada = gravar(pasta, DOC)
        rc, out, err = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "doc.html"),
                                      "--camada", EXEMPLO_CAMADA)
        self.assertEqual(rc, 0, out + err)
        self.assertIn("lint=ok", out)
        self.assertIn("normalizado=2", out)
        self.assertIn("fx loja -> fX Loja", out)
        self.assertIn("FXLOJA+ -> fX Loja+", out)
        with open(entrada, encoding="utf-8") as f:
            novo = f.read()
        self.assertIn("| Produto | fX Loja e fX Loja+ |", novo, "doc.md regravado igual ao que sobe")
        self.assertIn("https://exemplo.com/fxloja", novo, "URL intocada")
        self.assertIn("tabelas_html=1", out)
        with open(os.path.join(pasta, "doc.html"), encoding="utf-8") as f:
            html = f.read()
        self.assertEqual(html.count("<table"), 1)
        self.assertIn('<col style="width:30.0%">', html)

    def test_lint_reprova_marca_solta_e_traco(self):
        pasta = tmp()
        entrada = gravar(pasta, "# T\n\nA FX decidiu \u2014 sem volta.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"),
                                    "--camada", EXEMPLO_CAMADA)
        self.assertEqual(rc, 1)
        self.assertIn("lint=FALHOU", out)
        self.assertIn("linha 3: traço longo ou meia-risca", out)
        self.assertIn('linha 3: marca escrita "FX"', out)
        self.assertFalse(os.path.exists(os.path.join(pasta, "d.html")))

    def test_camada_que_libera_o_traco(self):
        pasta = tmp()
        camada = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["escrita"].update(travessao_proibido=False))
        entrada = gravar(pasta, "# T\n\nUm \u2014 outro.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"), "--camada", camada)
        self.assertEqual(rc, 0, out)

    def test_sem_camada_so_converte(self):
        pasta = tmp()
        entrada = gravar(pasta, "# T\n\nA FX e a fx loja \u2014 sem regra.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"), cwd=pasta)
        self.assertEqual(rc, 0, out)
        self.assertIn("camada=nenhuma", out)
        self.assertIn("lint=ok", out)
        self.assertNotIn("normalizado", out)

    def test_camada_ao_lado_da_entrada(self):
        pasta = tmp()
        copiar_camada(os.path.join(pasta, "camada"))
        entrada = gravar(pasta, "# T\n\nA fx loja.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"), cwd=tmp())
        self.assertEqual(rc, 0, out)
        self.assertIn("normalizado=1", out)

    def test_variavel_de_ambiente(self):
        pasta = tmp()
        entrada = gravar(pasta, "# T\n\nA fx pagamentos.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"), cwd=tmp(),
                                    env={"VANTA_CAMADA": EXEMPLO_CAMADA})
        self.assertIn("normalizado=1", out)

    def test_subir_exige_nome(self):
        pasta = tmp()
        entrada = gravar(pasta, "# T\n\nTexto.\n")
        rc, out, _ = python_isolado(GERAR_DOC, entrada, "--html", os.path.join(pasta, "d.html"),
                                    "--camada", EXEMPLO_CAMADA, "--subir")
        self.assertEqual(rc, 2)
        self.assertIn("--subir exige --nome", out)


@precisa_node
class TesteParidadeComOValidador(unittest.TestCase):
    """O validador (JavaScript) e o gerador (Python) leem as mesmas regras da camada e
    têm de chegar ao mesmo veredito sobre o mesmo texto."""

    CORPUS = [
        "texto limpo sem marca",
        "a marca fX sozinha",
        "a marca FX sozinha",
        "a marca Fx sozinha",
        "a marca fx sozinha",
        "fX Loja, fX Loja+ e fX Pagamentos",
        "fx loja",
        "FXLOJA",
        "fX loja+",
        "fXloja +",
        "fx pagamentos",
        "e-mail fx" + "@exemplo.com e hash #fx",
        "https://exemplo.com/fxloja e https://fx.exemplo.com",
        "veja https://exemplo.com/?x=fx agora",
        "caminho/fx/arquivo e a.fx",
        "fx-loja e fx_loja",
        "um \u2014 traço longo",
        "uma \u2013 meia-risca",
        "ação do fX com acentuação ção",
    ]

    def test_mesmo_veredito(self):
        js = (
            "import {carregar, problemasDeTexto} from %s;"
            "const c = carregar(process.argv[1]);"
            "const linhas = JSON.parse(process.argv[2]);"
            "console.log(JSON.stringify(linhas.map(l => problemasDeTexto(l, c.regras).length > 0)));"
        ) % json.dumps("file://" + os.path.join(PLUGIN, "scripts", "lib", "camada.mjs"))
        r = subprocess.run([NODE, "--input-type=module", "-e", js, EXEMPLO_CAMADA, json.dumps(self.CORPUS)],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        veredito_js = json.loads(r.stdout)

        regras = gerar_doc.carregar_regras(gerar_doc.achar_camada(EXEMPLO_CAMADA, "x"))
        veredito_py = []
        for linha in self.CORPUS:
            # o validador reprova o texto como veio; o gerador normaliza antes de reprovar.
            # Por isso a comparação é no lint cru (sem normalizar), que é a regra de reprovação.
            veredito_py.append(bool(gerar_doc.lint(linha, regras)))
        diferentes = [(l, a, b) for l, a, b in zip(self.CORPUS, veredito_js, veredito_py) if a != b]
        self.assertEqual(diferentes, [], "JavaScript e Python divergem")


if __name__ == "__main__":
    unittest.main()
