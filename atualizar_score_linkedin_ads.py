"""
Atualiza o score ABM (equipe ABM Setima) a partir do relatório de empresas do
LinkedIn Ads.

Relatório esperado: Campaign Manager → Plano → Empresas → View "Engagement",
"Last 30 days" → Export (CSV). O Diego exporta toda segunda-feira e envia no
Claude Code; este script lê o CSV e grava um sinal por conta.

O sinal é uma FOTO dos últimos 30 dias, não um acumulado: a cada importação o
sinal "LinkedIn Ads – relatório 30 dias" anterior da conta é desativado e um
novo é criado. Assim o relatório semanal (que sempre cobre 30 dias) nunca soma
o mesmo engajamento duas vezes.

Pontuação por conta (teto 30 = no máximo "Engajada"; mídia sozinha nunca deixa
uma conta "Quente" — isso exige resposta, formulário ou conversa):

  Nível de engajamento do LinkedIn (já relativo ao porte da empresa)
      Very Low 0 · Low 5 · Medium 10 · High 20 · Very High 25
  Interações (cliques pagos + engajamentos pagos + engajamentos orgânicos)
      1–9 → 5 · 10–29 → 10 · 30+ → 15
  Exposição = impressões pagas ÷ pessoas no comitê (mínimo 10)
      ≥ 2 → 5 · ≥ 4 → 10
  Impressões e views absolutas não pontuam: medem o nosso investimento, não o
  interesse da conta, e favorecem quem tem comitê grande.

Uso:
    python atualizar_score_linkedin_ads.py relatorio.csv            # simulação
    python atualizar_score_linkedin_ads.py relatorio.csv --aplicar  # grava

Credenciais: ODOO_URL, ODOO_DB, ODOO_API_KEY (variáveis de ambiente ou .env).
"""

import argparse
import csv
import os
import re
import sys
import unicodedata
from datetime import date

import requests
from dotenv import load_dotenv

load_dotenv()

TEAM_ABM_SETIMA = 20
TIPO_SINAL = "li_ads_relatorio"
TETO = 30

PONTOS_NIVEL = {"very low": 0, "low": 5, "medium": 10, "high": 20, "very high": 25}
FAIXAS = ((60, "quente"), (30, "engajada"), (0, "fria"))


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


def faixa(score):
    return next(nome for limite, nome in FAIXAS if score >= limite)


def normalizar(nome):
    nome = unicodedata.normalize("NFKD", nome or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", nome.lower()).strip()


def numero(valor):
    try:
        return int(float(valor)) if valor not in (None, "") else 0
    except ValueError:
        return 0


class Odoo:
    def __init__(self):
        url = os.environ["ODOO_URL"].strip().rstrip("/")
        # A URL copiada do navegador costuma vir com /odoo (rota do painel web);
        # a API JSON-2 fica na raiz do domínio.
        self.url = re.sub(r"/odoo$", "", url)
        self.headers = {
            "Authorization": f"Bearer {os.environ['ODOO_API_KEY']}",
            "X-Odoo-Database": os.environ["ODOO_DB"],
        }

    def call(self, model, method, **params):
        r = requests.post(f"{self.url}/json/2/{model}/{method}",
                          headers=self.headers, json=params, timeout=60)
        if r.status_code != 200:
            raise RuntimeError(f"{model}.{method}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()


def ler_relatorio(caminho):
    with open(caminho, encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f))
    obrigatorias = {"Company name", "Engagement level", "Paid impressions",
                    "Paid clicks", "Paid engagements", "Organic engagements"}
    faltando = obrigatorias - set(linhas[0].keys() if linhas else [])
    if faltando:
        sys.exit(f"CSV não é o relatório de Empresas do Campaign Manager. Faltam colunas: {sorted(faltando)}")
    return linhas


def data_do_relatorio(caminho):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(caminho))
    return m.group(1) if m else date.today().isoformat()


