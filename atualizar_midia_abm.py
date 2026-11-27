#!/usr/bin/env python3
"""
Mídia do ABM Sétima: planilha do LinkedIn Ads (Make → Google Sheets) → Odoo.

Uso (a partir da raiz do repositório):

    python atualizar_midia_abm.py --planilha midia.xlsx                        # simulação
    python atualizar_midia_abm.py --planilha midia.xlsx --cargos cargos.json   # + público (cargo/senioridade/função)
    python atualizar_midia_abm.py --planilha midia.xlsx --aplicar              # grava no Odoo

--planilha é o export .xlsx da planilha "LinkedIn Ads — Sétima (dados Make)" (abas diario_campanha e
empresas_abm). --cargos é o JSON das respostas do adAnalytics com pivô MEMBER_JOB_TITLE, MEMBER_SENIORITY e
MEMBER_JOB_FUNCTION por frente (formato em ler_cargos). Os registros são gravados em três modelos criados pelo
módulo abm_setima_dashboard e lidos pelo painel (seção "Mídia"):

    x_abm_midia_dia        uma linha por dia × campanha   (chave "AAAA-MM-DD|id da campanha")
    x_abm_midia_empresa    uma linha por período × empresa, casada com a conta ABM pelo "Nome no LinkedIn"
    x_abm_midia_segmento   uma linha por período × frente × dimensão × valor

Rodar de novo atualiza (upsert pela chave x_name); nunca duplica.
"""

import argparse
import datetime as dt
import json
import logging
import os
import re
import sys

from dotenv import load_dotenv

from atualizar_linkedin_ads_abm import norm_nome, paginas_da_conta

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ABM_TEAM_ID = int(os.environ.get("ABM_TEAM_ID", "20"))

# Frente de cada campanha (id numérico da campanha no Campaign Manager).
FRENTES = {
    "904675316": "comite",   # Contas - Montadora
    "907014956": "comite",   # Comitê - 93 montadoras
    "907279086": "comite",   # Lista + Comitê
    "907332366": "comite",   # Comitê + Lista
    "917108416": "educacao", # [Comite] - Educação (contas do ABM BrandSpot)
}

COLUNAS_DIA = {
    "impressoes": "x_impressoes", "cliques": "x_cliques", "custo_brl": "x_custo", "cliques_lp": "x_cliques_lp",
    "leads_formulario": "x_leads_form", "aberturas_formulario": "x_aberturas_form",
    "conversoes_site": "x_conversoes", "engajamentos": "x_engajamentos", "video_views": "x_video_views",
    "alcance_aprox": "x_alcance", "reacoes": "x_reacoes", "comentarios": "x_comentarios",
    "compartilhamentos": "x_compartilhamentos", "seguidores": "x_seguidores",
    "cliques_pagina_empresa": "x_cliques_pagina", "video_inicios": "x_video_inicios",
    "video_completos": "x_video_completos",
}

