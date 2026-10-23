"""Relatório de empresas do LinkedIn Ads: páginas somadas por conta e pontuação."""

from atualizar_abm_linkedin_setima import calcular, nomes_linkedin, somar_linhas


def linha(nome, nivel="Very Low", **valores):
    base = {"Company name": nome, "Engagement level": nivel}
    base.update({k.replace("_", " "): str(v) for k, v in valores.items()})
    return base


def test_nomes_linkedin_separa_por_ponto_e_virgula_e_inclui_o_nome_da_conta():
    conta = {"name": "Scania Group",
             "x_abm_linkedin_empresa": "Scania Group; Scania Latin America ;Scania Brasil"}
    assert nomes_linkedin(conta) == ["Scania Group", "Scania Latin America", "Scania Brasil",
                                     "Scania Group"]


def test_nomes_linkedin_sem_campo_usa_so_o_nome():
    assert nomes_linkedin({"name": "Jacto", "x_abm_linkedin_empresa": False}) == ["Jacto"]


def test_somar_linhas_soma_numeros_e_fica_com_o_maior_nivel():
    soma = somar_linhas([
        linha("Scania Group", "Low", Paid_impressions=78, Paid_engagements=4, Paid_video_views=32),
        linha("Scania Latin America", "High", Paid_impressions=17, Paid_engagements=3, Paid_video_views=9),
        linha("Scania Brasil", "Very Low", Paid_impressions=3),
    ])
    assert soma["Engagement level"] == "High"
    assert soma["Paid impressions"] == "98"
    assert soma["Paid engagements"] == "7"
    assert soma["Paid video views"] == "41"
    assert soma["Company name"] == "Scania Group + Scania Latin America + Scania Brasil"


def test_somar_uma_linha_devolve_a_propria():
    unica = linha("Jacto", "Low", Paid_impressions=200)
    assert somar_linhas([unica]) is unica


def test_scania_com_paginas_somadas_chega_a_30():
    soma = somar_linhas([
        linha("Scania Group", "Low", Paid_impressions=78, Paid_engagements=4),
        linha("Scania Latin America", "High", Paid_impressions=17, Paid_engagements=3),
    ])
    r = calcular(soma, comite=24)
    assert r["exposicao"] == 4.0
    assert r["pontos"] == 30  # High 20 + interações 5 + exposição 10


def test_valores_vazios_do_export_contam_como_zero():
    soma = somar_linhas([linha("A", Paid_impressions=""), linha("B", Paid_impressions=5)])
    assert soma["Paid impressions"] == "5"
