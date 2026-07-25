"""Edição de dados (Fase 2): dry-run, limite de confirmação, auditoria e escopo."""

import json

import pytest

from odoo.errors import ConfirmationRequired, OdooError, ScopeViolationError, UnknownFieldError
from odoo.write import Editor
from conftest import ClienteFalso

LEADS_NO_ESCOPO = [{"id": i, "team_id": [16, "Inbound Sétima"], "name": f"Lead {i}",
                    "user_id": [3, "Ana"]} for i in range(1, 61)]
LEADS_MISTOS = LEADS_NO_ESCOPO[:2] + [{"id": 99, "team_id": [42, "Fora"], "name": "Alheio"}]


def montar_editor(leads, schema, **kwargs):
    cliente = ClienteFalso({
        ("crm.lead", "search_read"): leads,
        ("crm.lead", "read"): leads,
        ("crm.lead", "search"): [l["id"] for l in leads],
    })
    return cliente, Editor(cliente, schema, **kwargs)


def test_dry_run_e_o_padrao_e_nao_chama_write(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)

    plano = editor.escrever("crm.lead", {"user_id": 7}, ids=[1, 2])

    assert plano.aplicado is False
    assert ("crm.lead", "write") not in cliente.chamadas
    assert plano.ids == [1, 2]
    assert plano.previa  # mostra antes → depois


def test_apply_executa_e_grava_auditoria(schema, tmp_path, monkeypatch):
    arquivo = tmp_path / "audit.jsonl"
    monkeypatch.setattr("odoo.audit.ARQUIVO_AUDITORIA", str(arquivo))
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)

    plano = editor.escrever("crm.lead", {"user_id": 7}, ids=[1, 2], aplicar=True)

    assert plano.aplicado is True
    assert cliente.ultima_escrita == {"model": "crm.lead", "ids": [1, 2],
                                      "vals": {"user_id": 7}}
    entrada = json.loads(arquivo.read_text(encoding="utf-8").strip())
    assert entrada["model"] == "crm.lead"
    assert entrada["method"] == "write"
    assert entrada["ids"] == [1, 2]
    assert entrada["payload"] == {"user_id": 7}
    assert entrada["perfil"] == "operacional"
    assert entrada["timestamp"]


def test_acima_do_limite_pede_confirmacao(schema):
    perguntas = []

    def confirmador(mensagem):
        perguntas.append(mensagem)
        return True

    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema, confirmador=confirmador)
    ids = [l["id"] for l in LEADS_NO_ESCOPO]  # 60 > 50

    editor.escrever("crm.lead", {"user_id": 7}, ids=ids, aplicar=True)

    assert len(perguntas) == 1
    assert "60" in perguntas[0]


def test_confirmacao_negada_nao_escreve(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema, confirmador=lambda _: False)
    ids = [l["id"] for l in LEADS_NO_ESCOPO]

    with pytest.raises(ConfirmationRequired):
        editor.escrever("crm.lead", {"user_id": 7}, ids=ids, aplicar=True)
    assert ("crm.lead", "write") not in cliente.chamadas


def test_abaixo_do_limite_nao_pergunta(schema):
    def confirmador(_):
        raise AssertionError("não deveria perguntar")

    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema, confirmador=confirmador)
    editor.escrever("crm.lead", {"user_id": 7}, ids=[1, 2, 3], aplicar=True)


def test_limite_de_confirmacao_configuravel(schema):
    perguntas = []
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema, limite_confirmacao=2,
                                    confirmador=lambda m: perguntas.append(m) or True)
    editor.escrever("crm.lead", {"user_id": 7}, ids=[1, 2, 3], aplicar=True)
    assert len(perguntas) == 1


def test_registro_fora_do_escopo_aborta_tudo(schema):
    cliente, editor = montar_editor(LEADS_MISTOS, schema)

    with pytest.raises(ScopeViolationError) as erro:
        editor.escrever("crm.lead", {"user_id": 7}, ids=[1, 2, 99], aplicar=True)

    assert erro.value.ids_bloqueados == [99]
    assert ("crm.lead", "write") not in cliente.chamadas  # nem os que estavam no escopo


def test_domain_vazio_e_recusado(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)
    for vazio in ([], None):
        with pytest.raises(OdooError) as erro:
            editor.escrever("crm.lead", {"user_id": 7}, domain=vazio, aplicar=True)
        assert "domain" in str(erro.value).lower() or "ids" in str(erro.value).lower()


def test_domain_e_resolvido_para_ids_antes_de_escrever(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO[:3], schema)
    plano = editor.escrever("crm.lead", {"user_id": 7}, domain=[("stage_id", "=", 5)])
    assert plano.ids == [1, 2, 3]
    # A seleção do domain já sai escopada pelas equipes permitidas.
    dominio_da_selecao = cliente.domains[0][1]
    assert ("team_id", "in", [16, 17, 21]) in dominio_da_selecao


def test_campo_inexistente_vira_erro_nomeando_o_campo(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)
    with pytest.raises(UnknownFieldError) as erro:
        editor.escrever("crm.lead", {"usr_id": 7}, ids=[1])
    assert "usr_id" in str(erro.value)
    assert "user_id" in str(erro.value)  # sugere o parecido


def test_modelo_fora_da_lista_editavel_e_bloqueado(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)
    with pytest.raises(OdooError):
        editor.escrever("crm.stage", {"name": "x"}, ids=[1])


def test_criar_lead_exige_equipe_permitida(schema):
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)

    with pytest.raises(OdooError) as sem_equipe:
        editor.criar("crm.lead", {"name": "Novo"})
    assert "team_id" in str(sem_equipe.value)

    with pytest.raises(OdooError):
        editor.criar("crm.lead", {"name": "Novo", "team_id": 42})

    plano = editor.criar("crm.lead", {"name": "Novo", "team_id": 16})
    assert plano.aplicado is False


def test_criar_com_apply_registra_auditoria(schema, tmp_path, monkeypatch):
    arquivo = tmp_path / "audit.jsonl"
    monkeypatch.setattr("odoo.audit.ARQUIVO_AUDITORIA", str(arquivo))
    cliente, editor = montar_editor(LEADS_NO_ESCOPO, schema)

    plano = editor.criar("crm.lead", {"name": "Novo", "team_id": 16}, aplicar=True)

    assert plano.aplicado is True
    entrada = json.loads(arquivo.read_text(encoding="utf-8").strip())
    assert entrada["method"] == "create"
    assert entrada["ids"] == plano.ids


def test_auditoria_esconde_valores_sensiveis(tmp_path):
    from odoo import audit

    arquivo = tmp_path / "audit.jsonl"
    audit.registrar(perfil="operacional", model="crm.lead", method="write", ids=[1],
                    payload={"name": "x", "api_key": "segredo"}, resultado=True,
                    arquivo=str(arquivo))
    entrada = json.loads(arquivo.read_text(encoding="utf-8").strip())
    assert entrada["payload"]["api_key"] == "***"
    assert "segredo" not in arquivo.read_text(encoding="utf-8")


def test_editor_recusa_cliente_somente_leitura(schema, sessao):
    from conftest import montar_cliente

    cliente = montar_cliente(sessao, somente_leitura=True)
    with pytest.raises(OdooError):
        Editor(cliente, schema)


def test_modulo_de_escrita_nao_tem_unlink():
    from pathlib import Path

    fonte = (Path(__file__).resolve().parent.parent / "odoo" / "write.py").read_text(
        encoding="utf-8")
    assert "unlink" in fonte  # só na frase que diz que não apaga
    assert "def unlink" not in fonte
    assert '"unlink"' not in fonte and "'unlink'" not in fonte