# Taxonomias padrão do LinkedIn (urn:li:seniority / urn:li:function).
SENIORIDADE = {
    "1": "Não remunerado", "2": "Em treinamento", "3": "Júnior / entrada", "4": "Sênior (individual)",
    "5": "Gerente", "6": "Diretor", "7": "Vice-presidente", "8": "C-level", "9": "Sócio", "10": "Proprietário",
}
FUNCAO = {
    "1": "Contabilidade", "2": "Administrativo", "3": "Artes e design", "4": "Desenvolvimento de negócios",
    "5": "Serviços comunitários", "6": "Consultoria", "7": "Educação", "8": "Engenharia",
    "9": "Empreendedorismo", "10": "Finanças", "11": "Saúde", "12": "Recursos humanos",
    "13": "Tecnologia da informação", "14": "Jurídico", "15": "Marketing", "16": "Mídia e comunicação",
    "17": "Militar e segurança", "18": "Operações", "19": "Gestão de produto", "20": "Programas e projetos",
    "21": "Compras", "22": "Qualidade", "23": "Imobiliário", "24": "Pesquisa", "25": "Vendas", "26": "Suporte",
}
CARGO_PT = {
    "Academic Advisor": "Orientador acadêmico", "Academic Coordinator": "Coordenador acadêmico",
    "Advisor": "Conselheiro", "Aftermarket Manager": "Gerente de aftermarket",
    "Aftersales Manager": "Gerente de pós-venda", "Appraiser": "Avaliador",
    "Assistant Professor": "Professor assistente", "Board Member": "Membro do conselho",
    "Brand Analyst": "Analista de marca", "Brand Development Specialist": "Especialista em desenvolvimento de marca",
    "Brand Manager": "Gerente de marca", "Brand Specialist": "Especialista de marca", "Co-Founder": "Cofundador",
    "Commercial Director": "Diretor comercial", "Communications Coordinator": "Coordenador de comunicação",
    "Communications Specialist": "Especialista em comunicação", "Consultant": "Consultor",
    "Content Coordinator": "Coordenador de conteúdo", "Coordinator": "Coordenador",
    "Course Coordinator": "Coordenador de curso", "Digital Marketing Specialist": "Especialista em marketing digital",
    "Digital Specialist": "Especialista digital", "Director": "Diretor",
    "Director of Product Management": "Diretor de produto", "Education Coordinator": "Coordenador educacional",
    "Education Specialist": "Especialista em educação", "Education Technician": "Técnico educacional",
    "Educational Counselor": "Orientador educacional", "Engineering Manager": "Gerente de engenharia",
    "Engineering Specialist": "Especialista de engenharia", "Engineering Supervisor": "Supervisor de engenharia",
    "Executive Director": "Diretor executivo", "Faculty Coordinator": "Coordenador de faculdade",
    "Founder": "Fundador", "Head of Marketing": "Head de marketing", "Head of Product": "Head de produto",
    "Inspector": "Inspetor", "Intern": "Estagiário", "Lead Product Manager": "Gerente de produto líder",
    "Lecturer": "Docente", "Logistics Supervisor": "Supervisor de logística", "MBA Professor": "Professor de MBA",
    "Maintenance Supervisor": "Supervisor de manutenção", "Manager": "Gerente",
    "Market Intelligence Analyst": "Analista de inteligência de mercado", "Market Specialist": "Especialista de mercado",
    "Marketing Analyst": "Analista de marketing", "Marketing Communications Manager": "Gerente de comunicação de marketing",
    "Marketing Communications Specialist": "Especialista em comunicação de marketing",
    "Marketing Consultant": "Consultor de marketing", "Marketing Coordinator": "Coordenador de marketing",
    "Marketing Director": "Diretor de marketing", "Marketing Intern": "Estagiário de marketing",
    "Marketing Manager": "Gerente de marketing", "Marketing Specialist": "Especialista de marketing",
    "Marketing Supervisor": "Supervisor de marketing", "Mentor": "Mentor", "Paraprofessional": "Auxiliar",
    "Partner": "Sócio", "Performance Manager": "Gerente de performance", "Performance Specialist": "Especialista de performance",
    "Planning Specialist": "Especialista de planejamento", "Planning Supervisor": "Supervisor de planejamento",
    "Postgraduate": "Pós-graduando", "President": "Presidente", "Product Analyst": "Analista de produto",
    "Product Consultant": "Consultor de produto", "Product Designer": "Designer de produto",
    "Product Development Coordinator": "Coordenador de desenvolvimento de produto",
    "Product Development Engineer": "Engenheiro de desenvolvimento de produto",
    "Product Development Manager": "Gerente de desenvolvimento de produto",
    "Product Development Specialist": "Especialista em desenvolvimento de produto",
    "Product Engineer": "Engenheiro de produto", "Product Engineering Specialist": "Especialista em engenharia de produto",
    "Product Management Specialist": "Especialista em gestão de produto", "Product Manager": "Gerente de produto",
    "Product Marketing Analyst": "Analista de marketing de produto",
    "Product Marketing Manager": "Gerente de marketing de produto",
    "Product Marketing Specialist": "Especialista em marketing de produto", "Product Owner": "Product owner",
    "Product Specialist": "Especialista de produto", "Product Strategist": "Estrategista de produto",
    "Product Supervisor": "Supervisor de produto", "Production Supervisor": "Supervisor de produção",
    "Professional Coordinator": "Coordenador profissional", "Professor": "Professor",
    "Program Coordinator": "Coordenador de programa", "Project Management Officer": "Analista de PMO",
    "Project Management Specialist": "Especialista em gestão de projetos", "Project Manager": "Gerente de projetos",
    "Quality Specialist": "Especialista de qualidade", "Quality Supervisor": "Supervisor de qualidade",
    "Regional Sales Supervisor": "Supervisor regional de vendas",
    "Research And Development Specialist": "Especialista em P&D", "Researcher": "Pesquisador",
    "Sales Consultant": "Consultor de vendas", "Sales Supervisor": "Supervisor de vendas", "Seller": "Vendedor",
    "Senior Analyst": "Analista sênior", "Senior Marketing Analyst": "Analista de marketing sênior",
    "Senior Product Manager": "Gerente de produto sênior", "Service Supervisor": "Supervisor de serviços",
    "Software Engineer": "Engenheiro de software", "Specialist": "Especialista", "Strategist": "Estrategista",
    "Supervisor": "Supervisor", "Teacher": "Professor (ensino básico)", "Teaching Specialist": "Especialista em ensino",
    "Trade Marketing Analyst": "Analista de trade marketing", "Trade Marketing Specialist": "Especialista de trade marketing",
    "Tutor": "Tutor", "User Experience Designer": "Designer de UX", "User Experience Researcher": "Pesquisador de UX",
    "User Interface Designer": "Designer de UI", "Vice President": "Vice-presidente", "Visiting Professor": "Professor visitante",
}
CARGOS_POR_FRENTE = 40  # só os cargos com mais impressões (o resto é cauda longa com poucas impressões)


