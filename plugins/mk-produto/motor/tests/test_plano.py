"""plano.json: contrato, validar-plano.mjs, descricao-issue.mjs e o bloco gestor da camada."""
import json
import os
import re
import unittest

from _util import (EXEMPLO_CAMADA, PLANO, PLUGIN, copiar_camada, gravar_json, issue, node,
                   plano, precisa_node, tmp)


def validar(dados, camada=EXEMPLO_CAMADA):
    caminho = gravar_json(tmp(), "plano.json", dados)
    args = [caminho] + (["--camada", camada] if camada else [])
    return node("validar-plano.mjs", *args, cwd=tmp())


def descrever(dados, *extra, camada=EXEMPLO_CAMADA):
    caminho = gravar_json(tmp(), "plano.json", dados)
    args = [caminho, *extra] + (["--camada", camada] if camada else [])
    return node("descricao-issue.mjs", *args, cwd=tmp())


def projeto_novo(d):
    """O plano de um projeto que ainda não existe no gestor: a skill propõe criar projeto e milestones."""
    d["ref"]["projeto"] = {"nome": "Projeto Exemplo", "novo": True, "descricao": "Projeto fictício para testar a etapa opcional."}
    for m in d["milestones"]:
        m.pop("id", None)
        m["novo"] = True
        if m["data"]:
            m["data_fonte"] = "marco de Pessoa Exemplo, mensagem de 09/11/2026"


