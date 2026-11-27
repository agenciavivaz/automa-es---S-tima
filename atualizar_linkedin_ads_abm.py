#!/usr/bin/env python3
"""
Relatório de empresas do LinkedIn (CSV do Campaign Manager) → sinais do ABM Sétima.

Uso (a partir da raiz do repositório):

    python atualizar_linkedin_ads_abm.py caminho/companies-export.csv            # simulação
    python atualizar_linkedin_ads_abm.py caminho/companies-export.csv --aplicar  # grava no Odoo

Para cada conta do ABM (crm.team 20, ativa, fora de Descartada/Cliente) o script
soma as páginas do LinkedIn listadas em "Nome no LinkedIn" (x_abm_linkedin_empresa,
separadas por ";") e grava UM sinal "li_ads_relatorio" (snapshot de 30 dias), no
mesmo padrão dos relatórios anteriores:

    Nível LinkedIn  Very Low +0 · Low +5 · Medium +10 · High +20 · Very High +25
                    (o mais alto entre as páginas da conta)
    Interações      engajamentos orgânicos + pagos: 1–9 → +5 · 10–29 → +10 · 30+ → +15
    Exposição       frequência de mídia da conta (x_abm_midia_freq = impressões ÷ público estimado
                    na segmentação da campanha; ver odoo_modules/abm_setima_dashboard/README.md):
                    < 2× → +0 · 2–4× → +5 · ≥ 4× → +10 (acima de 8× é alerta de mídia, não muda o score).
                    Conta ainda sem medição de mídia (x_abm_midia_impressoes vazio) usa a regra
                    antiga até ser medida: impressões PAGAS / pessoas no comitê, com as mesmas faixas.
                    Contas em Engajada ou Em cadência ficam SEMPRE na regra antiga (ESTAGIOS_REGRA_ANTIGA).
    Total           soma dos três, com teto de 30

O snapshot anterior da conta (li_ads_relatorio ativo) é desativado (x_ativo = False),
porque o relatório é uma foto da janela de 30 dias e não um evento acumulável. Contas
que somam 0 ponto não recebem sinal. Em todas as contas ativas, x_abm_exposicao
(impressões por pessoa do comitê) é atualizada; conta fora do relatório fica em 0.

O score, a faixa, o tier e as automações (A2 engaja com 30, A4 avisa com 60, A13
expira o sinal em 30 dias) são do próprio Odoo: este script só grava sinais.
"""

import argparse
import csv
import datetime as dt
import logging
import os
import re
import sys
import unicodedata

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ABM_TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))
ESTAGIOS_FORA = [95, 96]  # Descartada e Cliente – expansão não recebem sinal
# Engajada e Em cadência ficam na regra antiga de exposição (impressões ÷ comitê), mesmo com
# frequência de mídia medida: decisão de 27/11/2026 para não mexer no score de quem já avançou.
ESTAGIOS_REGRA_ANTIGA = [89, 90]
TETO = 30

NIVEL_PONTOS = {"very low": 0, "low": 5, "medium": 10, "high": 20, "very high": 25}
TIPO = "li_ads_relatorio"
ORIGEM = "linkedin_ads"


# ---------------------------------------------------------------------------
# Regras puras (testadas em tests/test_linkedin_ads_abm.py)
# ---------------------------------------------------------------------------

