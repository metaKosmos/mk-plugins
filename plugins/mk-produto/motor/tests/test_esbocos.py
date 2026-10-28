"""O registro de esboços (jsonl lido e escrito), o isolamento por empresa, a promoção a template e a
decisão de "formato parecido", que olha os blocos e o elemento visual de cada um. E o montador do canvas
do esboço, que reprova direção sem elemento visual."""
import json
import os
import unittest

from _util import copiar_camada, node, precisa_node, tmp

PROPOSTA_A = "Capa|Problema|Solução|Roadmap|Riscos"
PROPOSTA_B = "Capa|Problema|Solucao|Linha do tempo|Riscos|Próximos passos"
OUTRO = "Capa|Equipe|Orçamento|Anexos|Glossário|FAQ"


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def cenario():
    """Camada de exemplo, registro e HOME em pasta própria: nada escreve fora do teste."""
    base = tmp()
    camada = copiar_camada(os.path.join(base, "camada"))
    return camada, os.path.join(base, "dados", "esbocos.jsonl"), os.path.join(base, "home")


def comparar(a, b, limiar=None, va=None, vb=None):
    extra = ["--limiar", str(limiar)] if limiar else []
    ea = ["--visuais", va] if va else []
    eb = ["--visuais", vb] if vb else []
    rc, out, err = node("esbocos.mjs", "comparar", "--estrutura", a, *ea, "--estrutura", b, *eb, *extra)
    assert rc == 0, err
    return json.loads(out)


def visuais_padrao(estrutura):
    """Um visual por bloco: o segundo é um fluxograma, o resto é texto de apoio."""
    n = len(estrutura.split("|"))
    return "|".join("fluxograma" if i == 1 else "texto" for i in range(n))


def registrar(camada, reg, pedido, estrutura, rotulo="A", nome="Narrativa", env=None, extra=(), visuais="padrao"):
    if visuais == "padrao":
        visuais = visuais_padrao(estrutura)
    com_visuais = ["--visuais", visuais] if visuais else []
    rc, out, err = node("esbocos.mjs", "registrar", "--camada", camada, "--registro", reg, "--pedido", pedido,
                        "--rotulo", rotulo, "--nome", nome, "--estrutura", estrutura, *com_visuais, *extra, env=env)
    return rc, json.loads(out)


def consultar(camada, reg, *estruturas, env=None):
    args = []
    for e in estruturas:
        args += ["--estrutura", e]
    rc, out, err = node("esbocos.mjs", "consultar", "--camada", camada, "--registro", reg, *args, env=env)
    assert rc == 0, err
    return json.loads(out)


@precisa_node
class TesteSimilaridade(unittest.TestCase):
    def test_mesma_estrutura_pontua_1(self):
        r = comparar(PROPOSTA_A, PROPOSTA_A)
        self.assertEqual(r["pontuacao"], 1)
        self.assertTrue(r["parecido"])

    def test_acento_caixa_plural_e_artigo_nao_separam_blocos(self):
        r = comparar("Hipóteses|O Problema|Capacidades", "hipotese|problema|capacidade")
        self.assertEqual(r["em_comum"], 3)
        self.assertEqual(r["pontuacao"], 1)

    def test_formato_parecido_com_blocos_a_mais_e_trocados(self):
        r = comparar(PROPOSTA_A, PROPOSTA_B)
        self.assertEqual(r["em_comum"], 4)
        self.assertEqual(r["blocos_em_comum"], ["Capa", "Problema", "Solução", "Riscos"])
        self.assertTrue(r["parecido"], r)

    def test_estrutura_de_outro_assunto_nao_e_parecida(self):
        r = comparar(PROPOSTA_A, OUTRO)
        self.assertFalse(r["parecido"], r)
        self.assertEqual(r["em_comum"], 1)

    def test_mesma_ordem_pesa_mais_que_ordem_trocada(self):
        em_ordem = comparar("A1 x|B2 y|C3 z|D4 w", "A1 x|B2 y|C3 z|D4 w")
        trocada = comparar("A1 x|B2 y|C3 z|D4 w", "D4 w|C3 z|B2 y|A1 x")
        self.assertGreater(em_ordem["pontuacao"], trocada["pontuacao"])
        self.assertEqual(trocada["conjunto"], 1)
        self.assertLess(trocada["ordem"], 1)

    def test_tres_blocos_em_comum_e_o_minimo(self):
        """Pontuação alta com só 2 blocos iguais não é formato."""
        r = comparar("Capa|Resumo", "Capa|Resumo")
        self.assertEqual(r["pontuacao"], 1)
        self.assertEqual(r["em_comum"], 2)
        self.assertFalse(r["parecido"])

    def test_limiar_muda_a_decisao(self):
        self.assertTrue(comparar(PROPOSTA_A, PROPOSTA_B, 0.6)["parecido"])
        self.assertFalse(comparar(PROPOSTA_A, PROPOSTA_B, 0.9)["parecido"])