@precisa_node
class TesteValidarPlano(unittest.TestCase):
    def reprova(self, dados, trecho, camada=EXEMPLO_CAMADA):
        rc, out, _ = validar(dados, camada)
        self.assertEqual(rc, 1, out)
        self.assertIn(trecho, out)
        return out

    def test_exemplo_e_valido_com_e_sem_camada(self):
        rc, out, _ = node("validar-plano.mjs", PLANO, "--camada", EXEMPLO_CAMADA)
        self.assertEqual(rc, 0, out)
        self.assertIn("0 erros", out)
        rc, out, _ = node("validar-plano.mjs", PLANO)
        self.assertEqual(rc, 0, out)
        self.assertIn("sem camada", out)

    def test_controle_positivo_o_exemplo_cobre_as_tres_naturezas_de_issue(self):
        d = plano()
        tipos = {i.get("tipo", "fluxo") for i in d["issues"]}
        self.assertEqual(tipos, {"fluxo", "risco", "clareza"})
        self.assertTrue(any(i.get("responsavel_autorizado") for i in d["issues"]))
        self.assertTrue(any(i.get("responsavel_sugerido") for i in d["issues"]))

    def test_campo_obrigatorio_e_campo_desconhecido(self):
        self.reprova(issue(lambda i: i.pop("resultado")), "issues[0].resultado: campo obrigatório ausente")
        self.reprova(issue(lambda i: i.update(inventado=1)), "issues[0].inventado: campo desconhecido")

    # ---- contrato de onze campos (PROD-3071) ----

    def test_os_quatro_campos_novos_e_o_contexto_sao_obrigatorios(self):
        for campo in ("modo", "pode_mexer_em", "entrega", "portao", "contexto"):
            with self.subTest(campo):
                self.reprova(issue(lambda i: i.pop(campo)), f"issues[0].{campo}: campo obrigatório ausente")

    def test_modo_aceita_os_quatro_e_recusa_outro(self):
        for modo in ("direto", "entrevista", "brainstorming", "pesquisa"):
            with self.subTest(modo):
                rc, out, _ = validar(issue(lambda i: i.update(modo=modo)))
                self.assertEqual(rc, 0, out)
        self.reprova(issue(lambda i: i.update(modo="plan mode")), "issues[0].modo")

    def test_entrega_e_pode_mexer_em_nao_ficam_vazios(self):
        self.reprova(issue(lambda i: i.update(entrega=[])), "issues[0].entrega: precisa de pelo menos 1")
        self.reprova(issue(lambda i: i.update(pode_mexer_em=[])), "issues[0].pode_mexer_em: precisa de pelo menos 1")
        self.reprova(issue(lambda i: i.update(portao="")), "issues[0].portao: vazio")

    def test_texto_so_com_espaco_reprova_como_vazio(self):
        # PROD-3070: "   " passava o schema (minLength contava o espaço)
        for campo, valor in (
            ("fluxo", "   "), ("resultado", " \t"), ("teste_principal", "   "), ("portao", "   "),
            ("fora", " "), ("se_nunca_for_feita", "  "), ("contexto", "  "), ("titulo", "   "),
            ("entrega", ["  "]), ("pode_mexer_em", [" "]), ("repos", ["  "]),
        ):
            with self.subTest(campo):
                self.reprova(issue(lambda i: i.update({campo: valor})), f"issues[0].{campo}")

    def test_texto_com_espaco_nas_pontas_continua_valido(self):
        rc, out, _ = validar(issue(lambda i: i.update(portao="  quem confere, com a prova  ")))
        self.assertEqual(rc, 0, out)

    def test_json_ilegivel(self):
        pasta = tmp()
        arq = os.path.join(pasta, "p.json")
        with open(arq, "w", encoding="utf-8") as f:
            f.write("{nao e json")
        rc, out, err = node("validar-plano.mjs", arq, cwd=pasta)
        self.assertEqual(rc, 1)
        self.assertIn("JSON ilegível", err)

    def test_sem_argumento_sai_com_2(self):
        rc, _, err = node("validar-plano.mjs")
        self.assertEqual(rc, 2)
        self.assertIn("uso:", err)

    # ---- título ----

    def test_titulo_por_mecanismo_reprova(self):
        for termo in ("endpoint", "tabela", "migração", "Refatorar", "API", "banco de dados"):
            with self.subTest(termo):
                self.reprova(issue(lambda i: i.update(titulo=f"Checkout fX Loja: criar {termo} de pedidos")),
                             "é mecanismo")

    def test_titulo_nao_confunde_palavra_que_so_contem_o_termo(self):
        rc, out, _ = validar(issue(lambda i: i.update(titulo="Checkout fX Loja: cliente paga rápido e vê a rapidez da tela")))
        self.assertEqual(rc, 0, out)

    def test_termo_extra_da_camada(self):
        rc, out, _ = validar(issue(lambda i: i.update(titulo="Checkout fX Loja: cliente recebe o webhook")))
        self.assertEqual(rc, 1)
        self.assertIn('"webhook" é mecanismo', out)

    def test_titulo_sem_superficie_reprova(self):
        self.reprova(issue(lambda i: i.update(titulo="cliente paga o pedido por cartão")),
                     "não segue \"<Superfície>: <o que o usuário faz>\"")

    # ---- teste principal ----

    def test_teste_principal_vago_reprova(self):
        self.reprova(issue(lambda i: i.update(teste_principal="funciona")), "issues[0].teste_principal")

    def test_teste_principal_com_tres_partes_sem_abertura_passa(self):
        rc, out, _ = validar(issue(lambda i: i.update(teste_principal="loja de exemplo, pedido de teste, vejo a confirmação")))
        self.assertEqual(rc, 0, out)

    def test_teste_principal_com_verbos_de_quem_usa_passa_sem_comecar_por_abro(self):
        for texto in (
            "peço para quebrar o projeto de leads e vejo a proposta por interface",
            "comento na issue e vejo o comentário no topo da lista",
            "gero o relatório do mês e vejo o total por produto",
            "digo o nome da loja ao assistente e vejo a loja escolhida",
            "escolho o mês, baixo o extrato e vejo o arquivo com as vendas",
        ):
            with self.subTest(texto):
                rc, out, _ = validar(issue(lambda i: i.update(teste_principal=texto)))
                self.assertEqual(rc, 0, out)

    def test_teste_principal_sem_verbo_de_quem_usa_continua_reprovado(self):
        for texto in ("o endpoint devolve 200", "tela de saldo funcionando", "relatório correto e completo"):
            with self.subTest(texto):
                self.reprova(issue(lambda i: i.update(teste_principal=texto)), "issues[0].teste_principal")

    def test_teste_principal_com_verbo_de_quem_usa_fora_da_lista_passa(self):
        # PROD-3070, achado 3: a lista fechada de verbos reprovava frases legítimas
        for texto in (
            "converso com o agente sobre o projeto e vejo a resposta com fonte",
            "testo o comando no terminal e vejo o resultado",
            "solicito o relatório pelo painel e vejo o PDF",
            "uso o painel para filtrar por marca e vejo só os pedidos dela",
            "chamo o comando /plano e vejo a tabela",
            # verbo que nenhuma lista conhece: o que vale é a ação em primeira pessoa e o que se vê
            "inspeciono o painel de saldo e vejo uma linha por produto",
            "reviso o pedido de teste e confiro o total na tela",
            "aciono o botão de exportar e o arquivo aparece na pasta",
        ):
            with self.subTest(texto):
                rc, out, _ = validar(issue(lambda i: i.update(teste_principal=texto)))
                self.assertEqual(rc, 0, out)

    def test_teste_principal_tecnico_sem_pessoa_reprova(self):
        for texto in (
            "o endpoint devolve 200",
            "a função retorna true",
            "o teste passa",
            "o projeto aparece com o resultado correto",  # palavra em o que não é verbo
            "todo o relatório aparece como o painel mostra",
            "o endpoint devolve 200 e vejo o log",  # observa, mas ninguém age
        ):
            with self.subTest(texto):
                self.reprova(issue(lambda i: i.update(teste_principal=texto)), "issues[0].teste_principal")

    def test_teste_principal_com_acao_e_sem_observacao_reprova(self):
        self.reprova(issue(lambda i: i.update(teste_principal="converso com o agente sobre o projeto")),
                     "issues[0].teste_principal")

    def test_teste_principal_sem_o_que_se_ve_avisa(self):
        rc, out, _ = validar(issue(lambda i: i.update(teste_principal="abro a loja de exemplo e finalizo o pedido de teste")))
        self.assertEqual(rc, 0, out)
        self.assertIn("não diz o que se vê", out)

    # ---- pontos ----

    def test_pontos_fora_da_escada_reprova(self):
        self.reprova(issue(lambda i: i.update(pontos=4)), "issues[0].pontos: 4 fora da escada")

    def test_pontos_acima_do_teto_pede_fatiar(self):
        out = self.reprova(issue(lambda i: i.update(pontos=8)), "passa do teto de 5. Fatie por fluxo")
        self.assertNotIn("fora da escada", out)

    def test_pontos_ausente_e_zero_reprovam(self):
        self.reprova(issue(lambda i: i.update(pontos=None)), "sem estimativa")
        self.reprova(issue(lambda i: i.update(pontos=0)), "issues[0].pontos")

    def test_escada_e_teto_vem_da_camada(self):
        def ajuste(c):
            c["gestor"]["escada_pontos"] = [1, 2, 3, 4, 5, 6]
            c["gestor"]["teto_pontos"] = 3
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = validar(issue(lambda i: i.update(pontos=4)), pasta)
        self.assertEqual(rc, 1)
        self.assertIn("passa do teto de 3", out)
        self.assertNotIn("fora da escada", out)

    def test_sem_bloco_gestor_valem_os_padroes_neutros(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c.pop("gestor"))
        rc, out, _ = validar(plano(), pasta)
        self.assertEqual(rc, 0, out)
        self.reprova(issue(lambda i: i.update(pontos=8)), "passa do teto de 5", pasta)

    # ---- responsável ----

    def test_responsavel_sem_ordem_reprova(self):
        def ajuste(i):
            i["responsavel_autorizado"] = False
        self.reprova(issue(ajuste), "issues[0].responsavel: \"Pessoa Exemplo\" sem responsavel_autorizado")

    def test_responsavel_autorizado_sem_a_ordem_reprova(self):
        self.reprova(issue(lambda i: i.pop("autorizado_por")), "issues[0].autorizado_por: obrigatório")

    def test_responsavel_sem_o_campo_de_autorizacao_reprova(self):
        def ajuste(i):
            i.pop("responsavel_autorizado")
        self.reprova(issue(ajuste), "sem responsavel_autorizado")

    def test_sugerido_nao_precisa_de_ordem(self):
        rc, out, _ = validar(issue(lambda i: i.update(responsavel_sugerido="Pessoa Exemplo"), indice=1))
        self.assertEqual(rc, 0, out)

    # ---- data, milestone ----

    def test_data_sem_marco_reprova(self):
        self.reprova(issue(lambda i: i.pop("data_limite_fonte")), "issues[0].data_limite_fonte: obrigatório")

    def test_data_inexistente_reprova(self):
        self.reprova(issue(lambda i: i.update(data_limite="2026-02-31")), "não é uma data real")

    def test_milestone_inexistente_e_milestone_com_espaco_a_menos(self):
        self.reprova(issue(lambda i: i.update(milestone="Marco que não existe")), "não existe em milestones[]")

        def ajuste(d):
            d["milestones"][0]["nome"] = "Marco 1: lojista vende "
        out = self.reprova(plano(ajuste), "difere")
        self.assertIn("espaço das pontas", out)

    def test_milestone_com_espaco_no_fim_passa_quando_o_nome_e_exato(self):
        def ajuste(d):
            d["milestones"][0]["nome"] = "Marco 1: lojista vende "
            for i in d["issues"]:
                if i["milestone"] == "Marco 1: lojista vende":
                    i["milestone"] = "Marco 1: lojista vende "
        rc, out, _ = validar(plano(ajuste))
        self.assertEqual(rc, 0, out)

    def test_milestone_vencida_e_sem_data_viram_aviso_de_pergunta(self):
        def ajuste(d):
            d["milestones"][0]["data"] = "2026-10-01"
        rc, out, _ = validar(plano(ajuste))
        self.assertEqual(rc, 0, out)
        self.assertIn("venceu em 2026-10-01", out)
        self.assertIn("sem data", out)

    # ---- projeto e milestones novos (etapa opcional) ----

    def test_projeto_e_milestones_novos_passam_sem_id(self):
        rc, out, _ = validar(plano(projeto_novo))
        self.assertEqual(rc, 0, out)
        self.assertNotIn("sem id em milestones", out)

    def test_projeto_novo_nao_tem_id(self):
        def ajuste(d):
            projeto_novo(d)
            d["ref"]["projeto"]["id"] = "EXEMPLO-P1"
        self.reprova(plano(ajuste), "ref.projeto.id: projeto novo não tem id")

    def test_milestone_nova_nao_tem_id(self):
        def ajuste(d):
            projeto_novo(d)
            d["milestones"][0]["id"] = "ms-exemplo-1"
        self.reprova(plano(ajuste), "milestones[0].id: milestone nova não tem id")

    def test_milestone_nova_com_data_pede_o_marco(self):
        def ajuste(d):
            projeto_novo(d)
            d["milestones"][0].pop("data_fonte")
        self.reprova(plano(ajuste), "milestones[0].data_fonte: obrigatório com data")

    def test_milestone_nova_sem_data_vira_aviso_de_pergunta(self):
        rc, out, _ = validar(plano(projeto_novo))
        self.assertIn("Marco 3: lojista decide", out)
        self.assertIn("sem data", out)

    def test_milestone_nova_precisa_de_projeto_existente_ou_novo(self):
        def ajuste(d):
            projeto_novo(d)
            d["ref"]["projeto"].pop("novo")
        self.reprova(plano(ajuste), "milestones[0]: milestone nova precisa de ref.projeto com id ou novo")

        def sem_projeto(d):
            projeto_novo(d)
            d["ref"].pop("projeto")
        self.reprova(plano(sem_projeto), "milestones[0]: milestone nova precisa de ref.projeto com id ou novo")

    def test_issue_com_milestone_nova_continua_conferida_pelo_nome(self):
        def ajuste(d):
            projeto_novo(d)
            d["issues"][0]["milestone"] = "Marco que não existe"
        self.reprova(plano(ajuste), "não existe em milestones[]")

    # ---- texto ----

    def test_marca_e_travessao_da_camada(self):
        self.reprova(issue(lambda i: i.update(resultado="O cliente paga no FX Loja")), "marca escrita")
        self.reprova(issue(lambda i: i.update(fora="Pix \u2014 boleto")), "traço longo")
        self.reprova(issue(lambda i: i.update(fora="Pix \u2013 boleto")), "traço longo")

    def test_sem_camada_sem_regra_de_marca(self):
        rc, out, _ = validar(issue(lambda i: i.update(resultado="O cliente paga no FX Loja \u2014 pronto")), None)
        self.assertEqual(rc, 0, out)

    def test_pr_com_hash_reprova_porque_autolinka(self):
        out = self.reprova(issue(lambda i: i.update(contexto="Veio da PR #84 do motor.")), 'Escreva "PR N"')
        self.assertIn("issues[0].contexto", out)
        rc, out, _ = validar(issue(lambda i: i.update(contexto="Veio da PR 84 do motor.")))
        self.assertEqual(rc, 0, out)

    def test_descricao_longa_avisa(self):
        rc, out, _ = validar(issue(lambda i: i.update(resultado="palavra " * 160)))
        self.assertEqual(rc, 0, out)
        self.assertIn("passa de 150", out)

    # ---- ligações ----

    def test_ids_repetidos_e_ligacao_inexistente(self):
        def repetido(d):
            d["issues"][1]["id_local"] = "I1"
        self.reprova(plano(repetido), 'id_local: "I1" repetido')
        self.reprova(issue(lambda i: i.update(bloqueia=["I99"])), '"I99" não é id_local da proposta')
        self.reprova(issue(lambda i: i.update(relacionada=["I1"])), "ligada a ela mesma")

    def test_ligacao_com_issue_que_ja_existe_no_gestor_passa(self):
        rc, out, _ = validar(issue(lambda i: i.update(relacionada=["EXEMPLO-12", "I2"])))
        self.assertEqual(rc, 0, out)

    def test_bloqueio_em_ciclo_reprova(self):
        def ajuste(d):
            d["issues"][1]["bloqueia"] = ["I1"]
        self.reprova(plano(ajuste), "bloqueio em ciclo (I1 > I2 > I1)")

    # ---- conferência ----

    def test_conferencia_traz_o_repo_e_a_fonte_fica_so_caminho_linha(self):
        d = plano()
        self.assertTrue(all(c.get("repo") for c in d["conferencia"][:3]))
        self.assertTrue(re.match(r"^\S+:\d+$", d["conferencia"][0]["fonte"]))
        rc, out, _ = validar(d)
        self.assertEqual(rc, 0, out)

    def test_conferencia_existe_e_parcial_sem_repo_reprovam(self):
        for indice in (0, 2):
            with self.subTest(indice):
                def ajuste(d):
                    d["conferencia"][indice].pop("repo")
                self.reprova(plano(ajuste), f"conferencia[{indice}].repo: ")

    def test_conferencia_nao_existe_sem_repo_reprova(self):
        # a linha "não existe" precisa dizer onde se procurou
        def sem(d):
            d["conferencia"][1].pop("repo")
        self.reprova(plano(sem), "conferencia[1].repo: ")

    def test_conferencia_nao_verificavel_aceita_repo_sem_exigir(self):
        def sem(d):
            d["conferencia"][3].pop("repo", None)
        rc, out, _ = validar(plano(sem))
        self.assertEqual(rc, 0, out)

    def test_conferencia_repo_so_com_espaco_nao_conta(self):
        def vazio(d):
            d["conferencia"][1]["repo"] = "  "
        self.reprova(plano(vazio), "conferencia[1].repo")

    def test_conferencia_fonte_com_prefixo_do_repo_reprova(self):
        def prefixada(d):
            d["conferencia"][0]["fonte"] = "loja-web/src/checkout/cartao.js:42"
        out = self.reprova(plano(prefixada), "conferencia[0].fonte: ")
        self.assertIn("sem o prefixo", out)

    def test_conferencia_fonte_de_repo_com_varios_repos_tambem_reprova_prefixo(self):
        def varios(d):
            d["conferencia"][0]["repo"] = "loja-web, pagamentos-web"
            d["conferencia"][0]["fonte"] = "pagamentos-web/src/x.js:1"
        self.reprova(plano(varios), "conferencia[0].fonte: ")

    def test_conferencia_fonte_com_pasta_de_outro_nome_passa(self):
        # controle positivo: só o prefixo do próprio repo reprova
        def pasta(d):
            d["conferencia"][0]["fonte"] = "src/loja-web/cartao.js:42"
        rc, out, _ = validar(plano(pasta))
        self.assertEqual(rc, 0, out)

    def test_conferencia_exige_fonte_sha_e_motivo(self):
        def sem_fonte(d):
            d["conferencia"][0].pop("fonte")
        self.reprova(plano(sem_fonte), "conferencia[0].fonte")

        def sem_sha(d):
            d["conferencia"][2].pop("sha")
        self.reprova(plano(sem_sha), "conferencia[2].sha")

        def sem_motivo(d):
            d["conferencia"][3].pop("motivo")
        self.reprova(plano(sem_motivo), "conferencia[3].motivo")

    def test_nao_verificavel_nao_pede_sha(self):
        d = plano()
        self.assertNotIn("sha", d["conferencia"][3])
        rc, out, _ = validar(d)
        self.assertEqual(rc, 0, out)

    def test_estado_fora_da_lista_reprova(self):
        def ajuste(d):
            d["conferencia"][0]["estado"] = "talvez"
        self.reprova(plano(ajuste), "conferencia[0].estado")

    def test_plano_sem_issue_avisa(self):
        rc, out, _ = validar(plano(lambda d: d.update(issues=[])))
        self.assertEqual(rc, 0, out)
        self.assertIn("issues vazio", out)


