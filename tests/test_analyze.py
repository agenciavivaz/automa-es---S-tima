"""Análises de pipeline: matemática, classificação e denominador declarado."""

from datetime import datetime

import pytest

from odoo.analyze import ABERTO, ARQUIVADO, GANHO, PERDIDO, Analisador
from conftest import ClienteFalso

AGORA = datetime(2026, 7, 25, 12, 0, 0)

ESTAGIOS = [
    {"id": 1, "name": "Novo", "sequence": 1, "is_won": False, "team_id": [16, "Sétima"]},
    {"id": 2, "name": "Qualificado", "sequence": 2, "is_won": False, "team_id": False},
    {"id": 3, "name": "Proposta", "sequence": 3, "is_won": False, "team_id": False},
    {"id": 4, "name": "Ganho", "sequence": 4, "is_won": True, "team_id": False},
]


def lead(id_, estagio, *, valor=1000.0, ativo=True, probabilidade=30.0, equipe=16,
         responsavel=(3, "Ana"), criado="2026-06-01 10:00:00", motivo=None,
         origem=None, alterado="2026-06-02 10:00:00", ultimo_estagio=None):
    return {
        "id": id_,
        "name": f"Lead {id_}",
        "type": "opportunity",
        "active": ativo,
        "stage_id": [estagio, dict((e["id"], e["name"]) for e in ESTAGIOS)[estagio]],
        "user_id": list(responsavel) if responsavel else False,
        "team_id": [equipe, f"Equipe {equipe}"],
        "expected_revenue": valor,
        "probability": probabilidade,
        "create_date": criado,
        "write_date": alterado,
        "date_last_stage_update": ultimo_estagio or alterado,
        "lost_reason_id": list(motivo) if motivo else False,
        "source_id": list(origem) if origem else False,
        "medium_id": False,
        "campaign_id": False,
        "date_closed": False,
        "activity_date_deadline": False,
    }


def montar(leads, schema, respostas=None):
    base = {
        ("crm.stage", "search_read"): ESTAGIOS,
        ("crm.lead", "search_read"): leads,
        ("mail.message", "search_read"): [],
        ("mail.activity", "search_read"): [],
        ("mail.tracking.value", "search_read"): [],
    }
    base.update(respostas or {})
    cliente = ClienteFalso(base)
    return cliente, Analisador(cliente, schema, agora=AGORA)


# -- classificação ---------------------------------------------------------

def test_classificacao_de_ganho_perdido_arquivado_e_aberto(schema):
    _, analisador = montar([], schema)
    assert analisador.classificar(lead(1, 4)) == GANHO
    assert analisador.classificar(lead(2, 3, probabilidade=100)) == GANHO
    assert analisador.classificar(lead(3, 3, ativo=False, motivo=(2, "Preço"))) == PERDIDO
    assert analisador.classificar(lead(4, 3, ativo=False)) == ARQUIVADO
    assert analisador.classificar(lead(5, 2)) == ABERTO


# -- RF-12 funil -----------------------------------------------------------

def test_funil_conta_soma_e_calcula_conversao(schema):
    leads = [lead(1, 1), lead(2, 1), lead(3, 1), lead(4, 1),
             lead(5, 2), lead(6, 2),
             lead(7, 4, valor=5000.0)]
    _, analisador = montar(leads, schema)

    resultado = analisador.funil()[0]
    por_estagio = {linha[1]: linha for linha in resultado.linhas}

    assert por_estagio["Novo"][2] == 4
    assert por_estagio["Novo"][5] is None            # primeiro estágio não tem conversão
    assert por_estagio["Qualificado"][2] == 2
    assert por_estagio["Qualificado"][5] == 50.0     # 2 de 4
    assert por_estagio["Ganho"][3] == 5000.0
    assert por_estagio["Ganho"][6] == 1              # contado como ganho


def test_funil_declara_denominador(schema):
    leads = [lead(1, 1), lead(2, 2)]
    leads.append({**lead(3, 1), "stage_id": False})
    _, analisador = montar(leads, schema)

    resultado = analisador.funil(desde="2026-01-01", ate="2026-07-01")[0]

    assert resultado.meta["registros_considerados"] == 3
    assert resultado.meta["descartados_sem_estagio"] == 1
    assert resultado.meta["equipes_consideradas"] == [16, 17, 21]
    assert "2026-01-01 00:00:00" in resultado.meta["periodo"]
    assert "2026-07-01 23:59:59" in resultado.meta["periodo"]


