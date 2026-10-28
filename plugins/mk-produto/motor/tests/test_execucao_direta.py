"""Execução direta por caminho com symlink (macOS: /var -> /private/var do mktemp, HOME via link).

O Node resolve o symlink do módulo principal: import.meta.url vem com o caminho real e process.argv[1]
com o que foi digitado. Comparar os dois sem resolver faz o script sair com exit 0 e SEM saída, um falso
verde. Aqui cada script roda por uma pasta que é symlink e tem de dar a mesma saída e o mesmo exit
code de quando roda pelo caminho real."""
import os
import unittest

from _util import COMPLETO, EXEMPLO_CAMADA, NODE, PLANO, PLUGIN, precisa_node, rodar, tmp

SCRIPTS = os.path.join(PLUGIN, "scripts")
# scripts que só executam quando chamados direto (têm o guarda de execução direta)
COM_GUARDA = ["validar-plano.mjs", "validar-projeto.mjs", "descricao-issue.mjs", "medir-pranchas.mjs"]


def link_para(destino):
    """Uma pasta nova no tmp que é symlink para `destino`."""
    base = tmp()
    link = os.path.join(base, "link")
    os.symlink(destino, link)
    return link


@precisa_node
class TesteExecucaoPorSymlink(unittest.TestCase):
    def test_uso_sai_igual_pelo_symlink_e_pelo_caminho_real(self):
        link = link_para(SCRIPTS)
        for nome in COM_GUARDA:
            with self.subTest(script=nome):
                real = rodar([NODE, os.path.join(SCRIPTS, nome)])
                via = rodar([NODE, os.path.join(link, nome)])
                self.assertEqual(real[0], 2, real)
                self.assertIn("uso:", real[1] + real[2])
                self.assertEqual(via, real, "pelo symlink o script ficou mudo ou mudou o exit code")

    def test_validar_projeto_pelo_symlink_valida_de_verdade(self):
        link = link_para(SCRIPTS)
        rc, out, err = rodar([NODE, os.path.join(link, "validar-projeto.mjs"), COMPLETO, "--camada", EXEMPLO_CAMADA])
        self.assertEqual(rc, 0, out + err)
        self.assertTrue((out + err).strip(), "exit 0 sem saída é o falso verde")

    def test_validar_projeto_pelo_symlink_reprova_o_que_reprova(self):
        # o falso verde também escondia a reprovação: um arquivo que não existe tem de dar erro
        link = link_para(SCRIPTS)
        rc, out, err = rodar([NODE, os.path.join(link, "validar-projeto.mjs"), os.path.join(tmp(), "nao-existe.json")])
        self.assertNotEqual(rc, 0, out + err)
        self.assertTrue((out + err).strip())

    def test_validar_plano_pelo_symlink(self):
        link = link_para(SCRIPTS)
        real = rodar([NODE, os.path.join(SCRIPTS, "validar-plano.mjs"), PLANO, "--camada", EXEMPLO_CAMADA])
        via = rodar([NODE, os.path.join(link, "validar-plano.mjs"), PLANO, "--camada", EXEMPLO_CAMADA])
        self.assertEqual(real[0], 0, real)
        self.assertTrue(real[1].strip())
        self.assertEqual(via, real)

    def test_descricao_issue_pelo_symlink(self):
        link = link_para(SCRIPTS)
        real = rodar([NODE, os.path.join(SCRIPTS, "descricao-issue.mjs"), PLANO, "--estrutura", "--camada", EXEMPLO_CAMADA])
        via = rodar([NODE, os.path.join(link, "descricao-issue.mjs"), PLANO, "--estrutura", "--camada", EXEMPLO_CAMADA])
        self.assertEqual(real[0], 0, real)
        self.assertTrue(real[1].strip())
        self.assertEqual(via, real)

    def test_symlink_para_o_arquivo_do_script(self):
        # o caminho digitado é um link para o arquivo, não para a pasta
        base = tmp()
        link = os.path.join(base, "vp.mjs")
        os.symlink(os.path.join(SCRIPTS, "validar-projeto.mjs"), link)
        rc, out, err = rodar([NODE, link])
        self.assertEqual(rc, 2, out + err)
        self.assertIn("uso:", out + err)


@precisa_node
class TesteHelperExecutadoDiretamente(unittest.TestCase):
    def escrever(self, pasta):
        arq = os.path.join(pasta, "ex.mjs")
        lib = os.path.join(SCRIPTS, "lib", "execucao.mjs")
        with open(arq, "w", encoding="utf-8") as f:
            f.write(f"import {{ executadoDiretamente }} from '{lib}';\n"
                    "console.log(executadoDiretamente(import.meta.url));\n")
        return arq

    def test_true_por_caminho_real_e_por_symlink_de_pasta(self):
        pasta = tmp()
        arq = self.escrever(pasta)
        self.assertEqual(rodar([NODE, arq])[1].strip(), "true")
        link = link_para(pasta)
        self.assertEqual(rodar([NODE, os.path.join(link, "ex.mjs")])[1].strip(), "true")

    def test_false_quando_o_modulo_e_importado(self):
        pasta = tmp()
        arq = self.escrever(pasta)
        outro = os.path.join(pasta, "main.mjs")
        with open(outro, "w", encoding="utf-8") as f:
            f.write(f"await import('{arq}');\n")
        rc, out, err = rodar([NODE, outro])
        self.assertEqual(out.strip(), "false", out + err)

    def test_false_sem_argv1(self):
        lib = os.path.join(SCRIPTS, "lib", "execucao.mjs")
        rc, out, err = rodar([NODE, "-e",
                              f"import('{lib}').then(m => console.log(m.executadoDiretamente('file:///x/y.mjs', undefined)))"])
        self.assertEqual(out.strip(), "false", out + err)


if __name__ == "__main__":
    unittest.main()
