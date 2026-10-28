#!/usr/bin/env python3
"""
Visitas ao site (Apollo) → sinais das contas do ABM Sétima no Odoo.

Roda uma vez por dia. Uma consulta à busca de empresas do Apollo cruza os
domínios das contas do ABM (crm.team 20) com as visitas ao site rastreado
(setima.cc) e, para cada conta que visitou, grava um sinal em x_abm_sinal:

- "Visita ao site (Apollo)"           (visita_dominio, +10)
- "Visitou cases, lead magnet ou contato" (visita_alta_intencao, +15) quando
  alguma página vista é de alta intenção ou o Apollo marca intenção alta.

O score, a faixa e as automações (A20 tira de Alvo, A2 engaja com 30, A4
avisa com 60, A13 expira o sinal em 30 dias) são do próprio Odoo: este script
só grava o sinal.

Deduplicação: um sinal por conta por data de última visita. A data vai no
detalhe do sinal ("Última visita: AAAA-MM-DD") e é conferida antes de gravar.

Domínio compartilhado (ex.: stellantis.com em Stellantis, Jeep, Ram e
Leapmotor): o sinal vai para a conta com o domínio como principal e o maior
comitê; as demais recebem só uma nota no chatter.

Custo: 1 crédito do Apollo por página de resultado não vazia (0 se ninguém do
ABM visitou). A chave vai no header X-Api-Key, nunca na URL.
"""

import datetime as dt
import logging
import os
import re
import sys

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
APOLLO_URL = "https://api.apollo.io/api/v1/mixed_companies/search"
APOLLO_DOMINIO_RASTREADO = os.environ.get("APOLLO_DOMINIO_RASTREADO", "setima.cc").strip()
# Janela de busca: o Apollo só aceita 1, 7, 15, 30, 60 ou 90. Com 7 dias, um
# dia sem execução não perde visita; a dedup evita sinal repetido.
APOLLO_JANELA_DIAS = int(os.environ.get("APOLLO_JANELA_DIAS", "7"))
APOLLO_TIMEOUT = 60

ABM_TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))
# Descartada e Cliente – expansão não recebem sinal.
ESTAGIOS_FORA = [95, 96]

DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() in ("1", "true", "sim", "yes")

# Trechos de caminho que indicam alta intenção (cases, contato, obrigado do formulário).
PAGINAS_ALTA_INTENCAO = ("/case", "/contato", "/contact", "/obrigado", "/thank", "/orcamento", "/proposta")

# Domínios que nunca identificam uma conta (e-mail pessoal etc.).
DOMINIOS_GENERICOS = {"gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com"}

TIPO_VISITA = "visita_dominio"
TIPO_ALTA = "visita_alta_intencao"
MARCA_DATA = "Última visita: "


# ---------------------------------------------------------------------------
# Regras (puras, testadas em tests/test_apollo_visitas.py)
# ---------------------------------------------------------------------------

def normalizar_dominio(valor):
    v = (valor or "").strip().lower()
    v = re.sub(r"^https?://", "", v)
    v = re.sub(r"^www\.", "", v)
    return v.split("/")[0]


def dominios_da_conta(conta):
    """Domínio principal + extras (separados por vírgula, ponto e vírgula ou espaço)."""
    brutos = [conta.get("x_abm_dominio") or ""] + re.split(r"[;,\s]+", conta.get("x_abm_dominios_extra") or "")
    vistos = []
    for b in brutos:
        d = normalizar_dominio(b)
        if d and d not in DOMINIOS_GENERICOS and d not in vistos:
            vistos.append(d)
    return vistos


def mapa_dominios(contas):
    """domínio → [contas], com a dona do domínio em primeiro.

    Dona = quem tem o domínio como principal; empate pelo maior comitê.
    """
    mapa = {}
    for c in contas:
        for d in dominios_da_conta(c):
            mapa.setdefault(d, []).append(c)
    for d, lista in mapa.items():
        lista.sort(key=lambda c: (
            0 if normalizar_dominio(c.get("x_abm_dominio")) == d else 1,
            -(c.get("x_abm_comite_total") or 0),
            c.get("name") or "",
        ))
    return mapa


def agregado_do_site(empresa, dominio_rastreado):
    """Bloco de visitas da empresa ao nosso site, ou None."""
    sinal = empresa.get("intent_signal_account") or {}
    for agg in sinal.get("domain_aggregates") or []:
        if normalizar_dominio(agg.get("domain")) == dominio_rastreado:
            return agg
    return None