@precisa_node
class TesteDescricaoIssue(unittest.TestCase):
    ROTULOS = ["Modo", "Fluxo", "Repos", "Pode mexer em", "Resultado", "O que entrega",
               "Teste principal", "Portão", "Fora", "Se nunca for feita", "Contexto"]

    def test_formato_do_contrato_com_os_onze_campos_na_ordem(self):
        rc, out, err = descrever(plano(), "--id", "I2")
        self.assertEqual(rc, 0, err)
        rotulos = re.findall(r"(?m)^\*\*(.+?):\*\*", out)
        self.assertEqual(rotulos, self.ROTULOS)
        linhas = out.rstrip("\n").split("\n")
        self.assertEqual(linhas[0], "**Modo:** direto")
        self.assertEqual(linhas[-2], "")
        self.assertEqual(linhas[-1], "Responsável sugerido: Pessoa Dois Exemplo (quem prioriza atribui)")

    def test_os_seis_campos_de_antes_continuam_e_na_mesma_ordem(self):
        rc, out, _ = descrever(plano(), "--id", "I2")
        antigos = ["Fluxo", "Repos", "Resultado", "Teste principal", "Fora", "Se nunca for feita"]
        rotulos = [r for r in re.findall(r"(?m)^\*\*(.+?):\*\*", out) if r in antigos]
        self.assertEqual(rotulos, antigos)

    def test_entrega_vira_checklist_e_pode_mexer_em_vira_lista(self):
        rc, out, _ = descrever(plano(), "--id", "I1")
        self.assertIn("**O que entrega:**\n- [ ] Cartão como forma de pagamento no checkout\n- [ ] Confirmação com o número do pedido\n- [ ] Pedido de teste pago com cartão\n**Teste principal:**", out)
        self.assertIn("**Pode mexer em:** loja-web: src/checkout/\n", out)
        self.assertIn("**Portão:** CI verde e o teste principal rodado por quem prioriza\n", out)

    def test_contexto_e_campo_com_rotulo_antes_do_responsavel_sugerido(self):
        rc, out, _ = descrever(plano(), "--id", "I2")
        self.assertIn("**Contexto:** Nenhum código de Pix existe hoje (conferido em 09/11/2026).\n\nResponsável sugerido", out)

    def test_issue_atribuida_nao_leva_responsavel_sugerido(self):
        d = issue(lambda i: i.update(responsavel_sugerido="Pessoa Dois Exemplo"))
        rc, out, _ = descrever(d, "--id", "I1")
        self.assertEqual(rc, 0)
        self.assertNotIn("Responsável sugerido", out)

    def test_repos_vazio_vira_nenhum_e_varios_viram_lista(self):
        rc, out, _ = descrever(plano(), "--id", "I6")
        self.assertIn("**Repos:** nenhum", out)
        rc, out, _ = descrever(issue(lambda i: i.update(repos=["loja-web", "pagamentos-web"])), "--id", "I1")
        self.assertIn("**Repos:** loja-web, pagamentos-web", out)

    def test_sem_sugestao_o_contexto_fecha_a_descricao(self):
        rc, out, _ = descrever(plano(), "--id", "I4")
        self.assertTrue(out.rstrip("\n").endswith("**Contexto:** Nenhum extrato existe hoje (conferido em 09/11/2026)."))

    def test_modo_abre_a_descricao(self):
        rc, out, _ = descrever(issue(lambda i: i.update(modo="pesquisa")), "--id", "I1")
        self.assertTrue(out.startswith("**Modo:** pesquisa\n**Fluxo:**"))

    def test_rotulos_vem_da_camada(self):
        def ajuste(c):
            c["gestor"]["contrato_campos"] = ["Jeito", "Quem", "Onde", "Limite", "Entrega", "Lista", "Teste", "Porta", "Não entra", "Se não sair", "Cenário"]
            c["gestor"]["quem_atribui"] = "o líder"
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = descrever(plano(), "--id", "I2", camada=pasta)
        self.assertEqual(rc, 0)
        self.assertIn("**Jeito:** direto", out)
        self.assertIn("**Quem:** ", out)
        self.assertIn("**Lista:**\n- [ ] ", out)
        self.assertIn("**Porta:** ", out)
        self.assertIn("**Se não sair:** ", out)
        self.assertIn("**Cenário:** ", out)
        self.assertIn("(o líder atribui)", out)

    def test_estrutura_de_projeto_existente_nao_cria_nada(self):
        rc, out, err = descrever(plano(), "--estrutura")
        self.assertEqual(rc, 0, err)
        self.assertEqual(json.loads(out), {"projeto": None, "milestones": [], "time": "Time Exemplo"})

    def test_estrutura_traz_so_o_que_a_criacao_do_projeto_e_das_milestones_recebe(self):
        rc, out, err = descrever(plano(projeto_novo), "--estrutura")
        self.assertEqual(rc, 0, err)
        e = json.loads(out)
        self.assertEqual(e["projeto"], {"nome": "Projeto Exemplo", "descricao": "Projeto fictício para testar a etapa opcional."})
        self.assertEqual([m["nome"] for m in e["milestones"]],
                         ["Marco 1: lojista vende", "Marco 2: lojista acompanha", "Marco 3: lojista decide"])
        self.assertEqual([m["data"] for m in e["milestones"]], ["2026-12-04", "2026-12-18", None])
        self.assertEqual(e["time"], "Time Exemplo")

    def test_estrutura_so_lista_a_milestone_marcada_como_nova(self):
        def ajuste(d):
            d["ref"]["projeto"]["id"] = "EXEMPLO-P1"
            d["milestones"][0]["id"] = "ms-exemplo-1"
            d["milestones"][1]["id"] = "ms-exemplo-2"
            d["milestones"][2].pop("id")
            d["milestones"][2]["novo"] = True
        rc, out, err = descrever(plano(ajuste), "--estrutura")
        self.assertEqual(rc, 0, err)
        e = json.loads(out)
        self.assertIsNone(e["projeto"])
        self.assertEqual([m["nome"] for m in e["milestones"]], ["Marco 3: lojista decide"])

    def test_estrutura_nao_gera_de_plano_invalido(self):
        rc, out, err = descrever(issue(lambda i: i.update(pontos=13)), "--estrutura")
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")

    def test_json_das_issues_leva_a_milestone_pelo_nome_mesmo_com_milestone_nova(self):
        rc, out, _ = descrever(plano(projeto_novo), "--json")
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)[0]["milestone"], "Marco 1: lojista vende")

    def test_sem_flag_um_bloco_por_issue(self):
        rc, out, _ = descrever(plano())
        self.assertEqual(rc, 0)
        self.assertEqual(len(re.findall(r"^## I\d: ", out, re.M)), 6)
        self.assertIn("## I1: Checkout fX Loja: cliente paga o pedido por cartão", out)

    def test_json_traz_o_que_a_criacao_precisa(self):
        rc, out, _ = descrever(plano(), "--json")
        self.assertEqual(rc, 0)
        lista = json.loads(out)
        self.assertEqual([i["id_local"] for i in lista], ["I1", "I2", "I3", "I4", "I5", "I6"])
        i1, i2 = lista[0], lista[1]
        self.assertEqual(i1["responsavel"], "Pessoa Exemplo")
        self.assertEqual(i1["data_limite"], "2026-12-04")
        self.assertEqual(i1["pontos"], 5)
        self.assertEqual(i1["estado"], "Backlog")
        self.assertEqual(i1["milestone"], "Marco 1: lojista vende")
        self.assertIsNone(i2["responsavel"], "sugerido nunca vira responsável")
        self.assertIsNone(i2["data_limite"])

    def test_estado_inicial_e_labels_vem_da_camada(self):
        def ajuste(c):
            c["gestor"]["estado_inicial"] = "Todo"
            c["gestor"]["labels"] = ["plano"]
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=ajuste)
        rc, out, _ = descrever(plano(), "--json", camada=pasta)
        lista = json.loads(out)
        self.assertEqual(lista[0]["estado"], "Todo")
        self.assertEqual(lista[0]["labels"], ["plano"])

    def test_responsavel_sem_ordem_nunca_sai_no_json(self):
        d = issue(lambda i: i.update(responsavel_autorizado=False))
        rc, out, err = descrever(d, "--json")
        self.assertEqual(rc, 1, "plano inválido não gera descrição")
        self.assertIn("sem responsavel_autorizado", err)

    def test_plano_invalido_nao_gera(self):
        rc, out, err = descrever(issue(lambda i: i.update(pontos=13)))
        self.assertEqual(rc, 1)
        self.assertEqual(out, "")
        self.assertIn("plano inválido", err)

    def test_id_inexistente_sai_com_1(self):
        rc, out, err = descrever(plano(), "--id", "I99")
        self.assertEqual(rc, 1)
        self.assertIn("não existe em issues[]", err)

    def test_sem_argumento_sai_com_2(self):
        rc, _, err = node("descricao-issue.mjs")
        self.assertEqual(rc, 2)
        self.assertIn("uso:", err)


