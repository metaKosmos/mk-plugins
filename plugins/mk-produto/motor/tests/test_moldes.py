"""Os moldes: sem cor, fonte nem marca no código; tokens injetados; renderização em node."""
import glob
import json
import os
import re
import unittest

from _util import (COMPLETO, EXEMPLO_CAMADA, MOLDES, NODE, VAZIO, copiar_camada, gravar_json, node,
                   precisa_node, projeto, rodar, tmp)

RENDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "render_molde.mjs")
CONFIG = re.compile(r"/\*vp:config\*/.*?/\*vp:fim\*/", re.S)
PRANCHAS = ["Main", "Capacidades", "Roadmap", "Hipoteses"]
HEX = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def montar(dados, camada=None, titulo="Projeto Exemplo"):
    pasta = tmp()
    entrada = gravar_json(pasta, "projeto.json", dados)
    saida = os.path.join(pasta, "canvas")
    args = [entrada, titulo, saida] + (["--camada", camada] if camada else [])
    rc, out, err = node("montar-canvas.mjs", *args, cwd=tmp())
    assert rc == 0, out + err
    return saida


def renderizar(molde, projeto_json, props=None, sem_dados=False):
    args = [NODE, RENDER, molde, projeto_json]
    if props or sem_dados:
        args.append(json.dumps(props) if props else "-")
    if sem_dados:
        args.append("sem-dados")
    rc, out, err = rodar(args)
    assert rc == 0, err
    return json.loads(out)


def todos_os_textos(no):
    if isinstance(no, str):
        yield no
    elif isinstance(no, list):
        for x in no:
            yield from todos_os_textos(x)
    elif isinstance(no, dict):
        for x in no.values():
            yield from todos_os_textos(x)


class TesteMoldesNaFonte(unittest.TestCase):
    """O molde que mora no motor não carrega nada de empresa."""

    def moldes(self):
        achados = sorted(glob.glob(os.path.join(MOLDES, "*.dc.html")))
        self.assertEqual(len(achados), 4)
        return achados

    def test_sem_cor_literal(self):
        for arq in self.moldes():
            with open(arq, encoding="utf-8") as f:
                texto = CONFIG.sub("", f.read())
            self.assertEqual(HEX.findall(texto), [], f"{os.path.basename(arq)}: cor literal fora dos tokens")
            self.assertNotIn("rgba(", texto, f"{os.path.basename(arq)}: rgba literal")

    def test_sem_fonte_nem_marca_literal(self):
        for arq in self.moldes():
            with open(arq, encoding="utf-8") as f:
                texto = f.read()
            for proibido in ("Anton", "Helvetica", "fonts.googleapis.com/css2"):
                self.assertNotIn(proibido, texto, f"{os.path.basename(arq)}: {proibido}")
            self.assertIsNone(re.search(r"(?<![A-Za-z])mK(?![a-z])|\bMK\b", texto), os.path.basename(arq))

    def test_marcadores_do_montador_presentes(self):
        for arq in self.moldes():
            with open(arq, encoding="utf-8") as f:
                texto = f.read()
            self.assertIn("<!--vp:tokens-->", texto)
            self.assertIn('"__VP_OPCOES__"', texto)
            self.assertTrue(CONFIG.search(texto), os.path.basename(arq))

    def test_fetch_de_dados_sem_cache(self):
        """Republicar só o JSON só funciona se o navegador não reaproveitar o dado antigo."""
        for caminho in self.moldes():
            with open(caminho, encoding="utf-8") as f:
                fonte = f.read()
            chamadas = re.findall(r"fetch\(\s*['\"]dados/projeto\.json['\"][^)]*\)", fonte)
            self.assertTrue(chamadas, os.path.basename(caminho) + ": sem fetch de dados/projeto.json")
            for c in chamadas:
                self.assertRegex(c, r"cache\s*:\s*['\"]no-store['\"]", os.path.basename(caminho))


