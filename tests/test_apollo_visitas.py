"""Regras da sincronização Apollo → sinais do ABM. Nenhum teste toca rede."""

import datetime as dt

import pytest

import sincronizar_apollo_visitas_abm as sync

HOJE = dt.date(2026, 10, 28)
JANELA = HOJE - dt.timedelta(days=7)


def conta(id_, nome, dominio, extras="", comite=0):
    return {"id": id_, "name": nome, "x_abm_dominio": dominio,
            "x_abm_dominios_extra": extras, "x_abm_comite_total": comite}


def empresa(nome, dominio, ultima="20261027", caminhos=("setima.cc/PT",), intent="low", site="setima.cc"):
    return {
        "name": nome, "primary_domain": dominio,
        "intent_signal_account": {"domain_aggregates": [{
            "domain": site, "total_visits": 3, "unique_visitors": 2, "last_visit": ultima,
            "intent": intent, "intent_score": 7.2,
            "top_5_paths": [{"_id": c, "total_visits": 1} for c in caminhos],
        }]},
    }


CONTAS = [
    conta(1, "Stellantis South America", "stellantis.com", "fcagroup.com", comite=132),
    conta(2, "Jeep", "stellantis.com", "jeep.com", comite=5),
    conta(3, "Ram do Brasil", "ram.com.br"),
    conta(4, "Ford Brasil", "https://www.ford.com/", "ford.com.br; gmail.com"),
]


def test_dominios_normalizados_sem_genericos():
    assert sync.dominios_da_conta(CONTAS[3]) == ["ford.com", "ford.com.br"]


def test_dominio_compartilhado_vai_para_principal_com_maior_comite():
    mapa = sync.mapa_dominios(CONTAS)
    assert [c["name"] for c in mapa["stellantis.com"]] == ["Stellantis South America", "Jeep"]


def test_visita_simples_gera_visita_dominio():
    mapa = sync.mapa_dominios(CONTAS)
    sinais, notas, _ = sync.montar_sinais([empresa("Ram", "ram.com.br")], mapa, "setima.cc", {}, JANELA)
    assert len(sinais) == 1 and not notas
    v = sinais[0]["vals"]
    assert v["x_lead_id"] == 3 and v["x_tipo"] == sync.TIPO_VISITA and v["x_origem"] == "site"
    assert v["x_data"] == "2026-10-27 12:00:00"
    assert "Última visita: 2026-10-27" in v["x_detalhe"]


@pytest.mark.parametrize("caminhos,intent", [
    (("setima.cc/PT", "setima.cc/PT/obrigado"), "low"),
    (("setima.cc/PT/cases/vw-tera",), "low"),
    (("setima.cc/PT",), "high"),
])
def test_alta_intencao_por_pagina_ou_intencao(caminhos, intent):
    mapa = sync.mapa_dominios(CONTAS)
    sinais, _, _ = sync.montar_sinais([empresa("Ford", "ford.com", caminhos=caminhos, intent=intent)],
                                      mapa, "setima.cc", {}, JANELA)
    assert sinais[0]["vals"]["x_tipo"] == sync.TIPO_ALTA


def test_compartilhado_um_sinal_e_nota_nas_demais():
    mapa = sync.mapa_dominios(CONTAS)
    sinais, notas, _ = sync.montar_sinais([empresa("Stellantis", "stellantis.com")], mapa, "setima.cc", {}, JANELA)
    assert [s["lead"]["name"] for s in sinais] == ["Stellantis South America"]
    assert [n[0]["name"] for n in notas] == ["Jeep"]


def test_dedup_por_conta_e_data():
    mapa = sync.mapa_dominios(CONTAS)
    sinais, _, ign = sync.montar_sinais([empresa("Ram", "ram.com.br")], mapa, "setima.cc",
                                        {3: [(dt.date(2026, 10, 27), sync.TIPO_VISITA)]}, JANELA)
    assert not sinais and ign[0][2] == "já registrado"