@precisa_node
class TesteGestorDaCamada(unittest.TestCase):
    def test_teto_fora_da_escada_reprova_a_camada(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["gestor"].update(teto_pontos=4))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.teto_pontos: 4 não está em gestor.escada_pontos", out)

    def test_escada_fora_de_ordem_reprova_a_camada(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["gestor"].update(escada_pontos=[1, 3, 2, 5]))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.escada_pontos: precisa ser crescente", out)

    def test_contrato_com_campos_a_menos_reprova_a_camada(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["gestor"].update(contrato_campos=["Fluxo"]))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.contrato_campos: são onze rótulos", out)

    def test_contrato_antigo_de_seis_campos_reprova_a_camada(self):
        seis = ["Fluxo", "Repos", "Resultado", "Teste principal", "Fora", "Se nunca for feita"]
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["gestor"].update(contrato_campos=seis))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("são onze rótulos", out)

    def test_campo_desconhecido_no_gestor_reprova_a_camada(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c["gestor"].update(inventado=True))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 1)
        self.assertIn("gestor.inventado", out)

    def test_camada_sem_gestor_continua_valida(self):
        pasta = copiar_camada(os.path.join(tmp(), "c"), ajuste=lambda c: c.pop("gestor"))
        rc, out, _ = node("validar-camada.mjs", pasta)
        self.assertEqual(rc, 0, out)