@precisa_node
class TesteSimilaridadeVisual(unittest.TestCase):
    BLOCOS = "Visão geral|Fluxo|Arquitetura|Fila"
    VISUAIS_A = "texto|fluxograma|diagrama-de-blocos|linha-do-tempo"

    def test_mesmos_blocos_e_mesmos_visuais_seguem_parecidos(self):
        r = comparar(self.BLOCOS, self.BLOCOS, va=self.VISUAIS_A, vb=self.VISUAIS_A)
        self.assertEqual(r["visual"], 1)
        self.assertEqual(r["pontuacao"], 1)
        self.assertTrue(r["parecido"])

    def test_mesmos_blocos_com_visuais_diferentes_nao_sao_parecidos(self):
        outros = "texto|grafico|matriz|mapa-de-jornada"
        sem = comparar(self.BLOCOS, self.BLOCOS)
        com = comparar(self.BLOCOS, self.BLOCOS, va=self.VISUAIS_A, vb=outros)
        self.assertTrue(sem["parecido"], "só pelos nomes seriam o mesmo formato")
        self.assertEqual(com["conjunto"], 1)
        self.assertEqual(com["ordem"], 1)
        self.assertEqual(com["visual"], 0.25, "só o bloco de texto coincide")
        self.assertFalse(com["parecido"], com)

    def test_um_visual_diferente_entre_quatro_continua_parecido(self):
        r = comparar(self.BLOCOS, self.BLOCOS, va=self.VISUAIS_A, vb="texto|fluxograma|diagrama-de-blocos|grafico")
        self.assertEqual(r["visual"], 0.75)
        self.assertTrue(r["parecido"], r)

    def test_sem_visuais_de_um_dos_lados_a_conta_e_a_de_antes(self):
        """Linha antiga do registro não tem visuais: compara pelos nomes e não reprova por isso."""
        r = comparar(self.BLOCOS, self.BLOCOS, va=self.VISUAIS_A)
        self.assertIsNone(r["visual"])
        self.assertEqual(r["pontuacao"], 1)

    def test_visuais_de_tamanho_errado_sao_ignorados(self):
        r = comparar(self.BLOCOS, self.BLOCOS, va="texto|fluxograma", vb=self.VISUAIS_A)
        self.assertIsNone(r["visual"])


