"""Regras da foto do LinkedIn Ads no leadscore do ABM. Nenhum teste toca rede."""

import datetime as dt

import importar_linkedin_ads_abm as ads

AGORA = dt.datetime(2026, 10, 30, 18, 0, tzinfo=dt.timezone.utc)
DATA = dt.date(2026, 10, 30)
TITULO = ads.TITULO % "2026-10-30"


def conta(id_, nome, linkedin="", link="", comite=10):
    return {"id": id_, "name": nome, "x_abm_linkedin_empresa": linkedin,
            "x_abm_link_linkedin": link, "x_abm_comite_total": comite}


def linha(nome, slug=None, nivel="Very Low", impressoes=0, interacoes=0, videos=0):
    return {"nome": nome, "slug": slug, "nivel": nivel, "impressoes": impressoes,
            "interacoes": interacoes, "videos": videos}


def test_reguas():
    assert [ads.pontos_nivel(n) for n in ("Very Low", "Low", "Medium", "High", "Very High", "")] == [0, 5, 10, 20, 25, 0]
    assert [ads.pontos_interacoes(n) for n in (0, 1, 9, 10, 29, 30, 78)] == [0, 5, 5, 10, 10, 15, 15]
    assert [ads.pontos_exposicao(e) for e in (0, 1.9, 2, 3.9, 4, 107)] == [0, 0, 5, 5, 10, 10]


def test_foto_reproduz_a_de_28_10():
    # Marcopolo em 28/10: High (+20) · 78 interações (+15) · 369/30 = 12.3 (+10) → teto 30
    foto = ads.foto_da_conta(conta(1, "Marcopolo S.A.", comite=30),
                             [linha("Marcopolo S.A.", nivel="High", impressoes=369, interacoes=78, videos=135)])
    assert foto["pontos"] == 30
    assert foto["exposicao"] == 12.3
    assert "369 impressões / 30 no comitê = 12.3 (+10)" in foto["detalhe"]


def test_varias_paginas_somam_e_ficam_com_o_maior_nivel():
    c = conta(1, "AGCO Corporation", linkedin="AGCO Corporation; Fendt", comite=74)
    foto = ads.foto_da_conta(c, [linha("AGCO Corporation", nivel="Low", impressoes=500, interacoes=5),
                                 linha("Fendt", nivel="Very Low", impressoes=353, interacoes=8)])
    assert foto["exposicao"] == 11.5
    assert foto["pontos"] == 5 + 10 + 10
    assert "Páginas somadas: AGCO Corporation, Fendt" in foto["detalhe"]


def test_comite_vazio_nao_divide_por_zero():
    assert ads.foto_da_conta(conta(1, "Scania Brasil", comite=0), [linha("Scania Brasil", impressoes=50)])["exposicao"] == 0


def test_casamento_pelo_link_e_pela_lista_curada():
    contas = [
        conta(1, "Iveco", linkedin="IVECO Brasil"),
        conta(2, "Liebherr Brasil", link="https://www.linkedin.com/company/liebherrbrasil/"),
        conta(3, "Comil Ônibus"),
    ]
    linhas = [
        linha("IVECO", nivel="Very High"),       # página global: fora, a lista curada manda
        linha("IVECO Brasil", impressoes=65),
        linha("Liebherr Brasil (outro nome)", slug="liebherrbrasil", impressoes=7),
        linha("Comil Onibus", impressoes=35),    # sem lista: cai no nome da conta, sem acento
    ]
    casadas = ads.casar(contas, linhas)
    assert [l["nome"] for l in casadas[1]] == ["IVECO Brasil"]
    assert [l["impressoes"] for l in casadas[2]] == [7]
    assert [l["impressoes"] for l in casadas[3]] == [35]


def test_nome_compartilhado_vai_para_o_maior_comite():
    contas = [conta(1, "Honda", linkedin="Honda", comite=11), conta(2, "Honda Brasil", linkedin="Honda", comite=105)]
    assert list(ads.casar(contas, [linha("Honda", impressoes=10)])) == [2]


def test_plano_substitui_a_foto_e_zera_conta_ausente():
    contas = [conta(1, "Marcopolo S.A.", linkedin="Marcopolo S.A.", comite=30), conta(2, "Porsche Brasil")]
    ativos = {1: [{"id": 143, "x_name": ads.TITULO % "2026-10-28"}], 2: [{"id": 99, "x_name": "velho"}]}
    planos, puladas, sem_conta = ads.planejar(
        contas, [linha("Marcopolo S.A.", nivel="High", impressoes=369, interacoes=78), linha("FGV", impressoes=500)],
        ativos, DATA, AGORA)
    assert not puladas
    assert [l["nome"] for l in sem_conta] == ["FGV"]
    marcopolo, porsche = planos
    assert ads.valores_da_conta(marcopolo) == {
        "x_abm_exposicao": 12.3,
        "x_abm_sinal_ids": [[1, 143, {"x_ativo": False}], [0, 0, marcopolo["novo"]]],
    }
    assert marcopolo["novo"]["x_pontos_custom"] == 30
    assert marcopolo["novo"]["x_name"] == TITULO
    assert marcopolo["novo"]["x_data"] == "2026-10-30 18:00:00"
    # Sem linha no relatório: a foto antiga sai do score e não entra sinal novo.
    assert ads.valores_da_conta(porsche) == {"x_abm_exposicao": 0, "x_abm_sinal_ids": [[1, 99, {"x_ativo": False}]]}


def test_rodar_de_novo_nao_duplica():
    contas = [conta(1, "Marcopolo S.A.", linkedin="Marcopolo S.A.")]
    planos, puladas, _ = ads.planejar(contas, [linha("Marcopolo S.A.", impressoes=100)],
                                     {1: [{"id": 7, "x_name": TITULO}]}, DATA, AGORA)
    assert planos == []
    assert puladas == [("Marcopolo S.A.", "foto desta data já gravada")]


def test_le_o_csv_do_campaign_manager(tmp_path):
    arquivo = tmp_path / "companies-export_508640297_2026-10-30_14-16-34.csv"
    arquivo.write_text(
        "﻿Company name,Company page URL,Engagement level,Organic impressions,Organic engagements,"
        "Paid impressions,Paid clicks,Paid engagements,Paid video views,Paid conversions,Paid leads,"
        "Paid qualified leads,Cost per qualified lead\n"
        '"Stellantis South America",https://www.linkedin.com/company/stellantislatam,Very Low,5,3,1318,7,14,436,,,,\n',
        encoding="utf-8")
    assert ads.ler_relatorio(arquivo) == [{
        "nome": "Stellantis South America", "slug": "stellantislatam", "nivel": "Very Low",
        "impressoes": 1318, "interacoes": 17, "videos": 436,
    }]
    assert ads.data_do_arquivo(str(arquivo)) == DATA
