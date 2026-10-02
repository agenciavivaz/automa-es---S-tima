"""
Importa contatos de um export de contatos do Apollo para os comitês das contas
ABM Sétima (equipe 20), com a MESMA estrutura dos contatos já existentes.

Regras (derivadas dos 1.224 contatos importados em 2026-09-24):
  - Só pessoas baseadas no Brasil (Country = Brazil).
  - Só empresas que já são conta ABM (Company Name = "Nome no LinkedIn" da conta).
  - Deduplicação contra TODO o Odoo: Apollo Contact ID (na nota), e-mail e LinkedIn.
  - Senioridade → prioridade/papel:
        C suite, Vp, Director, Owner, Partner → 1 Decisor
        Head    → 2 Influenciador-chave       Manager → 2 Influenciador
        Senior  → 3 Usuário/Técnico           Entry/Intern → 3 Usuário/Ponto de entrada
    Área Financeiro, RH ou Jurídico → prioridade 9 (fora do ICP), papel mantido.
  - Área pelos departamentos do Apollo (Compras > Marketing > TI > Produto >
    Engenharia > Operações > Vendas > RH > Finanças > Jurídico > Outros).
  - Status do e-mail → canal inicial (Verificado/Válido → e-mail + LinkedIn;
    Extrapolado/catch-all → e-mail arriscado; demais → LinkedIn primeiro).
  - phone = celular; telefone direto vai para a nota. Tag "ABM Montadoras".

Uso:
    python importar_comite_apollo.py export.csv            # simulação
    python importar_comite_apollo.py export.csv --aplicar  # grava
"""

import argparse
import csv
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

TEAM_ABM_SETIMA = 20
TAG_ABM_MONTADORAS = 17

SENIORIDADE = {
    "c suite": ("C suite", 1, "Decisor"), "founder": ("Owner", 1, "Decisor"),
    "owner": ("Owner", 1, "Decisor"), "partner": ("Owner", 1, "Decisor"),
    "vp": ("Vp", 1, "Decisor"), "director": ("Director", 1, "Decisor"),
    "head": ("Head", 2, "Influenciador-chave"), "manager": ("Manager", 2, "Influenciador"),
    "senior": ("Senior", 3, "Usuário/Técnico"), "entry": ("Entry", 3, "Usuário/Ponto de entrada"),
    "intern": ("Intern", 3, "Usuário/Ponto de entrada"),
}
FORA_DO_ICP = {"Financeiro/Controladoria", "RH", "Compliance/Jurídico"}
STATUS_EMAIL = {
    "verified": "Verificado", "valid": "Válido", "extrapolated": "Extrapolado",
    "catch-all": "catch-all", "unavailable": "Indisponível", "invalid": "Inválido",
    "email no longer verified": "Inválido", "potentially invalid": "Inválido",
}
COMPRAS = re.compile(r"procure|purchas|sourcing|compras|suprimento|buyer", re.I)


def area(departamentos, subdepartamentos, cargo):
    deps = {d.strip() for d in departamentos.split(",") if d.strip()}
    if COMPRAS.search(subdepartamentos) or COMPRAS.search(cargo):
        return "Compras/Procurement"
    # O cargo manda quando é claramente de área fora do ICP (o Apollo às vezes
    # classifica "Compliance Analyst" em Engenharia).
    for padrao, nome in ((r"compliance|legal|jur[ií]dic|attorney|advogad", "Compliance/Jurídico"),
                         (r"\bRH\b|human resources|recursos humanos|talent", "RH"),
                         (r"financ|controller|controladoria|audit|accounting|contab", "Financeiro/Controladoria")):
        if re.search(padrao, cargo, re.I):
            return nome
    if "Marketing" in deps:
        return "Marketing"
    if "Information Technology" in deps and deps & {"Product", "Engineering & Technical"}:
        return "TI/Digital"
    por_departamento = "Outros"
    for dep, nome in (("Product", "Produto"), ("Engineering & Technical", "Engenharia/Design"),
                      ("Information Technology", "TI/Digital"), ("Operations", "Operações"),
                      ("Sales", "Comercial/Vendas"), ("Human Resources", "RH"),
                      ("Finance", "Financeiro/Controladoria"), ("Legal", "Compliance/Jurídico")):
        if dep in deps:
            por_departamento = nome
            break
    # Sem departamento útil (ou RH sem cargo de RH, ex.: "E-Performance Manager"),
    # o cargo decide. CEO/presidente seguem em "Outros", como nos comitês atuais.
    if por_departamento in ("Outros", "RH"):
        for padrao, nome in ((r"marketing|brand|marca|comunica|communication|rela[cç][oõ]es p[uú]blicas|\bpr\b|crm|reputa", "Marketing"),
                             (r"product|produto|e-performance", "Produto"),
                             (r"digital|e-commerce|ecommerce|\bit\b|technology|tecnologia", "TI/Digital"),
                             (r"design|engenharia|engineering", "Engenharia/Design"),
                             (r"sales|vendas|comercial|commercial|dealer|concession", "Comercial/Vendas")):
            if re.search(padrao, cargo, re.I):
                return nome
    return por_departamento


def canal(status):
    if status in ("Verificado", "Válido"):
        return "email_linkedin"
    if status in ("Extrapolado", "catch-all"):
        return "email_arriscado_linkedin"
    return "linkedin_primeiro"


def telefone(valor):
    return (valor or "").strip().lstrip("'") or False


