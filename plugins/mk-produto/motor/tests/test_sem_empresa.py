"""O motor não carrega nome de empresa, marca, cor de marca nem caminho de usuário.

O que é de uma empresa mora na camada. A pasta tests/ fica de fora da busca porque as suítes
guardam os padrões proibidos como dado. A camada de exemplo (exemplos/camada-exemplo) é
fictícia e fica dentro da busca."""
import os
import re
import unittest

from _util import PLUGIN

ESTE = os.path.abspath(__file__)
PADROES = {
    "caminho absoluto de usuário": r"/(Users|home)/[A-Za-z]",
    "pasta de uma estação": r"Desktop/|Documents/",
    "empresa de origem": r"(?i)metakosmos|mk-projeto|harness-dev|ktirio|montuvia|david-os",
    "marca de origem": r"(?<![A-Za-z])mK(?![a-z])|\bMK\b",
    "servidor de uma conta": r"linear-mk|linear-214|vanta-identidade",
    "cores da marca de origem": r"(?i)#E10600|#DC0B9F|#6F8F00|#7DD3FC",
    "fonte da marca de origem": r"\bAnton\b",
    "pessoas dos documentos de origem": r"Diana|Luiza",
    "link de tipo de uma conta": r"QKN21svewxgyPb6SYRqWnd",
    "e-mail": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|br|io)",
    "id de issue de uma empresa": r"P-PROD-\d|PROD-\d",
}
# o nome do autor do repositório aparece no plugin.json, como em todos os plugins daqui
IGNORAR = {os.path.join(".claude-plugin", "plugin.json")}


def busca(padrao):
    achados = []
    for raiz, pastas, arquivos in os.walk(PLUGIN):
        pastas[:] = [p for p in pastas if p not in ("__pycache__", "node_modules", "tests")]
        for nome in arquivos:
            caminho = os.path.join(raiz, nome)
            rel = os.path.relpath(caminho, PLUGIN)
            if os.path.abspath(caminho) == ESTE or rel in IGNORAR:
                continue
            try:
                with open(caminho, encoding="utf-8") as f:
                    texto = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            for n, linha in enumerate(texto.splitlines(), 1):
                if re.search(padrao, linha):
                    achados.append(f"{rel}:{n}")
    return achados


class TesteSemEmpresa(unittest.TestCase):
    def test_nenhum_padrao_de_empresa(self):
        for rotulo, padrao in PADROES.items():
            with self.subTest(rotulo):
                self.assertEqual(busca(padrao), [], rotulo)

    def test_controle_positivo_a_busca_acha_o_que_existe(self):
        """Sem controle positivo, uma busca quebrada passaria por limpa."""
        self.assertTrue(busca(r"fX Loja"), "a camada de exemplo tem de aparecer na busca")
        self.assertTrue(busca(r"Bebas Neue"))

    def test_sem_travessao(self):
        self.assertEqual(busca("[\u2014\u2013]"), [])

    def test_sem_emoji(self):
        self.assertEqual(busca("[\U0001F300-\U0001FAFF\u2600-\u27bf]"), [])

    def test_so_a_camada_de_exemplo_tem_marca_fx(self):
        dentro = [a for a in busca(r"\bfX\b") if not a.startswith("exemplos" + os.sep)
                  and not a.startswith(os.path.join("schema", "")) and not a.startswith("README.md")
                  and "SKILL.md" not in a and "esqueleto" not in a and "levantamento" not in a]
        self.assertEqual(dentro, [], "marca de exemplo vazando para o código do motor")


if __name__ == "__main__":
    unittest.main()