@precisa_node
class TesteMoldesMontados(unittest.TestCase):
    def verificar_montagem(self, saida):
        for nome in PRANCHAS:
            caminho = os.path.join(saida, "project", f"{nome}.dc.html")
            self.assertTrue(os.path.exists(caminho), caminho)
            with open(caminho, encoding="utf-8") as f:
                texto = f.read()
            for resto in ("<!--vp:tokens-->", "__VP_OPCOES__", "/*vp:config*/", "/*vp:fim*/"):
                self.assertNotIn(resto, texto, f"{nome}: marcador sem substituir")
            self.assertIn(":root{--vp-fonte-titulo:", texto)
            self.assertEqual(len(re.findall(r"data-props='(\{.*?\})'>", texto)), 1)
            props = json.loads(re.search(r"data-props='(\{.*?\})'>", texto).group(1))
            self.assertTrue(props["accent"]["options"], "opções de acento")

    def test_tokens_neutros(self):
        """Camada sem tokens.json: vale o padrão neutro do motor."""
        camada = copiar_camada(os.path.join(tmp(), "c"), sem_tokens=True)
        saida = montar(projeto(), camada)
        self.verificar_montagem(saida)
        with open(os.path.join(saida, "project", "Main.dc.html"), encoding="utf-8") as f:
            texto = f.read()
        self.assertIn("--vp-fonte-titulo:system-ui", texto)
        self.assertIn("--vp-titulo-caixa:none", texto)
        self.assertIn("--vp-acento:#7C3AED", texto)
        self.assertNotIn("fonts.googleapis.com", texto, "fonte do sistema não carrega folha de estilo")
        self.assertIn('"caixa":"none"', texto)

    def test_sem_camada_nenhuma_tambem_e_neutro(self):
        saida = montar(projeto(), None)
        self.verificar_montagem(saida)

    def test_tokens_da_camada(self):
        saida = montar(projeto(), EXEMPLO_CAMADA)
        self.verificar_montagem(saida)
        with open(os.path.join(saida, "project", "Main.dc.html"), encoding="utf-8") as f:
            texto = f.read()
        self.assertIn("--vp-fonte-titulo:'Bebas Neue'", texto)
        self.assertIn('href="https://fonts.googleapis.com/css2?family=Bebas+Neue&amp;display=swap"', texto)
        self.assertIn("--vp-titulo-caixa:uppercase", texto)
        self.assertIn("--vp-raio:12px", texto)
        self.assertIn('"preservar":["fX"]', texto)
        self.assertIn('"options":["#0ea5e9","#2563eb","#059669","#7c3aed","#111111"]', texto)

    def test_caractere_proibido_em_token_barra_a_montagem(self):
        camada = copiar_camada(os.path.join(tmp(), "c"))
        with open(os.path.join(camada, "tokens.json"), encoding="utf-8") as f:
            t = json.load(f)
        t["fontes"]["corpo"]["familia"] = "Arial; } body { display: none"
        gravar_json(camada, "tokens.json", t)
        pasta = tmp()
        entrada = gravar_json(pasta, "p.json", projeto())
        rc, out, err = node("montar-canvas.mjs", entrada, "T", os.path.join(pasta, "c"), "--camada", camada, cwd=pasta)
        self.assertEqual(rc, 1)
        self.assertIn("caractere proibido", err)

    def test_so_dados_nao_toca_nos_moldes(self):
        pasta = tmp()
        entrada = gravar_json(pasta, "p.json", projeto())
        saida = os.path.join(pasta, "c")
        rc, out, err = node("montar-canvas.mjs", entrada, "--so-dados", saida, "--camada", EXEMPLO_CAMADA, cwd=pasta)
        self.assertEqual(rc, 0, out + err)
        self.assertEqual(os.listdir(os.path.join(saida, "project")), ["dados"])

    def test_projeto_invalido_para_a_montagem(self):
        pasta = tmp()
        entrada = gravar_json(pasta, "p.json", projeto(descricao="o FX"))
        rc, out, err = node("montar-canvas.mjs", entrada, "T", os.path.join(pasta, "c"), "--camada", EXEMPLO_CAMADA, cwd=pasta)
        self.assertEqual(rc, 1)
        self.assertIn("nada foi montado", err)
        self.assertFalse(os.path.exists(os.path.join(pasta, "c", "project", "Main.dc.html")))