@precisa_node
class TesteRegistro(unittest.TestCase):
    def test_registrar_cria_a_pasta_e_o_jsonl_e_consultar_le_de_volta(self):
        camada, reg, _ = cenario()
        self.assertFalse(os.path.exists(os.path.dirname(reg)))
        rc, r = registrar(camada, reg, "proposta de feira", PROPOSTA_A, extra=["--canvas", "https://exemplo.test/c1", "--data", "2026-10-01"])
        self.assertEqual(rc, 0, r)
        self.assertEqual(r["ocorrencia"], 1)
        self.assertFalse(r["propor_template"])
        with open(reg, encoding="utf-8") as f:
            linhas = f.read().splitlines()
        self.assertEqual(len(linhas), 1)
        e = json.loads(linhas[0])
        self.assertEqual(e["empresa"], "Fábrica Exemplo")
        self.assertEqual(e["data"], "2026-10-01")
        self.assertEqual(e["estrutura"], PROPOSTA_A.split("|"))
        self.assertEqual(e["canvas"], "https://exemplo.test/c1")
        c = consultar(camada, reg, PROPOSTA_A)
        self.assertEqual(c["entradas_lidas"], 1)
        self.assertEqual(c["parecidos"][0]["pedido"], "proposta de feira")
        self.assertEqual(c["parecidos"][0]["canvas"], "https://exemplo.test/c1")

    def test_registro_vazio_ou_ausente_nao_acha_nada(self):
        camada, reg, _ = cenario()
        c = consultar(camada, reg, PROPOSTA_A)
        self.assertEqual(c["entradas_lidas"], 0)
        self.assertEqual(c["parecidos"], [])
        self.assertFalse(c["segunda_ocorrencia"])

    def test_linha_ruim_vira_aviso_e_nao_trava(self):
        camada, reg, _ = cenario()
        registrar(camada, reg, "primeiro", PROPOSTA_A)
        with open(reg, "a", encoding="utf-8") as f:
            f.write("isto nao e json\n\n{\"sem\": \"estrutura\"}\n")
        registrar(camada, reg, "terceiro", OUTRO)
        c = consultar(camada, reg, PROPOSTA_A)
        self.assertEqual(c["entradas_lidas"], 2)
        self.assertEqual(len(c["avisos"]), 2)
        self.assertIn("linha 2 ignorada", c["avisos"][0])
        self.assertEqual(len(c["parecidos"]), 1)

    def test_registro_de_outra_empresa_nao_aparece(self):
        camada, reg, _ = cenario()
        outra = copiar_camada(os.path.join(tmp(), "camada2"), ajuste=lambda c: c["empresa"].update(nome="Outra Empresa"))
        registrar(outra, reg, "pedido da outra", PROPOSTA_A)
        c = consultar(camada, reg, PROPOSTA_A)
        self.assertEqual(c["entradas_lidas"], 1)
        self.assertEqual(c["entradas_da_empresa"], 0)
        self.assertEqual(c["parecidos"], [])
        rc, r = registrar(camada, reg, "meu pedido", PROPOSTA_A)
        self.assertEqual(r["ocorrencia"], 1, "formato da outra empresa não conta como uso anterior")

    def test_caminho_do_registro_vem_da_camada_com_til(self):
        base = tmp()
        camada = copiar_camada(os.path.join(base, "camada"),
                               ajuste=lambda c: c["esbocos"].update(registro="~/meus-esbocos/reg.jsonl"))
        home = os.path.join(base, "home")
        rc, out, err = node("esbocos.mjs", "registrar", "--camada", camada, "--pedido", "p", "--rotulo", "A",
                            "--nome", "n", "--estrutura", PROPOSTA_A, "--visuais", visuais_padrao(PROPOSTA_A), env={"HOME": home})
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.exists(os.path.join(home, "meus-esbocos", "reg.jsonl")))

    def test_padrao_e_fora_do_plugin_na_config_do_usuario(self):
        base = tmp()
        camada = copiar_camada(os.path.join(base, "camada"), ajuste=lambda c: c.pop("esbocos"))
        home = os.path.join(base, "home")
        rc, out, err = node("esbocos.mjs", "registrar", "--camada", camada, "--pedido", "p", "--rotulo", "A",
                            "--nome", "n", "--estrutura", PROPOSTA_A, "--visuais", visuais_padrao(PROPOSTA_A), env={"HOME": home})
        self.assertEqual(rc, 0, err)
        self.assertTrue(os.path.exists(os.path.join(home, ".config", "vanta-produto", "esbocos.jsonl")))

    def test_estrutura_curta_e_recusada_e_nada_e_gravado(self):
        camada, reg, _ = cenario()
        rc, r = registrar(camada, reg, "p", "Capa|Resumo")
        self.assertEqual(rc, 1)
        self.assertFalse(r["registrado"])
        self.assertIn("no mínimo 3 blocos", r["erros"][0])
        self.assertFalse(os.path.exists(reg))

    def test_texto_fora_da_marca_ou_com_travessao_e_recusado(self):
        camada, reg, _ = cenario()
        rc, r = registrar(camada, reg, "proposta do FX", PROPOSTA_A)
        self.assertEqual(rc, 1)
        self.assertTrue(any('"fX"' in e for e in r["erros"]), r)
        rc, r = registrar(camada, reg, "pedido — com travessão", PROPOSTA_A)
        self.assertEqual(rc, 1)
        self.assertTrue(any("traço longo" in e for e in r["erros"]), r)
        self.assertFalse(os.path.exists(reg))

    def test_registro_grava_privilegia_visuais_dominante_e_leitor(self):
        camada, reg, _ = cenario()
        rc, r = registrar(camada, reg, "mapa", PROPOSTA_A, extra=["--privilegia", "o fluxo de ponta a ponta", "--visual-dominante", "fluxograma"])
        self.assertEqual(rc, 0, r)
        with open(reg, encoding="utf-8") as f:
            e = json.loads(f.read())
        self.assertEqual(e["direcao"]["privilegia"], "o fluxo de ponta a ponta")
        self.assertEqual(e["direcao"]["visual_dominante"], "fluxograma")
        self.assertEqual(e["visuais"], ["texto", "fluxograma", "texto", "texto", "texto"])
        self.assertEqual(e["leitor"], "visual")
        self.assertEqual(len(e["visuais"]), len(e["estrutura"]))

    def test_registrar_sem_nenhum_bloco_visual_e_recusado(self):
        camada, reg, _ = cenario()
        for rotulo, visuais in {"sem visuais": None, "só texto": "texto|texto|texto|texto|texto"}.items():
            with self.subTest(rotulo):
                rc, r = registrar(camada, reg, "mapa", PROPOSTA_A, visuais=visuais)
                self.assertEqual(rc, 1, r)
                self.assertTrue(any("nenhum bloco visual" in e for e in r["erros"]), r)
        self.assertFalse(os.path.exists(reg))

    def test_leitor_textual_declarado_dispensa_o_visual(self):
        camada, reg, _ = cenario()
        rc, r = registrar(camada, reg, "ata", PROPOSTA_A, visuais="texto|texto|texto|texto|texto", extra=["--leitor", "textual"])
        self.assertEqual(rc, 0, r)
        rc, out, err = node("esbocos.mjs", "registrar", "--camada", camada, "--registro", reg, "--pedido", "p", "--rotulo", "A",
                            "--nome", "n", "--estrutura", PROPOSTA_A, "--leitor", "qualquer")
        self.assertEqual(rc, 2)

    def test_visuais_fora_da_lista_ou_de_tamanho_errado_sao_recusados(self):
        camada, reg, _ = cenario()
        rc, r = registrar(camada, reg, "p", PROPOSTA_A, visuais="texto|fluxograma|texto")
        self.assertEqual(rc, 1)
        self.assertTrue(any("um por bloco" in e for e in r["erros"]), r)
        rc, r = registrar(camada, reg, "p", PROPOSTA_A, visuais="texto|desenho|texto|texto|texto")
        self.assertEqual(rc, 1)
        self.assertTrue(any('"desenho" fora do permitido' in e for e in r["erros"]), r)
        self.assertFalse(os.path.exists(reg))

    def test_mesmos_blocos_com_visuais_diferentes_nao_contam_como_o_mesmo_formato(self):
        camada, reg, _ = cenario()
        registrar(camada, reg, "mapa", PROPOSTA_A, visuais="texto|fluxograma|diagrama-de-blocos|linha-do-tempo|texto")
        c = consultar(camada, reg, PROPOSTA_A)
        self.assertEqual(len(c["parecidos"]), 1, "sem visuais no rascunho, só os nomes contam")
        rc, r = registrar(camada, reg, "outro mapa", PROPOSTA_A, visuais="texto|grafico|matriz|mapa-de-jornada|amostras-de-design")
        self.assertEqual(r["ocorrencia"], 1, "mesmos blocos, visuais todos diferentes: outro formato")
        self.assertFalse(r["propor_template"])
        rc, r = registrar(camada, reg, "mapa de novo", PROPOSTA_A, visuais="texto|fluxograma|diagrama-de-blocos|linha-do-tempo|texto")
        self.assertEqual(r["ocorrencia"], 2)
        self.assertTrue(r["propor_template"])

    def test_linha_antiga_sem_visuais_continua_valendo(self):
        camada, reg, _ = cenario()
        os.makedirs(os.path.dirname(reg))
        with open(reg, "w", encoding="utf-8") as f:
            f.write(json.dumps({"versao": 1, "data": "2026-09-01", "empresa": "Fábrica Exemplo", "pedido": "antigo",
                                "direcao": {"rotulo": "A", "nome": "n"}, "estrutura": PROPOSTA_A.split("|"), "canvas": None}) + "\n")
        rc, out, err = node("esbocos.mjs", "consultar", "--camada", camada, "--registro", reg, "--estrutura", PROPOSTA_A,
                            "--visuais", visuais_padrao(PROPOSTA_A))
        self.assertEqual(rc, 0, err)
        c = json.loads(out)
        self.assertEqual(len(c["parecidos"]), 1)
        self.assertIsNone(c["parecidos"][0]["visual"])

    def test_sem_camada_o_registro_nao_roda(self):
        rc, out, err = node("esbocos.mjs", "consultar", "--estrutura", PROPOSTA_A, cwd=tmp())
        self.assertEqual(rc, 2)
        self.assertIn("camada não encontrada", err)


