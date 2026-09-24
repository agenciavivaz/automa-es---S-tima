#!/usr/bin/env python3
"""
Alimenta o comitê de compra das contas ABM Sétima (equipe 20) a partir de um
export de contatos do Apollo (CSV).

Como o comitê aparece no Odoo: o campo `x_studio_comite` da oportunidade é
`partner_id.child_ids` — ou seja, os contatos filhos da empresa da
oportunidade. Ampliar o comitê = criar/ligar contatos como filhos da empresa.

Para cada linha do CSV:
  1. Acha a oportunidade ABM Sétima pelo nome da empresa (Company Name).
  2. Procura o contato já existente: e-mail (base inteira), LinkedIn ou nome
     entre os filhos da empresa.
  3. Existe → só preenche campos VAZIOS (nunca sobrescreve) e garante a tag
     "ABM Montadoras". Existe sem empresa → liga à empresa (entra no comitê).
     Existe ligado a outra empresa → não mexe, sai no relatório.
  4. Não existe → cria como filho da empresa, com cargo, e-mail, telefone,
     LinkedIn, senioridade, papel na decisão, área e status do e-mail.

Dry-run é o padrão. Para gravar: APLICAR=true.

    python enriquecer_comite_abm_setima.py export.csv            # simula
    APLICAR=true python enriquecer_comite_abm_setima.py export.csv

Relatório linha a linha em data/odoo/comite_abm_setima_<timestamp>.csv.
"""

import csv
import os
import re
import sys
import unicodedata
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
ODOO_URL = os.environ["ODOO_URL"].rstrip("/").removesuffix("/odoo")
ODOO_DB = os.environ["ODOO_DB"]
ODOO_API_KEY = os.environ["ODOO_API_KEY"]
ODOO_TEAM_ID = int(os.environ.get("ODOO_TEAM_ID_ABM_SETIMA", "20"))    # ABM Setima
TAG_ABM_ID = int(os.environ.get("ODOO_TAG_ABM_MONTADORAS", "17"))      # ABM Montadoras
APLICAR = os.environ.get("APLICAR", "false").lower() == "true"

ORIGEM = f"Apollo export {datetime.now():%Y-%m-%d}"

# ---------------------------------------------------------------------------
# Mapeamentos Apollo → seleções ABM do Odoo
# ---------------------------------------------------------------------------
SENIORIDADE = {
    "c suite": "C suite", "vp": "Vp", "owner": "Owner", "head": "Head",
    "director": "Director", "manager": "Manager", "senior": "Senior",
    "entry": "Entry", "intern": "Intern",
}

# Mesmo critério já usado nos contatos ABM existentes na base.
PAPEL_POR_SENIORIDADE = {
    "C suite": "Decisor", "Vp": "Decisor", "Owner": "Decisor", "Director": "Decisor",
    "Head": "Influenciador-chave", "Manager": "Influenciador",
    "Senior": "Usuário/Técnico", "Entry": "Usuário/Ponto de entrada",
    "Intern": "Usuário/Ponto de entrada",
}

AREA_POR_DEPARTAMENTO = {
    "marketing": "Marketing", "product": "Produto",
    "information technology": "TI/Digital",
    "engineering & technical": "Engenharia/Design", "design": "Engenharia/Design",
    "operations": "Operações", "sales": "Comercial/Vendas",
    "finance": "Financeiro/Controladoria", "human resources": "RH",
    "legal": "Compliance/Jurídico",
}

# Palavras no cargo que vencem o departamento do Apollo (ele não tem "compras").
AREA_POR_CARGO = [
    (re.compile(r"compra|purchas|procurement|sourcing|suprimento", re.I), "Compras/Procurement"),
    (re.compile(r"compliance|jur[ií]dic|legal|auditor", re.I), "Compliance/Jurídico"),
    (re.compile(r"marketing|brand|marca|comunica", re.I), "Marketing"),
]

STATUS_EMAIL = {
    "verified": "Verificado", "extrapolated": "Extrapolado",
    "unavailable": "Indisponível", "valid": "Válido", "probable": "Válido",
    "catch-all": "catch-all", "catch-all@pro": "catch-all", "invalid": "Inválido",
    # "Unverified" fica vazio de propósito: não há opção equivalente honesta.
}


