"""
Cria as contas do ABM BrandSpot (equipe 22) a partir de um export de CONTAS do Apollo,
com a mesma estrutura de card do ABM Sétima (criar_contas_abm.py).

Para cada conta do CSV:
  - Negócio (crm.lead): Alvo · Tier 2 · preparação "na fila" · cadência "não iniciada"
    · campanha "ABM BrandSpot Educação" · tag "ABM BrandSpot" · SDR Amanda · empresa
    Brandspot · links com UTM do brandspot.com.br (utm_content = slug da conta)
    · nome no LinkedIn = "Company Name" do Apollo (é por ele que o importador de
    comitê casa as pessoas) · Apollo Account Id, setor e porte na descrição.
  - Empresa (res.partner): reaproveita a do card existente, ou uma empresa com o
    mesmo domínio/nome, ou cria uma nova (tag "ABM Educação", conta-alvo).
  - Conta que já está na equipe 22 (mesmo domínio ou nome) é ATUALIZADA, não duplicada.
  - Cards da equipe 22 que NÃO estão no CSV viram Tier 3 (backlog): continuam no
    programa, mas a fila diária (tier → score → comitê) prepara a lista antes.
  - Não cria atividades: a conta entra na fila diária de preparação.

Uso (na raiz do repositório):
    python -m abm_brandspot.criar_contas export.csv            # simulação
    python -m abm_brandspot.criar_contas export.csv --aplicar  # grava
"""

import argparse
import csv
import re
import sys
import unicodedata
from urllib.parse import urlparse

from ._odoo import Odoo

TEAM_ID = 22
SDR_USER_ID = 31
EMPRESA_BRANDSPOT = 12
CATEGORIA_PARCEIRO = 18   # "ABM Educação"
IDIOMA_PT_BR = 60
UTM = ("https://www.brandspot.com.br/?utm_source={fonte}&utm_medium=abm_1a1"
       "&utm_campaign=abm-brandspot-educacao&utm_content={slug}")


def slug(nome):
    nome = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", nome).strip("-")


def dominio(url):
    if not url:
        return ""
    host = urlparse(url if "//" in url else "http://" + url).hostname or ""
    return re.sub(r"^www\.", "", host.lower())