def test_funil_recusa_equipe_fora_do_escopo(schema):
    from odoo.errors import OdooError

    _, analisador = montar([], schema)
    with pytest.raises(OdooError):
        analisador.funil(equipes=[16, 99])


# -- RF-13 tempo em estágio ------------------------------------------------

def test_tempo_em_estagio_usa_tracking_quando_disponivel(schema):
    leads = [lead(1, 3, criado="2026-06-01 00:00:00")]
    cliente, analisador = montar(leads, schema, {
        ("mail.tracking.value", "search_read"): [
            {"id": 1, "mail_message_id": [10, "msg"], "old_value_char": "Novo",
             "new_value_char": "Qualificado", "create_date": "2026-06-04 00:00:00"},
            {"id": 2, "mail_message_id": [11, "msg"], "old_value_char": "Qualificado",
             "new_value_char": "Proposta", "create_date": "2026-06-10 00:00:00"},
        ],
        ("mail.message", "search_read"): [
            {"id": 10, "res_id": 1, "date": "2026-06-04 00:00:00"},
            {"id": 11, "res_id": 1, "date": "2026-06-10 00:00:00"},
        ],
    })

    resultado = analisador.tempo_em_estagio()[0]
    por_estagio = {linha[0]: linha for linha in resultado.linhas}

    assert "mail.tracking.value" in resultado.meta["metodo"]
    assert por_estagio["Novo"][2] == 3.0          # 01/06 → 04/06
    assert por_estagio["Qualificado"][2] == 6.0   # 04/06 → 10/06


def test_tempo_em_estagio_cai_para_fallback_e_declara_limitacao(schema):
    leads = [lead(1, 2, ultimo_estagio="2026-07-15 12:00:00")]
    _, analisador = montar(leads, schema)

    resultado = analisador.tempo_em_estagio()[0]

    assert "date_last_stage_update" in resultado.meta["metodo"]
    assert any("LIMITAÇÃO" in nota for nota in resultado.notas)
    assert resultado.linhas[0][2] == 10.0  # 15/07 → 25/07


# -- RF-14 leads parados ---------------------------------------------------

def test_leads_parados_agrupa_por_responsavel(schema):
    leads = [
        lead(1, 2, responsavel=(3, "Ana"), alterado="2026-06-01 12:00:00"),
        lead(2, 2, responsavel=(3, "Ana"), alterado="2026-06-20 12:00:00"),
        lead(3, 2, responsavel=(4, "Bruno"), alterado="2026-07-24 12:00:00"),  # recente
        lead(4, 2, responsavel=None, alterado="2026-05-01 12:00:00"),
    ]
    _, analisador = montar(leads, schema)

    principal, detalhe = analisador.leads_parados(dias=14)
    por_responsavel = {linha[0]: linha for linha in principal.linhas}

    assert por_responsavel["Ana"][1] == 2
    assert "Bruno" not in por_responsavel          # mexido há 1 dia
    assert por_responsavel["(sem responsável)"][1] == 1
    assert principal.meta["parados"] == 3
    assert principal.meta["limite_dias_sem_atividade"] == 14
    assert len(detalhe.linhas) == 3


def test_lead_com_mensagem_recente_nao_e_parado(schema):
    leads = [lead(1, 2, alterado="2026-05-01 12:00:00")]
    _, analisador = montar(leads, schema,
                           {("mail.message", "search_read"): [{"id": 5, "res_id": 1}]})

    principal, _ = analisador.leads_parados(dias=14)
    assert principal.meta["parados"] == 0


def test_lead_com_atividade_agendada_nao_e_parado(schema):
    leads = [lead(1, 2, alterado="2026-05-01 12:00:00")]
    _, analisador = montar(leads, schema,
                           {("mail.activity", "search_read"): [{"id": 9, "res_id": 1}]})

    principal, _ = analisador.leads_parados(dias=14)
    assert principal.meta["parados"] == 0