# ---------------------------------------------------------------------------
# Odoo JSON-2
# ---------------------------------------------------------------------------
def odoo(model, method, **params):
    resp = requests.post(
        f"{ODOO_URL}/json/2/{model}/{method}",
        headers={
            "Authorization": f"Bearer {ODOO_API_KEY}",
            "X-Odoo-Database": ODOO_DB,
            "Content-Type": "application/json",
        },
        json=params,
        timeout=120,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"{model}.{method} → HTTP {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------
def chave_nome(nome: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().lower()


def chave_linkedin(url: str) -> str:
    m = re.search(r"linkedin\.com/in/([^/?#]+)", url or "", re.I)
    return m.group(1).lower() if m else ""


def limpar_telefone(raw: str) -> str:
    return (raw or "").strip().lstrip("'").strip()


def area_do_contato(cargo: str, departamentos: str) -> str:
    for padrao, area in AREA_POR_CARGO:
        if padrao.search(cargo or ""):
            return area
    for dep in (departamentos or "").split(","):
        area = AREA_POR_DEPARTAMENTO.get(dep.strip().lower())
        if area:
            return area
    return "Outros"


# ---------------------------------------------------------------------------
# CSV do Apollo
# ---------------------------------------------------------------------------
def ler_apollo(caminho: str) -> list[dict]:
    """Lê o export. O Apollo repete a coluna "Email" (a 2ª costuma vir vazia),
    então a primeira ocorrência de cada cabeçalho é a que vale."""
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        linhas = list(csv.reader(f))
    cab = linhas[0]
    idx = {}
    for i, nome in enumerate(cab):
        idx.setdefault(nome, i)
    return [
        {nome: (linha[i] if i < len(linha) else "") for nome, i in idx.items()}
        for linha in linhas[1:] if any(linha)
    ]


def valores_do_contato(row: dict) -> dict:
    nome = f"{row['First Name']} {row['Last Name']}".strip()
    cargo = row["Title"].strip()
    senioridade = SENIORIDADE.get(row["Seniority"].strip().lower())
    celular = limpar_telefone(row["Mobile Phone"])
    direto = limpar_telefone(row["Work Direct Phone"])

    notas = [f"Origem: {ORIGEM}"]
    if row.get("Apollo Contact Id"):
        notas.append(f"Apollo Contact ID: {row['Apollo Contact Id']}")
    if row["Departments"]:
        notas.append(f"Departamentos: {row['Departments']}")
    if row["Sub Departments"]:
        notas.append(f"Subdepartamentos: {row['Sub Departments']}")
    if celular and direto and celular != direto:
        notas.append(f"Telefone direto: {direto}")
    if row["City"] or row["State"]:
        notas.append(f"Local: {', '.join(p for p in (row['City'], row['State']) if p)}")

    vals = {
        "name": nome,
        "function": cargo,
        "email": row["Email"].strip().lower(),
        "phone": celular or direto,
        "x_linkedin_url": row["Person Linkedin Url"].strip(),
        "x_abm_senioridade": senioridade,
        "x_abm_papel": PAPEL_POR_SENIORIDADE.get(senioridade),
        "x_abm_area": area_do_contato(cargo, row["Departments"]),
        "x_email_status": STATUS_EMAIL.get(row["Email Status"].strip().lower()),
        "x_abm_notas": "\n".join(notas),
        "city": row["City"].strip(),
    }
    return {k: v for k, v in vals.items() if v}


# ---------------------------------------------------------------------------
# Fluxo principal
# ---------------------------------------------------------------------------
CAMPOS_PARTNER = [
    "id", "name", "parent_id", "email", "phone", "function", "category_id",
    "x_linkedin_url", "x_abm_senioridade", "x_abm_papel", "x_abm_area",
    "x_email_status", "x_abm_notas", "city", "active",
]


def main(caminho_csv: str) -> None:
    linhas = ler_apollo(caminho_csv)
    print(f"{len(linhas)} contato(s) no CSV | modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")

    leads = odoo("crm.lead", "search_read",
                 domain=[["team_id", "=", ODOO_TEAM_ID]],
                 fields=["id", "name", "partner_id", "partner_name"])
    empresa_por_nome = {}
    for lead in leads:
        if lead["partner_id"]:
            for nome in (lead["name"], lead["partner_name"], lead["partner_id"][1]):
                if nome:
                    empresa_por_nome[chave_nome(nome)] = (lead["partner_id"][0], lead["name"])
    empresas = sorted({pid for pid, _ in empresa_por_nome.values()})

    filhos = odoo("res.partner", "search_read",
                  domain=[["parent_id", "in", empresas], ["active", "in", [True, False]]],
                  fields=CAMPOS_PARTNER)
    por_nome = {(p["parent_id"][0], chave_nome(p["name"])): p for p in filhos}
    por_linkedin = {chave_linkedin(p["x_linkedin_url"]): p for p in filhos if p["x_linkedin_url"]}

    emails_csv = sorted({r["Email"].strip().lower() for r in linhas if r["Email"].strip()})
    por_email = {}
    for p in odoo("res.partner", "search_read",
                  domain=[["email", "in", emails_csv], ["active", "in", [True, False]]],
                  fields=CAMPOS_PARTNER):
        por_email.setdefault((p["email"] or "").strip().lower(), p)

    relatorio, criar, atualizar = [], [], []
    vistos = set()
    for row in linhas:
        vals = valores_do_contato(row)
        empresa = empresa_por_nome.get(chave_nome(row["Company Name"]))
        linha_rel = {"empresa": row["Company Name"], "contato": vals.get("name", ""),
                     "email": vals.get("email", ""), "acao": "", "partner_id": "", "campos": ""}
        relatorio.append(linha_rel)

        if not empresa:
            linha_rel["acao"] = "ignorado: empresa sem oportunidade ABM Sétima"
            continue
        empresa_id, _ = empresa
        chave_dup = (empresa_id, vals.get("email") or chave_nome(vals.get("name", "")))
        if chave_dup in vistos:
            linha_rel["acao"] = "ignorado: duplicado dentro do CSV"
            continue
        vistos.add(chave_dup)

        existente = (
            por_email.get(vals.get("email", ""))
            or por_linkedin.get(chave_linkedin(vals.get("x_linkedin_url", "")))
            or por_nome.get((empresa_id, chave_nome(vals.get("name", ""))))
        )

        if not existente:
            novo = {**vals, "parent_id": empresa_id, "type": "contact",
                    "category_id": [TAG_ABM_ID], "is_company": False}
            criar.append((novo, linha_rel))
            linha_rel["acao"] = "criar"
            linha_rel["campos"] = ",".join(sorted(vals))
            continue

        linha_rel["partner_id"] = existente["id"]
        pai = existente["parent_id"][0] if existente["parent_id"] else None
        if pai and pai != empresa_id:
            linha_rel["acao"] = f"ignorado: contato já ligado a {existente['parent_id'][1]}"
            continue

        mudancas = {}
        for campo, valor in vals.items():
            if campo == "name":
                continue
            if campo == "x_abm_notas":
                atual = existente.get(campo) or ""
                if "Apollo Contact ID" not in atual:
                    mudancas[campo] = f"{atual}\n{valor}".strip()
            elif not existente.get(campo):
                mudancas[campo] = valor
        if not pai:
            mudancas["parent_id"] = empresa_id
        if TAG_ABM_ID not in (existente.get("category_id") or []):
            mudancas["category_id"] = [(4, TAG_ABM_ID)]

        if mudancas:
            atualizar.append((existente["id"], mudancas, linha_rel))
            linha_rel["acao"] = "completar" if pai else "ligar à empresa + completar"
            linha_rel["campos"] = ",".join(sorted(mudancas))
        else:
            linha_rel["acao"] = "sem alteração (já completo)"

    # ---------------------------------------------------------------- resumo
    resumo = {}
    for r in relatorio:
        acao = r["acao"].split(":")[0]
        resumo[acao] = resumo.get(acao, 0) + 1
    print("Resumo:", resumo)
    por_empresa = {}
    for novo, rel in criar:
        por_empresa[rel["empresa"]] = por_empresa.get(rel["empresa"], 0) + 1
    for empresa, qtd in sorted(por_empresa.items(), key=lambda x: -x[1]):
        print(f"  +{qtd:>3} no comitê de {empresa}")

    # --------------------------------------------------------------- escrita
    if APLICAR:
        for i in range(0, len(criar), 50):
            lote = criar[i:i + 50]
            ids = odoo("res.partner", "create", vals_list=[v for v, _ in lote])
            for pid, (_, rel) in zip(ids, lote):
                rel["partner_id"] = pid
                rel["acao"] = "criado"
        for pid, mudancas, rel in atualizar:
            odoo("res.partner", "write", ids=[pid], vals=mudancas)
            rel["acao"] = rel["acao"].replace("completar", "completado")
        print(f"Gravado: {len(criar)} criado(s), {len(atualizar)} completado(s).")
    else:
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true para gravar.")

    os.makedirs("data/odoo", exist_ok=True)
    saida = f"data/odoo/comite_abm_setima_{datetime.now():%Y%m%d_%H%M%S}.csv"
    with open(saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(relatorio[0]))
        w.writeheader()
        w.writerows(relatorio)
    print(f"Relatório: {saida}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: python enriquecer_comite_abm_setima.py <export_apollo.csv>")
    main(sys.argv[1])
