#!/usr/bin/env python3
"""
Cria telas próprias do CRM para a equipe ABM Setima, sem tocar nas das
outras equipes.

No Odoo as visões são do modelo (crm.lead), não da equipe. Para editar o
kanban e o formulário do ABM Setima no Studio de forma independente, este
script cria:
  - 2 visões primárias (kanban e formulário), herdando as padrão do CRM;
  - 1 ação de janela filtrada na equipe ABM Setima, usando essas visões;
  - 1 menu "ABM Setima" na barra do CRM.

Abrindo o Studio a partir desse menu, as edições caem nessas cópias.
Idempotente: tudo é registrado em ir.model.data (module='abm_setima') e
reaproveitado numa segunda execução. Dry-run por padrão; APLICAR=true grava.
"""

import os

import requests
from dotenv import load_dotenv

load_dotenv()

ODOO_URL = os.environ["ODOO_URL"].rstrip("/").removesuffix("/odoo")
ODOO_DB = os.environ["ODOO_DB"]
ODOO_API_KEY = os.environ["ODOO_API_KEY"]
APLICAR = os.environ.get("APLICAR", "false").lower() == "true"
MODULO = "abm_setima"
EQUIPE_NOME = "ABM Setima"


def odoo(model, method, **params):
    resp = requests.post(
        f"{ODOO_URL}/json/2/{model}/{method}",
        headers={"Authorization": f"Bearer {ODOO_API_KEY}", "X-Odoo-Database": ODOO_DB,
                 "Content-Type": "application/json"},
        json=params, timeout=60,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{model}.{method} → HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


def ref(xmlid):
    modulo, _, nome = xmlid.partition(".")
    r = odoo("ir.model.data", "search_read", domain=[["module", "=", modulo], ["name", "=", nome]],
             fields=["res_id"])
    return r[0]["res_id"] if r else None


def garantir(nome, model, vals):
    """Cria o registro se o external id abm_setima.<nome> ainda não existir."""
    existente = ref(f"{MODULO}.{nome}")
    if existente:
        print(f"  = {MODULO}.{nome} já existe ({model} #{existente})")
        return existente
    if not APLICAR:
        print(f"  + criaria {MODULO}.{nome} ({model}): {vals.get('name')}")
        return None
    rid = odoo(model, "create", vals_list=[vals])[0]
    odoo("ir.model.data", "create", vals_list=[{"module": MODULO, "name": nome, "model": model,
                                                "res_id": rid, "noupdate": True}])
    print(f"  + criado {MODULO}.{nome} ({model} #{rid})")
    return rid


def main():
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    equipe = odoo("crm.team", "search_read", domain=[["name", "=", EQUIPE_NOME]], fields=["id"])
    if len(equipe) != 1:
        raise SystemExit(f"Equipe '{EQUIPE_NOME}' não encontrada ou ambígua: {equipe}")
    team_id = equipe[0]["id"]

    kanban_base = ref("crm.crm_case_kanban_view_leads")
    form_base = ref("crm.crm_lead_view_form")
    pipeline = ref("crm.crm_lead_action_pipeline")
    menu_crm = ref("crm.crm_menu_root")
    busca = odoo("ir.actions.act_window", "read", ids=[pipeline], fields=["search_view_id"])[0]["search_view_id"]

    # Cópias primárias: herdam a visão padrão (e as customizações do Studio
    # já aplicadas nela), mas o Studio passa a editar só a cópia.
    kanban = garantir("view_kanban", "ir.ui.view", {
        "name": "crm.lead.kanban.abm_setima", "model": "crm.lead", "type": "kanban",
        "mode": "primary", "inherit_id": kanban_base, "priority": 99,
        "arch": '<xpath expr="//kanban" position="attributes">'
                '<attribute name="class" add="o_abm_setima" separator=" "/></xpath>',
    })
    form = garantir("view_form", "ir.ui.view", {
        "name": "crm.lead.form.abm_setima", "model": "crm.lead", "type": "form",
        "mode": "primary", "inherit_id": form_base, "priority": 99,
        "arch": '<xpath expr="//form" position="attributes">'
                '<attribute name="class" add="o_abm_setima" separator=" "/></xpath>',
    })

    acao = garantir("action_pipeline", "ir.actions.act_window", {
        "name": EQUIPE_NOME, "res_model": "crm.lead",
        "view_mode": "kanban,list,form,calendar,pivot,graph,activity",
        "domain": f"[('type','=','opportunity'),('team_id','=',{team_id})]",
        "context": f"{{'default_type': 'opportunity', 'default_team_id': {team_id}}}",
        "search_view_id": busca[0] if busca else False,
        "view_ids": [
            (0, 0, {"sequence": 0, "view_mode": "kanban", "view_id": kanban}),
            (0, 0, {"sequence": 1, "view_mode": "list", "view_id": ref("crm.crm_case_tree_view_oppor")}),
            (0, 0, {"sequence": 2, "view_mode": "form", "view_id": form}),
        ],
    })

    garantir("menu_pipeline", "ir.ui.menu", {
        "name": EQUIPE_NOME, "parent_id": menu_crm, "sequence": 2,
        "action": f"ir.actions.act_window,{acao}" if acao else False,
    })

    if not APLICAR:
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")


if __name__ == "__main__":
    main()
