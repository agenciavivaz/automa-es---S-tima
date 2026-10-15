"""Reconciliação do Dashboard Inbound v2 (§12) — diferença tolerada: zero.

Para cada período (Este mês, Mês anterior, Este ano) calcula cada número por consulta
INDEPENDENTE ao CRM (search_count / read_group com domínio explícito, escrito aqui em
Python, sem reaproveitar o calc.js) e compara com o valor que o dashboard calcula
(valores_dashboard.mjs roda o mesmo calc.js/data.js do módulo via JSON-2).

    python inbound_v2/scripts/reconciliar.py            # imprime e grava inbound_v2/RECONCILIACAO.md
    AGORA=2026-10-15T12:00:00 python ...                 # fixa o "agora" (padrão: agora)

Somente leitura. Credenciais só do ambiente; nunca impressas.
"""

import json
import os
import re
import statistics
import subprocess
import sys
from datetime import datetime, timedelta
from html import unescape
from zoneinfo import ZoneInfo

from conexao import cliente

TZ = ZoneInfo("America/Sao_Paulo")
AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = [["team_id", "=", 16], ["type", "=", "opportunity"], ["active", "in", [True, False]]]
CTX = {"active_test": False}
# Etapas por NOME (independente do mapeamento por posição do calc.js)
NOMES_MQL_MAIS = ["MQL", "Discovery", "SQL", "Oportunidade Setima", "Oportunidade"]
NOMES_DISCOVERY_MAIS = ["Discovery", "SQL", "Oportunidade Setima", "Oportunidade"]
NOMES_SQL_MAIS = ["SQL", "Oportunidade Setima", "Oportunidade"]
NOMES_OPP = ["Oportunidade Setima", "Oportunidade"]


def agora():
    a = os.environ.get("AGORA")
    return datetime.fromisoformat(a).replace(tzinfo=TZ) if a else datetime.now(TZ)


def periodos(now):
    hoje = now.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_hoje = hoje.replace(hour=23, minute=59, second=59, microsecond=999000)
    ini_mes = hoje.replace(day=1)
    ini_mes_ant = (ini_mes - timedelta(days=1)).replace(day=1)
    fim_mes_ant = (ini_mes - timedelta(days=1)).replace(hour=23, minute=59, second=59, microsecond=999000)
    ini_ano = hoje.replace(month=1, day=1)
    return {
        "this_month": ("Este mês", ini_mes, fim_hoje),
        "prev_month": ("Mês anterior", ini_mes_ant, fim_mes_ant),
        "year": ("Este ano", ini_ano, fim_hoje),
    }


def utc(d):
    return d.astimezone(ZoneInfo("UTC")).strftime("%Y-%m-%d %H:%M:%S")


def entrada(a, b):
    return ["|",
            "&", "&", ["x_pipedrive_add_time", "!=", False], ["x_pipedrive_add_time", ">=", utc(a)], ["x_pipedrive_add_time", "<=", utc(b)],
            "&", "&", ["x_pipedrive_add_time", "=", False], ["create_date", ">=", utc(a)], ["create_date", "<=", utc(b)]]


def stage_ids(c, nomes):
    return c.search("crm.stage", [["name", "in", nomes]])


def ou_ganho(ids):
    return ["|", ["won_status", "=", "won"], ["stage_id", "in", ids]]


RE_TEXTO = [
    ("convite", r"agenda\b|agendar|agendamento|marcar(mos)?\b|marcamos|reuni[ãa]o|disponibilidade|\bmeet\b|invite"),
    ("whatsapp", r"datacrazy|datacray|whats|wpp|\bzap\b|mensagem"),
    ("email", r"e-?mail"),
    ("ligacao", r"liga[çc]|ligu|telefon|api4com|caixa postal"),
    ("pesquisa", r"site|cnpj|linkedin|capital social|pesquis|qualific|\bicp\b|raz[ãa]o social"),
]
CONTATO = {"convite", "whatsapp", "email", "ligacao", "reuniao"}


def tipo(texto):
    t = texto.lower()
    for k, r in RE_TEXTO:
        if re.search(r, t):
            return k
    return "outro"