# ---------------------------------------------------------------------------
# Regras puras (testadas em tests/test_midia_abm.py)
# ---------------------------------------------------------------------------

def numero(v, inteiro=True):
    if v in (None, ""):
        return 0
    try:
        f = float(str(v).replace(",", "."))
    except ValueError:
        return 0
    return int(round(f)) if inteiro else round(f, 2)


def data_iso(v):
    if isinstance(v, dt.datetime):
        return v.date().isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    s = str(v or "").strip()[:10]
    return s if re.match(r"^\d{4}-\d{2}-\d{2}$", s) else None


def id_campanha(urn):
    return str(urn or "").rsplit(":", 1)[-1].strip()


def linha_dia(r):
    """Linha da aba diario_campanha → valores de x_abm_midia_dia (None se a linha não tem data/campanha)."""
    data, cid = data_iso(r.get("data")), id_campanha(r.get("campanha_urn"))
    if not data or not cid:
        return None
    vals = {
        "x_name": f"{data}|{cid}", "x_data": data, "x_campanha_id": cid,
        "x_campanha": re.sub(r"\s+", " ", str(r.get("campanha_nome") or "")).strip(),
        "x_frente": FRENTES.get(cid, "outra"),
        "x_coletado_em": str(r.get("coletado_em") or "")[:16],
    }
    for col, campo in COLUNAS_DIA.items():
        vals[campo] = numero(r.get(col), inteiro=campo != "x_custo")
    return vals


def indice_contas(contas):
    """nome normalizado da página do LinkedIn → id da conta ABM."""
    idx = {}
    for c in contas:
        for k in paginas_da_conta(c):
            idx.setdefault(k, c["id"])
    return idx


def linha_empresa(r, idx):
    ini, fim = data_iso(r.get("periodo_inicio")), data_iso(r.get("periodo_fim"))
    urn = str(r.get("empresa_urn") or "").strip()
    if not ini or not urn:
        return None
    nome = str(r.get("empresa_nome") or "").strip()
    return {
        "x_name": f"{ini}|{urn}", "x_periodo_inicio": ini, "x_periodo_fim": fim, "x_empresa_urn": urn,
        "x_empresa": nome, "x_impressoes": numero(r.get("impressoes")), "x_cliques": numero(r.get("cliques")),
        "x_lead_id": idx.get(norm_nome(nome), False),
    }


def nome_segmento(dimensao, vid, titulos):
    if dimensao == "senioridade":
        return SENIORIDADE.get(vid, f"Senioridade {vid}")
    if dimensao == "funcao":
        return FUNCAO.get(vid, f"Função {vid}")
    en = titulos.get(vid)
    return CARGO_PT.get(en, en) if en else None


def linhas_segmento(cargos):
    """JSON de cargos → valores de x_abm_midia_segmento.

    Formato: {"periodo_inicio": "AAAA-MM-DD", "periodo_fim": "AAAA-MM-DD", "titulos": {"315": "Product Specialist"},
              "frentes": {"comite": {"cargo": [elementos do adAnalytics], "senioridade": [...], "funcao": [...]}}}
    """
    ini, fim, titulos = cargos["periodo_inicio"], cargos["periodo_fim"], cargos.get("titulos", {})
    out = []
    for frente, dims in cargos["frentes"].items():
        for dimensao, elementos in dims.items():
            elementos = sorted(elementos, key=lambda e: -e.get("impressions", 0))
            if dimensao == "cargo":
                elementos = elementos[:CARGOS_POR_FRENTE]
            for e in elementos:
                vid = id_campanha((e.get("pivotValues") or [""])[0])
                nome = nome_segmento(dimensao, vid, titulos)
                if not nome:
                    continue
                out.append({
                    "x_name": f"{ini}|{fim}|{frente}|{dimensao}|{vid}", "x_periodo_inicio": ini, "x_periodo_fim": fim,
                    "x_frente": frente, "x_dimensao": dimensao, "x_valor_id": vid, "x_valor": nome,
                    "x_impressoes": numero(e.get("impressions")), "x_cliques": numero(e.get("clicks")),
                    "x_custo": numero(e.get("costInLocalCurrency"), inteiro=False),
                })
    return out


