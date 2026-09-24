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
    <field name="x_abm_prioridade" string="Prior." width="50px"/>
    <field name="name" string="Nome"/>
    <field name="function" string="Cargo"/>
    <field name="x_abm_papel" string="Papel" widget="badge"
           decoration-danger="x_abm_papel == 'Decisor'"
           decoration-warning="x_abm_papel == 'Influenciador-chave'"
           decoration-info="x_abm_papel == 'Influenciador'"/>
    <field name="x_abm_area" string="Área"/>
    <field name="x_abm_senioridade" string="Senioridade" optional="hide"/>
    <field name="email" string="E-mail" widget="email"/>
    <field name="x_email_status" string="Status e-mail" widget="badge"
           decoration-success="x_email_status in ('Verificado', 'Válido')"
           decoration-warning="x_email_status in ('Extrapolado', 'catch-all')"
           decoration-danger="x_email_status in ('Inválido', 'Indisponível')"/>
    <field name="phone" string="Telefone" widget="phone" optional="show"/>
    <field name="x_linkedin_url" string="LinkedIn" widget="url" text="Perfil"/>
    <field name="x_abm_li_conexao" string="Conexão" widget="badge"
           decoration-success="x_abm_li_conexao == 'aceito'"
           decoration-info="x_abm_li_conexao == 'enviado'"
           decoration-danger="x_abm_li_conexao == 'recusado_ou_expirado'"/>
    <field name="x_abm_na_cadencia" string="Cadência" widget="boolean_toggle"/>
    <field name="x_abm_optout" string="Opt-out" widget="boolean_toggle" optional="show"/>
    <field name="x_abm_canal_inicial" string="Canal inicial" optional="hide"/>
    <field name="city" string="Cidade" optional="hide"/>
    <field name="category_id" string="Tags" widget="many2many_tags" optional="hide"/>
    <field name="x_abm_notas" string="Anotações" optional="hide"/>
"""

LISTA_COMITE = f"""
<list string="Comitê de compra" editable="bottom" limit="100"
      default_order="x_abm_prioridade, x_abm_papel, name"
      decoration-bf="x_abm_papel in ('Decisor', 'Influenciador-chave')"
      decoration-muted="x_abm_optout or x_abm_prioridade == 9">
    {COLUNAS_COMITE}
