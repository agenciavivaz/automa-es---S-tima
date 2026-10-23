#!/usr/bin/env python3
"""
Atualiza o pipeline ABM Sétima (crm.team 20) com o export de empresas do LinkedIn Ads.

Entrada: CSV "companies-export_<conta>_<data>.csv" (Campaign Manager → Contas /
Company engagement, janela de 30 dias). Cada relatório é uma FOTO do engajamento
da conta, então substitui o anterior:

  1. grava `x_abm_exposicao` = impressões pagas ÷ pessoas no comitê (mín. 10);
  2. desativa os sinais `li_ads_relatorio` ainda ativos da conta;
  3. cria um sinal novo `li_ads_relatorio` (origem linkedin_ads) quando a conta
     pontua. O score da conta é recalculado pelo próprio Odoo.

Pontuação (teto 30):
  Nível LinkedIn   Very Low 0 · Low 5 · Medium 10 · High 20 · Very High 25
  Interações       (engajamentos pagos + orgânicos) 0 → 0 · 1–9 → 5 · 10–29 → 10 · 30+ → 15
  Exposição        < 2 → 0 · 2 a < 4 → 5 · ≥ 4 → 10

Casamento: coluna "Company name" contra `x_abm_linkedin_empresa` (ou o nome da
conta). Só contas ativas da equipe ABM entram; o resto é listado no relatório.

Dry-run é o padrão. Use --apply para gravar.

    python atualizar_abm_linkedin_setima.py companies-export.csv
    python atualizar_abm_linkedin_setima.py companies-export.csv --data 2026-10-23 --apply
"""

import argparse
import csv
import datetime
import os
import sys

from dotenv import load_dotenv

from odoo.client import cliente_operacional

load_dotenv()

TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))
SINAL = "x_abm_sinal"
TIPO = "li_ads_relatorio"
TETO = 30
COMITE_MINIMO = 10

PONTOS_NIVEL = {"very low": 0, "low": 5, "medium": 10, "high": 20, "very high": 25}


def pontos_interacoes(n):
    if n >= 30:
        return 15
    if n >= 10:
        return 10
    if n >= 1:
        return 5
    return 0


def pontos_exposicao(e):
    if e >= 4:
        return 10
    if e >= 2:
        return 5
    return 0


def inteiro(valor):
    valor = (valor or "").strip()
    return int(float(valor)) if valor else 0


def normalizar(nome):
    return " ".join((nome or "").casefold().split())


def ler_export(caminho):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        linhas = list(csv.DictReader(f))
    if not linhas or "Company name" not in linhas[0]:
        sys.exit(f"{caminho} não parece um export de empresas do LinkedIn Ads (falta 'Company name').")
    return linhas