def norm_nome(valor):
    s = unicodedata.normalize("NFKD", valor or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def inteiro(valor):
    v = (valor or "").strip().replace(".", "").replace(",", "")
    return int(v) if v.isdigit() else 0


def ler_csv(caminho):
    """Linhas do export de empresas, com os números já convertidos."""
    with open(caminho, newline="", encoding="utf-8-sig") as f:
        linhas = []
        for r in csv.DictReader(f):
            linhas.append({
                "nome": r["Company name"].strip(),
                "url": r["Company page URL"].strip(),
                "nivel": (r["Engagement level"] or "").strip().lower(),
                "imp_org": inteiro(r["Organic impressions"]),
                "eng_org": inteiro(r["Organic engagements"]),
                "imp_pago": inteiro(r["Paid impressions"]),
                "eng_pago": inteiro(r["Paid engagements"]),
                "cliques": inteiro(r["Paid clicks"]),
                "videos": inteiro(r["Paid video views"]),
            })
    return linhas


def pontos_nivel(nivel):
    return NIVEL_PONTOS.get((nivel or "").lower(), 0)


def pontos_interacoes(n):
    if n >= 30:
        return 15
    if n >= 10:
        return 10
    if n >= 1:
        return 5
    return 0


def pontos_exposicao(razao):
    if razao >= 4:
        return 10
    if razao >= 2:
        return 5
    return 0


def paginas_da_conta(conta):
    """Páginas do LinkedIn da conta: "Nome no LinkedIn" manda; senão, o nome da conta."""
    brutos = (conta.get("x_abm_linkedin_empresa") or "").split(";")
    chaves = [norm_nome(n) for n in brutos if norm_nome(n)] or [norm_nome(conta["name"])]
    return list(dict.fromkeys(chaves))


def agregar(conta, por_nome):
    """Soma as páginas do LinkedIn da conta. Devolve (agregado, páginas usadas)."""
    paginas = []
    for k in paginas_da_conta(conta):
        paginas.extend(por_nome.get(k, []))
    if not paginas:
        return None, []
    agg = {
        "imp": sum(p["imp_pago"] for p in paginas),
        "inter": sum(p["eng_org"] + p["eng_pago"] for p in paginas),
        "videos": sum(p["videos"] for p in paginas),
        "nivel": max((p["nivel"] for p in paginas), key=pontos_nivel),
    }
    return agg, [p["nome"] for p in paginas]


def estagio_id(conta):
    st = (conta or {}).get("stage_id")
    return st[0] if isinstance(st, (list, tuple)) and st else st


def frequencia_midia(conta):
    """Frequência de mídia medida (x_abm_midia_freq) ou None se a conta ainda não foi medida
    ou está em Engajada / Em cadência (essas seguem na regra antiga)."""
    if not conta or not conta.get("x_abm_midia_impressoes"):
        return None
    if estagio_id(conta) in ESTAGIOS_REGRA_ANTIGA:
        return None
    return float(conta.get("x_abm_midia_freq") or 0.0)


def avaliar(agg, comite, freq=None):
    """Pontuação do snapshot.

    freq = frequência de mídia da conta (impressões ÷ público estimado na segmentação). Quando existe,
    é ela que define a exposição. Sem medição, cai na regra antiga: impressões ÷ comitê (mín. 1).
    """
    razao = round(agg["imp"] / max(comite, 1), 1)
    base = "frequencia" if freq is not None else "comite"
    pn, pi = pontos_nivel(agg["nivel"]), pontos_interacoes(agg["inter"])
    pe = pontos_exposicao(freq if freq is not None else razao)
    return {
        "razao": razao, "freq": freq, "base": base, "nivel": pn, "interacoes": pi, "exposicao": pe,
        "total": min(pn + pi + pe, TETO),
    }


def detalhe(agg, av, comite, paginas):
    if av.get("base") == "frequencia":
        exposicao = "Exposição: frequência de mídia %s× (impressões ÷ público estimado na segmentação) (+%d)" % (
            av["freq"], av["exposicao"])
    else:
        exposicao = "Exposição: %d impressões / %d no comitê = %s (+%d)" % (
            agg["imp"], comite, av["razao"], av["exposicao"])
    texto = (
        "Nível LinkedIn: %s (+%d) · Interações: %d (+%d) · %s · Views de vídeo: %d · Total %d (teto %d)"
    ) % (agg["nivel"].title(), av["nivel"], agg["inter"], av["interacoes"], exposicao,
         agg["videos"], av["total"], TETO)
    if len(paginas) > 1:
        texto += " · Páginas somadas: " + ", ".join(paginas)
    return texto


def planejar(contas, linhas, hoje):
    """Decide sinais e exposição por conta. Devolve (itens, páginas do CSV sem conta)."""
    por_nome = {}
    for p in linhas:
        por_nome.setdefault(norm_nome(p["nome"]), []).append(p)
    usadas = set()
    itens = []
    for c in contas:
        comite = c.get("x_abm_comite_total") or 0
        agg, paginas = agregar(c, por_nome)
        usadas.update(norm_nome(n) for n in paginas)
        if not agg:
            itens.append({"conta": c, "agg": None, "av": None, "sinal": None, "exposicao": 0.0, "paginas": []})
            continue
        av = avaliar(agg, comite, frequencia_midia(c))
        sinal = None
        if av["total"] > 0:
            sinal = {
                "x_name": "LinkedIn Ads 30 dias · relatório de %s" % hoje.isoformat(),
                "x_data": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "x_lead_id": c["id"],
                "x_origem": ORIGEM,
                "x_tipo": TIPO,
                "x_pontos_custom": av["total"],
                "x_detalhe": detalhe(agg, av, comite, paginas),
                "x_ativo": True,
            }
        itens.append({"conta": c, "agg": agg, "av": av, "sinal": sinal, "exposicao": av["razao"], "paginas": paginas})
    sem_conta = [p["nome"] for p in linhas if norm_nome(p["nome"]) not in usadas]
    return itens, sem_conta


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv")
    ap.add_argument("--aplicar", action="store_true", help="grava no Odoo (padrão: só simula)")
    args = ap.parse_args()

    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)
    from odoo.client import cliente_operacional

    odoo = cliente_operacional(somente_leitura=not args.aplicar)
    contas = odoo.search_read(
        "crm.lead",
        [["team_id", "=", ABM_TEAM_ID], ["active", "=", True], ["stage_id", "not in", ESTAGIOS_FORA]],
        ["id", "name", "stage_id", "x_abm_linkedin_empresa", "x_abm_comite_total", "x_abm_score", "x_abm_exposicao",
         "x_abm_midia_freq", "x_abm_midia_impressoes"],
    )
    linhas = ler_csv(args.csv)
    itens, sem_conta = planejar(contas, linhas, dt.date.today())

    antigos = odoo.search_read(
        "x_abm_sinal",
        [["x_tipo", "=", TIPO], ["x_ativo", "=", True], ["x_lead_id", "in", [c["id"] for c in contas]]],
        ["id", "x_lead_id"],
    )
    log.info("%d contas ativas · %d páginas no CSV · %d sinal(is) novo(s) · %d snapshot(s) anterior(es) a desativar",
             len(contas), len(linhas), sum(1 for i in itens if i["sinal"]), len(antigos))
    for i in sorted(itens, key=lambda i: -(i["av"] or {"total": -1})["total"]):
        av = i["av"]
        log.info("%-38s %s", i["conta"]["name"],
                 "sem dados no relatório (exposição 0)" if not av else
                 "+%d  (nível %d · interações %d · exposição %d, %s)" % (
                     av["total"], av["nivel"], av["interacoes"], av["exposicao"],
                     "frequência %.1f×" % av["freq"] if av["base"] == "frequencia"
                     else "%.1f impr./pessoa do comitê, regra antiga" % av["razao"]))
    if sem_conta:
        log.info("Páginas do CSV sem conta no ABM (ignoradas): %s", ", ".join(sem_conta))

    if not args.aplicar:
        log.info("SIMULAÇÃO: nada gravado. Use --aplicar para gravar.")
        return
    if antigos:
        odoo.write("x_abm_sinal", [a["id"] for a in antigos], {"x_ativo": False})
    novos = [i["sinal"] for i in itens if i["sinal"]]
    if novos:
        odoo.create("x_abm_sinal", novos)
    for i in itens:
        if (i["conta"].get("x_abm_exposicao") or 0.0) != i["exposicao"]:
            odoo.write("crm.lead", [i["conta"]["id"]], {"x_abm_exposicao": i["exposicao"]})
    log.info("Gravado: %d sinal(is) novos, %d antigos desativados.", len(novos), len(antigos))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha ao atualizar o LinkedIn Ads no ABM")
        sys.exit(1)
