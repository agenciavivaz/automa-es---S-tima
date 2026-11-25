"""Regras do sinal "abriu o formulário do LinkedIn". Nenhum teste toca rede."""

import datetime as dt

import sincronizar_linkedin_formularios_abm as sync

DESDE = dt.date(2026, 11, 1)


def conta(id_, nome, li="", dom="", extras=""):
    return {"id": id_, "name": nome, "x_abm_linkedin_empresa": li or nome,
            "x_abm_dominio": dom, "x_abm_dominios_extra": extras}


def empresa(nome, site="", aberturas=3, fim="2026-11-16", org="123"):
    return {"nome": nome, "site": site, "org_urn": "urn:li:organization:%s" % org,
            "periodo_inicio": "2026-11-10", "periodo_fim": fim, "aberturas": aberturas,
            "envios": 0, "impressoes": 500, "cliques": 4, "engajamentos": 6}


CONTAS = [
    conta(1, "Stellantis South America", li="Stellantis South America;Stellantis", dom="stellantis.com"),
    conta(2, "Senac", dom="senac.br"),
    conta(3, "FGV Brazil", dom=""),
    conta(4, "Jeep", dom="stellantis.com"),
    conta(5, "Senai São Paulo", dom="sp.senai.br"),
]


def test_nome_sem_acento_e_caixa():
    c, como = sync.casar(empresa("SENAI SAO PAULO"), CONTAS)
    assert c["id"] == 5 and como == "nome"


def test_nome_alternativo_do_linkedin():
    c, _ = sync.casar(empresa("Stellantis"), CONTAS)
    assert c["id"] == 1


def test_subdominio_casa_com_dominio_da_conta():
    c, como = sync.casar(empresa("Senac São Paulo", "https://www.sp.senac.br/"), CONTAS)
    assert c["id"] == 2 and como == "domínio"


def test_dominio_compartilhado_e_ambiguo():
    c, motivo = sync.casar(empresa("Stellantis Brasil", "stellantis.com"), CONTAS)
    assert c is None and "ambígua" in motivo


def test_sem_conta():
    c, motivo = sync.casar(empresa("Fundação Getulio Vargas", "http://www.fgv.br"), CONTAS)
    assert c is None and "sem conta" in motivo


def test_sinal_vem_com_pontos_variaveis_e_chave_de_dedup():
    sinais, fora = sync.montar_sinais([empresa("Stellantis South America", org="69731863")], CONTAS, set(), DESDE)
    assert not fora
    v = sinais[0]["vals"]
    assert v["x_lead_id"] == 1 and v["x_tipo"] == "outro" and v["x_origem"] == "linkedin_ads"
    assert v["x_pontos_custom"] == sync.PONTOS and v["x_ativo"] is True
    assert v["x_data"] == "2026-11-16 12:00:00"
    assert "LinkedIn org 69731863 · semana até 2026-11-16" in v["x_detalhe"]


def test_dedup_e_janela():
    k = "LinkedIn org 9 · semana até 2026-11-16"
    sinais, fora = sync.montar_sinais(
        [empresa("Senac", org="9"), empresa("Senac", org="9", fim="2026-10-20"), empresa("Senac", aberturas=0)],
        CONTAS, {(2, k)}, DESDE)
    assert not sinais
    assert [m for _, _, m in fora] == ["já registrado em Senac", "semana até 2026-10-20: fora da janela de 30 dias"]


def test_conta_em_expansao_nao_pontua():
    vw = dict(conta(9, "Volkswagen do Brasil", dom="vw.com.br"), stage_id=[96, "Cliente – expansão"])
    sinais, fora = sync.montar_sinais([empresa("Volkswagen do Brasil")], CONTAS + [vw], set(), DESDE)
    assert not sinais and fora[0][2] == "conta Volkswagen do Brasil em Cliente – expansão: não pontua"


def test_mesma_empresa_duas_vezes_no_lote_grava_uma():
    sinais, fora = sync.montar_sinais([empresa("Senac", org="9"), empresa("Senac", org="9")], CONTAS, set(), DESDE)
    assert len(sinais) == 1 and "já registrado" in fora[0][2]
