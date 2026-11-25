#!/usr/bin/env python3
"""
LinkedIn Ads: empresa que abriu o formulário do anúncio → sinal no ABM (Odoo).

O LinkedIn não diz QUEM abriu o formulário de Lead Gen, só a EMPRESA (pivot
MEMBER_COMPANY do adAnalytics). Abrir o formulário e não enviar é intenção
alta que hoje se perde: o score só pontua o formulário enviado (formulario,
+60). Este script transforma a abertura em sinal da conta.

Fonte: o cenário do Make "LinkedIn Ads Sétima → formulários abertos por
empresa (semanal)" grava, toda segunda, uma linha por empresa que abriu o
formulário na semana anterior no data store "LinkedIn · formulários abertos
por empresa". Este script lê esse data store pela API do Make (ou um JSON
local com --arquivo), casa cada empresa com uma conta do ABM e grava o sinal.

Contas: ABM Sétima (crm.team 20) e ABM BrandSpot (crm.team 22). Etapas
Descartada e Cliente – expansão ficam fora, como nos demais sinais.

Casamento empresa do LinkedIn → conta (nesta ordem):
1. nome igual ao nome da conta ou a um dos nomes em "ABM · Nome no LinkedIn"
   (x_abm_linkedin_empresa, separados por ";"), sem acento e sem caixa;
2. site da empresa no LinkedIn igual ao domínio da conta (x_abm_dominio ou
   x_abm_dominios_extra) ou subdomínio dele (sp.senac.br → senac.br).
Mais de uma conta possível → não grava e registra no log como ambígua.

Sinal: enquanto o Odoo não tiver um tipo próprio, usa o tipo "outro" com
pontos variáveis (PONTOS_FORMULARIO_ABERTO, padrão 20). A automação A13 expira
o sinal em 30 dias, como os demais.

Deduplicação: um sinal por conta por empresa por semana. A chave
"LinkedIn org <id> · semana até AAAA-MM-DD" vai no detalhe e é conferida antes
de gravar.
"""

import argparse
import datetime as dt
import json
import logging
import os
import re
import sys
import unicodedata

import requests
from dotenv import load_dotenv

from odoo.client import cliente_operacional

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurações
# ---------------------------------------------------------------------------
MAKE_ZONE = os.environ.get("MAKE_ZONE", "us1.make.com").strip()
MAKE_DATASTORE_ID = os.environ.get("MAKE_DATASTORE_ID", "102062").strip()
MAKE_TIMEOUT = 60

TIMES_ABM = [int(t) for t in os.environ.get("ABM_TEAM_IDS", "20,22").split(",") if t.strip()]
# Descartada e Cliente – expansão (ABM Sétima: 95/96; ABM BrandSpot: 98/99).
ESTAGIOS_FORA = [95, 96, 98, 99]

PONTOS = int(os.environ.get("PONTOS_FORMULARIO_ABERTO", "20"))
TIPO = "outro"
JANELA_DIAS = int(os.environ.get("JANELA_DIAS", "30"))  # sinal expira em 30 dias
DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() in ("1", "true", "sim", "yes")

MARCA = "LinkedIn org "
DOMINIOS_GENERICOS = {"linkedin.com", "lnkd.in", "bit.ly", "linktr.ee", "gmail.com", "hotmail.com"}


# ---------------------------------------------------------------------------
# Normalização
# ---------------------------------------------------------------------------

def norm(texto):
    t = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def dominio(url):
    """'https://www.sp.senac.br/x' → 'sp.senac.br'. Vazio se não parecer domínio."""
    d = (url or "").strip().lower()
    d = re.sub(r"^[a-z]+://", "", d)
    d = d.split("/")[0].split("?")[0].split(":")[0]
    d = re.sub(r"^www\d?\.", "", d)
    return d if "." in d and d not in DOMINIOS_GENERICOS else ""


def nomes_da_conta(conta):
    nomes = [conta.get("name") or ""] + (conta.get("x_abm_linkedin_empresa") or "").split(";")
    return {norm(n) for n in nomes if norm(n)}