</list>
"""


def form_arch(acao_comite_id: int) -> str:
    """Tela da conta em largura total: formulário SEM <sheet> (o sheet do
    Odoo 19 tem max-width de 1400px — web/.../form_controller.scss; sem ele o
    formulário ocupa toda a área). Sem sheet, o chatter fica onde foi posto,
    no fim, e não vai para a lateral (mail/.../form_compiler.js). Campos
    vazios somem para não ocupar espaço."""
    comite = f'type="action" name="{acao_comite_id}" class="oe_stat_button"'
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
    <div class="oe_button_box" name="button_box">
            <button {comite} icon="fa-users" help="Abrir e editar o comitê">
                <field name="x_abm_comite_total" widget="statinfo" string="No comitê"/>
            </button>
            <button {comite} icon="fa-star" help="Decisores (prioridade 1)">
                <field name="x_abm_comite_decisores" widget="statinfo" string="Decisores"/>
            </button>
            <button {comite} icon="fa-linkedin-square" help="Conectados no LinkedIn">
                <field name="x_abm_comite_conectados" widget="statinfo" string="Conectados"/>
            </button>
            <button {comite} icon="fa-envelope-o" help="E-mails verificados ou válidos">
                <field name="x_abm_comite_emails_ok" widget="statinfo" string="E-mails ok"/>
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

        <div class="oe_title o_abm_header mb-3">
            <h1 class="mb-2"><field name="name" placeholder="Nome da conta"/></h1>
            <div class="d-flex flex-wrap align-items-center gap-2">
                <field name="x_abm_faixa" widget="badge" readonly="1"
                       decoration-info="x_abm_faixa == 'fria'"
                       decoration-warning="x_abm_faixa == 'engajada'"
                       decoration-danger="x_abm_faixa == 'quente'"/>
                <span class="fw-bold">Score <field name="x_abm_score" readonly="1" class="d-inline"/></span>
                <span class="text-muted">·</span>
                <span class="badge text-bg-success" invisible="x_abm_cadencia_status != 'ativa'">
                    <i class="fa fa-play me-1"/><field name="x_abm_cadencia_label" class="d-inline"/>
                </span>
                <field name="x_abm_dominio" widget="url" class="d-inline" invisible="not x_abm_dominio"/>
                <field name="tag_ids" widget="many2many_tags" options="{{'color_field': 'color'}}"
                       placeholder="Tags"/>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-12 col-lg-4">
                <div class="o_abm_box h-100">
                    <div class="o_abm_box_title"><i class="fa fa-bullseye"/>Conta</div>
                    <group>
                        <field name="x_abm_tier" string="Tier"/>
                        <field name="x_abm_trilha" string="Trilha"/>
                        <field name="x_abm_preparacao" string="Preparação"/>
                        <field name="user_id" string="SDR" widget="many2one_avatar_user"/>
                        <field name="x_abm_ultimo_sinal_data" string="Último sinal" readonly="1"
                               invisible="not x_abm_ultimo_sinal_data"/>
                    </group>
                </div>
            </div>
            <div class="col-12 col-lg-4">
                <div class="o_abm_box h-100">
                    <div class="o_abm_box_title"><i class="fa fa-road"/>Cadência</div>
                    <group>
                        <field name="x_abm_cadencia_status" string="Status"/>
                        <field name="x_abm_cadencia_inicio" string="Início" invisible="not x_abm_cadencia_inicio"/>
                        <field name="x_abm_onda" string="Onda" invisible="not x_abm_onda"/>
                        <field name="x_abm_ref_inatividade" string="Sem sinal desde" readonly="1"
                               invisible="not x_abm_ref_inatividade"/>
                        <field name="activity_date_deadline" string="Próxima atividade" readonly="1"
                               widget="remaining_days" invisible="not activity_date_deadline"/>
                        <field name="activity_summary" string="O que fazer" readonly="1"
                               invisible="not activity_summary"/>
                    </group>
                </div>
            </div>
            <div class="col-12 col-lg-4">
                <div class="o_abm_box h-100">
                    <div class="o_abm_box_title"><i class="fa fa-building-o"/>Empresa</div>
                    <group>
                        <field name="partner_id" string="Empresa"
                               context="{{'res_partner_search_mode': 'customer', 'show_address': 1}}"
                               options="{{'always_reload': True}}"/>
                        <field name="x_abm_dominios_extra" string="Outros domínios" invisible="not x_abm_dominios_extra"/>
                        <field name="x_abm_linkedin_empresa" string="Nome no LinkedIn"/>
                        <field name="website" string="Site" widget="url" invisible="not website"/>
                        <field name="phone" string="Telefone" widget="phone" invisible="not phone"/>
                        <field name="email_from" string="E-mail" widget="email" invisible="not email_from"/>
                        <field name="team_id" invisible="1"/>
                    </group>
                </div>
            </div>
        </div>

        <notebook>
            <page string="Comitê de compra" name="abm_comite">
                <div class="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-2">
                    <span class="o_abm_section_hint">
                        Ordenado por prioridade: 1 decisor, 2 influenciador, 3 demais, 9 fora do ICP.
                    </span>
                    <button {comite.replace('class="oe_stat_button"', 'class="btn btn-secondary btn-sm"')}
                            icon="fa-pencil" string="Editar comitê"/>
                </div>
                <field name="x_studio_comite" nolabel="1" readonly="1" colspan="2">
                    <list limit="100" default_order="x_abm_prioridade, x_abm_papel, name"
                          decoration-bf="x_abm_papel in ('Decisor', 'Influenciador-chave')"
                          decoration-muted="x_abm_optout or x_abm_prioridade == 9">
                        {COLUNAS_COMITE}
                    </list>
                </field>
            </page>
            <page string="Sinais" name="abm_sinais">
                <div class="o_abm_section_hint mb-2">
                    Cada sinal soma pontos por 30 dias. 30+ = Engajada, 60+ = Quente.
                </div>
                <field name="x_abm_sinal_ids" nolabel="1" colspan="2"
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
                    <group string="Links com UTM">
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
                        <field name="priority" string="Prioridade" widget="priority"/>
                    </group>
                    <group string="Origem">
                        <field name="campaign_id" string="Campanha"/>
                        <field name="source_id" string="Origem"/>
                        <field name="medium_id" string="Meio"/>
                        <field name="create_date" string="Criada em" readonly="1"/>
                        <field name="date_last_stage_update" string="Último movimento" readonly="1"/>
                    </group>
                </group>
            </page>
        </notebook>
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


# Card do kanban ABM (aprovado na prévia "Card ABM Setima"). Substitui o
# template do card herdado; só vale para a visão abm_setima.view_kanban.
# Cores: borda/selo por temperatura (fria info, engajada warning, quente
# danger, cliente success). Só classes Bootstrap e ícones Font Awesome.
_COR = "record.x_abm_cor.raw_value"
_BORDA = (f"{_COR} == 'quente' ? 'border-danger' : {_COR} == 'engajada' ? 'border-warning' : "
          f"{_COR} == 'cliente' ? 'border-success' : 'border-info'")
_SELO = (f"{_COR} == 'quente' ? 'text-bg-danger' : {_COR} == 'engajada' ? 'text-bg-warning' : 'text-bg-info'")
_BARRA = (f"{_COR} == 'quente' ? 'bg-danger' : {_COR} == 'engajada' ? 'bg-warning' : 'bg-info'")
_ICONE = (f"{_COR} == 'quente' ? 'fa-fire' : {_COR} == 'engajada' ? 'fa-thermometer-half' : 'fa-snowflake-o'")

KANBAN_ARCH = f"""
<data>
    <xpath expr="//kanban" position="attributes">
        <attribute name="class" add="o_abm_setima" separator=" "/>
    </xpath>
    <xpath expr="//progressbar" position="replace">
        <progressbar field="x_abm_faixa"
                     colors='{{"fria": "info", "engajada": "warning", "quente": "danger"}}'
                     help="Temperatura das contas da coluna: fria, engajada, quente."/>
    </xpath>
    <xpath expr="//templates" position="before">
        <field name="x_abm_cor"/>
        <field name="x_abm_faixa"/>
        <field name="x_abm_score"/>
        <field name="x_abm_score_pct"/>
        <field name="x_abm_tier"/>
        <field name="x_abm_trilha"/>
        <field name="x_abm_preparacao"/>
        <field name="x_abm_cadencia_status"/>
        <field name="x_abm_cadencia_label"/>
        <field name="x_abm_comite_total"/>
        <field name="x_abm_comite_decisores"/>
        <field name="x_abm_comite_conectados"/>
        <field name="x_abm_comite_emails_ok"/>
        <field name="x_abm_dias_estagio"/>
        <field name="activity_state"/>
        <field name="activity_summary"/>
        <field name="activity_type_id"/>
        <field name="activity_type_icon"/>
        <field name="activity_date_deadline"/>
    </xpath>
    <xpath expr="//t[@t-name='card']" position="replace">
        <t t-name="card">
            <div t-att-class="'border-start border-4 ps-2 d-flex flex-column gap-2 ' + ({_BORDA})">
                <div class="d-flex justify-content-between align-items-start gap-2">
                    <div class="text-truncate">
                        <field name="name" class="fw-bold fs-6 d-block text-truncate"/>
                        <field name="x_abm_dominio" class="small text-muted"/>
                    </div>
                    <span t-if="{_COR} == 'cliente'" class="badge rounded-pill text-bg-success">Cliente</span>
                    <span t-elif="record.x_abm_tier.raw_value"
                          t-att-class="'badge ' + (record.x_abm_tier.raw_value == '1' ? 'text-bg-dark' : 'text-bg-light border')">
                        T<t t-out="record.x_abm_tier.raw_value"/>
                    </span>
                </div>

                <div t-if="{_COR} != 'cliente'" class="d-flex align-items-center gap-2">
                    <span t-att-class="'badge rounded-pill ' + ({_SELO})">
                        <i t-att-class="'fa me-1 ' + ({_ICONE})"/><t t-out="record.x_abm_faixa.value or 'Fria'"/>
                    </span>
                    <div class="progress flex-grow-1 position-relative" style="height: 6px;"
                         title="Score: 30 = engajada, 60 = quente">
                        <div t-att-class="'progress-bar ' + ({_BARRA})"
                             t-attf-style="width: {{{{ record.x_abm_score_pct.raw_value }}}}%;"/>
                        <span class="position-absolute top-0 bottom-0 border-start border-secondary opacity-50" style="left: 33%;"/>
                        <span class="position-absolute top-0 bottom-0 border-start border-secondary opacity-50" style="left: 66%;"/>
                    </div>
                    <span class="fw-bold small"><t t-out="record.x_abm_score.raw_value"/></span>
                </div>

                <div class="d-flex flex-wrap gap-1">
                    <span t-if="record.x_abm_cadencia_label.raw_value"
                          t-att-class="'badge rounded-pill ' + (record.x_abm_cadencia_status.raw_value == 'ativa' ? 'text-bg-success' : 'text-bg-light border')">
                        <i t-if="record.x_abm_cadencia_status.raw_value == 'ativa'" class="fa fa-play me-1"/>
                        <t t-out="record.x_abm_cadencia_label.raw_value"/>
                    </span>
                    <span t-elif="record.x_abm_preparacao.raw_value == 'fila' and {_COR} != 'cliente'"
                          class="badge rounded-pill text-bg-light border">
                        <i class="fa fa-hourglass-half me-1"/>Preparação na fila
                    </span>
                    <span t-elif="record.x_abm_preparacao.raw_value == 'liberada'"
                          class="badge rounded-pill text-bg-light border">
                        <i class="fa fa-check me-1"/>Preparação liberada
                    </span>
                    <span t-if="record.x_abm_trilha.raw_value and record.x_abm_trilha.raw_value != 'a_definir'"
                          class="badge rounded-pill text-bg-light border">
                        <t t-out="record.x_abm_trilha.value"/>
                    </span>
                </div>

                <div class="d-flex flex-wrap column-gap-3 small text-muted">
                    <span title="Pessoas no comitê"><i class="fa fa-users me-1"/><b class="text-body"><t t-out="record.x_abm_comite_total.raw_value"/></b></span>
                    <span title="Decisores"><i class="fa fa-star me-1"/><b class="text-body"><t t-out="record.x_abm_comite_decisores.raw_value"/></b> decisores</span>
                    <span t-if="{_COR} != 'cliente'" title="Conectados no LinkedIn"><i class="fa fa-linkedin-square me-1 text-primary"/><b class="text-body"><t t-out="record.x_abm_comite_conectados.raw_value"/></b></span>
                    <span title="E-mails válidos"><i class="fa fa-envelope-o me-1"/><b class="text-body"><t t-out="record.x_abm_comite_emails_ok.raw_value"/></b></span>
                </div>

                <div t-if="record.activity_date_deadline.raw_value"
                     t-att-class="'d-flex align-items-center gap-2 rounded px-2 py-1 small bg-light ' + (record.activity_state.raw_value == 'overdue' ? 'text-danger' : '')">
                    <i t-att-class="'fa ' + (record.activity_type_icon.raw_value or 'fa-tasks')"/>
                    <span class="text-truncate"><t t-out="record.activity_summary.raw_value or record.activity_type_id.value"/></span>
                    <field name="activity_date_deadline" widget="remaining_days" class="ms-auto text-nowrap"/>
                </div>
                <div t-else="" class="d-flex align-items-center gap-2 rounded px-2 py-1 small bg-light text-muted">
                    <i class="fa fa-minus"/><span>Sem atividade agendada</span>
                </div>
            </div>
            <footer class="pt-1">
                <div class="d-flex align-items-center gap-2 w-100">
                    <field name="user_id" widget="many2one_avatar_user" domain="[('share', '=', False)]"/>
                    <field name="activity_ids" widget="kanban_activity"/>
                    <span class="ms-auto small text-muted" title="Dias no estágio atual">
                        <i class="fa fa-clock-o me-1"/><t t-out="record.x_abm_dias_estagio.raw_value"/> d no estágio
                    </span>
                </div>
            </footer>
        </t>
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
