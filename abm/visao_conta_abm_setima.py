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
    <field name="x_abm_prioridade" string="Prior."/>
    <field name="x_abm_li_conexao" string="Conexão LI" widget="badge"
           decoration-success="x_abm_li_conexao == 'aceito'"
           decoration-info="x_abm_li_conexao == 'enviado'"
           decoration-danger="x_abm_li_conexao == 'recusado_ou_expirado'"/>
    <field name="x_abm_na_cadencia" string="Na cadência" widget="boolean_toggle"/>
    <field name="x_abm_optout" string="Opt-out" widget="boolean_toggle"/>
    <field name="x_abm_canal_inicial" string="Canal inicial" optional="hide"/>
    <field name="city" string="Cidade" optional="hide"/>
    <field name="category_id" string="Tags" widget="many2many_tags" optional="hide"/>
    <field name="x_abm_notas" string="Anotações" optional="hide"/>
"""

LISTA_COMITE = f"""
<list string="Comitê de compra" editable="bottom" default_order="x_abm_prioridade, x_abm_papel, name"
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
            <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
                <field name="x_abm_faixa" widget="badge" readonly="1"
                       decoration-info="x_abm_faixa == 'fria'"
                       decoration-warning="x_abm_faixa == 'engajada'"
                       decoration-danger="x_abm_faixa == 'quente'"/>
                <span class="fw-bold">Score <field name="x_abm_score" readonly="1" class="d-inline"/></span>
                <field name="tag_ids" widget="many2many_tags" options="{{'color_field': 'color'}}"
                       placeholder="Tags"/>
            </div>
        </div>

        <group>
            <group string="Conta ABM">
                <field name="x_abm_tier" string="Tier"/>
                <field name="x_abm_trilha" string="Trilha"/>
                <field name="x_abm_preparacao" string="Preparação"/>
                <field name="x_abm_preparacao_inicio" string="Preparação liberada em" readonly="1"
                       invisible="not x_abm_preparacao_inicio"/>
                <field name="x_abm_ultimo_sinal_data" string="Último sinal" readonly="1"/>
                <field name="user_id" string="Responsável (SDR)" widget="many2one_avatar_user"/>
                <field name="priority" string="Prioridade" widget="priority"/>
                <field name="activity_date_deadline" string="Próxima atividade" readonly="1"/>
                <field name="activity_summary" string="Resumo da atividade" readonly="1"/>
            </group>
            <group string="Cadência">
                <field name="x_abm_cadencia_status" string="Status"/>
                <field name="x_abm_cadencia_inicio" string="Início"/>
                <field name="x_abm_onda" string="Onda"/>
                <field name="x_abm_ref_inatividade" string="Sem sinal desde" readonly="1"/>
                <field name="date_last_stage_update" string="Último movimento" readonly="1"/>
                <field name="team_id" string="Equipe" readonly="1"/>
            </group>
            <group string="Empresa">
                <field name="partner_id" string="Empresa"
                       context="{{'res_partner_search_mode': 'customer', 'show_address': 1}}"
                       options="{{'always_reload': True}}"/>
                <field name="website" string="Site" widget="url"/>
                <field name="phone" string="Telefone geral" widget="phone"/>
                <field name="city" string="Cidade"/>
                <field name="state_id" string="Estado"/>
            </group>
            <group string="Identificação">
                <field name="x_abm_dominio" string="Domínio"/>
                <field name="x_abm_dominios_extra" string="Outros domínios"/>
                <field name="x_abm_linkedin_empresa" string="Nome no LinkedIn"/>
                <field name="email_from" string="E-mail geral" widget="email"/>
            </group>
        </group>

        <notebook>
            <page string="Comitê de compra" name="abm_comite">
                <div class="text-muted mb-2">
                    Ordenado por prioridade (1 decisor, 2 influenciador, 3 demais, 9 fora).
                    Para incluir ou editar (papel, conexão, na cadência, opt-out), use o botão
                    <b>Editar comitê</b> no topo.
                </div>
                <field name="x_studio_comite" nolabel="1" readonly="1">
                    <list default_order="x_abm_prioridade, x_abm_papel, name"
                          decoration-bf="x_abm_papel in ('Decisor', 'Influenciador-chave')"
                          decoration-muted="x_abm_optout or x_abm_prioridade == 9">
                        {COLUNAS_COMITE}
                    </list>
                </field>
            </page>
            <page string="Sinais" name="abm_sinais">
                <div class="text-muted mb-2">
                    Cada sinal soma pontos por 30 dias. 30+ = Engajada, 60+ = Quente.
                </div>
                <field name="x_abm_sinal_ids" nolabel="1"
                       context="{{'default_x_lead_id': id}}">
                    <list editable="top" default_order="x_data desc"
                          decoration-muted="not x_ativo">
                        <field name="x_data" string="Data"/>
                        <field name="x_tipo" string="Tipo"/>
                        <field name="x_partner_id" string="Contato"
                               domain="[('parent_id', '=', parent.partner_id)]"/>
                        <field name="x_origem" string="Origem"/>
                        <field name="x_pontos" string="Pontos" sum="Total"/>
                        <field name="x_ativo" string="Ativo"/>
                        <field name="x_detalhe" string="Detalhe"/>
                        <field name="x_name" column_invisible="1"/>
                    </list>
                </field>
            </page>
            <page string="Dossiê, asset e links" name="abm_dossie">
                <group>
                    <group string="Materiais">
                        <field name="x_abm_dossie_url" string="Dossiê" widget="url"/>
                        <field name="x_abm_asset_url" string="Asset" widget="url"/>
                    </group>
                    <group string="Links com UTM (copiar e usar no canal)">
                        <field name="x_abm_link_email" string="E-mail" widget="CopyClipboardChar"/>
                        <field name="x_abm_link_linkedin" string="LinkedIn DM" widget="CopyClipboardChar"/>
                        <field name="x_abm_link_whatsapp" string="WhatsApp" widget="CopyClipboardChar"/>
                    </group>
                </group>
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

    sinais_menu()

    arch = form_arch(acao_id or 0)
    if not APLICAR:
        print(f"  ~ atualizaria {MODULO}.view_form (ir.ui.view #{form_id}) com o layout de conta")
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")
        return

    # Código com o id real da lista (garantir() pode ter acabado de criá-la).
    odoo("ir.actions.server", "write", ids=[acao_id], vals={"code": codigo})
    odoo("ir.ui.view", "write", ids=[lista_id], vals={"arch": LISTA_COMITE})
    odoo("ir.ui.view", "write", ids=[form_id],
         vals={"inherit_id": False, "mode": "primary", "arch": arch})
    print(f"  ~ atualizado {MODULO}.view_form (ir.ui.view #{form_id})")

    odoo("ir.ui.view", "write", ids=[ref(f"{MODULO}.view_kanban")], vals={"arch": KANBAN_ARCH})
    print(f"  ~ atualizado {MODULO}.view_kanban (card com faixa, score, tier, trilha e cadência)")

    # Contas novas criadas pelo menu já nascem com a SDR como responsável.
    team_id = int(odoo("ir.config_parameter", "get_param", key="abm.team_id"))
    sdr_id = int(odoo("ir.config_parameter", "get_param", key="abm.sdr_user_id"))
    odoo("ir.actions.act_window", "write", ids=[ref(f"{MODULO}.action_pipeline")], vals={
        "context": f"{{'default_type': 'opportunity', 'default_team_id': {team_id}, "
                   f"'default_user_id': {sdr_id}}}"})


