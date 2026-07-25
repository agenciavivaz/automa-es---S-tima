"""Cliente JSON-2: headers, erros, retry, paginação e proteção da chave."""

import json

import pytest
import requests

from odoo.errors import (
    OdooAuthError,
    OdooPermissionError,
    OdooRequestError,
    OdooTransportError,
    ReadOnlyClientError,
)
from conftest import CHAVE_FALSA, RespostaFalsa, SessaoFalsa, montar_cliente


def test_monta_endpoint_headers_e_corpo_nomeado(sessao, cliente):
    sessao.respostas.append(RespostaFalsa(200, [{"id": 1, "name": "Lead A"}]))

    cliente.search_read("crm.lead", [("team_id", "in", [16])], ["id", "name"], limit=10)

    chamada = sessao.chamadas[0]
    assert chamada["url"] == "https://exemplo.odoo.com/json/2/crm.lead/search_read"
    assert chamada["headers"]["Authorization"] == f"Bearer {CHAVE_FALSA}"
    assert chamada["headers"]["X-Odoo-Database"] == "basefalsa"
    assert chamada["headers"]["Content-Type"] == "application/json"
    # Parâmetros nomeados, nunca posicionais.
    assert chamada["body"] == {
        "domain": [["team_id", "in", [16]]],
        "fields": ["id", "name"],
        "limit": 10,
    }


def test_write_e_create_usam_ids_vals_e_vals_list(sessao, cliente):
    sessao.respostas.extend([RespostaFalsa(200, True), RespostaFalsa(200, [42])])

    cliente.write("crm.lead", [1, 2], {"user_id": 7})
    cliente.create("crm.lead", {"name": "Novo", "team_id": 16})

    assert sessao.corpos_de("crm.lead", "write")[0] == {"ids": [1, 2], "vals": {"user_id": 7}}
    assert sessao.corpos_de("crm.lead", "create")[0] == {
        "vals_list": [{"name": "Novo", "team_id": 16}]
    }


def test_paginacao_invisivel_para_o_chamador(sessao, cliente):
    pagina_um = [{"id": i} for i in range(1, 501)]
    pagina_dois = [{"id": i} for i in range(501, 801)]
    sessao.respostas.extend([RespostaFalsa(200, pagina_um), RespostaFalsa(200, pagina_dois)])

    registros = cliente.search_read_all("crm.lead", [], ["id"])

    assert len(registros) == 800
    corpos = sessao.corpos_de("crm.lead", "search_read")
    assert corpos[0]["limit"] == 500 and "offset" not in corpos[0]
    assert corpos[1]["offset"] == 500


def test_paginacao_para_quando_pagina_vem_completa_e_proxima_vazia(sessao, cliente):
    sessao.respostas.extend([
        RespostaFalsa(200, [{"id": i} for i in range(500)]),
        RespostaFalsa(200, []),
    ])
    assert len(cliente.search_read_all("crm.lead", [], ["id"])) == 500
    assert len(sessao.chamadas) == 2


def test_retry_em_429_e_5xx(monkeypatch, sessao):
    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    sessao.respostas.extend([
        RespostaFalsa(429, {"message": "devagar"}, headers={"Retry-After": "0"}),
        RespostaFalsa(503, {"message": "indisponível"}),
        RespostaFalsa(200, [{"id": 1}]),
    ])
    cliente = montar_cliente(sessao)

    assert cliente.search_read("crm.lead", [], ["id"]) == [{"id": 1}]
    assert len(sessao.chamadas) == 3


def test_sem_retry_em_4xx_que_nao_seja_429(monkeypatch, sessao):
    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    sessao.respostas.append(
        RespostaFalsa(400, {"name": "ValidationError", "message": "campo inválido"})
    )
    cliente = montar_cliente(sessao)

    with pytest.raises(OdooRequestError) as erro:
        cliente.search_read("crm.lead", [], ["id"])

    assert erro.value.status_code == 400
    assert len(sessao.chamadas) == 1


