#!/usr/bin/env python3
"""
Fase 1b do ABM Sétima: carga/normalização dos dados já existentes (seção 2 da
spec, adaptada — as contas e os contatos já estão no Odoo).

Contas (oportunidades da equipe ABM Setima):
  - estágio: Alvo; Volkswagen e Hyundai (clientes) → Cliente – expansão + tag
    "Conta cliente";
  - tag ABM Sétima, campanha UTM, trilha "a definir", cadência "não iniciada";
  - domínio principal/extras deduzidos dos e-mails do comitê;
  - links com UTM por canal; nome no LinkedIn = nome da conta (conferir);
  - responsável = SDR (Amanda), Diego como seguidor. Sem notificação por e-mail.
  - os estágios antigos "ABM · …" deixam de aparecer na equipe ABM Setima
    (continuam no ABM BrandSpot).

Contatos (filhos das empresas das contas):
  - prioridade: 1 decisor, 2 influenciador, 3 demais, 9 fora do ICP
    (Compliance/Jurídico, RH, Financeiro);
  - conexão LinkedIn "não enviado", fora da cadência, sem opt-out;
  - canal inicial pelo status do e-mail.
Só preenche campos ABM novos; não altera nome, cargo, e-mail etc.

Dry-run por padrão; APLICAR=true grava.
"""

import collections
import os
import re
import sys
import unicodedata

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, odoo, ref  # noqa: E402

CLIENTES = {"Volkswagen do Brasil", "Hyundai Motor Brasil"}
AREAS_FORA = {"Compliance/Jurídico", "RH", "Financeiro/Controladoria"}
PRIORIDADE_PAPEL = {"Decisor": 1, "Influenciador-chave": 2, "Influenciador": 2, "Fora": 9}
DOMINIOS_GENERICOS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "yahoo.com.br",
                      "icloud.com", "live.com", "uol.com.br", "bol.com.br"}
URL_UTM = ("https://www.setima.cc/PT?utm_source={canal}&utm_medium=abm_1a1"
           "&utm_campaign=abm-setima-montadoras&utm_content={slug}")
SEM_NOTIFICAR = {"mail_auto_subscribe_no_notify": True, "tracking_disable": False}


def slug(nome):
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def canal_inicial(status):
    if status in ("Verificado", "Válido"):
        return "email_linkedin"
    if status in ("Extrapolado", "catch-all"):
        return "email_arriscado_linkedin"
    return "linkedin_primeiro"


def main():
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    team_id = int(odoo("ir.config_parameter", "get_param", key="abm.team_id"))
    sdr_id = int(odoo("ir.config_parameter", "get_param", key="abm.sdr_user_id"))
    alvo, cliente = ref(f"{MODULO}.stage_alvo"), ref(f"{MODULO}.stage_cliente_expansao")
    tag_abm = odoo("crm.tag", "search", domain=[["name", "=", "ABM Sétima"]])[0]
    tag_cliente = odoo("crm.tag", "search", domain=[["name", "=", "Conta cliente"]])[0]
    campanha = odoo("utm.campaign", "search", domain=[["name", "=", "ABM Sétima Montadoras"]])[0]
    diego_partner = odoo("res.users", "read", ids=[22], fields=["partner_id"])[0]["partner_id"][0]

    contas = odoo("crm.lead", "search_read", domain=[["team_id", "=", team_id]],
                  fields=["id", "name", "partner_id", "stage_id", "user_id"])
    empresas = [c["partner_id"][0] for c in contas if c["partner_id"]]
    contatos = odoo("res.partner", "search_read",
                    domain=[["parent_id", "in", empresas], ["active", "in", [True, False]]],
                    fields=["id", "parent_id", "email", "x_abm_papel", "x_abm_area",
                            "x_email_status", "x_abm_prioridade", "x_abm_li_conexao"])
    por_empresa = collections.defaultdict(list)
    for p in contatos:
        por_empresa[p["parent_id"][0]].append(p)

    # --------------------------------------------------------------- contas
    print(f"Contas: {len(contas)}")
    for c in contas:
        dominios = collections.Counter(
            p["email"].split("@")[-1].lower() for p in por_empresa.get(c["partner_id"][0], [])
            if p["email"] and "@" in p["email"])
        dominios = [d for d, _ in dominios.most_common() if d not in DOMINIOS_GENERICOS]
        e_cliente = c["name"] in CLIENTES
        s = slug(c["name"])
        vals = {
            "stage_id": cliente if e_cliente else alvo,
            "tag_ids": [(4, tag_abm)] + ([(4, tag_cliente)] if e_cliente else []),
            "campaign_id": campanha, "user_id": sdr_id,
            "x_abm_trilha": "a_definir", "x_abm_cadencia_status": "nao_iniciada", "x_abm_onda": 0,
            "x_abm_dominio": dominios[0] if dominios else False,
            "x_abm_dominios_extra": ", ".join(dominios[1:]) or False,
            "x_abm_linkedin_empresa": c["name"],
            "x_abm_link_email": URL_UTM.format(canal="email", slug=s),
            "x_abm_link_linkedin": URL_UTM.format(canal="linkedin_dm", slug=s),
            "x_abm_link_whatsapp": URL_UTM.format(canal="whatsapp", slug=s),
        }
        print(f"  {c['name']:<34} → {'Cliente – expansão' if e_cliente else 'Alvo':<19} "
              f"domínio={vals['x_abm_dominio']}")
        if APLICAR:
            odoo("crm.lead", "write", ids=[c["id"]], vals=vals, context=SEM_NOTIFICAR)
            odoo("crm.lead", "message_subscribe", ids=[c["id"]], partner_ids=[diego_partner])

    # Estágios antigos "ABM · …" deixam de valer para esta equipe.
    antigos = odoo("crm.stage", "search", domain=[["name", "=like", "ABM · %"], ["team_ids", "in", [team_id]]])
    print(f"Estágios antigos a desvincular da equipe {team_id}: {antigos}")
    if APLICAR and antigos:
        odoo("crm.stage", "write", ids=antigos, vals={"team_ids": [(3, team_id)]})

    # ------------------------------------------------------------ contatos
    lotes = collections.defaultdict(list)
    for p in contatos:
        prioridade = 9 if p["x_abm_area"] in AREAS_FORA else PRIORIDADE_PAPEL.get(p["x_abm_papel"], 3)
        vals = {"x_abm_prioridade": prioridade, "x_abm_canal_inicial": canal_inicial(p["x_email_status"]),
                "x_abm_na_cadencia": False, "x_abm_optout": False}
        if not p["x_abm_li_conexao"]:
            vals["x_abm_li_conexao"] = "nao_enviado"
        lotes[tuple(sorted(vals.items()))].append(p["id"])
    resumo = collections.Counter()
    for chave, ids in lotes.items():
        resumo[dict(chave)["x_abm_prioridade"]] += len(ids)
    print(f"Contatos: {len(contatos)} | por prioridade: {dict(sorted(resumo.items()))}")
    if APLICAR:
        for chave, ids in lotes.items():
            for i in range(0, len(ids), 200):
                odoo("res.partner", "write", ids=ids[i:i + 200], vals=dict(chave))
        print("Gravado.")
    else:
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")


if __name__ == "__main__":
    main()