# Card do kanban: acrescenta a linha ABM logo abaixo das tags (herda o card padrão).
KANBAN_ARCH = """
<data>
    <xpath expr="//kanban" position="attributes">
        <attribute name="class" add="o_abm_setima" separator=" "/>
    </xpath>
    <xpath expr="//t[@t-name='card']//field[@name='tag_ids']" position="after">
        <div class="d-flex flex-wrap align-items-center gap-1 mt-1">
            <field name="x_abm_faixa" widget="badge"
                   decoration-info="x_abm_faixa == 'fria'"
                   decoration-warning="x_abm_faixa == 'engajada'"
                   decoration-danger="x_abm_faixa == 'quente'"/>
            <span class="badge text-bg-light" title="Score ABM">
                <i class="fa fa-signal me-1"/><field name="x_abm_score"/>
            </span>
            <span class="badge text-bg-light" invisible="not x_abm_tier">
                Tier <field name="x_abm_tier"/>
            </span>
            <field name="x_abm_trilha" widget="badge" invisible="x_abm_trilha in (False, 'a_definir')"/>
            <field name="x_abm_cadencia_status" widget="badge"
                   decoration-success="x_abm_cadencia_status == 'ativa'"
                   invisible="x_abm_cadencia_status in (False, 'nao_iniciada')"/>
        </div>
    </xpath>
    <xpath expr="//t[@t-name='card']//field[@name='lead_properties']" position="attributes">
        <attribute name="invisible">1</attribute>
    </xpath>
</data>
"""


