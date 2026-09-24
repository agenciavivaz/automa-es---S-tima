#!/usr/bin/env python3
"""
Monta a "visão de conta" do ABM Setima: o formulário da oportunidade mostra a
empresa inteira — dados da conta, comitê de compra completo e histórico.

Só mexe nos registros abm_setima.* (criados por criar_visoes_abm_setima.py),
que são usados apenas pelo menu CRM → ABM Setima. As telas das outras equipes
não são tocadas.

Cria/atualiza:
  - abm_setima.view_form            formulário próprio (não herda o padrão,
                                    que tem customizações do Studio de outras
                                    equipes);
  - abm_setima.view_partner_comite  lista editável de contatos do comitê;
  - abm_setima.action_editar_comite ação do botão "Editar comitê".

Dry-run por padrão; APLICAR=true grava.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, garantir, odoo, ref  # noqa: E402

TAG_ABM_MONTADORAS = 17

# Colunas do comitê (mesmas na aba da conta e na lista editável).
COLUNAS_COMITE = """
    <field name="name" string="Nome"/>
    <field name="function" string="Cargo"/>
    <field name="x_abm_papel" string="Papel" widget="badge"
           decoration-danger="x_abm_papel == 'Decisor'"
           decoration-warning="x_abm_papel == 'Influenciador-chave'"
           decoration-info="x_abm_papel == 'Influenciador'"/>
    <field name="x_abm_senioridade" string="Senioridade"/>
    <field name="x_abm_area" string="Área"/>
    <field name="email" string="E-mail" widget="email"/>
    <field name="x_email_status" string="Status e-mail" widget="badge"
           decoration-success="x_email_status in ('Verificado', 'Válido')"
           decoration-warning="x_email_status in ('Extrapolado', 'catch-all')"
           decoration-danger="x_email_status in ('Inválido', 'Indisponível')"/>
    <field name="phone" string="Telefone" widget="phone"/>
    <field name="x_linkedin_url" string="LinkedIn" widget="url"/>
    <field name="city" string="Cidade" optional="hide"/>
    <field name="category_id" string="Tags" widget="many2many_tags" optional="hide"/>
    <field name="x_abm_notas" string="Anotações" optional="hide"/>
"""

LISTA_COMITE = f"""
<list string="Comitê de compra" editable="bottom" default_order="x_abm_papel, name"
      decoration-bf="x_abm_papel in ('Decisor', 'Influenciador-chave')">
    {COLUNAS_COMITE}
</list>
"""


def form_arch(acao_comite_id: int) -> str:
    return f"""