def ler_csv(caminho):
    contas = []
    with open(caminho, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            nome = r["Company Name"].strip()
            if not nome:
                continue
            contas.append({
                "conta": nome,
                "dominio": dominio(r.get("Website")),
                "website": (r.get("Website") or "").replace("http://", "https://") or False,
                "cidade": r.get("Company City") or False,
                "funcionarios": r.get("# Employees") or "",
                "setor": r.get("Industry") or "",
                "linkedin": r.get("Company Linkedin Url") or "",
                "apollo_id": r.get("Apollo Account Id") or "",
            })
    return contas


def descricao(c):
    linhas = [f"Apollo Account Id: {c['apollo_id']}" if c["apollo_id"] else "",
              f"Setor (Apollo): {c['setor']}" if c["setor"] else "",
              f"Funcionários (Apollo): {c['funcionarios']}" if c["funcionarios"] else "",
              f"LinkedIn: {c['linkedin']}" if c["linkedin"] else ""]
    return "<p>" + "<br/>".join(l for l in linhas if l) + "</p>"


def padrao_abm(ref, tier, s):
    """Campos que todo card do ABM BrandSpot tem (os mesmos da Sétima)."""
    return {
        "type": "opportunity", "team_id": TEAM_ID, "user_id": SDR_USER_ID,
        "company_id": EMPRESA_BRANDSPOT, "stage_id": ref["stage_alvo"],
        "tag_ids": [[6, 0, [ref["tag_abm"]]]], "campaign_id": ref["campaign_educacao"],
        "lang_id": IDIOMA_PT_BR, "x_abm_tier": tier, "x_abm_preparacao": "fila",
        "x_abm_cadencia_status": "nao_iniciada", "x_abm_onda": 0,
        "x_abm_link_email": UTM.format(fonte="email", slug=s),
        "x_abm_link_linkedin": UTM.format(fonte="linkedin_dm", slug=s),
        "x_abm_link_whatsapp": UTM.format(fonte="whatsapp", slug=s),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    contas = ler_csv(args.csv)
    odoo = Odoo()

    ref = {x["name"]: x["res_id"] for x in odoo.call(
        "ir.model.data", "search_read", domain=[["module", "=", "abm_brandspot"],
                                               ["name", "in", ["stage_alvo", "tag_abm", "campaign_educacao"]]],
        fields=["name", "res_id"])}
    if len(ref) < 3:
        sys.exit("Estrutura do ABM BrandSpot não encontrada: rode antes python -m abm_brandspot.estrutura --aplicar")

    existentes = odoo.call("crm.lead", "search_read",
                           domain=[["team_id", "=", TEAM_ID], ["active", "in", [True, False]]],
                           fields=["name", "partner_id", "website", "x_abm_dominio", "stage_id", "x_abm_preparacao"])
    por_chave = {}
    for l in existentes:
        for chave in (slug(l["name"]), l["x_abm_dominio"] or dominio(l["website"])):
            if chave:
                por_chave.setdefault(chave, l)

    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULAÇÃO (nada é gravado)'}")
    print(f"{len(contas)} conta(s) no CSV · {len(existentes)} card(s) já na equipe {TEAM_ID}\n")
    usados, criadas, atualizadas = set(), 0, 0
    for c in contas:
        s = slug(c["conta"])
        existente = por_chave.get(c["dominio"]) if c["dominio"] else None
        existente = existente or por_chave.get(s)
        vals = {**padrao_abm(ref, "2", s),
                "name": c["conta"], "website": c["website"], "city": c["cidade"],
                "x_abm_dominio": c["dominio"] or False, "x_abm_linkedin_empresa": c["conta"],
                "description": descricao(c)}
        if existente and existente["id"] not in usados:
            usados.add(existente["id"])
            # Card antigo: mantém etapa se já andou e mantém a preparação já liberada.
            if existente["stage_id"][0] != ref["stage_alvo"]:
                vals.pop("stage_id")
            if existente["x_abm_preparacao"] in ("liberada", "pular"):
                vals.pop("x_abm_preparacao")
            print(f"  ATUALIZA {c['conta'][:44]:44} card #{existente['id']} (era '{existente['name']}')")
            atualizadas += 1
            if args.aplicar:
                odoo.call("crm.lead", "write", ids=[existente["id"]], vals=vals)
            continue

        parceiro = None
        if c["dominio"]:
            achados = odoo.call("res.partner", "search_read",
                                domain=[["is_company", "=", True], ["website", "ilike", c["dominio"]]],
                                fields=["name", "website"], limit=5)
            parceiro = next((p for p in achados if dominio(p["website"]) == c["dominio"]), None)
        if not parceiro:
            achados = odoo.call("res.partner", "search_read",
                                domain=[["is_company", "=", True], ["name", "=ilike", c["conta"]]],
                                fields=["name"], limit=1)
            parceiro = achados[0] if achados else None
        acao = f"reaproveita empresa #{parceiro['id']}" if parceiro else "cria empresa"
        print(f"  CRIA     {c['conta'][:44]:44} Alvo · T2 · {c['dominio'] or 'sem domínio':28} {acao}")
        criadas += 1
        if not args.aplicar:
            continue
        if parceiro:
            pid = parceiro["id"]
            odoo.call("res.partner", "write", ids=[pid], vals={
                "x_conta_alvo": True, "category_id": [[4, CATEGORIA_PARCEIRO]]})
        else:
            pid = odoo.call("res.partner", "create", vals_list=[{
                "name": c["conta"], "is_company": True, "website": c["website"], "city": c["cidade"],
                "lang": "pt_BR", "x_conta_alvo": True, "x_employee_count": c["funcionarios"] or False,
                "category_id": [[6, 0, [CATEGORIA_PARCEIRO]]]}])[0]
        odoo.call("crm.lead", "create", vals_list=[{**vals, "partner_id": pid}])

    backlog = [l for l in existentes if l["id"] not in usados]
    print(f"\nCards da equipe {TEAM_ID} fora do CSV → Tier 3 (backlog, continuam no programa):")
    for l in backlog:
        s = slug(l["name"])
        vals = {**padrao_abm(ref, "3", s), "x_abm_linkedin_empresa": l["name"],
                "x_abm_dominio": l["x_abm_dominio"] or dominio(l["website"]) or False}
        if l["stage_id"][0] != ref["stage_alvo"]:
            vals.pop("stage_id")
        if l["x_abm_preparacao"] in ("liberada", "pular"):
            vals.pop("x_abm_preparacao")
        print(f"  TIER 3   {l['name'][:44]:44} card #{l['id']}")
        if args.aplicar:
            odoo.call("crm.lead", "write", ids=[l["id"]], vals=vals)

    print(f"\n{criadas} a criar · {atualizadas} card(s) existente(s) atualizado(s) · {len(backlog)} no backlog (Tier 3).")
    if not args.aplicar:
        print("Simulação concluída. Rode com --aplicar para gravar.")


if __name__ == "__main__":
    sys.exit(main())