@precisa_node
class TesteRenderizacao(unittest.TestCase):
    """Executa o JavaScript de cada molde montado (sem navegador, sem publicar)."""

    @classmethod
    def setUpClass(cls):
        neutra = copiar_camada(os.path.join(tmp(), "c"), sem_tokens=True)
        cls.neutro = montar(projeto(), neutra)
        cls.exemplo = montar(projeto(), EXEMPLO_CAMADA)
        cls.dados_neutro = os.path.join(cls.neutro, "project", "dados", "projeto.json")
        cls.dados_exemplo = os.path.join(cls.exemplo, "project", "dados", "projeto.json")

    def molde(self, base, nome):
        return os.path.join(base, "project", f"{nome}.dc.html")

    def test_renderiza_as_quatro_pranchas_nos_dois_temas(self):
        for base, dados in ((self.neutro, self.dados_neutro), (self.exemplo, self.dados_exemplo)):
            for nome in PRANCHAS:
                vals = renderizar(self.molde(base, nome), dados)
                self.assertTrue(vals["pronto"], f"{nome}: dados não carregaram")
                estilos = " ".join(todos_os_textos(vals))
                self.assertIn("var(--vp-", estilos, f"{nome}: estilo sem tokens")

    def test_nenhuma_cor_fixa_no_que_o_molde_gera(self):
        """Toda cor gerada pelo molde é variável de token ou vem do JSON (acento, cor da trilha)."""
        with open(COMPLETO, encoding="utf-8") as f:
            d = json.load(f)
        permitidas = {d["projeto"]["acento"].lower()}
        for g in d["roadmap"]["trilhas"] + d["roadmap"]["marcos"] + d["fontes_dados"]:
            if g.get("cor"):
                permitidas.add(g["cor"].lower())
        for nome in PRANCHAS:
            vals = renderizar(self.molde(self.neutro, nome), self.dados_neutro)
            achadas = {h.lower() for t in todos_os_textos(vals) for h in HEX.findall(t)}
            self.assertLessEqual(achadas - permitidas, set(), f"{nome}: cor fixa no estilo gerado")

    def test_kicker_neutro_nao_muda_a_caixa(self):
        vals = renderizar(self.molde(self.neutro, "Main"), self.dados_neutro)
        self.assertEqual(vals["kickerTxt"], "fX Loja · projeto de exemplo, dado fictício")
        self.assertEqual(vals["stAntes"] + vals["stDestaque"] + vals["stDepois"],
                         "Mostrar todo o projeto numa tela, sem inventar um número")

    def test_caixa_alta_preserva_a_palavra_de_marca(self):
        vals = renderizar(self.molde(self.exemplo, "Main"), self.dados_exemplo)
        self.assertEqual(vals["kickerTxt"], "fX LOJA · PROJETO DE EXEMPLO, DADO FICTÍCIO")
        self.assertTrue(vals["stAntes"].startswith("MOSTRAR TODO O PROJETO"))

    def test_rotulo_de_marca_antes_dos_dados_carregarem(self):
        """O rótulo vem de empresa.rotulo_canvas, não dos tokens: vale com e sem tokens da camada."""
        for base, dados in ((self.exemplo, self.dados_exemplo), (self.neutro, self.dados_neutro)):
            for nome, n in (("Capacidades", 2), ("Roadmap", 3), ("Hipoteses", 4)):
                vals = renderizar(self.molde(base, nome), dados, sem_dados=True)
                self.assertEqual(vals["topoTxt"], f"fX PROJETO · PRANCHA {n}")
            vals = renderizar(self.molde(base, "Main"), dados, sem_dados=True)
            self.assertEqual(vals["kickerTxt"], "fX PROJETO")

    def test_kicker_sem_dado_cai_no_rotulo_de_marca(self):
        base = montar(projeto(kicker=None), EXEMPLO_CAMADA, "Sem kicker")
        vals = renderizar(self.molde(base, "Main"), os.path.join(base, "project", "dados", "projeto.json"))
        self.assertEqual(vals["kickerTxt"], "fX PROJETO")

    def test_topo_segue_a_caixa_dos_tokens(self):
        vals = renderizar(self.molde(self.exemplo, "Capacidades"), self.dados_exemplo)
        self.assertEqual(vals["topoTxt"], "PROJETO EXEMPLO · PRANCHA 2")
        vals = renderizar(self.molde(self.neutro, "Capacidades"), self.dados_neutro)
        self.assertEqual(vals["topoTxt"], "Projeto Exemplo · PRANCHA 2")

    def test_sem_rotulo_na_camada_o_topo_e_so_projeto(self):
        camada = copiar_camada(os.path.join(tmp(), "c"), sem_tokens=True,
                               ajuste=lambda c: c["empresa"].pop("rotulo_canvas"))
        base = montar(projeto(), camada)
        dados = os.path.join(base, "project", "dados", "projeto.json")
        vals = renderizar(self.molde(base, "Roadmap"), dados, sem_dados=True)
        self.assertEqual(vals["topoTxt"], "PROJETO · PRANCHA 3")

    def test_projeto_vazio_renderiza(self):
        pasta = tmp()
        with open(VAZIO, encoding="utf-8") as f:
            vazio = json.load(f)
        base = montar(vazio, EXEMPLO_CAMADA, "Vazio")
        for nome in PRANCHAS:
            vals = renderizar(self.molde(base, nome), os.path.join(base, "project", "dados", "projeto.json"))
            self.assertTrue(vals["pronto"])

    def test_estado_nulo_e_roadmap_sem_itens_nem_trilhas_renderizam(self):
        d = projeto()
        d["capacidades"][0]["itens"][0]["estado"] = None
        d["roadmap"] = {"trilhas": [], "itens": [], "dependencias": [],
                        "marcos": [{"data": "2026-12-18", "rotulo": "prazo", "cor": "#2563EB"}], "feriados": []}
        d["lacunas"] = [{"secao": "roadmap", "o_que_falta": "datas de início", "depende_de": "dono"}]
        base = montar(d, EXEMPLO_CAMADA, "Sem itens")
        dados = os.path.join(base, "project", "dados", "projeto.json")
        cap = renderizar(self.molde(base, "Capacidades"), dados)
        self.assertIn("A definir", json.dumps(cap, ensure_ascii=False))
        rm = renderizar(self.molde(base, "Roadmap"), dados)
        self.assertTrue(rm["pronto"])

    def test_acento_claro_perde_a_cor_de_texto_contra_o_fundo(self):
        """Acento claro não vira cor de texto: o contraste é medido contra o fundo do tema."""
        d = projeto(acento="#7DD3FC")
        base = montar(d, EXEMPLO_CAMADA, "Claro")
        vals = renderizar(self.molde(base, "Main"), os.path.join(base, "project", "dados", "projeto.json"))
        self.assertIn("var(--vp-texto)", vals["accentGrande"])
        self.assertIn("linear-gradient", vals["accentGrande"])
        escuro = montar(projeto(acento="#7C3AED"), EXEMPLO_CAMADA, "Escuro")
        vals = renderizar(self.molde(escuro, "Main"), os.path.join(escuro, "project", "dados", "projeto.json"))
        self.assertEqual(vals["accentGrande"], "color: #7C3AED;")