<form string="Conta ABM" class="o_abm_setima">
    <header>
        <button name="action_set_won_rainbowman" string="Ganho" type="object"
                invisible="won_status == 'won' or not active"/>
        <button name="action_restore" string="Restaurar" type="object"
                invisible="won_status != 'lost'"/>
        <button name="{ref('crm.crm_lead_lost_action')}" string="Perdido" type="action"
                invisible="won_status != 'pending' or not active"/>
        <field name="stage_id" widget="statusbar_duration"
               options="{{'clickable': '1', 'fold_field': 'fold'}}"
               domain="['|', ('team_ids', 'in', team_id), ('team_ids', '=', False)]"
               readonly="won_status == 'lost' or not active"/>
    </header>
    <sheet>
        <div class="oe_button_box" name="button_box">
            <button name="{acao_comite_id}" type="action" class="oe_stat_button" icon="fa-users">
                <div class="o_stat_info"><span class="o_stat_text">Editar comitê</span></div>
            </button>
            <button name="action_schedule_meeting" type="object" class="oe_stat_button"
                    icon="fa-calendar" context="{{'partner_id': partner_id}}" invisible="not id">
                <div class="o_stat_info">
                    <span class="o_stat_text"><field name="meeting_display_label"/></span>
                    <field name="meeting_display_date" class="o_stat_value"
                           invisible="not meeting_display_date"/>
                </div>
            </button>
        </div>
        <widget name="web_ribbon" title="Perdido" bg_color="text-bg-danger"
                invisible="won_status != 'lost'"/>
        <widget name="web_ribbon" title="Ganho" invisible="won_status != 'won'"/>
        <field name="active" invisible="1"/>
        <field name="won_status" invisible="1"/>
        <field name="type" invisible="1"/>
        <field name="company_currency" invisible="1"/>

        <div class="oe_title">
            <h1><field name="name" placeholder="Nome da conta"/></h1>
            <field name="tag_ids" widget="many2many_tags" options="{{'color_field': 'color'}}"
                   placeholder="Tags (tier, trilha...)"/>
        </div>

        <group>
            <group string="Empresa">
                <field name="partner_id" string="Empresa"
                       context="{{'res_partner_search_mode': 'customer', 'show_address': 1}}"
                       options="{{'always_reload': True}}"/>
                <field name="website" string="Site" widget="url"/>
                <field name="email_from" string="E-mail geral" widget="email"/>
                <field name="phone" string="Telefone geral" widget="phone"/>
                <field name="city" string="Cidade"/>
                <field name="state_id" string="Estado"/>
            </group>
            <group string="Gestão da conta">
                <field name="user_id" string="Responsável" widget="many2one_avatar_user"/>
                <field name="team_id" string="Equipe" readonly="1"/>
                <field name="priority" string="Prioridade" widget="priority"/>
                <field name="activity_date_deadline" string="Próxima atividade" readonly="1"/>
                <field name="activity_summary" string="Resumo da atividade" readonly="1"/>
                <field name="date_last_stage_update" string="Último movimento" readonly="1"/>
            </group>
        </group>

        <notebook>
            <page string="Comitê de compra" name="abm_comite">
                <div class="text-muted mb-2">
                    Contatos ligados à empresa. Para incluir ou editar, use o botão
                    <b>Editar comitê</b> no topo.
                </div>
                <field name="x_studio_comite" nolabel="1" readonly="1">
                    <list default_order="x_abm_papel, name"
                          decoration-bf="x_abm_papel in ('Decisor', 'Influenciador-chave')">
                        {COLUNAS_COMITE}
                    </list>
                </field>
            </page>
            <page string="Dossiê e notas" name="abm_dossie">
                <field name="description" placeholder="Dossiê da conta, contexto, próximos passos..."/>
            </page>
            <page string="Negócio" name="abm_negocio">
                <group>
                    <group string="Valor">
                        <field name="expected_revenue" string="Receita esperada" widget="monetary"
                               options="{{'currency_field': 'company_currency'}}"/>
                        <field name="probability" string="Probabilidade (%)"/>
                        <field name="date_deadline" string="Fechamento esperado"/>
                    </group>
                    <group string="Origem">
                        <field name="campaign_id" string="Campanha"/>
                        <field name="source_id" string="Origem"/>
                        <field name="medium_id" string="Meio"/>
                        <field name="create_date" string="Criada em" readonly="1"/>
                    </group>
                </group>
            </page>
        </notebook>
    </sheet>
    <chatter/>
</form>
"""


def main():
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    form_id = ref(f"{MODULO}.view_form")
    if not form_id:
        raise SystemExit("Rode antes abm/criar_visoes_abm_setima.py (view_form não existe).")

    lista_id = garantir("view_partner_comite", "ir.ui.view", {
        "name": "res.partner.list.abm_setima.comite", "model": "res.partner", "type": "list",
        "mode": "primary", "priority": 99, "arch": LISTA_COMITE,
    })

    codigo = f"""
empresa = record.partner_id.commercial_partner_id
action = {{
    'type': 'ir.actions.act_window',
    'name': 'Comitê · %s' % (empresa.name or record.name),
    'res_model': 'res.partner',
    'view_mode': 'list,form',
    'views': [({lista_id or 0}, 'list'), (False, 'form')],
    'domain': [('parent_id', '=', empresa.id)],
    'context': {{'default_parent_id': empresa.id, 'default_type': 'contact',
                'default_is_company': False, 'default_category_id': [{TAG_ABM_MONTADORAS}]}},
    'target': 'current',
}}
"""
    acao_id = garantir("action_editar_comite", "ir.actions.server", {
        "name": "ABM · Editar comitê", "model_id": odoo("ir.model", "search", domain=[["model", "=", "crm.lead"]])[0],
        "state": "code", "code": codigo,
    })

    arch = form_arch(acao_id or 0)
    if not APLICAR:
        print(f"  ~ atualizaria {MODULO}.view_form (ir.ui.view #{form_id}) com o layout de conta")
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")
        return

    # Código com o id real da lista (garantir() pode ter acabado de criá-la).
    odoo("ir.actions.server", "write", ids=[acao_id], vals={"code": codigo})
    odoo("ir.ui.view", "write", ids=[form_id],
         vals={"inherit_id": False, "mode": "primary", "arch": arch})
    print(f"  ~ atualizado {MODULO}.view_form (ir.ui.view #{form_id})")


if __name__ == "__main__":
    main()