def dominios_da_conta(conta):
    brutos = [conta.get("x_abm_dominio") or ""] + re.split(r"[;,\s]+", conta.get("x_abm_dominios_extra") or "")
    return {d for d in (dominio(b) for b in brutos if b) if d}


def casar(empresa, contas):
    """(conta, como) ou (None, motivo)."""
    alvo = norm(empresa.get("nome"))
    por_nome = [c for c in contas if alvo and alvo in nomes_da_conta(c)]
    if len(por_nome) == 1:
        return por_nome[0], "nome"
    if len(por_nome) > 1:
        return None, "ambígua por nome: " + ", ".join(c["name"] for c in por_nome)

    site = dominio(empresa.get("site"))
    if not site:
        return None, "sem conta (nome não bate e empresa sem site)"
    por_dom = [c for c in contas
               if any(site == d or site.endswith("." + d) for d in dominios_da_conta(c))]
    if len(por_dom) == 1:
        return por_dom[0], "domínio"
    if len(por_dom) > 1:
        return None, "ambígua por domínio %s: %s" % (site, ", ".join(c["name"] for c in por_dom))
    return None, "sem conta (nome e domínio %s não batem)" % site


# ---------------------------------------------------------------------------
# Regras do sinal
# ---------------------------------------------------------------------------

def org_id(empresa):
    return str(empresa.get("org_urn") or "").rsplit(":", 1)[-1]


def chave(empresa):
    return "%s%s · semana até %s" % (MARCA, org_id(empresa), empresa.get("periodo_fim"))


def montar_sinais(empresas, contas, ja_registrados, desde):
    """Sinais a gravar e empresas que ficaram de fora (com o motivo)."""
    sinais, fora, feitos = [], [], set()
    for e in empresas:
        nome = e.get("nome") or e.get("org_urn") or "?"
        aberturas = int(float(e.get("aberturas") or 0))
        if aberturas <= 0:
            continue
        try:
            fim = dt.date.fromisoformat(str(e.get("periodo_fim")))
        except ValueError:
            fora.append((nome, aberturas, "período inválido: %r" % e.get("periodo_fim")))
            continue
        if fim < desde:
            fora.append((nome, aberturas, "semana até %s: fora da janela de %s dias" % (fim, JANELA_DIAS)))
            continue
        conta, como = casar(e, contas)
        if not conta:
            fora.append((nome, aberturas, como))
            continue
        etapa = conta.get("stage_id")
        if etapa and etapa[0] in ESTAGIOS_FORA:
            fora.append((nome, aberturas, "conta %s em %s: não pontua" % (conta["name"], etapa[1])))
            continue
        if conta.get("active") is False:
            fora.append((nome, aberturas, "conta %s arquivada: não pontua" % conta["name"]))
            continue
        k = chave(e)
        if (conta["id"], k) in ja_registrados or (conta["id"], k) in feitos:
            fora.append((nome, aberturas, "já registrado em %s" % conta["name"]))
            continue
        feitos.add((conta["id"], k))
        envios = int(float(e.get("envios") or 0))
        detalhe = (
            "%s abriu o formulário do anúncio %s vez(es) e enviou %s · semana %s a %s · "
            "impressões %s, cliques %s, engajamentos %s · casado por %s · %s"
        ) % (nome, aberturas, envios, e.get("periodo_inicio"), e.get("periodo_fim"),
             int(float(e.get("impressoes") or 0)), int(float(e.get("cliques") or 0)),
             int(float(e.get("engajamentos") or 0)), como, k)
        sinais.append({
            "lead": conta,
            "empresa": nome,
            "vals": {
                "x_name": "LinkedIn Ads · abriu o formulário (%sx) · semana até %s" % (
                    aberturas, fim.strftime("%d/%m")),
                "x_data": "%s 12:00:00" % fim.isoformat(),
                "x_lead_id": conta["id"],
                "x_origem": "linkedin_ads",
                "x_tipo": TIPO,
                "x_pontos_custom": PONTOS,
                "x_detalhe": detalhe,
                "x_ativo": True,
            },
        })
    return sinais, fora