def test_teto_bloqueia_segunda_visita_simples_na_semana():
    mapa = sync.mapa_dominios(CONTAS)
    sinais, _, ign = sync.montar_sinais([empresa("Ram", "ram.com.br", ultima="20261027")], mapa, "setima.cc",
                                        {3: [(dt.date(2026, 10, 23), sync.TIPO_VISITA)]}, JANELA)
    assert not sinais and ign[0][2].startswith("teto")


def test_teto_deixa_passar_alta_intencao_depois_de_visita_simples():
    mapa = sync.mapa_dominios(CONTAS)
    emp = empresa("Ram", "ram.com.br", caminhos=("setima.cc/PT/obrigado",))
    sinais, _, _ = sync.montar_sinais([emp], mapa, "setima.cc",
                                      {3: [(dt.date(2026, 10, 23), sync.TIPO_VISITA)]}, JANELA)
    assert sinais[0]["vals"]["x_tipo"] == sync.TIPO_ALTA
    sinais, _, ign = sync.montar_sinais([emp], mapa, "setima.cc",
                                        {3: [(dt.date(2026, 10, 23), sync.TIPO_ALTA)]}, JANELA)
    assert not sinais and ign[0][2].startswith("teto")


def test_teto_libera_depois_de_7_dias():
    mapa = sync.mapa_dominios(CONTAS)
    sinais, _, _ = sync.montar_sinais([empresa("Ram", "ram.com.br", ultima="20261027")], mapa, "setima.cc",
                                      {3: [(dt.date(2026, 10, 20), sync.TIPO_VISITA)]}, JANELA)
    assert len(sinais) == 1


def test_ignora_fora_do_abm_outro_site_e_fora_da_janela():
    mapa = sync.mapa_dominios(CONTAS)
    empresas = [
        empresa("Shed", "tryshed.com"),
        empresa("Ram", "ram.com.br", site="brandspot.com.br"),
        empresa("Ford", "ford.com", ultima="20261001"),
    ]
    sinais, _, ign = sync.montar_sinais(empresas, mapa, "setima.cc", {}, JANELA)
    assert not sinais
    assert [m for _, _, m in ign] == ["domínio fora do ABM", "sem visitas ao site rastreado",
                                      "última visita fora da janela"]


class _Resp:
    def __init__(self, payload, status=200):
        self._p, self.status_code = payload, status

    def json(self):
        return self._p

    def raise_for_status(self):
        pass


class _Sessao:
    def __init__(self, payloads):
        self.payloads, self.chamadas = list(payloads), []

    def post(self, url, json=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "body": json, "headers": headers})
        return _Resp(self.payloads.pop(0))


FILTRO_OK = [{"signal_field_name": "website_visitors_from_domains"}]


def test_chave_vai_no_header_e_pagina():
    s = _Sessao([
        {"breadcrumbs": FILTRO_OK, "accounts": [{"name": "A"}], "pagination": {"total_pages": 2}},
        {"breadcrumbs": FILTRO_OK, "organizations": [{"name": "B"}], "pagination": {"total_pages": 2}},
    ])
    r = sync.buscar_visitantes("segredo", ["ram.com.br"], session=s)
    assert [e["name"] for e in r] == ["A", "B"]
    assert all(c["headers"]["X-Api-Key"] == "segredo" for c in s.chamadas)
    assert all("segredo" not in c["url"] for c in s.chamadas)
    assert s.chamadas[0]["body"]["website_visitors_from_domains"] == [sync.APOLLO_DOMINIO_RASTREADO]


def test_aborta_se_api_ignorar_filtro_de_visitantes():
    s = _Sessao([{"breadcrumbs": [], "accounts": [{"name": "A"}], "pagination": {"total_pages": 1}}])
    with pytest.raises(SystemExit):
        sync.buscar_visitantes("k", ["ram.com.br"], session=s)