def test_maximo_de_tres_tentativas(monkeypatch, sessao):
    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    sessao.respostas.extend([RespostaFalsa(500, {"message": "boom"}) for _ in range(3)])
    cliente = montar_cliente(sessao)

    with pytest.raises(OdooRequestError):
        cliente.search_count("crm.lead", [])
    assert len(sessao.chamadas) == 3


def test_401_e_403_viram_erros_especificos(monkeypatch):
    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    cliente_401 = montar_cliente(SessaoFalsa([RespostaFalsa(401, {"message": "sem acesso"})]))
    with pytest.raises(OdooAuthError) as erro:
        cliente_401.search_count("crm.lead", [])
    assert "expirada" in str(erro.value)

    cliente_403 = montar_cliente(SessaoFalsa([RespostaFalsa(403, {"message": "negado"})]))
    with pytest.raises(OdooPermissionError):
        cliente_403.search_count("crm.lead", [])


def test_falha_de_rede_vira_erro_de_transporte(monkeypatch):
    class SessaoQueQuebra:
        def post(self, *args, **kwargs):
            raise requests.ConnectionError("dns falhou")

    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    cliente = montar_cliente(SessaoQueQuebra())
    with pytest.raises(OdooTransportError):
        cliente.search_count("crm.lead", [])


def test_chave_nunca_aparece_em_erro_nem_em_repr(monkeypatch):
    monkeypatch.setattr("odoo.client.time.sleep", lambda _: None)
    sessao = SessaoFalsa([
        RespostaFalsa(400, {"name": "Erro", "message": f"chave usada: {CHAVE_FALSA}"})
    ])
    cliente = montar_cliente(sessao)

    with pytest.raises(OdooRequestError) as erro:
        cliente.search_count("crm.lead", [])

    assert CHAVE_FALSA not in str(erro.value)
    assert CHAVE_FALSA not in repr(cliente.credentials)
    assert CHAVE_FALSA not in str(cliente.credentials)


def test_cliente_somente_leitura_bloqueia_escrita(sessao):
    cliente = montar_cliente(sessao, somente_leitura=True)
    with pytest.raises(ReadOnlyClientError):
        cliente.write("crm.lead", [1], {"name": "x"})
    with pytest.raises(ReadOnlyClientError):
        cliente.create("crm.lead", {"name": "x"})
    assert sessao.chamadas == []


def test_contexto_vai_no_corpo(sessao, cliente):
    sessao.respostas.append(RespostaFalsa(200, []))
    cliente.search_read("crm.lead", [], ["id"], context={"active_test": False})
    assert sessao.chamadas[0]["body"]["context"] == {"active_test": False}


def test_resposta_vazia_nao_quebra(sessao, cliente):
    sessao.respostas.append(RespostaFalsa(200, texto=""))
    assert cliente.call("crm.lead", "write", {"ids": [1], "vals": {}}) is None


def test_whoami_identifica_usuario_de_servico(sessao, cliente):
    sessao.respostas.append(RespostaFalsa(200, [
        {"id": 3, "user_id": [8, "Integração CRM"], "name": "chave automações",
         "scope": False, "expiration_date": "2026-10-01"},
    ]))
    identidade = cliente.whoami()
    assert identidade["usuario"] == "Integração CRM"
    assert identidade["usuario_id"] == 8
    assert identidade["ambiguo"] is False


def test_whoami_admite_ambiguidade_em_vez_de_inventar(sessao, cliente):
    sessao.respostas.append(RespostaFalsa(200, [
        {"id": 1, "user_id": [2, "Admin"], "name": "a"},
        {"id": 2, "user_id": [8, "Serviço"], "name": "b"},
    ]))
    identidade = cliente.whoami()
    assert identidade["usuario"] is None
    assert identidade["ambiguo"] is True


def test_timeout_configuravel(sessao):
    cliente = montar_cliente(sessao, timeout=5)
    sessao.respostas.append(RespostaFalsa(200, 0))
    cliente.search_count("crm.lead", [])
    assert sessao.chamadas[0]["timeout"] == 5.0