def calcular(linha, comite):
    nivel = (linha.get("Engagement level") or "Very Low").strip()
    impressoes = inteiro(linha.get("Paid impressions"))
    interacoes = inteiro(linha.get("Paid engagements")) + inteiro(linha.get("Organic engagements"))
    videos = inteiro(linha.get("Paid video views"))
    exposicao = round(impressoes / max(comite, COMITE_MINIMO), 1)

    p_nivel = PONTOS_NIVEL.get(nivel.casefold(), 0)
    p_inter = pontos_interacoes(interacoes)
    p_expo = pontos_exposicao(exposicao)
    total = min(p_nivel + p_inter + p_expo, TETO)

    detalhe = (
        f"Nível LinkedIn: {nivel} (+{p_nivel}) · Interações: {interacoes} (+{p_inter}) · "
        f"Exposição: {impressoes} impressões / {comite} no comitê = {exposicao:.1f} (+{p_expo}) · "
        f"Views de vídeo: {videos} · Total {total} (teto {TETO})"
    )
    return {"exposicao": exposicao, "pontos": total, "detalhe": detalhe}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("export", help="CSV companies-export do LinkedIn Ads")
    parser.add_argument("--data", default=datetime.date.today().isoformat(),
                        help="data do relatório (AAAA-MM-DD), vai no nome do sinal")
    parser.add_argument("--apply", action="store_true", help="grava no Odoo (sem isso é dry-run)")
    args = parser.parse_args()

    # O JSON-2 fica em <base>/json/2; uma URL copiada do navegador vem com /odoo no fim.
    url = os.environ.get("ODOO_URL", "").rstrip("/")
    if url.endswith("/odoo"):
        os.environ["ODOO_URL"] = url[: -len("/odoo")]

    linhas = ler_export(args.export)
    client = cliente_operacional(somente_leitura=not args.apply)

    contas = client.search_read_all(
        "crm.lead", [("team_id", "=", TEAM_ID)],
        ["name", "x_abm_linkedin_empresa", "x_abm_comite_total", "x_abm_exposicao", "x_abm_score"],
    )
    por_nome = {}
    for conta in contas:
        for chave in (conta.get("x_abm_linkedin_empresa"), conta["name"]):
            if chave:
                por_nome.setdefault(normalizar(chave), conta)

    nome_sinal = f"LinkedIn Ads 30 dias · relatório de {args.data}"
    ja_rodou = client.search_count(SINAL, [("x_tipo", "=", TIPO), ("x_name", "=", nome_sinal)],
                                   context={"active_test": False})
    if ja_rodou:
        sys.exit(f"Já existem {ja_rodou} sinais '{nome_sinal}'. Relatório desta data já aplicado.")

    agora = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    sem_conta = []
    vistos = set()
    resumo = []

    for linha in linhas:
        empresa = linha["Company name"].strip()
        conta = por_nome.get(normalizar(empresa))
        if not conta:
            sem_conta.append(empresa)
            continue
        if conta["id"] in vistos:
            continue
        vistos.add(conta["id"])

        comite = conta.get("x_abm_comite_total") or 0
        r = calcular(linha, comite)
        antigos = client.search(SINAL, [("x_lead_id", "=", conta["id"]), ("x_tipo", "=", TIPO),
                                        ("x_ativo", "=", True)])
        pontos_antigos = sum(s["x_pontos"] for s in client.read(SINAL, antigos, ["x_pontos"]))
        resumo.append((conta["name"], conta.get("x_abm_exposicao") or 0, r["exposicao"],
                       pontos_antigos, r["pontos"], conta.get("x_abm_score") or 0))

        if not args.apply:
            continue
        if round(conta.get("x_abm_exposicao") or 0, 1) != r["exposicao"]:
            client.write("crm.lead", [conta["id"]], {"x_abm_exposicao": r["exposicao"]})
        if antigos:
            client.write(SINAL, antigos, {"x_ativo": False})
        if r["pontos"] > 0:
            client.create(SINAL, {
                "x_name": nome_sinal,
                "x_tipo": TIPO,
                "x_origem": "linkedin_ads",
                "x_lead_id": conta["id"],
                "x_data": agora,
                "x_pontos_custom": r["pontos"],
                "x_ativo": True,
                "x_detalhe": r["detalhe"],
            })

    print(f"{'Conta':40} {'Exposição':>17} {'Pontos LI':>11} {'Score':>12}")
    for nome, exp_ant, exp_nova, p_ant, p_novo, score in sorted(resumo, key=lambda x: -x[4]):
        novo_score = score - p_ant + p_novo
        print(f"{nome[:40]:40} {exp_ant:7.1f} → {exp_nova:6.1f} {p_ant:4} → {p_novo:3} {score:4} → {novo_score:4}")
    print(f"\n{len(resumo)} contas atualizadas" + ("" if args.apply else " (dry-run: nada gravado)"))
    if sem_conta:
        print(f"{len(sem_conta)} empresas do export sem conta ativa na equipe {TEAM_ID}: "
              + ", ".join(sem_conta))


if __name__ == "__main__":
    main()
