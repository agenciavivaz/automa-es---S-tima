"""
Cria contas ABM Sétima (equipe 20) com a MESMA estrutura das contas existentes.

Para cada conta do JSON de entrada:
  - Empresa (res.partner): reaproveita a indicada em "partner_id" (marcando
    conta-alvo + tag "ABM Montadoras") ou cria uma nova.
  - Negócio (crm.lead): Alvo · Tier 2 · trilha "a definir" · preparação "na fila"
    · campanha "ABM Sétima Montadoras" · tag "ABM Sétima" · SDR Amanda · links
    com UTM (utm_content = slug da conta). Conta que já é cliente entra em
    "Cliente – expansão" com preparação "Não preparar" (campo "etapa": "cliente").
  - Não cria atividades. A conta entra na fila diária de preparação.
  - Pula conta que já existe no ABM (mesma empresa ou mesmo domínio).

Entrada (JSON): lista de objetos com conta, nome_linkedin, dominio,
dominios_extra, website, cidade, funcionarios, [partner_id], [etapa].

Uso:
    python criar_contas_abm.py contas.json            # simulação
    python criar_contas_abm.py contas.json --aplicar  # grava
"""

import argparse
import json
import os
import re
import sys
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()

TEAM_ABM_SETIMA = 20
SDR_USER_ID = 31
STAGE_ALVO = 87
STAGE_CLIENTE = 96
TAG_LEAD_ABM = 3
TAG_PARCEIRO_ABM = 17
CAMPANHA_ABM = 6
IDIOMA_PT_BR = 60
UTM = ("https://www.setima.cc/PT?utm_source={fonte}&utm_medium=abm_1a1"
       "&utm_campaign=abm-setima-montadoras&utm_content={slug}")


def slug(nome):
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", nome).strip("-")


class Odoo:
    def __init__(self):
        self.url = re.sub(r"/odoo$", "", os.environ["ODOO_URL"].strip().rstrip("/"))
        self.headers = {"Authorization": "Bearer " + os.environ["ODOO_API_KEY"],
                        "X-Odoo-Database": os.environ["ODOO_DB"]}

    def call(self, model, method, **params):
        r = requests.post(f"{self.url}/json/2/{model}/{method}", headers=self.headers,
                          json=params, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"{model}.{method}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("json")
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    contas = json.load(open(args.json, encoding="utf-8"))

    odoo = Odoo()
    existentes = odoo.call("crm.lead", "search_read",
                           domain=[["team_id", "=", TEAM_ABM_SETIMA], ["active", "in", [True, False]]],
                           fields=["name", "partner_id", "x_abm_dominio", "x_abm_dominios_extra"])
    parceiros_abm = {l["partner_id"][0] for l in existentes if l["partner_id"]}
    dominios_abm = {d.strip().lower() for l in existentes
                    for d in ((l["x_abm_dominio"] or "") + "," + (l["x_abm_dominios_extra"] or "")).split(",")
                    if d.strip()}

    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULAÇÃO (nada é gravado)'}\n")
    criadas = 0
    for c in contas:
        pid = c.get("partner_id")
        dominio = (c.get("dominio") or "").lower()
        if (pid and pid in parceiros_abm) or (dominio and dominio in dominios_abm):
            print(f"  PULA  {c['conta']}: já existe no ABM")
            continue
        cliente = c.get("etapa") == "cliente"
        s = slug(c["conta"])
        lead = {
            "name": c["conta"], "type": "opportunity", "team_id": TEAM_ABM_SETIMA,
            "user_id": SDR_USER_ID, "stage_id": STAGE_CLIENTE if cliente else STAGE_ALVO,
            "tag_ids": [[6, 0, [TAG_LEAD_ABM]]], "campaign_id": CAMPANHA_ABM, "lang_id": IDIOMA_PT_BR,
            "website": c.get("website") or False, "city": c.get("cidade") or False,
            "x_abm_tier": "2", "x_abm_trilha": "a_definir",
            "x_abm_preparacao": "pular" if cliente else "fila",
            "x_abm_cadencia_status": "nao_iniciada", "x_abm_onda": 0,
            "x_abm_dominio": dominio or False, "x_abm_dominios_extra": c.get("dominios_extra") or False,
            "x_abm_linkedin_empresa": c.get("nome_linkedin") or c["conta"],
            "x_abm_link_email": UTM.format(fonte="email", slug=s),
            "x_abm_link_linkedin": UTM.format(fonte="linkedin_dm", slug=s),
            "x_abm_link_whatsapp": UTM.format(fonte="whatsapp", slug=s),
        }
        acao = f"reaproveita empresa #{pid}" if pid else "cria empresa"
        print(f"  {'CRIA':5} {c['conta']:36} {'Cliente – expansão' if cliente else 'Alvo':18} {acao}")
        if not args.aplicar:
            continue
        if pid:
            atual = odoo.call("res.partner", "read", ids=[pid], fields=["website", "city"])[0]
            odoo.call("res.partner", "write", ids=[pid], vals={
                "x_conta_alvo": True, "category_id": [[4, TAG_PARCEIRO_ABM]],
                "website": atual["website"] or c.get("website") or False,
                "city": atual["city"] or c.get("cidade") or False})
        else:
            pid = odoo.call("res.partner", "create", vals_list=[{
                "name": c["conta"], "is_company": True, "website": c.get("website") or False,
                "city": c.get("cidade") or False, "lang": "pt_BR", "x_conta_alvo": True,
                "x_employee_count": str(c.get("funcionarios") or "") or False,
                "category_id": [[6, 0, [TAG_PARCEIRO_ABM]]]}])[0]
        lead["partner_id"] = pid
        odoo.call("crm.lead", "create", vals_list=[lead])
        criadas += 1
    if args.aplicar:
        print(f"\n{criadas} conta(s) criada(s).")
    else:
        print("\nSimulação concluída. Rode com --aplicar para gravar.")


if __name__ == "__main__":
    sys.exit(main())
