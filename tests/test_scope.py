"""Escopo de equipes — RE-01, RE-02, RE-03 e RE-04."""

import pytest

from odoo.domain import combinar_e, normalizar
from odoo.errors import ScopeViolationError
from odoo.extract import Extrator
from odoo.models import ALLOWED_TEAM_IDS
from odoo.scope import (
    equipe_permitida,
    escopar_dominio_lead,
    verificar_leads_no_escopo,
    verificar_partners_no_escopo,
    verificar_vals_de_equipe,
)
from conftest import ClienteFalso


# -- RE-01 -----------------------------------------------------------------

def test_lista_de_equipes_definida_em_um_lugar_so():
    assert ALLOWED_TEAM_IDS == (16, 17, 21)


def test_nenhum_outro_modulo_redefine_a_lista():
    """Só models.py atribui ALLOWED_TEAM_IDS; os demais importam."""
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent / "odoo"
    definicoes = [
        arquivo.name
        for arquivo in raiz.rglob("*.py")
        if any(linha.startswith("ALLOWED_TEAM_IDS =")
               for linha in arquivo.read_text(encoding="utf-8").splitlines())
    ]
    assert definicoes == ["models.py"]


# -- RE-02 -----------------------------------------------------------------

def test_dominio_simples_recebe_filtro_de_equipe():
    resultado = escopar_dominio_lead([("stage_id", "=", 5)])
    assert resultado == ["&", ("team_id", "in", [16, 17, 21]), ("stage_id", "=", 5)]


def test_dominio_vazio_ou_none_vira_apenas_o_filtro_de_equipe():
    esperado = [("team_id", "in", [16, 17, 21])]
    assert escopar_dominio_lead([]) == esperado
    assert escopar_dominio_lead(None) == esperado


def test_dominio_com_and_implicito_de_varias_folhas_continua_valido():
    resultado = escopar_dominio_lead([("a", "=", 1), ("b", "=", 2)])
    assert resultado == ["&", ("team_id", "in", [16, 17, 21]),
                         "&", ("a", "=", 1), ("b", "=", 2)]
    # Normalizar de novo é idempotente: o domain resultante é bem formado.
    assert normalizar(resultado) == resultado


def test_dominio_com_or_nao_e_corrompido():
    resultado = escopar_dominio_lead(["|", ("a", "=", 1), ("b", "=", 2)])
    assert resultado == ["&", ("team_id", "in", [16, 17, 21]),
                         "|", ("a", "=", 1), ("b", "=", 2)]
    assert normalizar(resultado) == resultado


def test_or_do_chamador_nao_escapa_do_filtro_de_equipe():
    """O OR fica encapsulado: nunca vira 'equipe OU qualquer coisa'."""
    escopado = escopar_dominio_lead(["|", ("team_id", "=", 99), ("id", "=", 1)])
    assert escopado[0] == "&"
    assert escopado[1] == ("team_id", "in", [16, 17, 21])


def test_toda_extracao_de_lead_leva_o_filtro(schema):
    cliente = ClienteFalso({("crm.lead", "search_read"): []})
    extrator = Extrator(cliente, schema)
    extrator.extrair("crm.lead", campos=["id", "name"], domain=[("probability", ">", 50)])
    assert ("team_id", "in", [16, 17, 21]) in cliente.ultimo_domain


def test_chamador_nao_consegue_desligar_o_filtro(schema):
    """Mesmo pedindo outra equipe no domain, o filtro permitido continua lá."""
    cliente = ClienteFalso({("crm.lead", "search_read"): []})
    Extrator(cliente, schema).extrair("crm.lead", campos=["id"],
                                      domain=[("team_id", "=", 99)])
    domain = cliente.ultimo_domain
    assert ("team_id", "in", [16, 17, 21]) in domain
    assert ("team_id", "=", 99) in domain  # vira interseção vazia, não bypass


# -- RE-03 -----------------------------------------------------------------

LEADS = [
    {"id": 1, "team_id": [16, "Inbound Sétima"]},
    {"id": 2, "team_id": [17, "Campanhas BrandSpot"]},
    {"id": 3, "team_id": [99, "Outra equipe"]},
    {"id": 4, "team_id": False},
]


def test_leads_no_escopo_passam():
    cliente = ClienteFalso({("crm.lead", "search_read"): LEADS})
    assert verificar_leads_no_escopo(cliente, [1, 2]) == {1: 16, 2: 17}


def test_um_registro_fora_aborta_a_operacao_inteira_e_nomeia_os_ids():
    cliente = ClienteFalso({("crm.lead", "search_read"): LEADS})
    with pytest.raises(ScopeViolationError) as erro:
        verificar_leads_no_escopo(cliente, [1, 2, 3])
    assert erro.value.ids_bloqueados == [3]
    assert "3" in str(erro.value)
    assert "99" in str(erro.value)  # diz qual equipe causou o bloqueio


# -- RE-04 -----------------------------------------------------------------

def test_team_id_vazio_conta_como_fora_do_escopo():
    cliente = ClienteFalso({("crm.lead", "search_read"): LEADS})
    with pytest.raises(ScopeViolationError) as erro:
        verificar_leads_no_escopo(cliente, [1, 4])
    assert erro.value.ids_bloqueados == [4]

    assert equipe_permitida(False) is False
    assert equipe_permitida(None) is False
    assert equipe_permitida(0) is False
    assert equipe_permitida([16, "Inbound"]) is True


def test_id_inexistente_tambem_bloqueia():
    cliente = ClienteFalso({("crm.lead", "search_read"): LEADS})
    with pytest.raises(ScopeViolationError) as erro:
        verificar_leads_no_escopo(cliente, [1, 777])
    assert 777 in erro.value.ids_bloqueados


def test_escrita_nao_pode_mover_registro_para_fora_do_escopo():
    with pytest.raises(ScopeViolationError):
        verificar_vals_de_equipe({"team_id": 99})
    verificar_vals_de_equipe({"team_id": 21})  # permitido, não levanta


# -- res.partner (escopo indireto) ----------------------------------------

def test_partner_sem_lead_no_escopo_e_bloqueado():
    cliente = ClienteFalso({("crm.lead", "search_read"): [
        {"id": 10, "partner_id": [5, "Cliente A"]},
    ]})
    assert verificar_partners_no_escopo(cliente, [5]) == {5: [10]}

    with pytest.raises(ScopeViolationError) as erro:
        verificar_partners_no_escopo(cliente, [5, 6])
    assert erro.value.ids_bloqueados == [6]


# -- combinação de domains -------------------------------------------------

def test_combinar_e_ignora_partes_vazias():
    assert combinar_e([], None, [("a", "=", 1)]) == [("a", "=", 1)]


def test_domain_malformado_e_recusado():
    from odoo.errors import OdooError

    with pytest.raises(OdooError):
        normalizar(["&", ("a", "=", 1)])  # falta a segunda expressão