def sinais_menu():
    """Menu CRM → ABM Setima ▸ Pipeline / Sinais ABM (seção 1.5 da spec)."""
    lista = garantir("view_sinal_list", "ir.ui.view", {
        "name": "x_abm_sinal.list.abm_setima", "model": "x_abm_sinal", "type": "list",
        "arch": """
<list editable="top" default_order="x_data desc" decoration-muted="not x_ativo">
    <field name="x_data" string="Data"/>
    <field name="x_lead_id" string="Conta" domain="[('team_id.name', '=', 'ABM Setima')]"/>
    <field name="x_partner_id" string="Contato"/>
    <field name="x_tipo" string="Tipo"/>
    <field name="x_origem" string="Origem"/>
    <field name="x_pontos" string="Pontos" sum="Total"/>
    <field name="x_ativo" string="Ativo"/>
    <field name="x_detalhe" string="Detalhe"/>
</list>"""})
    busca = garantir("view_sinal_search", "ir.ui.view", {
        "name": "x_abm_sinal.search.abm_setima", "model": "x_abm_sinal", "type": "search",
        "arch": """
<search>
    <field name="x_lead_id" string="Conta"/>
    <field name="x_partner_id" string="Contato"/>
    <field name="x_tipo" string="Tipo"/>
    <filter name="ativos" string="Ativos (contam no score)" domain="[('x_ativo', '=', True)]"/>
    <filter name="por_conta" string="Conta" context="{'group_by': 'x_lead_id'}"/>
    <filter name="por_tipo" string="Tipo" context="{'group_by': 'x_tipo'}"/>
</search>"""})
    acao = garantir("action_sinais", "ir.actions.act_window", {
        "name": "Sinais ABM", "res_model": "x_abm_sinal", "view_mode": "list,form",
        "view_id": lista or False, "search_view_id": busca or False,
        "context": "{'search_default_por_conta': 1, 'search_default_ativos': 1}",
    })
    menu_abm = ref(f"{MODULO}.menu_pipeline")
    pipeline = ref(f"{MODULO}.action_pipeline")
    garantir("menu_abm_pipeline", "ir.ui.menu", {
        "name": "Pipeline", "parent_id": menu_abm, "sequence": 1,
        "action": f"ir.actions.act_window,{pipeline}"})
    garantir("menu_sinais", "ir.ui.menu", {
        "name": "Sinais ABM", "parent_id": menu_abm, "sequence": 2,
        "action": f"ir.actions.act_window,{acao}" if acao else False})
    if APLICAR:  # "ABM Setima" vira menu-pai com os dois itens
        odoo("ir.ui.menu", "write", ids=[menu_abm], vals={"action": False})


if __name__ == "__main__":
    main()
