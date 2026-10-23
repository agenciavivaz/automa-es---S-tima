#!/usr/bin/env python3
"""
Contas de demonstração do ABM Sétima (equipe 20).

Cria contas fictícias "[DEMO] …" e leva cada uma a uma etapa do processo
usando as AUTOMAÇÕES REAIS do Odoo (A2, A3, A4, A5, A6, A11, A17, A20). As
tarefas que aparecem para a SDR e para o gestor são exatamente as do dia a
dia. Nada envia e-mail: as automações só criam tarefas, sinais e notas, e os
contatos fictícios usam domínios ".invalid".

Isolamento:
  - etiqueta "ABM · Demo" (parâmetro abm.tag_demo_id): a rotina da
    fila ignora essas contas e as tarefas delas não contam no freio da SDR
    (ver fila_preparacao_com_demo.py);
  - nomes começam com "[DEMO]" e os contatos terminam em "(demo)";
  - `limpar` apaga contas, contatos, sinais e tarefas (abertas e concluídas).

Enquanto existirem, as contas de demo aparecem no pipeline, no menu
Atividades ABM e no dashboard. Rode `limpar` ao fim do treinamento.

    python abm/demo/demo_abm.py status
    python abm/demo/demo_abm.py criar --apply            # todos os cenários
    python abm/demo/demo_abm.py criar 4 5 --apply        # só os cenários 4 e 5
    python abm/demo/demo_abm.py limpar --apply
"""

import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from dotenv import load_dotenv  # noqa: E402

from odoo.client import cliente_operacional  # noqa: E402

load_dotenv()

TEAM_ID = 20
EMPRESA_SETIMA = 2
TAG_ABM = 3
SDR_ID = 31
PREFIXO = "[DEMO]"
DOMINIO = "demo.invalid"

STAGE = {"alvo": 87, "aquecendo": 88, "engajada": 89, "em_cadencia": 90, "conversa": 91}
# Server actions das automações de tempo (rodadas direto, como o Odoo faria no prazo).
ACAO_A3 = 1327
ACAO_A17 = 1347

COMITE = [
    # nome, cargo, papel, prioridade, área, senioridade, telefone
    ("Marina Duarte", "Head de Marketing e Marca", "Decisor", 1, "Marketing", "Head", "(00) 00000-0001"),
    ("Rafael Nunes", "Diretor de Comunicação", "Decisor", 1, "Marketing", "Director", False),
    ("Camila Prado", "Gerente de Produto Digital", "Influenciador-chave", 2, "TI/Digital", "Manager", False),
    ("Bruno Teixeira", "Analista de Marketing Sênior", "Influenciador", 3, "Marketing", "Senior", False),
    ("Sérgio Lima", "Diretor de Compras", "Aprovador", 3, "Compras/Procurement", "Director", False),
]

CENARIOS = {
    1: ("Aurora Motors", "1 · Alvo na fila",
        "Conta-alvo esperando a fila de preparação. Nenhuma tarefa ainda."),
    2: ("Boreal Caminhões", "2 · Aquecendo (preparação)",
        "Visitou o site em Alvo: a A20 tirou da fila e liberou a preparação."),
    3: ("Cometa Máquinas", "3 · Pronta p/ abordagem",
        "Aquecendo com exposição alta aos 14 dias: a A17 antecipou o convite de LinkedIn."),
    4: ("Delta Agrícola", "4 · Engajada por score",
        "Chegou a 30 pontos (reagiu a post + visitou cases): a A2 levou para Engajada."),
    5: ("Estrela Ônibus", "5 · Em cadência",
        "Checklist feito e conta movida para Em cadência: a A5 criou os 8 toques. Um decisor aceitou a conexão (A11)."),
    6: ("Fênix Motos", "6 · Braço erguido → Conversa",
        "Em cadência, a decisora respondeu com interesse: a A4 moveu para Conversa e a A6 parou a cadência."),
    7: ("Gama Implementos", "7 · 21 dias sem engajar",
        "21 dias em Aquecendo sem chegar a 30 pontos: a A3 pediu revisão ao gestor."),
}