@precisa_node
class TesteSegundaOcorrencia(unittest.TestCase):
    def test_primeira_nao_propoe_segunda_propoe_e_promover_encerra_a_proposta(self):
        camada, reg, _ = cenario()
        rc, r1 = registrar(camada, reg, "proposta de feira", PROPOSTA_A)
        self.assertEqual((r1["ocorrencia"], r1["propor_template"]), (1, False))

        # a consulta anterior ao esboço já mostra o formato usado como direção e avisa da repetição
        c = consultar(camada, reg, PROPOSTA_B, OUTRO)
        self.assertEqual(len(c["parecidos"]), 1)
        self.assertTrue(c["segunda_ocorrencia"])
        self.assertTrue(c["propor_template"])

        rc, r2 = registrar(camada, reg, "proposta de convenção", PROPOSTA_B, rotulo="B")
        self.assertEqual(r2["ocorrencia"], 2)
        self.assertTrue(r2["propor_template"])
        self.assertIsNone(r2["template"])

        rc, out, err = node("esbocos.mjs", "promover", "--camada", camada, "--nome", "Proposta Curta",
                            "--entrega", "Proposta de uma página: problema, solução e riscos.",
                            "--estrutura", PROPOSTA_B, "--etapa", "3")
        self.assertEqual(rc, 0, out + err)
        tpl = json.loads(out)["template"]
        self.assertEqual((tpl["estado"], tpl["skill_do_motor"], tpl["etapa"]), ("em esboço", None, 3))

        rc, out, _ = node("validar-camada.mjs", camada)
        self.assertEqual(rc, 0, out)
        self.assertIn("Proposta Curta (em esboço)", out)

        rc, r3 = registrar(camada, reg, "proposta de abertura", PROPOSTA_A, rotulo="A")
        self.assertEqual(r3["ocorrencia"], 3)
        self.assertEqual(r3["template"]["nome"], "Proposta Curta")
        self.assertFalse(r3["propor_template"], "já é template: não propõe de novo")

    def test_formato_diferente_nao_conta_como_segunda_ocorrencia(self):
        camada, reg, _ = cenario()
        registrar(camada, reg, "proposta de feira", PROPOSTA_A)
        rc, r = registrar(camada, reg, "plano de orçamento", OUTRO, rotulo="C")
        self.assertEqual(r["ocorrencia"], 1)
        self.assertFalse(r["propor_template"])

    def test_template_do_exemplo_com_estrutura_e_reconhecido(self):
        camada, reg, _ = cenario()
        c = consultar(camada, reg, "Capa|O que entrou|O que ficou de fora|Próximos passos")
        self.assertEqual(c["template"]["nome"], "Resumo de Entrega")

    def test_promover_nome_repetido_e_recusado_e_o_arquivo_nao_muda(self):
        camada, _, _ = cenario()
        antes = ler(os.path.join(camada, "templates.json"))
        rc, out, _ = node("esbocos.mjs", "promover", "--camada", camada, "--nome", "ficha do projeto",
                          "--entrega", "x", "--estrutura", PROPOSTA_A)
        self.assertEqual(rc, 1)
        self.assertIn("já existe um template", out)
        self.assertEqual(ler(os.path.join(camada, "templates.json")), antes)

    def test_promover_com_texto_fora_da_marca_desfaz(self):
        camada, _, _ = cenario()
        antes = ler(os.path.join(camada, "templates.json"))
        rc, out, _ = node("esbocos.mjs", "promover", "--camada", camada, "--nome", "Painel FX",
                          "--entrega", "x", "--estrutura", PROPOSTA_A)
        self.assertEqual(rc, 1)
        self.assertEqual(ler(os.path.join(camada, "templates.json")), antes)

    def test_promover_cria_templates_json_quando_nao_existe(self):
        camada, _, _ = cenario()
        os.remove(os.path.join(camada, "templates.json"))
        rc, out, err = node("esbocos.mjs", "promover", "--camada", camada, "--nome", "Proposta Curta",
                            "--entrega", "x", "--estrutura", PROPOSTA_A)
        self.assertEqual(rc, 0, out + err)
        with open(os.path.join(camada, "templates.json"), encoding="utf-8") as f:
            self.assertEqual(json.load(f)["templates"][0]["nome"], "Proposta Curta")


