#!/usr/bin/env python3
"""
Relatório de empresas do LinkedIn Ads → foto semanal no leadscore do ABM Sétima.

Entrada: o CSV "companies-export_<conta>_<data>.csv" do Campaign Manager
(Plan → Audiences → Companies, janela de 30 dias). Uma linha por empresa, com
nível de engajamento, impressões, engajamentos e views de vídeo.

Para cada conta do ABM (crm.team 20, fora Descartada e Cliente – expansão):

- soma as linhas do relatório que batem com a conta (link da página da empresa
  ou um dos nomes em "ABM · Nome no LinkedIn"; o nome da conta só se a lista
  estiver vazia);
- calcula os pontos com a régua do programa, teto de 30:
    nível LinkedIn    Very Low 0 · Low 5 · Medium 10 · High 20 · Very High 25
    interações        0 → 0 · 1–9 → 5 · 10–29 → 10 · 30+ → 15
                      (engajamentos pagos + orgânicos)
    exposição         impressões pagas ÷ pessoas do comitê:
                      < 2 → 0 · 2 a 3,9 → 5 · 4+ → 10
- grava a exposição em x_abm_exposicao (0 se a conta não aparece);
- a foto substitui a anterior: os sinais li_ads_relatorio ativos da conta são
  desativados e, se a conta pontuou, entra um sinal novo com os pontos.

Tudo o que muda numa conta vai numa única escrita no crm.lead (comandos no
x_abm_sinal_ids + exposição). Assim o score é recalculado uma vez, do valor
antigo direto para o novo, e as automações por faixa não disparam por um
estado intermediário (ex.: 30 → 0 → 30 recriaria "Iniciar cadência").

O score, a faixa e as automações (A2, A4, A17, A18, A20…) são do próprio Odoo:
este script só grava a foto. Rodar de novo com o mesmo relatório não duplica:
se a conta já tem um sinal ativo com o mesmo título, ela é pulada.

Uso:
    DRY_RUN=true  python importar_linkedin_ads_abm.py companies-export_….csv
    DRY_RUN=false python importar_linkedin_ads_abm.py companies-export_….csv
A data da foto sai do nome do arquivo (AAAA-MM-DD) ou de --data AAAA-MM-DD.
"""

import argparse
import csv
import datetime as dt
import logging
import os
import re
import sys
import unicodedata
from collections import defaultdict

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
ABM_TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))
# Descartada e Cliente – expansão não recebem sinal.
ESTAGIOS_FORA = [95, 96]

DRY_RUN = os.environ.get("DRY_RUN", "true").strip().lower() in ("1", "true", "sim", "yes")

TIPO = "li_ads_relatorio"
TITULO = "LinkedIn Ads 30 dias · relatório de %s"
TETO = 30

PONTOS_NIVEL = {"very low": 0, "low": 5, "medium": 10, "high": 20, "very high": 25}
ORDEM_NIVEL = ["very low", "low", "medium", "high", "very high"]


# ---------------------------------------------------------------------------
# Regras (puras, testadas em tests/test_linkedin_ads.py)
# ---------------------------------------------------------------------------

