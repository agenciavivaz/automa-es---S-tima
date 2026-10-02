"""Cria/atualiza o menu CRM → ABM Setima → Atividades ABM (telas próprias de mail.activity, prioridade 250).
Idempotente. Uso: python abm/odoo/menu_atividades.py (requer ODOO_URL/ODOO_DB/ODOO_API_KEY)."""
import os, json, requests
U = os.environ["ODOO_URL"].rstrip("/").removesuffix("/odoo")
H = {"Authorization": "Bearer " + os.environ["ODOO_API_KEY"], "X-Odoo-Database": os.environ["ODOO_DB"]}
def call(model, method, **kw):
    r = requests.post(f"{U}/json/2/{model}/{method}", headers=H, json=kw, timeout=60); r.raise_for_status(); return r.json()
PRIO = 250  # bem acima do padrão (16): estas telas nunca viram a visão padrão de atividades
def xid(name):
    r=call("ir.model.data","search_read",domain=[["module","=","abm_setima"],["name","=",name]],fields=["res_id"])
    return r[0]["res_id"] if r else None
def upsert(name, model, vals):
    i=xid(name)
    if i:
        call(model,"write",ids=[i],vals=vals); return i
    i=call(model,"create",vals_list=[vals])[0]
    call("ir.model.data","create",vals_list=[{"module":"abm_setima","name":name,"model":model,"res_id":i,"noupdate":True}])
    return i

KANBAN = """<kanban default_group_by="activity_type_id" create="false" quick_create="false" group_create="false" group_delete="false" group_edit="false" records_draggable="false" default_order="date_deadline asc">
  <field name="state"/>
  <field name="res_model"/>
  <field name="res_id"/>
  <templates>
    <t t-name="card">
      <div class="d-flex justify-content-between">
        <field name="res_name" class="fw-bold text-truncate"/>
        <field name="user_id" widget="many2one_avatar_user"/>
      </div>
      <field name="summary" class="text-muted small"/>
      <field name="x_abm_partner_id" class="small"/>
      <div class="d-flex justify-content-between align-items-center mt-1">
        <field name="date_deadline" class="small"/>
        <span t-if="record.state.raw_value == 'overdue'" class="badge text-bg-danger">Atrasada</span>
        <span t-elif="record.state.raw_value == 'today'" class="badge text-bg-warning">Hoje</span>
        <span t-else="" class="badge text-bg-success">Planejada</span>
      </div>
    </t>
  </templates>
</kanban>"""

LIST = """<list create="false" default_order="date_deadline asc" decoration-danger="state == 'overdue'" decoration-warning="state == 'today'">
  <field name="state" column_invisible="1"/>
  <field name="res_model" column_invisible="1"/>
  <field name="date_deadline"/>
  <field name="res_name" string="Conta"/>
  <field name="activity_type_id" string="Etapa"/>
  <field name="summary"/>
  <field name="x_abm_partner_id" optional="show"/>
  <field name="user_id" widget="many2one_avatar_user"/>
  <button name="action_done" type="object" string="Feito" icon="fa-check" class="btn-link"/>
</list>"""

CAL = """<calendar date_start="date_deadline" color="user_id" mode="week" quick_create="false" create="false">
  <field name="res_name"/>
  <field name="summary"/>
  <field name="user_id" filters="1"/>
</calendar>"""

PIVOT = """<pivot>
  <field name="activity_type_id" type="row"/>
  <field name="user_id" type="col"/>
</pivot>"""

SEARCH = """<search>
  <field name="res_name" string="Conta"/>
  <field name="summary"/>
  <field name="x_abm_partner_id"/>
  <field name="activity_type_id" string="Etapa"/>
  <field name="user_id"/>
  <filter name="minhas" string="Minhas" domain="[('user_id', '=', uid)]"/>
  <separator/>
  <filter name="atrasadas" string="Atrasadas" domain="[('date_deadline', '&lt;', context_today().strftime('%Y-%m-%d'))]"/>
  <filter name="hoje" string="Hoje" domain="[('date_deadline', '=', context_today().strftime('%Y-%m-%d'))]"/>
  <filter name="ate_hoje" string="Atrasadas + hoje" domain="[('date_deadline', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
  <filter name="semana" string="Próximos 7 dias" domain="[('date_deadline', '&lt;=', (context_today() + relativedelta(days=7)).strftime('%Y-%m-%d'))]"/>
  <separator/>
  <filter name="preparacao" string="Preparação" domain="[('summary', 'ilike', '[Preparação]')]"/>
  <filter name="cadencia" string="Cadência" domain="[('summary', 'ilike', '[Cadência]')]"/>
  <filter name="quente" string="Quente / formulário" domain="['|', ('summary', 'ilike', '[Quente]'), ('summary', 'ilike', 'Formulário:')]"/>
  <filter name="rotinas" string="Rotinas" domain="[('res_model', '=', 'res.partner')]"/>
  <group>
    <filter name="g_etapa" string="Etapa" context="{'group_by': 'activity_type_id'}"/>
    <filter name="g_resp" string="Responsável" context="{'group_by': 'user_id'}"/>
    <filter name="g_conta" string="Conta" context="{'group_by': 'res_name'}"/>
    <filter name="g_prazo" string="Prazo (dia)" context="{'group_by': 'date_deadline:day'}"/>
  </group>
</search>"""

views={}
for name,typ,arch in [("view_atividade_kanban","kanban",KANBAN),("view_atividade_list","list",LIST),("view_atividade_calendar","calendar",CAL),("view_atividade_pivot","pivot",PIVOT),("view_atividade_search","search",SEARCH)]:
    views[typ]=upsert(name,"ir.ui.view",{"name":"mail.activity.%s.abm_setima"%typ,"model":"mail.activity","type":typ,"mode":"primary","priority":PRIO,"arch_db":arch})
act=upsert("action_atividades","ir.actions.act_window",{
  "name":"Atividades ABM","res_model":"mail.activity","view_mode":"kanban,list,calendar,pivot",
  "domain":"[('activity_type_id.name', '=like', 'ABM · %')]",
  "context":"{'create': False}",
  "search_view_id":views["search"],
  "help":"<p>Todas as tarefas do processo ABM Sétima (tipos de atividade “ABM · …”).</p>"})
# liga cada modo à sua tela própria
old=call("ir.actions.act_window.view","search_read",domain=[["act_window_id","=",act]],fields=["id"])
if old: call("ir.actions.act_window.view","unlink",ids=[o["id"] for o in old])
for seq,mode in enumerate(["kanban","list","calendar","pivot"]):
    call("ir.actions.act_window.view","create",vals_list=[{"act_window_id":act,"view_mode":mode,"view_id":views[mode],"sequence":seq}])
menu=upsert("menu_atividades","ir.ui.menu",{"name":"Atividades ABM","parent_id":826,"sequence":3,"action":"ir.actions.act_window,%d"%act})
print("views",views,"action",act,"menu",menu)