SVG = '<svg width="200" height="60" viewBox="0 0 200 60"><rect x="4" y="4" width="80" height="40" fill="none" stroke="currentColor"/><path d="M84 24 L140 24" stroke="currentColor"/></svg>'
FRAGMENTO = f'<h1 style="font-family:var(--vp-fonte-titulo)">Capa</h1>{SVG}<p>Texto da direção</p>'
DOMINANTES = {"A": "fluxograma", "B": "diagrama-de-blocos", "C": "linha-do-tempo"}


def estrutura_visual(r):
    """Três blocos: o texto de apoio e dois com elemento visual, um deles o dominante da direção."""
    return [{"bloco": "Capa", "visual": "texto"}, {"bloco": "Problema", "visual": DOMINANTES[r]}, {"bloco": "Solução", "visual": "matriz"}]


def escrever_esboco(pasta, direcoes=2, h=2000, final=None, fragmento=FRAGMENTO, leitor=None):
    os.makedirs(pasta, exist_ok=True)
    spec = {"versao": 1, "titulo": "Material de teste", "pedido": "um material de teste", "direcoes": [], "lacunas": [{"o_que_falta": "valor do orçamento", "depende_de": "financeiro"}]}
    if leitor:
        spec["leitor"] = leitor
    for i in range(direcoes):
        r = "ABC"[i]
        arq = f"d{r}.html"
        with open(os.path.join(pasta, arq), "w", encoding="utf-8") as f:
            f.write(fragmento)
        spec["direcoes"].append({"rotulo": r, "nome": f"Direção {r}", "privilegia": "a decisão", "visual_dominante": DOMINANTES[r], "estrutura": estrutura_visual(r), "arquivo": arq, "h": h})
    if final:
        with open(os.path.join(pasta, "final.html"), "w", encoding="utf-8") as f:
            f.write(fragmento)
        spec["final"] = final
    with open(os.path.join(pasta, "esboco.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False)
    return os.path.join(pasta, "esboco.json")


@precisa_node
class TesteMontarEsboco(unittest.TestCase):
    def setUp(self):
        base = tmp()
        self.camada = copiar_camada(os.path.join(base, "camada"))
        self.trab = os.path.join(base, "trab")
        self.saida = os.path.join(base, "saida")

    def test_monta_pranchas_lado_a_lado_com_tokens_da_camada(self):
        spec = escrever_esboco(self.trab, direcoes=3)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 0, out + err)
        with open(os.path.join(self.saida, "project", "canvas.json"), encoding="utf-8") as f:
            canvas = json.load(f)
        self.assertEqual(canvas["order"], ["Main.dc.html", "Direcao-B.dc.html", "Direcao-C.dc.html"])
        self.assertEqual([canvas["boards"][a]["x"] for a in canvas["order"]], [0, 1520, 3040])
        self.assertEqual(canvas["designSystems"], [])
        html = ler(os.path.join(self.saida, "project", "Main.dc.html"))
        self.assertIn("--vp-acento:#2563EB", html, "tokens da camada")
        self.assertIn("Bebas+Neue", html)
        self.assertIn("lacuna  valor do orçamento", out)

    def test_prancha_final_entra_no_mesmo_canvas(self):
        spec = escrever_esboco(self.trab, final={"escolha": "A com o bloco Problema de B", "estrutura": estrutura_visual("A"), "arquivo": "final.html", "h": 2400})
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 0, out + err)
        with open(os.path.join(self.saida, "project", "canvas.json"), encoding="utf-8") as f:
            canvas = json.load(f)
        self.assertEqual(canvas["order"][-1], "Final.dc.html")
        self.assertEqual(canvas["boards"]["Final.dc.html"]["h"], 2400)

    def test_altura_acima_do_teto_de_8000_reprova(self):
        spec = escrever_esboco(self.trab, h=8001)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 1)
        self.assertIn("passa do teto de 8000 px", err)
        self.assertFalse(os.path.exists(os.path.join(self.saida, "project", "canvas.json")))

    def test_altura_no_teto_passa(self):
        spec = escrever_esboco(self.trab, h=8000)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 0, out + err)

    def test_fragmento_com_script_ou_variavel_do_canvas_reprova(self):
        for n, (frag, msg) in enumerate((("<script>x()</script>", "<script>"), ("<p>{{nome}}</p>", '"{{"'))):
            with self.subTest(msg):
                spec = escrever_esboco(f"{self.trab}-{n}", fragmento=frag)
                rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
                self.assertEqual(rc, 1)
                self.assertIn(msg, err)

    def test_marca_e_travessao_no_fragmento_reprovam(self):
        spec = escrever_esboco(self.trab, fragmento="<p>Lançamento do FX — agora</p>")
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 1)
        self.assertIn("traço longo", err)
        self.assertIn('A grafia é "fX"', err)

    def _com_arquivo(self, valor):
        spec = escrever_esboco(self.trab)
        with open(spec, encoding="utf-8") as f:
            d = json.load(f)
        d["direcoes"][0]["arquivo"] = valor
        with open(spec, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        return spec

    def test_fragmento_fora_da_pasta_do_esboco_e_recusado(self):
        """Caminho absoluto, '..', extensão que não é .html e link simbólico para fora não são lidos."""
        segredo = os.path.join(os.path.dirname(self.trab), "segredo.html")
        with open(segredo, "w", encoding="utf-8") as f:
            f.write("<p>CONTEUDO-FORA-DA-PASTA</p>")
        escrever_esboco(self.trab)
        os.symlink(segredo, os.path.join(self.trab, "elo.html"))
        os.makedirs(os.path.join(self.trab, "sub"), exist_ok=True)
        with open(os.path.join(self.trab, "dados.txt"), "w", encoding="utf-8") as f:
            f.write("<p>texto</p>")
        casos = {
            "absoluto": segredo,
            "sobe com ..": "../segredo.html",
            "sobe no meio": "sub/../../segredo.html",
            "extensão": "dados.txt",
            "link simbólico": "elo.html",
        }
        for rotulo, valor in casos.items():
            with self.subTest(rotulo):
                spec = self._com_arquivo(valor)
                rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
                self.assertEqual(rc, 1, err)
                self.assertIn("recusado ou ilegível", err)
                self.assertNotIn("CONTEUDO-FORA-DA-PASTA", out + err)
                self.assertFalse(os.path.exists(os.path.join(self.saida, "project", "Main.dc.html")))

    def test_fragmento_em_subpasta_da_pasta_do_esboco_passa(self):
        spec = escrever_esboco(self.trab)
        os.makedirs(os.path.join(self.trab, "sub"))
        os.rename(os.path.join(self.trab, "dA.html"), os.path.join(self.trab, "sub", "dA.html"))
        with open(spec, encoding="utf-8") as f:
            d = json.load(f)
        d["direcoes"][0]["arquivo"] = "sub/dA.html"
        with open(spec, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 0, out + err)

    def test_menos_de_duas_direcoes_reprova_pelo_contrato(self):
        spec = escrever_esboco(self.trab, direcoes=1)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 1)
        self.assertIn("direcoes: precisa de pelo menos 2", err)

    def test_estrutura_com_menos_de_3_blocos_reprova_pelo_contrato(self):
        spec = escrever_esboco(self.trab)
        with open(spec, encoding="utf-8") as f:
            d = json.load(f)
        d["direcoes"][0]["estrutura"] = [{"bloco": "Capa", "visual": "texto"}, {"bloco": "Resumo", "visual": "fluxograma"}]
        with open(spec, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 1)
        self.assertIn("direcoes[0].estrutura: precisa de pelo menos 3", err)

    def test_rotulo_de_direcao_repetido_reprova(self):
        spec = escrever_esboco(self.trab, direcoes=2)
        with open(spec, encoding="utf-8") as f:
            d = json.load(f)
        d["direcoes"][1]["rotulo"] = "A"
        with open(spec, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        rc, out, err = node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)
        self.assertEqual(rc, 1)
        self.assertIn("rótulo repetido", err)