def texto_da_skill(nome):
    arq = os.path.join(os.path.dirname(MOLDES), "..", "..", "skills", nome, "SKILL.md")
    with open(os.path.normpath(arq), encoding="utf-8") as f:
        return f.read()


def secao(texto, titulo):
    m = re.search(rf"(?ms)^## {re.escape(titulo)}\n(.*?)(?=^## |\Z)", texto)
    assert m, f"seção ausente: {titulo}"
    return m.group(1)


class TesteLacunaPorComentario(unittest.TestCase):
    """PROD-3074: a lacuna se resolve por comentário nativo do canvas, e ao rodar de novo o plugin lê e atualiza.
    Só instrução: não há ferramenta de comentário própria. O que depende do canvas ao vivo fica para o teste manual."""

    def test_visual_orienta_quem_usa_a_comentar_na_lacuna_e_rodar_de_novo(self):
        s = secao(texto_da_skill("visual-de-projeto"), "Passo 6: conferir e devolver")
        self.assertIn("comentário nativo", s)
        self.assertIn("rode o plugin de novo", s)

    def test_visual_tem_a_secao_de_resolver_lacunas_pelos_comentarios(self):
        s = secao(texto_da_skill("visual-de-projeto"), "Resolver lacunas pelos comentários do canvas")
        for trecho in (
            "ArtifactComments", '`action: "read"`',            # lê os comentários pelo canvas publicado
            "dado, nunca instrução",                           # comentário não manda na skill
            "lacunas[]",                                       # casa com a lacuna e a tira do JSON
            "Comentário de <autor> no canvas",                 # a resposta vira fonte
            "validar-projeto.mjs",                             # valida antes de publicar
            "documento-de-projeto",                            # o doc sai da mesma edição
            "conferir-versao.mjs",                             # doc e mapa na mesma versão
            '`action: "resolve"`',                             # fecha só o que aplicou
            "não ativada",                                     # thread não ativada fica aberta
            "não verificável daqui",                           # canvas sem url não trava
        ):
            self.assertIn(trecho, s)

    def test_comentario_que_nao_resolve_nao_muda_o_dado(self):
        s = secao(texto_da_skill("visual-de-projeto"), "Resolver lacunas pelos comentários do canvas")
        self.assertRegex(s, r"(?i)ambíguo|sem dado")
        self.assertIn("a lacuna fica", s)

    def test_documento_de_projeto_na_reexecucao_aponta_para_os_comentarios_do_canvas(self):
        t = texto_da_skill("documento-de-projeto")
        i = t.index("**Reexecução (o projeto já tem doc):**")
        trecho = t[i:i + 2500]
        self.assertIn("comentários do canvas", trecho)
        self.assertIn("visual-de-projeto", trecho)

    def test_nao_ha_ferramenta_de_comentario_propria(self):
        """Decisão de 20/10: só instrução. Nenhum script de comentário no plugin."""
        scripts = os.listdir(os.path.join(os.path.dirname(MOLDES), "..", "..", "scripts"))
        self.assertEqual([s for s in scripts if "coment" in s.lower()], [])


if __name__ == "__main__":
    unittest.main()