def calcular(linha, pessoas_comite):
    nivel = (linha.get("Engagement level") or "").strip()
    interacoes = (numero(linha.get("Paid clicks")) + numero(linha.get("Paid engagements"))
                  + numero(linha.get("Organic engagements")))
    impressoes = numero(linha.get("Paid impressions"))
    razao = impressoes / max(pessoas_comite, 10)
    p_nivel = PONTOS_NIVEL.get(nivel.lower(), 0)
    p_inter = pontos_interacoes(interacoes)
    p_expo = pontos_exposicao(razao)
    total = min(p_nivel + p_inter + p_expo, TETO)
    detalhe = (
        f"Nível LinkedIn: {nivel or '-'} (+{p_nivel}) · "
        f"Interações: {interacoes} (+{p_inter}) · "
        f"Exposição: {impressoes} impressões / {pessoas_comite} no comitê = {razao:.1f} (+{p_expo}) · "
        f"Views de vídeo: {numero(linha.get('Paid video views'))} · "
        f"Total {total} (teto {TETO})"
    )
    return total, detalhe


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("csv")
    parser.add_argument("--aplicar", action="store_true", help="grava no Odoo (sem isto, só simula)")
    args = parser.parse_args()

    linhas = ler_relatorio(args.csv)
    referencia = data_do_relatorio(args.csv)
    rotulo = f"LinkedIn Ads 30 dias · relatório de {referencia}"
    por_nome = {normalizar(l["Company name"]): l for l in linhas}

    odoo = Odoo()
    contas = odoo.call("crm.lead", "search_read",
                       domain=[["team_id", "=", TEAM_ABM_SETIMA]],
                       fields=["name", "x_abm_linkedin_empresa", "x_abm_score",
                               "x_abm_comite_total", "stage_id"])
    anteriores = odoo.call("x_abm_sinal", "search_read",
                           domain=[["x_tipo", "=", TIPO_SINAL], ["x_ativo", "=", True],
                                   ["x_lead_id", "in", [c["id"] for c in contas]]],
                           fields=["x_lead_id", "x_pontos", "x_name"])
    anterior_por_conta = {}
    for s in anteriores:
        anterior_por_conta.setdefault(s["x_lead_id"][0], []).append(s)

    usados = set()
    plano = []
    sem_match = []
    for c in contas:
        chave = normalizar(c["x_abm_linkedin_empresa"] or c["name"])
        linha = por_nome.get(chave)
        antigos = anterior_por_conta.get(c["id"], [])
        pontos_antigos = sum(s["x_pontos"] for s in antigos)
        if linha:
            usados.add(chave)
            total, detalhe = calcular(linha, c["x_abm_comite_total"] or 0)
        else:
            sem_match.append(c["name"])
            total, detalhe = 0, "Conta não aparece no relatório"
        novo_score = (c["x_abm_score"] or 0) - pontos_antigos + total
        plano.append((c, antigos, total, detalhe, novo_score))

    print(f"Relatório: {args.csv} ({len(linhas)} empresas) · referência {referencia}")
    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULAÇÃO (nada é gravado)'}\n")
    print(f"{'Conta':38} {'Ads':>4} {'Score':>12}  Faixa")
    for c, antigos, total, detalhe, novo in sorted(plano, key=lambda p: (-p[2], p[0]["name"])):
        mudou = faixa(c["x_abm_score"] or 0) != faixa(novo)
        print(f"{c['name'][:38]:38} {total:>4} {c['x_abm_score'] or 0:>5} → {novo:<5} "
              f"{faixa(c['x_abm_score'] or 0)} → {faixa(novo)}{'  ◀ muda de faixa' if mudou else ''}")
        if total:
            print(f"{'':38}      {detalhe}")
    if sem_match:
        print(f"\nContas ABM sem linha no relatório (ficam com 0 de ads; confira o campo "
              f"'Nome no LinkedIn' se a empresa deveria aparecer): {', '.join(sem_match)}")

    fora = []
    for chave, l in por_nome.items():
        if chave in usados:
            continue
        # Só quem está na segmentação paga (tem impressão paga) e mostrou interesse;
        # engajamento só orgânico costuma ser agência/parceiro seguindo a página.
        if numero(l.get("Paid impressions")) == 0 or normalizar(l["Company name"]) == "setima":
            continue
        total, _ = calcular(l, 0)
        if (l.get("Engagement level") or "").lower() in ("medium", "high", "very high") or total >= 15:
            fora.append((total, l["Company name"], l.get("Engagement level")))
    if fora:
        print("\nEmpresas FORA do ABM com engajamento relevante (candidatas a conta-alvo):")
        for total, nome, nivel in sorted(fora, reverse=True)[:15]:
            print(f"  {nome[:50]:50} nível {nivel}")

    if not args.aplicar:
        print("\nSimulação concluída. Rode com --aplicar para gravar.")
        return

    for c, antigos, total, detalhe, _ in plano:
        if antigos and all(s["x_name"] == rotulo and s["x_pontos"] == total for s in antigos):
            continue  # mesmo relatório já importado
        if antigos:
            odoo.call("x_abm_sinal", "write", ids=[s["id"] for s in antigos], vals={"x_ativo": False})
        if total:
            odoo.call("x_abm_sinal", "create", vals_list=[{
                "x_name": rotulo,
                "x_lead_id": c["id"],
                "x_tipo": TIPO_SINAL,
                "x_origem": "linkedin_ads",
                "x_pontos_custom": total,
                "x_detalhe": detalhe,
            }])
    print("\nAplicado. Contas que mudaram de faixa disparam as automações do ABM (A2/A4).")


if __name__ == "__main__":
    main()