@precisa_node
class TesteMontarEsbocoVisual(unittest.TestCase):
    """O leitor é de produto e visual: direção só com texto em grade não passa."""

    def setUp(self):
        base = tmp()
        self.camada = copiar_camada(os.path.join(base, "camada"))
        self.trab = os.path.join(base, "trab")
        self.saida = os.path.join(base, "saida")

    def _editar(self, mudanca, **kw):
        spec = escrever_esboco(self.trab, **kw)
        with open(spec, encoding="utf-8") as f:
            d = json.load(f)
        mudanca(d)
        with open(spec, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False)
        return spec

    def _monta(self, spec):
        return node("montar-esboco.mjs", spec, self.saida, "--camada", self.camada)

    def _reprova(self, spec, trecho):
        rc, out, err = self._monta(spec)
        self.assertEqual(rc, 1, out + err)
        self.assertIn(trecho, err)
        self.assertFalse(os.path.exists(os.path.join(self.saida, "project", "canvas.json")))

    def test_direcao_sem_nenhum_bloco_visual_reprova(self):
        def so_texto(d):
            d["direcoes"][1]["estrutura"] = [{"bloco": b, "visual": "texto"} for b in ("Capa", "Problema", "Solução")]
        self._reprova(self._editar(so_texto), "direção B: nenhum bloco visual")

    def test_estrutura_so_com_nomes_vale_como_texto_e_reprova(self):
        """A forma antiga (lista de nomes) continua lida, e conta como bloco sem visual."""
        def antigo(d):
            d["direcoes"][0]["estrutura"] = ["Capa", "Problema", "Solução"]
        self._reprova(self._editar(antigo), "direção A: nenhum bloco visual")

    def test_leitor_textual_declarado_dispensa_o_visual(self):
        def so_texto(d):
            for x in d["direcoes"]:
                x["estrutura"] = ["Capa", "Problema", "Solução"]
                x.pop("visual_dominante")
        spec = self._editar(so_texto, leitor="textual", fragmento="<p>Só texto</p>")
        rc, out, err = self._monta(spec)
        self.assertEqual(rc, 0, out + err)

    def test_passa_com_visual_e_mostra_os_visuais_de_cada_prancha(self):
        rc, out, err = self._monta(escrever_esboco(self.trab))
        self.assertEqual(rc, 0, out + err)
        self.assertIn("[visuais: fluxograma, matriz]", out)

    def test_visual_dominante_e_obrigatorio(self):
        self._reprova(self._editar(lambda d: d["direcoes"][0].pop("visual_dominante")), 'falta "visual_dominante"')

    def test_visual_dominante_tem_de_aparecer_nos_blocos(self):
        def fora(d):
            d["direcoes"][0]["visual_dominante"] = "grafico"
        self._reprova(self._editar(fora), 'visual_dominante "grafico" não aparece')

    def test_direcoes_com_o_mesmo_visual_dominante_reprovam(self):
        def igual(d):
            d["direcoes"][1]["visual_dominante"] = "fluxograma"
            d["direcoes"][1]["estrutura"] = estrutura_visual("A")
        self._reprova(self._editar(igual), "o mesmo elemento visual dominante (fluxograma)")

    def test_grafico_sem_fonte_reprova_e_com_fonte_passa(self):
        def grafico(d):
            d["direcoes"][0]["visual_dominante"] = "grafico"
            d["direcoes"][0]["estrutura"][1] = {"bloco": "Problema", "visual": "grafico"}
        self._reprova(self._editar(grafico), "gráfico sem \"fonte\"")

        def com_fonte(d):
            grafico(d)
            d["direcoes"][0]["estrutura"][1]["fonte"] = "planilha de pedidos, aba Mensal"
        rc, out, err = self._monta(self._editar(com_fonte))
        self.assertEqual(rc, 0, out + err)

    def test_fragmento_sem_svg_reprova_com_leitor_visual(self):
        self._reprova(escrever_esboco(self.trab, fragmento="<h1>Capa</h1><p>texto em grade</p>"), "não tem nenhum <svg>")

    def test_visual_fora_da_lista_reprova_pelo_contrato(self):
        def invalido(d):
            d["direcoes"][0]["estrutura"][1]["visual"] = "desenho"
        self._reprova(self._editar(invalido), '"desenho" fora do permitido')

    def test_final_tambem_precisa_de_bloco_visual(self):
        final = {"escolha": "A", "estrutura": [{"bloco": b, "visual": "texto"} for b in ("Capa", "Problema", "Solução")], "arquivo": "final.html", "h": 2400}
        self._reprova(escrever_esboco(self.trab, final=final), "final: nenhum bloco visual")


if __name__ == "__main__":
    unittest.main()
