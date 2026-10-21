"""
Monta no Odoo a estrutura do ABM BrandSpot (equipe 22) igual à do ABM Sétima (equipe 20).

Cria ou atualiza, com xml-id `abm_brandspot.*` (mesmo esquema do `abm_setima.*`):
  - equipe 22 visível para todos (sem empresa), com líder e membros da ABM Setima;
  - parâmetros `abm_brandspot.*` (equipe, SDR, gestor, início, fila 4/dia, freio 10);
  - campo compartilhado `x_abm_estudio` (Estúdio interno) e a cor de card "cliente"
    valendo para as duas equipes;
  - as 10 etapas (Alvo → Cliente – expansão). As 7 etapas antigas da equipe 22
    ("ABM · Conta-alvo" …) são reaproveitadas e renomeadas: nenhum card muda de lugar;
  - tag, campanha UTM, 16 tipos de atividade "ABM BrandSpot · …", 12 modelos de
    e-mail (rascunho) e os 2 planos de atividade;
  - telas (kanban, ficha, comitê, sinais), ações, menu CRM / ABM BrandSpot;
  - 15 automações (A1–A12, A14–A16; A13 já vale para as duas equipes) e a fila
    diária de preparação.

Ficam DESLIGADAS, como na Sétima: A5 (início da cadência) e A14 (onda 2) até os
e-mails saírem do rascunho; e a fila diária até o comitê ser importado.
Ativo/desligado, parâmetros e próxima execução só são definidos na criação: rodar
de novo não desfaz o que foi ligado no Odoo.

Uso (na raiz do repositório):
    python -m abm_brandspot.estrutura            # simulação: só lista o que faria
    python -m abm_brandspot.estrutura --aplicar  # grava
"""

import argparse
import sys
from pathlib import Path

from . import codigo, textos
from ._odoo import Odoo

MODULO = "abm_brandspot"
TEAM_ID = 22            # crm.team "ABM BrandSpot" (empresa Brandspot)
SDR_USER_ID = 31        # Amanda — mesma SDR da Sétima
GESTOR_USER_ID = 22     # Diego
# Equipe e contas "Visível para todos" (sem empresa), como a ABM Setima: com a empresa
# Brandspot, quem está com a empresa Sétima ativa não vê a equipe nem os cards.
EMPRESA = False
MEMBROS = [31, 22, 34, 6]  # mesmos da ABM Setima
CATEGORIA_PARCEIRO = 18  # res.partner.category "ABM Educação"
INICIO = "2026-10-26"
VIEWS = Path(__file__).parent / "views"

# xml-id: (nome, sequência, recolhida, id da etapa antiga a reaproveitar)
ETAPAS = [
    ("stage_alvo", "Alvo", 300, False, 80),
    ("stage_aquecendo", "Aquecendo", 310, False, 81),
    ("stage_engajada", "Engajada", 320, False, 82),
    ("stage_em_cadencia", "Em cadência", 330, False, 83),
    ("stage_conversa", "Conversa", 340, False, 84),
    ("stage_reuniao_agendada", "Reunião agendada", 350, False, 85),
    ("stage_reuniao_realizada", "Reunião realizada", 360, False, 86),
    ("stage_nutricao", "Nutrição", 370, True, None),
    ("stage_descartada", "Descartada", 380, True, None),
    ("stage_cliente_expansao", "Cliente – expansão", 390, True, None),
]

PARAMETROS = {
    "abm_brandspot.team_id": str(TEAM_ID),
    "abm_brandspot.sdr_user_id": str(SDR_USER_ID),
    "abm_brandspot.gestor_user_id": str(GESTOR_USER_ID),
    "abm_brandspot.inicio": INICIO,
    "abm_brandspot.preparacao_contas_dia": "4",
    "abm_brandspot.preparacao_limite_pendentes": "10",
}