def texto_de(html):
    t = re.sub(r"<br\s*/?>|</(p|div|li)>", " ", html or "", flags=re.I)
    t = unescape(re.sub(r"<[^>]+>", "", t)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", t).strip()


def independente(c, a, b, now, ids_todos):
    r = {}
    coorte = BASE + entrada(a, b)
    r["leads"] = c.search_count("crm.lead", coorte, context=CTX)
    r["mql"] = c.search_count("crm.lead", coorte + ou_ganho(stage_ids(c, NOMES_MQL_MAIS)), context=CTX)
    r["sql"] = c.search_count("crm.lead", coorte + ou_ganho(stage_ids(c, NOMES_SQL_MAIS)), context=CTX)
    r["perdidos"] = c.search_count("crm.lead", coorte + [["won_status", "=", "lost"]], context=CTX)
    r["ganhos"] = c.search_count("crm.lead", coorte + [["won_status", "=", "won"]], context=CTX)
    r["funil"] = {
        "Lead": r["leads"], "MQL": r["mql"],
        "Discovery": c.search_count("crm.lead", coorte + ou_ganho(stage_ids(c, NOMES_DISCOVERY_MAIS)), context=CTX),
        "SQL": r["sql"],
        "Oportunidade Setima": c.search_count("crm.lead", coorte + ou_ganho(stage_ids(c, NOMES_OPP)), context=CTX),
        "Ganho": r["ganhos"],
    }
    tag = c.search("crm.tag", [["name", "=ilike", "datacrazy"]])
    r["datacrazy"] = c.search_count("crm.lead", coorte + [["tag_ids", "in", tag]], context=CTX)
    # reuniões: só estruturado (RN5)
    ev_criados = c.search_count("calendar.event", [["opportunity_id", "in", ids_todos], ["active", "in", [True, False]],
                                                   ["create_date", ">=", utc(a)], ["create_date", "<=", utc(b)]], context=CTX)
    at_meet = c.search_count("mail.activity", [["res_model", "=", "crm.lead"], ["res_id", "in", ids_todos], ["active", "in", [True, False]],
                                               ["activity_category", "=", "meeting"], ["calendar_event_id", "=", False],
                                               ["create_date", ">=", utc(a)], ["create_date", "<=", utc(b)]], context=CTX)
    r["reunioes"] = ev_criados + at_meet
    lim = min(b, now)
    r["reunioesRealizadas"] = c.search_count("calendar.event", [["opportunity_id", "in", ids_todos], ["active", "=", True],
                                                                ["start", ">=", utc(a)], ["start", "<=", utc(lim)]]) + \
        c.search_count("mail.activity", [["res_model", "=", "crm.lead"], ["res_id", "in", ids_todos], ["active", "=", False],
                                         ["activity_category", "=", "meeting"], ["calendar_event_id", "=", False],
                                         ["date_done", ">=", a.date().isoformat()], ["date_done", "<=", b.date().isoformat()]], context=CTX)
    # ações no período: mensagens com texto + atividades concluídas + eventos criados
    msgs = c.search_read_all("mail.message", [["model", "=", "crm.lead"], ["res_id", "in", ids_todos],
                                              ["message_type", "in", ["comment", "email"]],
                                              ["date", ">=", utc(a)], ["date", "<=", utc(b)]], ["body", "subject", "res_id"])
    msgs = [m for m in msgs if texto_de(m["body"]) or (m["subject"] or "").strip()]
    at_feitas = c.search_read_all("mail.activity", [["res_model", "=", "crm.lead"], ["res_id", "in", ids_todos], ["active", "=", False],
                                                    ["date_done", ">=", a.date().isoformat()], ["date_done", "<=", b.date().isoformat()]],
                                  ["res_id"], context=CTX)
    evs = c.search_read("calendar.event", [["opportunity_id", "in", ids_todos], ["active", "in", [True, False]],
                                           ["create_date", ">=", utc(a)], ["create_date", "<=", utc(b)]], ["opportunity_id"], context=CTX)
    r["acoes"] = len(msgs) + len(at_feitas) + len(evs)
    r["leadsTocados"] = len({m["res_id"] for m in msgs} | {x["res_id"] for x in at_feitas} | {e["opportunity_id"][0] for e in evs})
    # receita (RN2): ganhos com flag, qualquer pipeline; data = Data de Ganho, senão fechamento
    flag = [["x_origem_inbound", "=", True], ["won_status", "=", "won"], ["active", "in", [True, False]]]
    g = c.call("crm.lead", "read_group", {"domain": flag, "fields": ["expected_revenue:sum"], "groupby": []}, context=CTX)
    r["receitaAcumulada"] = (g[0].get("expected_revenue") or 0) if g else 0
    r["contratosAcumulados"] = c.search_count("crm.lead", flag, context=CTX)
    dper = ["|", "&", "&", ["x_studio_data_de_ganho", "!=", False], ["x_studio_data_de_ganho", ">=", a.date().isoformat()],
            ["x_studio_data_de_ganho", "<=", b.date().isoformat()],
            "&", "&", ["x_studio_data_de_ganho", "=", False], ["date_closed", ">=", utc(a)], ["date_closed", "<=", utc(b)]]
    gp = c.call("crm.lead", "read_group", {"domain": flag + dper, "fields": ["expected_revenue:sum"], "groupby": []}, context=CTX)
    r["receitaPeriodo"] = (gp[0].get("expected_revenue") or 0) if gp else 0
    r["contratosPeriodo"] = c.search_count("crm.lead", flag + dper, context=CTX)
    # 1º contato: mediana das horas até o 1º toque de saída (implementação independente)
    leads = c.search_read_all("crm.lead", coorte, ["create_date", "x_pipedrive_add_time"], context=CTX)
    ent = {l["id"]: datetime.fromisoformat(l["x_pipedrive_add_time"] or l["create_date"]).replace(tzinfo=ZoneInfo("UTC")) for l in leads}
    primeiro = {}
    if ent:
        todas = c.search_read_all("mail.message", [["model", "=", "crm.lead"], ["res_id", "in", list(ent)],
                                                   ["message_type", "in", ["comment", "email"]]], ["body", "subject", "res_id", "date"])
        for m in todas:
            t = texto_de(m["body"]) or (m["subject"] or "").strip()
            if not t or tipo(t) not in CONTATO:
                continue
            d = datetime.fromisoformat(m["date"]).replace(tzinfo=ZoneInfo("UTC"))
            if d >= ent[m["res_id"]] and (m["res_id"] not in primeiro or d < primeiro[m["res_id"]]):
                primeiro[m["res_id"]] = d
    horas = [(primeiro[i] - ent[i]).total_seconds() / 3600 for i in primeiro]
    r["contatados"] = len(horas)
    r["mediana1oContatoHoras"] = round(statistics.median(horas), 4) if horas else None
    return r


def dashboard(presets, now):
    env = dict(os.environ, NODE_USE_ENV_PROXY="1", AGORA=now.strftime("%Y-%m-%dT%H:%M:%S"))
    out = subprocess.run(["node", os.path.join(AQUI, "valores_dashboard.mjs"), *presets],
                         capture_output=True, text=True, env=env, timeout=600)
    if out.returncode:
        sys.exit("valores_dashboard.mjs falhou: " + out.stderr[-500:])
    return json.loads(out.stdout)


def checar_b1(textos):
    return [s for s in textos if re.search(r"[a-zA-Z0-9)][(]", s) or re.search(r",[^ \d]", s)]


CAMPOS = ["leads", "mql", "sql", "reunioes", "reunioesRealizadas", "perdidos", "ganhos", "datacrazy", "acoes",
          "leadsTocados", "contatados", "mediana1oContatoHoras", "receitaAcumulada", "contratosAcumulados",
          "receitaPeriodo", "contratosPeriodo"]


def main():
    now = agora()
    c = cliente()
    ids_todos = c.search("crm.lead", BASE, context=CTX)
    pers = periodos(now)
    dash = dashboard(list(pers), now)
    linhas = [f"# Reconciliação · Dashboard Inbound v2\n",
              f"Gerado em {now.strftime('%d/%m/%Y %H:%M')} (America/Sao_Paulo) por `inbound_v2/scripts/reconciliar.py`. "
              "Coluna *CRM* = consulta independente (`search_count`/`read_group` com domínio explícito); "
              "coluna *Dashboard* = mesmo `calc.js`/`data.js` do módulo. Diferença tolerada: 0.\n"]
    falhas = 0
    for key, (nome, a, b) in pers.items():
        ind = independente(c, a, b, now, ids_todos)
        d = dash[key]
        v = d["valores"]
        linhas.append(f"\n## {nome} · {d['periodo']['label']} (comparado com {d['periodo']['comparado']})\n")
        linhas.append("| Métrica | CRM | Dashboard | Diferença |\n|---|---:|---:|---:|")
        itens = [(k, ind[k], v[k]) for k in CAMPOS] + [(f"funil · {k}", ind["funil"][k], v["funil"].get(k)) for k in ind["funil"]]
        for k, x, y in itens:
            if k == "mediana1oContatoHoras":
                x = None if x is None else round(x, 4)
                y = None if y is None else round(y, 4)
            dif = 0 if x == y else ("—" if x is None or y is None else round(y - x, 4))
            if dif != 0:
                falhas += 1
            linhas.append(f"| {k} | {x} | {y} | {'✅ 0' if dif == 0 else '❌ ' + str(dif)} |")
        b1 = checar_b1(d["textos"] + d["leitura"]["destaques"] + d["leitura"]["atencao"])
        linhas.append(f"\nB1 (espaçamento nos textos gerados): {'✅ nenhum problema' if not b1 else '❌ ' + '; '.join(b1)}  ")
        linhas.append(f"Tempo de cálculo no Node (rede da sandbox): {d['ms']} ms\n")
        linhas.append("Leitura do período gerada:\n")
        linhas += [f"- Destaque: {t}" for t in d["leitura"]["destaques"]]
        linhas += [f"- Atenção: {t}" for t in d["leitura"]["atencao"]]
        falhas += len(b1)
    linhas.append(f"\n**Resultado: {'✅ todas as métricas reconciliadas (diferença 0)' if not falhas else f'❌ {falhas} divergência(s)'}**\n")
    texto = "\n".join(linhas)
    with open(os.path.join(AQUI, "..", "RECONCILIACAO.md"), "w", encoding="utf-8") as fh:
        fh.write(texto)
    print(texto)
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