def normalizar_url(url):
    return re.sub(r"^https?://(www\.)?", "", (url or "").strip().lower()).rstrip("/")


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
    parser.add_argument("csv")
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()

    linhas = list(csv.DictReader(open(args.csv, encoding="utf-8-sig")))
    if not linhas or "Apollo Contact Id" not in linhas[0]:
        sys.exit("CSV não parece um export de contatos do Apollo.")

    odoo = Odoo()
    contas = odoo.call("crm.lead", "search_read", domain=[["team_id", "=", TEAM_ABM_SETIMA]],
                       fields=["name", "x_abm_linkedin_empresa", "partner_id"])
    empresa_por_nome = {(c["x_abm_linkedin_empresa"] or c["name"]).strip().lower(): c
                        for c in contas if c["partner_id"]}

    emails = [l["Email"].strip().lower() for l in linhas if l["Email"].strip()]
    existentes = odoo.call("res.partner", "search_read",
                           domain=["|", "|", ["email", "in", emails],
                                   ["x_abm_notas", "ilike", "Apollo Contact ID"],
                                   ["x_linkedin_url", "!=", False]],
                           fields=["email", "x_abm_notas", "x_linkedin_url"])
    ids_conhecidos, emails_conhecidos, li_conhecidos = set(), set(), set()
    for p in existentes:
        if p["email"]:
            emails_conhecidos.add(p["email"].strip().lower())
        if p["x_linkedin_url"]:
            li_conhecidos.add(normalizar_url(p["x_linkedin_url"]))
        m = re.search(r"Apollo Contact ID:\s*(\S+)", p["x_abm_notas"] or "")
        if m:
            ids_conhecidos.add(m.group(1))

    motivos = Counter()
    fora_por_empresa = defaultdict(Counter)
    novos = []
    vistos = set()
    for l in linhas:
        empresa = l["Company Name"].strip()
        conta = empresa_por_nome.get(empresa.lower())
        email = l["Email"].strip().lower()
        li = normalizar_url(l["Person Linkedin Url"])
        if l["Country"].strip() != "Brazil":
            motivos["fora do Brasil"] += 1
            fora_por_empresa[empresa][l["Country"] or "sem país"] += 1
            continue
        if not conta:
            motivos["empresa não é conta ABM"] += 1
            fora_por_empresa[empresa]["sem conta ABM"] += 1
            continue
        chave = l["Apollo Contact Id"]
        if (chave in ids_conhecidos or (email and email in emails_conhecidos)
                or (li and li in li_conhecidos) or chave in vistos):
            motivos["já existe no Odoo"] += 1
            continue
        vistos.add(chave)

        senioridade, prioridade, papel = SENIORIDADE.get(
            l["Seniority"].strip().lower(), ("Entry", 3, "Usuário/Ponto de entrada"))
        ar = area(l["Departments"], l["Sub Departments"], l["Title"])
        if ar in FORA_DO_ICP:
            prioridade = 9
        status = STATUS_EMAIL.get(l["Email Status"].strip().lower(), False) if email else False
        nota = [f"Origem: Apollo export {date.today().isoformat()}",
                f"Apollo Contact ID: {chave}"]
        if telefone(l["Work Direct Phone"]):
            nota.append(f"Telefone direto: {telefone(l['Work Direct Phone'])}")
        if l["Departments"]:
            nota.append(f"Departamentos: {l['Departments']}")
        if l["Sub Departments"]:
            nota.append(f"Subdepartamentos: {l['Sub Departments']}")
        local = ", ".join(x for x in (l["City"], l["State"]) if x)
        if local:
            nota.append(f"Local: {local}")
        novos.append((conta, {
            "name": f"{l['First Name']} {l['Last Name']}".strip(),
            "parent_id": conta["partner_id"][0],
            "type": "contact",
            "function": l["Title"].strip() or False,
            "email": email or False,
            "phone": telefone(l["Mobile Phone"]),
            "city": l["City"].strip() or False,
            "x_linkedin_url": l["Person Linkedin Url"].strip() or False,
            "x_email_status": status,
            "x_abm_canal_inicial": canal(status),
            "x_abm_li_conexao": "nao_enviado",
            "x_abm_senioridade": senioridade,
            "x_abm_prioridade": prioridade,
            "x_abm_papel": papel,
            "x_abm_area": ar,
            "x_abm_notas": "\n".join(nota),
            "category_id": [TAG_ABM_MONTADORAS],
        }))

    print(f"Export: {len(linhas)} contatos · {len({l['Company Name'] for l in linhas})} empresas")
    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULAÇÃO (nada é gravado)'}\n")
    print("Descartados:", dict(motivos))
    for empresa, c in sorted(fora_por_empresa.items(), key=lambda kv: -sum(kv[1].values())):
        print(f"  {empresa[:40]:40} {dict(c)}")
    print(f"\nNovos contatos para incluir: {len(novos)}")
    for conta, v in sorted(novos, key=lambda x: (x[0]["name"], x[1]["x_abm_prioridade"])):
        print(f"  {conta['name'][:28]:28} P{v['x_abm_prioridade']} {v['x_abm_papel'][:20]:20} "
              f"{v['x_abm_area'][:18]:18} {v['name'][:28]:28} {(v['function'] or '')[:45]} "
              f"[{v['x_email_status'] or 'sem e-mail'}]")

    if not args.aplicar:
        print("\nSimulação concluída. Rode com --aplicar para gravar.")
        return
    if novos:
        criados = odoo.call("res.partner", "create", vals_list=[v for _, v in novos])
        print(f"\nCriados {len(criados)} contatos.")


if __name__ == "__main__":
    main()