class TesteSkill(unittest.TestCase):
    def test_frontmatter_e_gatilhos(self):
        arq = os.path.join(PLUGIN, "skills", "plano-no-linear", "SKILL.md")
        with open(arq, encoding="utf-8") as f:
            texto = f.read()
        fm = re.match(r"---\nname: (.+)\ndescription: (.+)\n---\n", texto)
        self.assertIsNotNone(fm, "frontmatter com name e description")
        self.assertEqual(fm.group(1), "plano-no-linear")
        for gatilho in ("transformar o plano em issues", "quebrar o projeto no Linear",
                        "criar as issues do projeto", "desdobrar no Linear"):
            self.assertIn(gatilho, fm.group(2))

    def test_skill_descreve_os_onze_campos_e_a_etapa_opcional_de_estrutura(self):
        arq = os.path.join(PLUGIN, "skills", "plano-no-linear", "SKILL.md")
        with open(arq, encoding="utf-8") as f:
            texto = f.read()
        for trecho in ("onze campos", "**Modo**", "**Pode mexer em**", "**O que entrega**", "**Portão**",
                       "descricao-issue.mjs", "--estrutura", "save_project", "save_milestone", "pergunta 6"):
            self.assertIn(trecho, texto)
        arq = os.path.join(PLUGIN, "skills", "plano-no-linear", "referencias", "conferencia.md")
        with open(arq, encoding="utf-8") as f:
            self.assertIn("`repo`", f.read())

    def test_skill_resolve_o_servidor_de_escrita_com_alternativo_e_confirma_o_workspace(self):
        arq = os.path.join(PLUGIN, "skills", "plano-no-linear", "SKILL.md")
        with open(arq, encoding="utf-8") as f:
            texto = f.read()
        for trecho in ("gestor.servidor_alternativo", "fontes.linear.servidor_alternativo",
                       "fontes-do-levantamento.mjs\" gestor", "get_workspace", "antes de qualquer escrita"):
            self.assertIn(trecho, texto)

    def test_etapas_de_a_a_f(self):
        arq = os.path.join(PLUGIN, "skills", "plano-no-linear", "SKILL.md")
        with open(arq, encoding="utf-8") as f:
            texto = f.read()
        for letra in "ABCDEF":
            self.assertRegex(texto, rf"(?m)^## Etapa {letra}: ")


if __name__ == "__main__":
    unittest.main()
