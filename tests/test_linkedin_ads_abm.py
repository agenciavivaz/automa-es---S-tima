"""Regras do relatório LinkedIn Ads → sinais do ABM. Nenhum teste toca rede."""

import datetime as dt

import pytest

import atualizar_linkedin_ads_abm as li


def pagina(nome, nivel="very low", imp_org=0, eng_org=0, imp_pago=0, eng_pago=0, videos=0):
    return {"nome": nome, "url": "", "nivel": nivel, "imp_org": imp_org, "eng_org": eng_org,
            "imp_pago": imp_pago, "eng_pago": eng_pago, "cliques": 0, "videos": videos}


def conta(id_, nome, comite, linkedin=""):
    return {"id": id_, "name": nome, "x_abm_comite_total": comite, "x_abm_linkedin_empresa": linkedin}


@pytest.mark.parametrize("n,esperado", [(0, 0), (3, 5), (9, 5), (10, 10), (27, 10), (43, 15), (83, 15)])
def test_pontos_interacoes_batem_com_o_historico(n, esperado):
    assert li.pontos_interacoes(n) == esperado


@pytest.mark.parametrize("razao,esperado", [(0.3, 0), (1.7, 0), (2.0, 5), (3.9, 5), (4.0, 10), (147.9, 10)])
def test_pontos_exposicao_batem_com_o_historico(razao, esperado):
    assert li.pontos_exposicao(razao) == esperado


@pytest.mark.parametrize("nivel,esperado", [("Very Low", 0), ("low", 5), ("Medium", 10), ("high", 20), ("Very High", 25)])
def test_pontos_nivel(nivel, esperado):
    assert li.pontos_nivel(nivel) == esperado


def test_exemplo_real_cnh_de_09_11():
    # "Interações: 10 (+10) · 1775 impressões / 12 no comitê = 147.9 (+10) · Total 20"
    agg = {"imp": 1775, "inter": 10, "videos": 584, "nivel": "very low"}
    av = li.avaliar(agg, 12)
    assert (av["nivel"], av["interacoes"], av["exposicao"], av["razao"], av["total"]) == (0, 10, 10, 147.9, 20)


def test_teto_de_30_pontos():
    av = li.avaliar({"imp": 1000, "inter": 90, "videos": 0, "nivel": "very high"}, 10)
    assert av["nivel"] + av["interacoes"] + av["exposicao"] == 50 and av["total"] == 30


def test_soma_paginas_da_conta_e_pega_o_maior_nivel():
    por_nome = {
        li.norm_nome("Scania Group"): [pagina("Scania Group", "low", 7, 8, 387, 7, 126)],
        li.norm_nome("Scania Brasil"): [pagina("Scania Brasil", "very low", 0, 0, 31, 0, 8)],
    }
    agg, usadas = li.agregar(conta(1, "Scania Group", 24, "Scania Group; Scania Latin America; Scania Brasil"), por_nome)
    assert usadas == ["Scania Group", "Scania Brasil"]
    assert agg == {"imp": 418, "inter": 15, "videos": 134, "nivel": "low"}


def test_conta_usa_o_proprio_nome_quando_nao_tem_nome_no_linkedin():
    por_nome = {li.norm_nome("Jacto"): [pagina("Jacto", imp_pago=100)]}
    agg, _ = li.agregar(conta(1, "Jacto", 9), por_nome)
    assert agg["imp"] == 100


def test_conta_fora_do_relatorio_zera_exposicao_e_nao_gera_sinal():
    itens, sem_conta = li.planejar([conta(1, "Sany Brasil", 2, "Sany Brasil")], [pagina("Outra")], dt.date(2026, 11, 13))
    assert itens[0]["sinal"] is None and itens[0]["exposicao"] == 0.0
    assert sem_conta == ["Outra"]


def test_planejar_grava_sinal_no_padrao_dos_relatorios_anteriores():
    linhas = [pagina("Toyota do Brasil", imp_pago=990, eng_pago=10, videos=341)]
    itens, _ = li.planejar([conta(7, "Toyota do Brasil", 52, "Toyota do Brasil")], linhas, dt.date(2026, 11, 13))
    s = itens[0]["sinal"]
    assert s["x_name"] == "LinkedIn Ads 30 dias · relatório de 2026-11-13"
    assert (s["x_tipo"], s["x_origem"], s["x_ativo"], s["x_lead_id"]) == ("li_ads_relatorio", "linkedin_ads", True, 7)
    assert s["x_pontos_custom"] == 20
    assert s["x_detalhe"] == ("Nível LinkedIn: Very Low (+0) · Interações: 10 (+10) · Exposição: 990 impressões / "
                              "52 no comitê = 19.0 (+10) · Views de vídeo: 341 · Total 20 (teto 30)")


def test_conta_sem_pontos_nao_recebe_sinal_mas_atualiza_exposicao():
    itens, _ = li.planejar([conta(1, "Jetour Brasil", 7, "Jetour")], [pagina("Jetour", imp_pago=11)], dt.date(2026, 11, 13))
    assert itens[0]["sinal"] is None and itens[0]["exposicao"] == 1.6