def data_visita(valor):
    """O Apollo manda a data como inteiro AAAAMMDD."""
    s = str(valor or "")
    if not re.fullmatch(r"\d{8}", s):
        return None
    return dt.date(int(s[:4]), int(s[4:6]), int(s[6:]))


def classificar(agg):
    """Tipo do sinal e páginas de alta intenção vistas."""
    caminhos = [p.get("_id") or "" for p in agg.get("top_5_paths") or []]
    altas = [p for p in caminhos if any(t in p.lower() for t in PAGINAS_ALTA_INTENCAO)]
    if altas or (agg.get("intent") or "").lower() == "high":
        return TIPO_ALTA, altas
    return TIPO_VISITA, altas


def detalhe(agg, ultima, altas):
    caminhos = ", ".join(
        "%s (%s)" % (p.get("_id"), p.get("total_visits")) for p in agg.get("top_5_paths") or []
    ) or "-"
    partes = [
        MARCA_DATA + ultima.isoformat(),
        "Visitas: %s · Pessoas diferentes: %s" % (agg.get("total_visits"), agg.get("unique_visitors")),
        "Intenção Apollo: %s (%s)" % (agg.get("intent") or "-", agg.get("intent_score") or "-"),
        "Páginas: " + caminhos,
    ]
    if altas:
        partes.append("Alta intenção: " + ", ".join(altas))
    return " · ".join(partes)


def dominio_da_empresa(empresa):
    return normalizar_dominio(empresa.get("primary_domain") or empresa.get("domain") or empresa.get("website_url"))


def montar_sinais(empresas, mapa, dominio_rastreado, ja_registrados, janela_ini):
    """Decide o que gravar. Devolve (sinais, notas, ignoradas).

    ja_registrados: {(lead_id, 'AAAA-MM-DD')} de sinais de visita já gravados.
    """
    sinais, notas, ignoradas = [], [], []
    feitos = set()
    for emp in empresas:
        nome = emp.get("name") or "?"
        dom = dominio_da_empresa(emp)
        contas = mapa.get(dom)
        if not contas:
            ignoradas.append((nome, dom, "domínio fora do ABM"))
            continue
        agg = agregado_do_site(emp, dominio_rastreado)
        if not agg:
            ignoradas.append((nome, dom, "sem visitas ao site rastreado"))
            continue
        ultima = data_visita(agg.get("last_visit"))
        if not ultima or ultima < janela_ini:
            ignoradas.append((nome, dom, "última visita fora da janela"))
            continue
        dona = contas[0]
        chave = (dona["id"], ultima.isoformat())
        if chave in ja_registrados or chave in feitos:
            ignoradas.append((nome, dom, "já registrado"))
            continue
        feitos.add(chave)
        tipo, altas = classificar(agg)
        texto = detalhe(agg, ultima, altas)
        sinais.append({
            "lead": dona,
            "empresa": nome,
            "vals": {
                "x_name": "Apollo · visita ao %s em %s" % (dominio_rastreado, ultima.strftime("%d/%m")),
                "x_data": "%s 12:00:00" % ultima.isoformat(),
                "x_lead_id": dona["id"],
                "x_origem": "site",
                "x_tipo": tipo,
                "x_detalhe": texto,
                "x_ativo": True,
            },
        })
        for outra in contas[1:]:
            notas.append((outra, "Visita de <b>%s</b> (domínio %s, compartilhado) ao %s em %s, "
                                 "registrada como sinal em <b>%s</b>. %s" % (
                                     nome, dom, dominio_rastreado, ultima.strftime("%d/%m"),
                                     dona["name"], texto)))
    return sinais, notas, ignoradas


# ---------------------------------------------------------------------------
# Apollo
# ---------------------------------------------------------------------------