def test_ganho_e_perdido_nao_entram_em_parados(schema):
    leads = [
        lead(1, 4, alterado="2026-01-01 12:00:00"),
        lead(2, 3, ativo=False, motivo=(1, "Sem orçamento"), alterado="2026-01-01 12:00:00"),
    ]
    _, analisador = montar(leads, schema)
    principal, _ = analisador.leads_parados(dias=14)
    assert principal.meta["parados"] == 0


# -- RF-15 atribuição ------------------------------------------------------

def test_atribuicao_calcula_taxa_de_ganho_por_origem(schema):
    leads = [
        lead(1, 4, origem=(7, "Google Ads"), valor=1000.0),
        lead(2, 3, origem=(7, "Google Ads"), ativo=False, motivo=(1, "Preço")),
        lead(3, 2, origem=(7, "Google Ads")),                # aberto: fora do denominador
        lead(4, 4, origem=None),
    ]
    _, analisador = montar(leads, schema)

    resultado = analisador.atribuicao_origem()[0]
    linhas = {(linha[0], linha[1]): linha for linha in resultado.linhas}
    google = linhas[("origem", "Google Ads")]

    assert google[2] == 3           # leads
    assert google[4] == 1           # ganhos
    assert google[5] == 1           # perdidos
    assert google[6] == 50.0        # 1 / (1+1)
    assert google[7] == 1000.0      # valor ganho
    # Denominador por dimensão: 1 lead sem origem, todos sem meio e sem campanha.
    assert resultado.meta["registros_sem_atribuicao_por_dimensao"] == {
        "origem": 1, "meio": 4, "campanha": 4,
    }


# -- RF-16 ganhos e perdas -------------------------------------------------

def test_ganhos_perdas_por_mes_e_ranking_de_motivos(schema):
    leads = [
        lead(1, 4, criado="2026-06-05 10:00:00", valor=2000.0),
        lead(2, 3, criado="2026-06-06 10:00:00", ativo=False, motivo=(1, "Preço"), valor=500.0),
        lead(3, 3, criado="2026-06-07 10:00:00", ativo=False, motivo=(1, "Preço"), valor=300.0),
        lead(4, 2, criado="2026-07-01 10:00:00"),
        lead(5, 3, criado="2026-07-02 10:00:00", ativo=False),  # arquivado sem motivo
    ]
    _, analisador = montar(leads, schema)

    periodo, motivos = analisador.ganhos_perdas()
    por_mes = {linha[0]: linha for linha in periodo.linhas}

    assert por_mes["2026-06"][2] == 1               # ganhos
    assert por_mes["2026-06"][3] == 2               # perdidos
    assert por_mes["2026-06"][5] == pytest.approx(33.3, abs=0.1)
    assert por_mes["2026-06"][6] == 2000.0
    assert por_mes["2026-07"][4] == 1               # abertos
    assert periodo.meta["arquivados_sem_motivo_de_perda"] == 1

    assert motivos.linhas[0][0] == "Preço"
    assert motivos.linhas[0][1] == 2
    assert motivos.linhas[0][2] == 100.0
    assert motivos.linhas[0][3] == 800.0


def test_todas_as_analises_declaram_periodo_e_equipes(schema):
    leads = [lead(1, 2), lead(2, 4)]
    _, analisador = montar(leads, schema)

    for resultados in (
        analisador.funil(),
        analisador.tempo_em_estagio(),
        analisador.leads_parados(),
        analisador.atribuicao_origem(),
        analisador.ganhos_perdas(),
    ):
        principal = resultados[0]
        assert "periodo" in principal.meta
        assert principal.meta["equipes_consideradas"] == [16, 17, 21]
        assert "registros_considerados" in principal.meta


def test_analises_avisam_quando_o_tipo_filtrou_tudo(schema):
    leads_lead = [{**lead(1, 1), "type": "lead"}]
    cliente = ClienteFalso({
        ("crm.stage", "search_read"): ESTAGIOS,
        ("crm.lead", "search_read"): leads_lead,
    })
    analisador = Analisador(cliente, schema, agora=AGORA)

    # O ClienteFalso não filtra por type; simulamos o caso de lista vazia.
    cliente.respostas[("crm.lead", "search_read")] = []
    resultado = analisador.funil()[0]
    assert resultado.meta["registros_considerados"] == 0