class Montador:
    def __init__(self, odoo, aplicar):
        self.odoo = odoo
        self.aplicar = aplicar
        self.contagem = {"cria": 0, "atualiza": 0}
        self._falso = 0

    # ------------------------------------------------------------- xml-ids
    def ref(self, xmlid):
        modulo, nome = xmlid.split(".") if "." in xmlid else (MODULO, xmlid)
        r = self.odoo.call("ir.model.data", "search_read",
                           domain=[["module", "=", modulo], ["name", "=", nome]], fields=["res_id"])
        return r[0]["res_id"] if r else None

    def _registrar(self, nome, model, res_id):
        self.odoo.call("ir.model.data", "create", vals_list=[{
            "module": MODULO, "name": nome, "model": model, "res_id": res_id, "noupdate": True}])

    def garantir(self, nome, model, vals, so_na_criacao=None, adotar=None, rotulo=None):
        """Cria (ou atualiza) o registro do xml-id `abm_brandspot.<nome>`.

        `so_na_criacao`: valores aplicados só ao criar (ativo, parâmetros...).
        `adotar`: id de um registro existente a assumir se o xml-id ainda não existe.
        Em simulação devolve um id fictício negativo para registros novos.
        """
        res_id = self.ref(nome)
        rotulo = rotulo or vals.get("name") or nome
        if res_id is None and adotar:
            print(f"  ADOTA    {model:28} {nome:32} #{adotar} → {rotulo}")
            if self.aplicar:
                self._registrar(nome, model, adotar)
            res_id = adotar
        elif res_id is None:
            print(f"  CRIA     {model:28} {nome:32} {rotulo}")
            self.contagem["cria"] += 1
            if not self.aplicar:
                self._falso -= 1
                return self._falso
            res_id = self.odoo.call(model, "create", vals_list=[{**vals, **(so_na_criacao or {})}])[0]
            self._registrar(nome, model, res_id)
            return res_id
        else:
            print(f"  ATUALIZA {model:28} {nome:32} #{res_id} {rotulo}")
        self.contagem["atualiza"] += 1
        if self.aplicar and vals:
            self.odoo.call(model, "write", ids=[res_id], vals=vals)
        return res_id

    def model_id(self, model):
        return self.odoo.call("ir.model", "search", domain=[["model", "=", model]])[0]

    def field_id(self, model, campo):
        return self.odoo.call("ir.model.fields", "search",
                              domain=[["model", "=", model], ["name", "=", campo]])[0]

    # ---------------------------------------------------------- estrutura
    def parametros(self):
        print("\n[parâmetros]")
        for chave, valor in PARAMETROS.items():
            existe = self.odoo.call("ir.config_parameter", "search_read",
                                    domain=[["key", "=", chave]], fields=["value"])
            if existe:
                print(f"  MANTÉM   {chave} = {existe[0]['value']}")
            else:
                print(f"  CRIA     {chave} = {valor}")
                if self.aplicar:
                    self.odoo.call("ir.config_parameter", "create", vals_list=[{"key": chave, "value": valor}])

    def campos(self):
        print("\n[campos]")
        lead = self.model_id("crm.lead")
        self.garantir("field_lead_estudio", "ir.model.fields", {
            "field_description": "ABM · Estúdio interno",
            "help": "BrandSpot: a conta já tem estúdio para gravar/transmitir aulas? Mapeado na preparação da conta.",
        }, so_na_criacao={
            "name": "x_abm_estudio", "model_id": lead, "ttype": "selection", "store": True, "copied": True,
            "selection_ids": [[0, 0, {"value": v, "name": n, "sequence": i}] for i, (v, n) in enumerate([
                ("tem_estudio", "Já tem estúdio interno"),
                ("estudio_baixa", "Estúdio interno de baixa qualidade"),
                ("indefinido", "Indefinido"),
            ])],
        }, rotulo="x_abm_estudio")
        cor = self.field_id("crm.lead", "x_abm_cor")
        print(f"  ATUALIZA ir.model.fields             x_abm_cor (compartilhado)        #{cor} cor 'cliente' nas duas equipes")
        if self.aplicar:
            self.odoo.call("ir.model.fields", "write", ids=[cor], vals={"compute": codigo.COR_CARD})

    def equipe(self):
        print("\n[equipe]")
        print(f"  ATUALIZA crm.team                     equipe {TEAM_ID}                        visível para todos, líder Diego, membros da ABM Setima")
        if self.aplicar:
            self.odoo.call("crm.team", "write", ids=[TEAM_ID], vals={
                "company_id": EMPRESA, "user_id": GESTOR_USER_ID, "member_ids": [[6, 0, MEMBROS]]})

    def etapas(self):
        print("\n[etapas]")
        self.stage = {}
        for nome, rotulo, seq, fold, antiga in ETAPAS:
            self.stage[nome] = self.garantir(nome, "crm.stage", {
                "name": rotulo, "sequence": seq, "fold": fold, "is_won": False,
                "team_ids": [[6, 0, [TEAM_ID]]]}, adotar=antiga)

    def basicos(self):
        print("\n[tag e campanha]")
        self.tag = self.garantir("tag_abm", "crm.tag", {"name": "ABM BrandSpot"}, so_na_criacao={"color": 4})
        self.campanha = self.garantir("campaign_educacao", "utm.campaign", {"name": "ABM BrandSpot Educação"})

    def atividades(self):
        print("\n[modelos de e-mail]")
        lead = self.model_id("crm.lead")
        modelos = []
        for cod, assunto, ideias in textos.EMAILS:
            for chave, rotulo in textos.ESTUDIOS:
                modelos.append(self.garantir(f"tmpl_{cod.lower()}_{chave}", "mail.template", {
                    "name": f"ABM BrandSpot · {cod} · {rotulo}",
                    "model_id": lead,
                    "subject": "{{ object.partner_id.name or object.name }} · " + assunto,
                    "body_html": textos.corpo_email(cod, rotulo, ideias[chave]),
                }))
        print("\n[tipos de atividade]")
        self.tipo = {}
        for nome, (rotulo, categoria, icone, res_model, nota, recorrente) in textos.TIPOS.items():
            vals = {"name": textos.PREFIXO + rotulo, "category": categoria, "icon": icone,
                    "res_model": res_model, "default_note": nota,
                    "delay_count": recorrente, "delay_unit": "days"}
            if nome == "act_email":
                vals["mail_template_ids"] = [[6, 0, [m for m in modelos if m > 0]]]
            self.tipo[nome] = self.garantir(nome, "mail.activity.type", vals)
            if recorrente and self.tipo[nome] > 0 and self.aplicar:
                self.odoo.call("mail.activity.type", "write", ids=[self.tipo[nome]], vals={
                    "chaining_type": "trigger", "triggered_next_type_id": self.tipo[nome]})
        print("\n[planos de atividade]")
        for nome, (rotulo, passos) in textos.PLANOS.items():
            self.garantir(nome, "mail.activity.plan", {
                "name": rotulo, "res_model": "crm.lead", "company_id": EMPRESA,
                "template_ids": [[5, 0, 0]] + [[0, 0, {
                    "activity_type_id": self.tipo[t], "delay_count": dias, "delay_unit": "days",
                    "delay_from": de, "summary": resumo, "responsible_type": "other",
                    "responsible_id": SDR_USER_ID, "note": textos.TIPOS[t][4] or False,
                }] for t, dias, de, resumo in passos],
            })

    def telas(self):
        print("\n[telas]")
        setima_kanban = self.odoo.call("ir.ui.view", "read", ids=[self.ref("abm_setima.view_kanban")],
                                       fields=["inherit_id"])[0]
        arq = lambda nome: (VIEWS / nome).read_text(encoding="utf-8")
        self.v_comite = self.garantir("view_partner_comite", "ir.ui.view", {
            "name": "res.partner.list.abm_brandspot.comite", "model": "res.partner", "type": "list",
            "mode": "primary", "priority": 99, "arch": arq("comite_list.xml")})
        self.a_comite = self.garantir("action_editar_comite", "ir.actions.server", {
            "name": "ABM BrandSpot · Editar comitê", "model_id": self.model_id("crm.lead"), "state": "code",
            "code": codigo.COMITE.replace("__VIEW_COMITE__", str(self.v_comite))
                                 .replace("__CATEGORIA__", str(CATEGORIA_PARCEIRO))})
        self.v_kanban = self.garantir("view_kanban", "ir.ui.view", {
            "name": "crm.lead.kanban.abm_brandspot", "model": "crm.lead", "type": "kanban", "mode": "primary",
            "priority": 99, "inherit_id": setima_kanban["inherit_id"][0], "arch": arq("kanban.xml")})
        perdido = self.ref("crm.crm_lead_lost_action")
        self.v_form = self.garantir("view_form", "ir.ui.view", {
            "name": "crm.lead.form.abm_brandspot", "model": "crm.lead", "type": "form", "mode": "primary",
            "priority": 99, "arch": arq("form.xml").replace("__ACAO_COMITE__", str(self.a_comite))
                                                    .replace("__ACAO_PERDIDO__", str(perdido))})
        self.v_sinal = self.garantir("view_sinal_list", "ir.ui.view", {
            "name": "x_abm_sinal.list.abm_brandspot", "model": "x_abm_sinal", "type": "list", "mode": "primary",
            "priority": 32, "arch": arq("sinal_list.xml").replace("__TEAM__", str(TEAM_ID))})

    def acoes_e_menus(self):
        print("\n[ações]")
        pipe_setima = self.odoo.call("ir.actions.act_window", "read", ids=[self.ref("abm_setima.action_pipeline")],
                                     fields=["view_mode", "search_view_id"])[0]
        self.a_pipe = self.garantir("action_pipeline", "ir.actions.act_window", {
            "name": "ABM BrandSpot", "res_model": "crm.lead", "view_mode": pipe_setima["view_mode"],
            "domain": f"[('type','=','opportunity'),('team_id','=',{TEAM_ID})]",
            "context": f"{{'default_type': 'opportunity', 'default_team_id': {TEAM_ID}, "
                       f"'default_user_id': {SDR_USER_ID}}}",
            "search_view_id": pipe_setima["search_view_id"][0],
            "help": "<p class=\"o_view_nocontent_smiling_face\">Nenhuma conta ABM BrandSpot ainda.</p>"})
        lista_oportunidade = self.ref("crm.crm_case_tree_view_oppor")
        for seq, (modo, view) in enumerate([("kanban", self.v_kanban), ("list", lista_oportunidade),
                                            ("form", self.v_form)]):
            self.garantir(f"action_pipeline_{modo}", "ir.actions.act_window.view", {
                "act_window_id": self.a_pipe, "view_mode": modo, "view_id": view, "sequence": seq},
                rotulo=f"ABM BrandSpot · {modo}")

        sinais_setima = self.odoo.call("ir.actions.act_window", "read", ids=[self.ref("abm_setima.action_sinais")],
                                       fields=["context", "search_view_id"])[0]
        self.a_sinais = self.garantir("action_sinais", "ir.actions.act_window", {
            "name": "Sinais ABM BrandSpot", "res_model": "x_abm_sinal", "view_mode": "list,form",
            "domain": f"[('x_lead_id.team_id', '=', {TEAM_ID})]", "context": sinais_setima["context"],
            "view_id": self.v_sinal, "search_view_id": sinais_setima["search_view_id"][0]})

        ativ_setima = self.odoo.call("ir.actions.act_window", "read", ids=[self.ref("abm_setima.action_atividades")],
                                     fields=["view_mode", "context", "search_view_id", "view_ids"])[0]
        self.a_ativ = self.garantir("action_atividades", "ir.actions.act_window", {
            "name": "Atividades ABM BrandSpot", "res_model": "mail.activity", "view_mode": ativ_setima["view_mode"],
            "domain": f"[('activity_type_id.name', '=like', '{textos.PREFIXO}%')]",
            "context": ativ_setima["context"], "search_view_id": ativ_setima["search_view_id"][0],
            "help": "<p>Todas as tarefas do processo ABM BrandSpot (tipos de atividade “ABM BrandSpot · …”).</p>"})
        # Mesmas telas de atividades da Sétima (são genéricas): só a ação filtra a frente.
        for av in self.odoo.call("ir.actions.act_window.view", "read", ids=ativ_setima["view_ids"],
                                 fields=["view_mode", "view_id", "sequence"]):
            self.garantir(f"action_atividades_{av['view_mode']}", "ir.actions.act_window.view", {
                "act_window_id": self.a_ativ, "view_mode": av["view_mode"], "view_id": av["view_id"][0],
                "sequence": av["sequence"]}, rotulo=f"Atividades · {av['view_mode']}")

        print("\n[menus]")
        menu_setima = self.odoo.call("ir.ui.menu", "read", ids=[self.ref("abm_setima.menu_pipeline")],
                                     fields=["parent_id", "sequence", "group_ids"])[0]
        raiz = self.garantir("menu_pipeline", "ir.ui.menu", {
            "name": "ABM BrandSpot", "parent_id": menu_setima["parent_id"][0],
            "sequence": menu_setima["sequence"], "group_ids": [[6, 0, menu_setima["group_ids"]]]})
        for nome, rotulo, seq, acao in [("menu_abm_pipeline", "Pipeline", 1, self.a_pipe),
                                        ("menu_sinais", "Sinais ABM", 2, self.a_sinais),
                                        ("menu_atividades", "Atividades ABM", 3, self.a_ativ)]:
            self.garantir(nome, "ir.ui.menu", {"name": rotulo, "parent_id": raiz, "sequence": seq,
                                               "action": f"ir.actions.act_window,{acao}"})

    def automacoes(self):
        print("\n[automações]")
        s = self.stage
        lead = self.model_id("crm.lead")
        parceiro = self.model_id("res.partner")
        t = TEAM_ID
        definicoes = [
            ("a1", "A1 · Entrou em Alvo", lead, "on_write", f"[('stage_id', 'not in', [{s['stage_alvo']}])]",
             f"[('team_id', '=', {t}), ('stage_id', 'in', [{s['stage_alvo']}])]", None, codigo.A1, True),
            ("a2", "A2 · Ficou engajada", lead, "on_write", "[('x_abm_faixa', 'in', [False, 'fria'])]",
             f"[('team_id', '=', {t}), ('x_abm_faixa', 'in', ['engajada', 'quente']), ('stage_id', 'in', "
             f"[{s['stage_alvo']}, {s['stage_aquecendo']}, {s['stage_nutricao']}])]", None, codigo.A2, True),
            ("a3", "A3 · 21 dias aquecendo", lead, "on_time", False,
             f"[('team_id', '=', {t}), ('stage_id', '=', {s['stage_aquecendo']})]",
             ("date_last_stage_update", 21), codigo.A3, True),
            ("a4", "A4 · Conta quente", lead, "on_write", "[('x_abm_faixa', '!=', 'quente')]",
             f"[('team_id', '=', {t}), ('x_abm_faixa', '=', 'quente'), ('stage_id', 'not in', "
             f"[{s['stage_conversa']}, {s['stage_reuniao_agendada']}, {s['stage_descartada']}, "
             f"{s['stage_cliente_expansao']}])]", None, codigo.A4, True),
            ("a5", "A5 · Início da cadência", lead, "on_write", f"[('stage_id', 'not in', [{s['stage_em_cadencia']}])]",
             f"[('team_id', '=', {t}), ('stage_id', 'in', [{s['stage_em_cadencia']}])]", None, codigo.A5, False),
            ("a6", "A6 · Parar cadência", lead, "on_write",
             f"[('stage_id', 'not in', [{s['stage_conversa']}, {s['stage_nutricao']}, {s['stage_descartada']}])]",
             f"[('team_id', '=', {t}), ('stage_id', 'in', [{s['stage_conversa']}, {s['stage_nutricao']}, "
             f"{s['stage_descartada']}])]", None, codigo.A6, True),
            ("a7", "A7 · Conversa", lead, "on_write", f"[('stage_id', 'not in', [{s['stage_conversa']}])]",
             f"[('team_id', '=', {t}), ('stage_id', 'in', [{s['stage_conversa']}])]", None, codigo.A7, True),
            ("a8", "A8 · Reunião agendada", lead, "on_write",
             f"[('stage_id', 'not in', [{s['stage_reuniao_agendada']}])]",
             f"[('team_id', '=', {t}), ('stage_id', 'in', [{s['stage_reuniao_agendada']}])]", None, codigo.A8, True),
            ("a9", "A9 · Cadência sem sinal", lead, "on_time", False,
             f"[('team_id', '=', {t}), ('stage_id', '=', {s['stage_em_cadencia']})]",
             ("x_abm_ref_inatividade", 35), codigo.A9, True),
            ("a10", "A10 · E-mail recebido", lead, "on_message_received", False,
             f"[('team_id', '=', {t})]", None, codigo.A10, True),
            ("a11", "A11 · Conexão aceita", parceiro, "on_write", "[('x_abm_li_conexao', '!=', 'aceito')]",
             "[('x_abm_li_conexao', '=', 'aceito'), ('parent_id', '!=', False)]", None, codigo.A11, True),
            ("a12", "A12 · Opt-out", parceiro, "on_write", "[('x_abm_optout', '=', False)]",
             "[('x_abm_optout', '=', True)]", None, codigo.A12, True),
            ("a14", "A14 · Onda 2", lead, "on_time", False,
             f"[('team_id', '=', {t}), ('stage_id', '=', {s['stage_em_cadencia']}), ('x_abm_onda', '=', 1)]",
             ("x_abm_cadencia_inicio", 21), codigo.A14, False),
            ("a15", "A15 · Formulário de conta-alvo", lead, "on_create", False,
             f"[('team_id', '!=', {t}), ('email_from', '!=', False)]", None, codigo.A15, True),
            ("a16", "A16 · Asset pronto", lead, "on_write", "[('x_abm_asset_url', '=', False)]",
             f"[('team_id', '=', {t}), ('x_abm_asset_url', '!=', False)]", None, codigo.A16, True),
        ]
        for chave, rotulo, model_id, gatilho, pre, filtro, prazo, corpo, ativo in definicoes:
            model = "crm.lead" if model_id == lead else "res.partner"
            vals = {"name": f"ABM BrandSpot · {rotulo}", "model_id": model_id, "trigger": gatilho,
                    "filter_pre_domain": pre, "filter_domain": filtro}
            if prazo:
                vals.update({"trg_date_id": self.field_id(model, prazo[0]), "trg_date_range": prazo[1],
                             "trg_date_range_type": "day", "trg_date_range_mode": "after"})
            auto = self.garantir(f"auto_{chave}", "base.automation", vals, so_na_criacao={"active": ativo})
            self.garantir(f"auto_{chave}_acao", "ir.actions.server", {
                "name": f"ABM BrandSpot · {rotulo}", "model_id": model_id, "state": "code",
                "code": codigo.com_preambulo(corpo)},
                so_na_criacao={"usage": "base_automation", "base_automation_id": auto})

        print("\n[fila diária de preparação]")
        self.garantir("cron_fila_preparacao", "ir.cron", {
            "name": "ABM BrandSpot · Fila de preparação", "model_id": lead, "state": "code",
            "code": codigo.FILA, "interval_number": 1, "interval_type": "days", "priority": 5},
            so_na_criacao={"active": False, "user_id": GESTOR_USER_ID, "nextcall": f"{INICIO} 10:00:00"})

    def tudo(self):
        self.parametros()
        self.equipe()
        self.campos()
        self.etapas()
        self.basicos()
        self.atividades()
        self.telas()
        self.acoes_e_menus()
        self.automacoes()


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aplicar", action="store_true", help="grava no Odoo (sem isso, só simula)")
    args = parser.parse_args()
    print(f"Modo: {'APLICAR' if args.aplicar else 'SIMULAÇÃO (nada é gravado)'}")
    m = Montador(Odoo(), args.aplicar)
    m.tudo()
    print(f"\n{m.contagem['cria']} a criar, {m.contagem['atualiza']} a atualizar.")
    if not args.aplicar:
        print("Simulação concluída. Rode com --aplicar para gravar.")


if __name__ == "__main__":
    sys.exit(main())