def slug(texto):
    return "".join(ch if ch.isalnum() else "-" for ch in texto.lower()).strip("-")


def ficha(empresa, titulo, resumo):
    return (
        '<div style="background-color:#7c2d12; color:#ffffff; padding:8px 12px; border-radius:6px; '
        'font-weight:bold; font-size:14px">🎓 CONTA DE DEMONSTRAÇÃO · %s</div>'
        '<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin:8px 0">'
        '⛔ Dados fictícios. <b>Não envie e-mails nem mensagens</b>: execute a tarefa no Odoo e marque como feita.</div>'
        '<p><b>Cenário:</b> %s</p><p>%s</p>'
        '<p><b>Gatilho:</b> lançamento do SUV elétrico Aurora E7 em março (fictício).<br/>'
        '<b>Observação do site:</b> configurador só troca a cor, sem interior, lento no celular.<br/>'
        '<b>Modelo para a prévia:</b> E7.<br/><b>Objeção provável:</b> "já temos agência de CGI".</p>'
    ) % (empresa, titulo, resumo)


class Demo:
    def __init__(self, client, aplicar):
        self.c = client
        self.aplicar = aplicar
        self.tag_demo = int(self._param("abm.tag_demo_id") or 0)

    # -- utilidades ------------------------------------------------------
    def _param(self, chave):
        r = self.c.search_read("ir.config_parameter", [("key", "=", chave)], ["value"])
        return r[0]["value"] if r else None

    def contas(self):
        return self.c.search_read("crm.lead", [("team_id", "=", TEAM_ID), ("name", "=like", PREFIXO + "%")],
                                  ["name", "stage_id", "x_abm_score", "partner_id", "tag_ids"],
                                  context={"active_test": False})

    def atividades(self, lead_ids, abertas_e_feitas=True):
        ctx = {"active_test": False} if abertas_e_feitas else None
        return self.c.search_read("mail.activity", [("res_model", "=", "crm.lead"), ("res_id", "in", lead_ids)],
                                  ["res_id", "summary", "user_id", "date_deadline", "active"], context=ctx)

    def sinal(self, lead_id, tipo, origem, nome, partner_id=False, pontos=None):
        vals = {"x_name": nome, "x_lead_id": lead_id, "x_tipo": tipo, "x_origem": origem,
                "x_data": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                "x_ativo": True, "x_partner_id": partner_id}
        if pontos is not None:
            vals["x_pontos_custom"] = pontos
        self.c.create("x_abm_sinal", vals)

    def rodar_acao(self, acao_id, lead_id):
        self.c.call("ir.actions.server", "run", {"ids": [acao_id]},
                    context={"active_model": "crm.lead", "active_ids": [lead_id], "active_id": lead_id})

    def concluir(self, lead_id, prefixo_resumo, feedback):
        abertas = [a for a in self.atividades([lead_id], abertas_e_feitas=False)
                   if (a["summary"] or "").startswith(prefixo_resumo)]
        if abertas:
            self.c.call("mail.activity", "action_feedback", {"ids": [a["id"] for a in abertas], "feedback": feedback})

    # -- criação ---------------------------------------------------------
    def criar_conta(self, n, etapa, preparacao, exposicao=0.0, trilha="a_definir"):
        empresa, titulo, resumo = CENARIOS[n]
        nome_empresa = "%s %s" % (PREFIXO, empresa)
        dominio = "%s.%s" % (slug(empresa), DOMINIO)
        empresa_id = self.c.create("res.partner", {
            "name": nome_empresa, "is_company": True, "website": "https://%s" % dominio,
            "x_conta_alvo": True})[0]
        contatos = []
        for nome, cargo, papel, prio, area, sen, fone in COMITE:
            contatos.append({
                "name": "%s (demo)" % nome, "parent_id": empresa_id, "function": cargo,
                "email": "%s@%s" % (slug(nome).replace("-", "."), dominio), "phone": fone,
                "x_abm_papel": papel, "x_abm_prioridade": prio, "x_abm_area": area,
                "x_abm_senioridade": sen, "x_email_status": "Verificado",
                "x_abm_li_conexao": "nao_enviado", "x_abm_canal_inicial": "email_linkedin",
                "x_linkedin_url": "https://example.com/demo/%s" % slug(nome),
            })
        contato_ids = self.c.create("res.partner", contatos)
        utm = "https://www.setima.cc/PT?utm_source=%s&utm_medium=abm_1a1&utm_campaign=demo&utm_content=" + slug(empresa)
        lead_id = self.c.create("crm.lead", {
            "name": "%s %s" % (PREFIXO, empresa), "type": "opportunity", "team_id": TEAM_ID,
            "company_id": EMPRESA_SETIMA, "user_id": SDR_ID, "partner_id": empresa_id,
            "tag_ids": [(6, 0, [TAG_ABM, self.tag_demo])], "stage_id": STAGE[etapa],
            "x_abm_tier": "1", "x_abm_trilha": trilha, "x_abm_preparacao": preparacao,
            "x_abm_dominio": dominio, "x_abm_linkedin_empresa": nome_empresa,
            "x_abm_exposicao": exposicao, "x_abm_comite_validado_em": datetime.date.today().isoformat(),
            "x_abm_link_email": utm % "email", "x_abm_link_linkedin": utm % "linkedin_dm",
            "x_abm_link_whatsapp": utm % "whatsapp",
            "description": ficha(empresa, titulo, resumo),
        })[0]
        return lead_id, dict(zip([c[0] for c in COMITE], contato_ids))

    def preparar_cadencia(self, lead_id, pessoas):
        """O que a SDR faz no checklist de "Iniciar cadência" antes de mover a conta."""
        ids = [pessoas[n] for n in ("Marina Duarte", "Rafael Nunes", "Camila Prado")]
        self.c.write("res.partner", ids, {"x_abm_na_cadencia": True})
        self.c.write("crm.lead", [lead_id], {
            "x_abm_trilha": "config_fraco",
            "x_abm_dossie_url": "https://example.com/demo/dossie.pdf"})
        self.concluir(lead_id, "Iniciar cadência", "Checklist ok (demo).")
        self.c.write("crm.lead", [lead_id], {"stage_id": STAGE["em_cadencia"]})  # → A5

    def cenario(self, n):
        if n == 1:
            self.criar_conta(1, "alvo", "fila")
        elif n == 2:
            lead, _ = self.criar_conta(2, "alvo", "fila")
            self.sinal(lead, "visita_dominio", "site", "Visita ao site – demo")  # → A20
        elif n == 3:
            lead, _ = self.criar_conta(3, "aquecendo", "liberada", exposicao=9.5)
            self.sinal(lead, "li_ads_relatorio", "linkedin_ads", "LinkedIn Ads 30 dias · demo", pontos=15)
            self.rodar_acao(ACAO_A17, lead)
        elif n == 4:
            lead, p = self.criar_conta(4, "aquecendo", "liberada", exposicao=6.0)
            self.sinal(lead, "li_reacao_post", "linkedin_manual", "Reagiu a post – Camila Prado",
                       partner_id=p["Camila Prado"])
            self.sinal(lead, "visita_alta_intencao", "site", "Visitou cases – demo")  # 30 → A2
        elif n in (5, 6):
            lead, p = self.criar_conta(n, "aquecendo", "liberada", exposicao=7.0, trilha="config_fraco")
            self.sinal(lead, "li_reacao_post", "linkedin_manual", "Reagiu a post – Rafael Nunes",
                       partner_id=p["Rafael Nunes"])
            self.sinal(lead, "visita_alta_intencao", "site", "Visitou cases – demo")  # → A2
            self.preparar_cadencia(lead, p)  # → A5
            if n == 5:
                self.c.write("res.partner", [p["Rafael Nunes"]], {"x_abm_li_conexao": "aceito"})  # → A11
            else:
                self.sinal(lead, "resposta_positiva", "email", "Braço erguido – Marina Duarte",
                           partner_id=p["Marina Duarte"])  # → A4 → Conversa → A6
        elif n == 7:
            lead, _ = self.criar_conta(7, "aquecendo", "liberada", exposicao=1.2)
            self.rodar_acao(ACAO_A3, lead)

    # -- limpeza ---------------------------------------------------------
    def limpar(self):
        contas = self.contas()
        if not contas:
            print("Nenhuma conta de demo.")
            return
        ids = [c["id"] for c in contas]
        acts = self.atividades(ids)
        sinais = self.c.search("x_abm_sinal", [("x_lead_id", "in", ids)], context={"active_test": False})
        empresas = sorted({c["partner_id"][0] for c in contas if c["partner_id"]})
        contatos = self.c.search("res.partner", [("parent_id", "in", empresas)], context={"active_test": False})
        print(f"{len(contas)} contas, {len(acts)} atividades, {len(sinais)} sinais, "
              f"{len(contatos)} contatos e {len(empresas)} empresas de demo.")
        if not self.aplicar:
            print("(dry-run: nada apagado; use --apply)")
            return
        if acts:
            self.c.call("mail.activity", "unlink", {"ids": [a["id"] for a in acts]})
        if sinais:
            self.c.call("x_abm_sinal", "unlink", {"ids": sinais})
        self.c.call("crm.lead", "unlink", {"ids": ids})
        self.c.call("res.partner", "unlink", {"ids": contatos + empresas})
        print("Demo apagada.")

    def status(self):
        contas = self.contas()
        if not contas:
            print("Nenhuma conta de demo.")
            return
        acts = self.atividades([c["id"] for c in contas], abertas_e_feitas=False)
        for c in sorted(contas, key=lambda x: x["name"]):
            minhas = [a for a in acts if a["res_id"] == c["id"]]
            por_pessoa = {}
            for a in minhas:
                por_pessoa[a["user_id"][1]] = por_pessoa.get(a["user_id"][1], 0) + 1
            print(f"{c['name'][:40]:40} {c['stage_id'][1]:14} score {c['x_abm_score']:3} | "
                  + ", ".join(f"{k}: {v}" for k, v in por_pessoa.items()) if minhas else
                  f"{c['name'][:40]:40} {c['stage_id'][1]:14} score {c['x_abm_score']:3} | sem tarefas abertas")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("comando", choices=["status", "criar", "limpar"])
    parser.add_argument("cenarios", nargs="*", type=int, help="números dos cenários (padrão: todos)")
    parser.add_argument("--apply", action="store_true", help="grava no Odoo (sem isso é dry-run)")
    args = parser.parse_args()

    demo = Demo(cliente_operacional(somente_leitura=not args.apply), args.apply)
    if args.comando == "status":
        demo.status()
    elif args.comando == "limpar":
        demo.limpar()
    else:
        if not demo.tag_demo:
            sys.exit("Parâmetro abm.tag_demo_id não existe: crie a etiqueta 'ABM · Demo' "
                     "e aplique a fila_preparacao_com_demo.py antes (senão a demo trava a fila).")
        escolhidos = args.cenarios or sorted(CENARIOS)
        if demo.contas():
            sys.exit("Já existem contas de demo. Rode `limpar --apply` antes de criar de novo.")
        for n in escolhidos:
            print(f"Cenário {CENARIOS[n][1]} · {CENARIOS[n][0]}" + ("" if args.apply else " (dry-run)"))
            if args.apply:
                demo.cenario(n)
        if args.apply:
            demo.status()


if __name__ == "__main__":
    main()