def buscar_visitantes(chave, dominios, *, session=None):
    """Todas as páginas da busca de empresas filtrada por visitas ao site."""
    session = session or requests.Session()
    headers = {"X-Api-Key": chave, "Content-Type": "application/json", "Cache-Control": "no-cache"}
    empresas, pagina = [], 1
    while True:
        corpo = {
            "q_organization_domains_list": dominios,
            "website_visitors_from_domains": [APOLLO_DOMINIO_RASTREADO],
            "website_visitors_from_past": APOLLO_JANELA_DIAS,
            "page": pagina,
            "per_page": 100,
        }
        r = session.post(APOLLO_URL, json=corpo, headers=headers, timeout=APOLLO_TIMEOUT)
        if r.status_code == 401:
            raise SystemExit("Apollo recusou a chave (401). Confira o secret APOLLO_API_KEY.")
        if r.status_code == 403:
            raise SystemExit("Apollo negou acesso (403): a busca de empresas exige chave mestre.")
        r.raise_for_status()
        dados = r.json()
        # Trava: se a API ignorar o filtro de visitantes, a busca devolveria as
        # contas do ABM como se todas tivessem visitado. Nesse caso, aborta.
        filtros = {b.get("signal_field_name") for b in dados.get("breadcrumbs") or []}
        if "website_visitors_from_domains" not in filtros:
            raise SystemExit("A API do Apollo não aplicou o filtro de visitantes do site; nada foi gravado.")
        lote = (dados.get("accounts") or []) + (dados.get("organizations") or [])
        empresas.extend(lote)
        total_paginas = (dados.get("pagination") or {}).get("total_pages") or 0
        if pagina >= total_paginas or not lote:
            return empresas
        pagina += 1


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def carregar_contas(odoo):
    return odoo.search_read(
        "crm.lead",
        [["team_id", "=", ABM_TEAM_ID], ["stage_id", "not in", ESTAGIOS_FORA]],
        ["id", "name", "x_abm_dominio", "x_abm_dominios_extra", "x_abm_comite_total"],
    )


def visitas_registradas(odoo, lead_ids, desde):
    sinais = odoo.search_read(
        "x_abm_sinal",
        [["x_lead_id", "in", lead_ids], ["x_tipo", "in", [TIPO_VISITA, TIPO_ALTA]],
         ["x_data", ">=", "%s 00:00:00" % desde.isoformat()]],
        ["x_lead_id", "x_detalhe"],
    )
    feitos = set()
    for s in sinais:
        m = re.search(re.escape(MARCA_DATA) + r"(\d{4}-\d{2}-\d{2})", s.get("x_detalhe") or "")
        if m and s.get("x_lead_id"):
            feitos.add((s["x_lead_id"][0], m.group(1)))
    return feitos


def nota(odoo, lead_id, corpo):
    odoo.call("crm.lead", "message_post", {
        "ids": [lead_id], "body": corpo,
        "message_type": "comment", "subtype_xmlid": "mail.mt_note",
    })


def main():
    chave = os.environ.get("APOLLO_API_KEY", "").strip()
    if not chave:
        raise SystemExit("APOLLO_API_KEY não definida.")
    # O secret às vezes vem com o caminho da interface (/odoo); a API fica na raiz.
    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)

    odoo = cliente_operacional(somente_leitura=DRY_RUN)
    contas = carregar_contas(odoo)
    mapa = mapa_dominios(contas)
    log.info("%s contas do ABM, %s domínios monitorados (%s dia(s) em %s)%s",
             len(contas), len(mapa), APOLLO_JANELA_DIAS, APOLLO_DOMINIO_RASTREADO,
             " — DRY_RUN" if DRY_RUN else "")
    sem_dominio = [c["name"] for c in contas if not dominios_da_conta(c)]
    if sem_dominio:
        log.warning("Contas sem domínio (fora do monitoramento): %s", ", ".join(sem_dominio))

    empresas = buscar_visitantes(chave, sorted(mapa))
    log.info("Apollo: %s empresa(s) com visita na janela", len(empresas))

    janela_ini = dt.date.today() - dt.timedelta(days=APOLLO_JANELA_DIAS)
    ja = visitas_registradas(odoo, [c["id"] for c in contas], janela_ini - dt.timedelta(days=1))
    sinais, notas, ignoradas = montar_sinais(empresas, mapa, APOLLO_DOMINIO_RASTREADO, ja, janela_ini)

    for nome, dom, motivo in ignoradas:
        log.info("Ignorada: %s (%s) — %s", nome, dom, motivo)
    for s in sinais:
        log.info("Sinal %s → %s: %s", s["vals"]["x_tipo"], s["lead"]["name"], s["vals"]["x_detalhe"])
    for conta, _ in notas:
        log.info("Nota de domínio compartilhado → %s", conta["name"])

    if DRY_RUN:
        log.info("DRY_RUN: nada gravado (%s sinal(is), %s nota(s)).", len(sinais), len(notas))
        return
    if sinais:
        odoo.create("x_abm_sinal", [s["vals"] for s in sinais])
    for conta, corpo in notas:
        nota(odoo, conta["id"], corpo)
    log.info("Gravados %s sinal(is) e %s nota(s).", len(sinais), len(notas))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha na sincronização Apollo → Odoo")
        sys.exit(1)
