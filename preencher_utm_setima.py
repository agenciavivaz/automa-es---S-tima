"""
Preenche as UTMs (origem, mídia, campanha) dos leads do Inbound Sétima vindos do Meta.

A planilha do Meta não tem colunas utm_*: traz campanha, conjunto, anúncio e plataforma,
que o import_leads_setima.py grava na descrição do lead. Este script lê a descrição e
preenche os campos padrão do Odoo:

    Plataforma ig / fb  → Origem (source_id): Instagram / Facebook
    (anúncio pago)      → Mídia (medium_id): Paid Social
    Campanha            → Campanha (campaign_id): uma utm.campaign por nome

Só preenche campo vazio (nunca sobrescreve) e inclui leads arquivados (ganhos/perdidos).
Conjunto e anúncio não têm campo UTM no lead: continuam na descrição.

Uso:
    DRY_RUN=true  python preencher_utm_setima.py   # só mostra o que faria (padrão)
    DRY_RUN=false python preencher_utm_setima.py   # grava

Variáveis: ODOO_URL (base, ex. https://grupo-setima.odoo.com), ODOO_DB, ODOO_API_KEY,
ODOO_TEAM_ID_SETIMA (padrão 16). Usa a API JSON-2 do Odoo 19.
"""

import os
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import urlsplit

import requests

TEAM_ID = int(os.environ.get("ODOO_TEAM_ID_SETIMA", "16"))
DRY_RUN = os.environ.get("DRY_RUN", "true").strip().lower() != "false"

_url = urlsplit(os.environ["ODOO_URL"])
BASE = f"{_url.scheme}://{_url.netloc}/json/2/"
HEADERS = {
    "Authorization": "Bearer " + os.environ["ODOO_API_KEY"],
    "X-Odoo-Database": os.environ["ODOO_DB"],
    "Content-Type": "application/json",
}

PLATAFORMAS = {"ig": "Instagram", "fb": "Facebook", "an": "Audience Network", "msg": "Messenger"}
MIDIA = "Paid Social"


def call(model, method, **kw):
    r = requests.post(BASE + f"{model}/{method}", headers=HEADERS, json=kw, timeout=120)
    if r.status_code != 200:
        raise RuntimeError(f"{model}.{method}: HTTP {r.status_code} {r.text[:500]}")
    return r.json()


def campo(rotulo, descricao):
    m = re.search(re.escape(rotulo) + r":\s*([^\n<]*)", descricao or "")
    valor = m.group(1).strip() if m else ""
    return valor or None


def get_or_create(model, nome, campo_nome="name", vals_extra=None):
    achado = call(model, "search_read", domain=[[campo_nome, "=", nome]], fields=["id"], limit=1)
    if achado:
        return achado[0]["id"], False
    if DRY_RUN:
        return f"(novo) {nome}", True  # marcador só para o relatório; nada é gravado
    vals = {campo_nome: nome, **(vals_extra or {})}
    novo = call(model, "create", vals_list=[vals])
    return (novo[0] if isinstance(novo, list) else novo), True


def main():
    leads = call(
        "crm.lead", "search_read",
        domain=[["team_id", "=", TEAM_ID], ["active", "in", [True, False]],
                ["description", "ilike", "Lead ID (Meta)"]],
        fields=["description", "source_id", "medium_id", "campaign_id"],
    )
    print(f"{len(leads)} lead(s) do Meta na equipe {TEAM_ID}.")

    origens, campanhas = {}, {}
    medium_id, criada = get_or_create("utm.medium", MIDIA)
    if criada:
        print(f"  criar mídia: {MIDIA}")

    grupos = defaultdict(list)  # vals → ids
    sem_dados = 0
    for lead in leads:
        desc = lead["description"]
        plataforma = (campo("Plataforma", desc) or "").lower()
        campanha = campo("Campanha", desc)
        vals = {}
        if not lead["source_id"] and plataforma:
            nome = PLATAFORMAS.get(plataforma, plataforma)
            if nome not in origens:
                origens[nome], criada = get_or_create("utm.source", nome)
                if criada:
                    print(f"  criar origem: {nome}")
            vals["source_id"] = origens[nome]
        if not lead["medium_id"]:
            vals["medium_id"] = medium_id
        if not lead["campaign_id"] and campanha:
            if campanha not in campanhas:
                campanhas[campanha], criada = get_or_create("utm.campaign", campanha, "title")
                if criada:
                    print(f"  criar campanha: {campanha}")
            vals["campaign_id"] = campanhas[campanha]
        if not plataforma and not campanha:
            sem_dados += 1
        if vals:
            grupos[tuple(sorted(vals.items()))].append(lead["id"])

    total = sum(len(ids) for ids in grupos.values())
    print(f"{total} lead(s) a atualizar em {len(grupos)} grupo(s); {sem_dados} sem plataforma/campanha na descrição.")
    nomes_origem = {v: k for k, v in origens.items()}
    nomes_campanha = {v: k for k, v in campanhas.items()}
    resumo = Counter()
    for chave, ids in grupos.items():
        vals = dict(chave)
        resumo[(nomes_origem.get(vals.get("source_id"), "-"), nomes_campanha.get(vals.get("campaign_id"), "-"))] += len(ids)
        if not DRY_RUN:
            call("crm.lead", "write", ids=ids, vals=vals)
    for (origem, campanha), n in resumo.most_common():
        print(f"  {n:4d}  {origem:10s}  {campanha}")
    print("DRY_RUN: nada gravado." if DRY_RUN else "UTMs gravadas.")


if __name__ == "__main__":
    sys.exit(main())