# ---------------------------------------------------------------------------
# Fonte: data store do Make
# ---------------------------------------------------------------------------

def ler_datastore(token, *, session=None):
    session = session or requests.Session()
    url = "https://%s/api/v2/data-stores/%s/data" % (MAKE_ZONE, MAKE_DATASTORE_ID)
    headers = {"Authorization": "Token %s" % token}
    registros, offset, limite = [], 0, 100
    while True:
        r = session.get(url, headers=headers, timeout=MAKE_TIMEOUT,
                        params={"pg[limit]": limite, "pg[offset]": offset})
        if r.status_code in (401, 403):
            raise SystemExit("Make recusou o token (%s). Confira o secret MAKE_API_TOKEN "
                             "(escopo datastores:read)." % r.status_code)
        r.raise_for_status()
        lote = r.json().get("records") or []
        registros.extend(x.get("data") or {} for x in lote)
        if len(lote) < limite:
            return registros
        offset += limite


def ler_arquivo(caminho):
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)
    if isinstance(dados, dict):
        dados = dados.get("records") or []
    return [x.get("data", x) for x in dados]


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def carregar_contas(odoo):
    # Inclui as etapas fora do score só para o log dizer "conta em expansão"
    # em vez de "sem conta"; montar_sinais não grava nelas.
    return odoo.search_read(
        "crm.lead",
        [["team_id", "in", TIMES_ABM], ["active", "in", [True, False]]],
        ["id", "name", "team_id", "stage_id", "active", "x_abm_linkedin_empresa", "x_abm_dominio",
         "x_abm_dominios_extra"],
    )


def ja_registrados(odoo, lead_ids, desde):
    sinais = odoo.search_read(
        "x_abm_sinal",
        [["x_lead_id", "in", lead_ids], ["x_origem", "=", "linkedin_ads"], ["x_tipo", "=", TIPO],
         ["x_data", ">=", "%s 00:00:00" % desde.isoformat()]],
        ["x_lead_id", "x_detalhe"],
    )
    feitos = set()
    for s in sinais:
        m = re.search(re.escape(MARCA) + r"\d+ · semana até \d{4}-\d{2}-\d{2}", s.get("x_detalhe") or "")
        if m and s.get("x_lead_id"):
            feitos.add((s["x_lead_id"][0], m.group(0)))
    return feitos


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--arquivo", help="JSON com os registros (em vez do data store do Make)")
    args = parser.parse_args()

    if args.arquivo:
        empresas = ler_arquivo(args.arquivo)
    else:
        token = os.environ.get("MAKE_API_TOKEN", "").strip()
        if not token:
            raise SystemExit("MAKE_API_TOKEN não definida (ou use --arquivo).")
        empresas = ler_datastore(token)
    log.info("%s registro(s) de formulário aberto lidos%s", len(empresas), " — DRY_RUN" if DRY_RUN else "")

    # O secret às vezes vem com o caminho da interface (/odoo); a API fica na raiz.
    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)
    odoo = cliente_operacional(somente_leitura=DRY_RUN)
    contas = carregar_contas(odoo)
    log.info("%s contas do ABM nas equipes %s", len(contas), TIMES_ABM)

    desde = dt.date.today() - dt.timedelta(days=JANELA_DIAS)
    ja = ja_registrados(odoo, [c["id"] for c in contas], desde - dt.timedelta(days=7))
    sinais, fora = montar_sinais(empresas, contas, ja, desde)

    for nome, aberturas, motivo in fora:
        log.info("Fora: %s (%s abertura(s)) — %s", nome, aberturas, motivo)
    for s in sinais:
        log.info("Sinal +%s → %s: %s", PONTOS, s["lead"]["name"], s["vals"]["x_detalhe"])

    if DRY_RUN:
        log.info("DRY_RUN: nada gravado (%s sinal(is)).", len(sinais))
        return
    if sinais:
        odoo.create("x_abm_sinal", [s["vals"] for s in sinais])
    log.info("Gravados %s sinal(is).", len(sinais))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha na sincronização LinkedIn (formulários abertos) → Odoo")
        sys.exit(1)