def normalizar_nome(valor):
    v = unicodedata.normalize("NFKD", valor or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", v).strip()


def slug_linkedin(url):
    """https://www.linkedin.com/company/john-deere/ → john-deere"""
    m = re.search(r"linkedin\.com/company/([^/?#\s]+)", (url or "").strip().lower())
    return m.group(1) if m else None


def numero(valor):
    v = (valor or "").strip().replace(".", "").replace(",", ".")
    try:
        return int(float(v))
    except ValueError:
        return 0


def ler_relatorio(caminho):
    """Linhas do CSV do LinkedIn, já com números inteiros."""
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = []
        for r in csv.DictReader(f):
            linhas.append({
                "nome": (r.get("Company name") or "").strip(),
                "slug": slug_linkedin(r.get("Company page URL")),
                "nivel": (r.get("Engagement level") or "").strip(),
                "impressoes": numero(r.get("Paid impressions")),
                "interacoes": numero(r.get("Paid engagements")) + numero(r.get("Organic engagements")),
                "videos": numero(r.get("Paid video views")),
            })
        return linhas


def pontos_nivel(nivel):
    return PONTOS_NIVEL.get((nivel or "").strip().lower(), 0)


def pontos_interacoes(n):
    if n >= 30:
        return 15
    if n >= 10:
        return 10
    if n >= 1:
        return 5
    return 0


def pontos_exposicao(exposicao):
    if exposicao >= 4:
        return 10
    if exposicao >= 2:
        return 5
    return 0


def chaves_da_conta(conta):
    """Link da página + nomes no LinkedIn. O nome da conta só entra se a lista
    "ABM · Nome no LinkedIn" estiver vazia: ela é curada e evita casar a página
    global (ex.: "IVECO") com a conta brasileira ("IVECO Brasil")."""
    slug = slug_linkedin(conta.get("x_abm_link_linkedin"))
    nomes = [n for n in (conta.get("x_abm_linkedin_empresa") or "").split(";") if n.strip()]
    if not nomes:
        nomes = [conta.get("name") or ""]
    return slug, {normalizar_nome(n) for n in nomes if normalizar_nome(n)}


def casar(contas, linhas):
    """conta_id → linhas do relatório. Cada linha vai para uma conta só.

    Primeiro pelo link da página da empresa; depois pelo nome. Se o nome bater
    com mais de uma conta, fica com a de maior comitê.
    """
    por_slug, por_nome = {}, defaultdict(list)
    for c in contas:
        slug, nomes = chaves_da_conta(c)
        if slug:
            por_slug.setdefault(slug, c)
        for n in nomes:
            por_nome[n].append(c)
    for lista in por_nome.values():
        lista.sort(key=lambda c: (-(c.get("x_abm_comite_total") or 0), c.get("name") or ""))

    casadas = defaultdict(list)
    for linha in linhas:
        conta = por_slug.get(linha["slug"]) if linha["slug"] else None
        if not conta:
            candidatas = por_nome.get(normalizar_nome(linha["nome"]))
            conta = candidatas[0] if candidatas else None
        if conta:
            casadas[conta["id"]].append(linha)
    return casadas


def foto_da_conta(conta, linhas):
    """Soma as linhas da conta e calcula pontos, exposição e o detalhe do sinal."""
    impressoes = sum(l["impressoes"] for l in linhas)
    interacoes = sum(l["interacoes"] for l in linhas)
    videos = sum(l["videos"] for l in linhas)
    niveis = [l["nivel"].lower() for l in linhas if l["nivel"].lower() in ORDEM_NIVEL]
    nivel = max(niveis, key=ORDEM_NIVEL.index) if niveis else "very low"
    nivel_label = nivel.title()
    comite = conta.get("x_abm_comite_total") or 0
    exposicao = round(impressoes / comite, 1) if comite else 0.0
    pn, pi, pe = pontos_nivel(nivel), pontos_interacoes(interacoes), pontos_exposicao(exposicao)
    total = min(TETO, pn + pi + pe)
    detalhe = (
        "Nível LinkedIn: %s (+%s) · Interações: %s (+%s) · "
        "Exposição: %s impressões / %s no comitê = %s (+%s) · Views de vídeo: %s · Total %s (teto %s)"
        % (nivel_label, pn, interacoes, pi, impressoes, comite, exposicao, pe, videos, total, TETO)
    )
    if len(linhas) > 1:
        detalhe += " · Páginas somadas: " + ", ".join(l["nome"] for l in linhas)
    return {"pontos": total, "exposicao": exposicao, "detalhe": detalhe}


def planejar(contas, linhas, ativos, data_foto, agora):
    """Decide o que gravar, uma entrada por conta.

    ativos: lead_id → [{"id", "x_name"}] dos sinais li_ads_relatorio ativos.
    Devolve (planos, puladas, sem_conta). Cada plano: conta, pontos, exposição,
    detalhe, ids a desativar e os valores do sinal novo (None se 0 pontos).
    """
    titulo = TITULO % data_foto.isoformat()
    casadas = casar(contas, linhas)
    planos, puladas = [], []
    for conta in contas:
        anteriores = ativos.get(conta["id"], [])
        if any(s["x_name"] == titulo for s in anteriores):
            puladas.append((conta["name"], "foto desta data já gravada"))
            continue
        foto = foto_da_conta(conta, casadas.get(conta["id"], []))
        novo = None
        if foto["pontos"] > 0:
            novo = {
                "x_name": titulo,
                "x_data": agora.strftime("%Y-%m-%d %H:%M:%S"),
                "x_origem": "linkedin_ads",
                "x_tipo": TIPO,
                "x_pontos_custom": foto["pontos"],
                "x_detalhe": foto["detalhe"],
                "x_ativo": True,
            }
        planos.append({**foto, "conta": conta, "desativar": [s["id"] for s in anteriores], "novo": novo})
    usados = {id(l) for ls in casadas.values() for l in ls}
    sem_conta = [l for l in linhas if id(l) not in usados]
    return planos, puladas, sem_conta


def valores_da_conta(plano):
    """Uma escrita no crm.lead: desativa a foto antiga, cria a nova, grava a exposição."""
    comandos = [[1, sid, {"x_ativo": False}] for sid in plano["desativar"]]
    if plano["novo"]:
        comandos.append([0, 0, plano["novo"]])
    vals = {"x_abm_exposicao": plano["exposicao"]}
    if comandos:
        vals["x_abm_sinal_ids"] = comandos
    return vals


def data_do_arquivo(caminho):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(caminho))
    return dt.date.fromisoformat(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def carregar_contas(odoo):
    return odoo.search_read(
        "crm.lead",
        [["team_id", "=", ABM_TEAM_ID], ["stage_id", "not in", ESTAGIOS_FORA]],
        ["id", "name", "x_abm_link_linkedin", "x_abm_linkedin_empresa", "x_abm_comite_total"],
    )


def sinais_ativos(odoo, lead_ids):
    sinais = odoo.search_read(
        "x_abm_sinal",
        [["x_lead_id", "in", lead_ids], ["x_tipo", "=", TIPO], ["x_ativo", "=", True]],
        ["id", "x_lead_id", "x_name"],
    )
    por_conta = defaultdict(list)
    for s in sinais:
        por_conta[s["x_lead_id"][0]].append(s)
    return por_conta


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", help="companies-export_….csv do Campaign Manager")
    ap.add_argument("--data", help="data da foto (AAAA-MM-DD); padrão: a do nome do arquivo")
    args = ap.parse_args()
    data_foto = dt.date.fromisoformat(args.data) if args.data else data_do_arquivo(args.csv)
    if not data_foto:
        raise SystemExit("Não achei a data no nome do arquivo; informe --data AAAA-MM-DD.")

    # O secret às vezes vem com o caminho da interface (/odoo); a API fica na raiz.
    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)

    linhas = ler_relatorio(args.csv)
    odoo = cliente_operacional(somente_leitura=DRY_RUN)
    contas = carregar_contas(odoo)
    ativos = sinais_ativos(odoo, [c["id"] for c in contas])
    agora = dt.datetime.now(dt.timezone.utc)
    planos, puladas, sem_conta = planejar(contas, linhas, ativos, data_foto, agora)

    log.info("Relatório de %s: %s empresa(s); %s conta(s) do ABM%s",
             data_foto.isoformat(), len(linhas), len(contas), " — DRY_RUN" if DRY_RUN else "")
    for nome, motivo in puladas:
        log.info("Pulada: %s — %s", nome, motivo)
    for p in sorted(planos, key=lambda p: (-p["pontos"], p["conta"]["name"])):
        if p["novo"]:
            log.info("+%s → %s: %s", p["pontos"], p["conta"]["name"], p["detalhe"])
    zeradas = sorted(p["conta"]["name"] for p in planos if not p["novo"])
    if zeradas:
        log.info("Sem pontos de Ads nesta foto (%s): %s", len(zeradas), ", ".join(zeradas))
    log.info("%s empresa(s) do relatório fora do ABM (maiores: %s)", len(sem_conta),
             ", ".join(l["nome"] for l in sorted(sem_conta, key=lambda l: -l["impressoes"])[:5]))

    novos = sum(1 for p in planos if p["novo"])
    desativados = sum(len(p["desativar"]) for p in planos)
    if DRY_RUN:
        log.info("DRY_RUN: nada gravado (%s sinal(is) novo(s), %s a desativar, exposição de %s conta(s)).",
                 novos, desativados, len(planos))
        return
    for p in planos:
        odoo.write("crm.lead", [p["conta"]["id"]], valores_da_conta(p))
    log.info("Gravados %s sinal(is), %s desativado(s), exposição de %s conta(s).",
             novos, desativados, len(planos))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha ao importar o relatório do LinkedIn Ads")
        sys.exit(1)
