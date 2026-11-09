"""Tira da tela "Atividades ABM" o que não é ABM e impede que volte a acontecer.

Causa: a automação "A10 · E-mail recebido" (on_message_received) disparou em lead
fora da equipe ABM (ex.: 26/0142 - Exen - Uninorte, Pipeline Sétima) e criou
"Classificar resposta" + sinal "resposta_a_classificar" nos dois ABMs (Sétima e
BrandSpot), apesar do filtro [('team_id', '=', N)] da automação.

O script:
  1. coloca uma trava de equipe no código das ações A10 (Sétima e BrandSpot):
     só processa `records` cuja equipe é a do ABM (idempotente);
  2. remove atividades de tipo "ABM · …" / "ABM BrandSpot · …" em leads que não
     são da equipe correspondente (20 / 22);
  3. remove os sinais x_abm_sinal ligados a leads fora das equipes ABM.

Dry-run por padrão. Para gravar:  python corrigir_atividades_fora_abm.py --aplicar
Usa ODOO_URL, ODOO_DB e ODOO_API_KEY (usuário com permissão de admin para o passo 1).
"""

import os
import re
import sys

import requests

ABMS = [
    # (prefixo do tipo de atividade, equipe, ação de servidor A10)
    ("ABM · ", 20, 1334),
    ("ABM BrandSpot · ", 22, 1375),
]
TRECHO_ANTIGO = "for conta in records:\n    msg ="
TRECHO_NOVO = (
    "# Trava de equipe: on_message_received chegou a disparar fora do ABM\n"
    "# (lead do Pipeline Sétima). Só processa contas da equipe deste ABM.\n"
    "for conta in records.filtered(lambda r: r.team_id.id == team_id):\n    msg ="
)


def cliente():
    url = re.sub(r"/odoo$", "", os.environ["ODOO_URL"].strip().rstrip("/"))
    headers = {
        "Authorization": "Bearer " + os.environ["ODOO_API_KEY"].strip(),
        "X-Odoo-Database": os.environ["ODOO_DB"].strip(),
        "Content-Type": "application/json",
    }

    def call(model, method, **kw):
        r = requests.post(f"{url}/json/2/{model}/{method}", headers=headers, json=kw, timeout=60)
        if r.status_code != 200:
            raise SystemExit(f"[HTTP {r.status_code}] {model}.{method}: {r.text[:500]}")
        return r.json()

    return call


def main(aplicar):
    call = cliente()
    modo = "APLICANDO" if aplicar else "DRY-RUN (use --aplicar para gravar)"
    print(f"== {modo}")

    # 1. Trava de equipe nas ações A10.
    for _prefixo, _equipe, acao_id in ABMS:
        codigo = call("ir.actions.server", "read", ids=[acao_id], fields=["name", "code"])[0]
        if TRECHO_NOVO in codigo["code"]:
            print(f"[A10] {codigo['name']}: trava já presente")
            continue
        if codigo["code"].count(TRECHO_ANTIGO) != 1:
            print(f"[A10] {codigo['name']}: trecho esperado não encontrado — revisar à mão")
            continue
        print(f"[A10] {codigo['name']}: adicionando trava de equipe")
        if aplicar:
            call("ir.actions.server", "write", ids=[acao_id],
                 vals={"code": codigo["code"].replace(TRECHO_ANTIGO, TRECHO_NOVO)})

    # 2. Atividades ABM em leads fora da equipe do ABM.
    for prefixo, equipe, _acao in ABMS:
        atividades = call("mail.activity", "search_read",
                          domain=[["activity_type_id.name", "=like", prefixo + "%"],
                                  ["res_model", "=", "crm.lead"]],
                          fields=["res_id", "res_name", "activity_type_id", "summary"])
        if not atividades:
            continue
        ids_lead = list({a["res_id"] for a in atividades})
        dentro = set(call("crm.lead", "search",
                          domain=[["id", "in", ids_lead], ["team_id", "=", equipe],
                                  ["active", "in", [True, False]]]))
        fora = [a for a in atividades if a["res_id"] not in dentro]
        for a in fora:
            print(f"[atividade {a['id']}] {a['res_name']} · {a['activity_type_id'][1]} · {a['summary']}")
        if aplicar and fora:
            call("mail.activity", "unlink", ids=[a["id"] for a in fora])

    # 3. Sinais ABM em leads fora das equipes ABM.
    sinais = call("x_abm_sinal", "search_read",
                  domain=[["x_lead_id.team_id", "not in", [e for _p, e, _a in ABMS]]],
                  fields=["x_name", "x_tipo", "x_lead_id"])
    for s in sinais:
        print(f"[sinal {s['id']}] {s['x_lead_id'][1]} · {s['x_tipo']} · {s['x_name']}")
    if aplicar and sinais:
        call("x_abm_sinal", "unlink", ids=[s["id"] for s in sinais])

    print("== fim")


if __name__ == "__main__":
    main("--aplicar" in sys.argv[1:])
