"""Utilitários das suítes: caminhos do plugin e execução dos scripts."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXEMPLO_CAMADA = os.path.join(PLUGIN, "exemplos", "camada-exemplo")
COMPLETO = os.path.join(PLUGIN, "exemplos", "projeto", "completo.json")
VAZIO = os.path.join(PLUGIN, "exemplos", "projeto", "vazio.json")
PLANO = os.path.join(PLUGIN, "exemplos", "plano", "completo.json")
GERAR_DOC = os.path.join(PLUGIN, "skills", "documento-de-projeto", "scripts", "gerar-doc.py")
MOLDES = os.path.join(PLUGIN, "skills", "visual-de-projeto", "moldes")
NODE = shutil.which("node")

precisa_node = unittest.skipUnless(NODE, "node não está no PATH")


def script(nome):
    return os.path.join(PLUGIN, "scripts", nome)


def rodar(args, cwd=None, env=None):
    e = dict(os.environ)
    e.pop("VANTA_CAMADA", None)
    if env:
        e.update(env)
    r = subprocess.run(args, capture_output=True, text=True, cwd=cwd, env=e)
    return r.returncode, r.stdout, r.stderr


def node(nome, *args, cwd=None, env=None):
    return rodar([NODE, script(nome), *args], cwd=cwd, env=env)


def python_isolado(caminho, *args, cwd=None, env=None):
    return rodar([sys.executable, "-I", caminho, *args], cwd=cwd, env=env)


def tmp():
    return tempfile.mkdtemp(prefix="vanta-produto-teste-")


def copiar_camada(destino, sem_tokens=False, ajuste=None):
    """Copia a camada de exemplo para `destino`; `ajuste(dict)` muda o camada.json antes de gravar."""
    shutil.copytree(EXEMPLO_CAMADA, destino)
    if sem_tokens:
        os.remove(os.path.join(destino, "tokens.json"))
    if ajuste:
        arq = os.path.join(destino, "camada.json")
        with open(arq, encoding="utf-8") as f:
            c = json.load(f)
        ajuste(c)
        with open(arq, "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False, indent=2)
    return destino


def projeto(**mudancas):
    """O completo.json com campos de projeto trocados (nome, acento, descricao...)."""
    with open(COMPLETO, encoding="utf-8") as f:
        d = json.load(f)
    d["projeto"].update(mudancas)
    return d


def gravar_json(pasta, nome, dados):
    caminho = os.path.join(pasta, nome)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return caminho


def plano(ajuste=None):
    """O exemplos/plano/completo.json; `ajuste(dict)` muda o plano antes de devolver."""
    with open(PLANO, encoding="utf-8") as f:
        d = json.load(f)
    if ajuste:
        ajuste(d)
    return d


def issue(ajuste=None, indice=0):
    """O plano de exemplo com `ajuste(issue)` aplicado à issue de índice `indice`."""
    return plano(lambda d: ajuste(d["issues"][indice]))