def ler_planilha(caminho):
    import openpyxl

    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    abas = {}
    for nome in ("diario_campanha", "empresas_abm"):
        linhas = list(wb[nome].iter_rows(values_only=True)) if nome in wb.sheetnames else []
        cab = [str(c or "").strip() for c in (linhas[0] if linhas else [])]
        abas[nome] = [dict(zip(cab, r)) for r in linhas[1:] if any(v not in (None, "") for v in r)]
    return abas


# ---------------------------------------------------------------------------
# Odoo
# ---------------------------------------------------------------------------

def upsert(odoo, modelo, valores, aplicar):
    if not valores:
        return 0, 0
    existentes = {r["x_name"]: r["id"] for r in odoo.search_read_all(
        modelo, [["x_name", "in", [v["x_name"] for v in valores]]], ["x_name"])}
    novos = [v for v in valores if v["x_name"] not in existentes]
    velhos = [v for v in valores if v["x_name"] in existentes]
    if aplicar:
        for i in range(0, len(novos), 200):
            odoo.create(modelo, novos[i:i + 200])
        for v in velhos:
            odoo.write(modelo, [existentes[v["x_name"]]], {k: x for k, x in v.items() if k != "x_name"})
    return len(novos), len(velhos)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--planilha", help="export .xlsx da planilha do LinkedIn Ads (Make)")
    ap.add_argument("--cargos", help="JSON com os pivôs de cargo, senioridade e função")
    ap.add_argument("--aplicar", action="store_true", help="grava no Odoo (padrão: só simula)")
    args = ap.parse_args()
    if not args.planilha and not args.cargos:
        ap.error("informe --planilha e/ou --cargos")

    url = os.environ.get("ODOO_URL", "").strip().rstrip("/")
    os.environ["ODOO_URL"] = re.sub(r"/odoo$", "", url)
    from odoo.client import cliente_operacional

    odoo = cliente_operacional(somente_leitura=not args.aplicar)
    if args.planilha:
        abas = ler_planilha(args.planilha)
        dias = [v for v in (linha_dia(r) for r in abas["diario_campanha"]) if v]
        contas = odoo.search_read("crm.lead", [["team_id", "=", ABM_TEAM_ID], ["type", "=", "opportunity"]],
                                  ["id", "name", "x_abm_linkedin_empresa"])
        idx = indice_contas(contas)
        empresas = [v for v in (linha_empresa(r, idx) for r in abas["empresas_abm"]) if v]
        n, a = upsert(odoo, "x_abm_midia_dia", dias, args.aplicar)
        log.info("Diário por campanha: %d linha(s) · %d nova(s) · %d atualizada(s) · %s a %s · R$ %.2f",
                 len(dias), n, a, min((d["x_data"] for d in dias), default="—"),
                 max((d["x_data"] for d in dias), default="—"), sum(d["x_custo"] for d in dias))
        n, a = upsert(odoo, "x_abm_midia_empresa", empresas, args.aplicar)
        casadas = [e for e in empresas if e["x_lead_id"]]
        log.info("Empresas: %d linha(s) · %d nova(s) · %d atualizada(s) · %d casada(s) com conta ABM",
                 len(empresas), n, a, len(casadas))
    if args.cargos:
        with open(args.cargos, encoding="utf-8") as f:
            segs = linhas_segmento(json.load(f))
        n, a = upsert(odoo, "x_abm_midia_segmento", segs, args.aplicar)
        log.info("Público (cargo/senioridade/função): %d linha(s) · %d nova(s) · %d atualizada(s)", len(segs), n, a)
    if not args.aplicar:
        log.info("SIMULAÇÃO: nada gravado. Use --aplicar para gravar.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        log.exception("Falha ao atualizar a mídia do ABM")
        sys.exit(1)
