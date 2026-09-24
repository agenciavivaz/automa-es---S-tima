#!/usr/bin/env python3
"""
Fase 1 do ABM Sétima Montadoras no Odoo: estrutura.

Implementa as seções 1.1–1.10 da spec (CLAUDE_CODE_abm_setima_odoo.md),
adaptadas ao que já existe na base:
  - estágios novos SÓ na equipe ABM Setima (os antigos continuam no BrandSpot);
  - campos de contato que já existiam são reaproveitados (x_abm_papel,
    x_linkedin_url, x_email_status, x_abm_senioridade, x_abm_area);
  - o comitê continua sendo os contatos filhos da empresa (x_studio_comite),
    então não há x_abm_lead_id;
  - as atividades vão para a SDR (parâmetro abm.sdr_user_id).

Nada aqui envia mensagem nem cria automação ativa. Tudo idempotente, com
external id abm_setima.*. Dry-run por padrão; APLICAR=true grava.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, garantir, odoo, ref  # noqa: E402

EQUIPE = "ABM Setima"
SDR_LOGIN = "amanda@vivazagencia.com.br"

_cache_modelo = {}


def modelo_id(model):
    if model not in _cache_modelo:
        _cache_modelo[model] = odoo("ir.model", "search", domain=[["model", "=", model]])[0]
    return _cache_modelo[model]


def por_nome(model, nome, vals=None, extra_domain=None):
    """Acha pelo nome (registros que já podem existir, ex.: origens UTM) ou cria."""
    r = odoo(model, "search", domain=[["name", "=", nome]] + (extra_domain or []), limit=1)
    if r:
        return r[0]
    if not APLICAR:
        print(f"  + criaria {model}: {nome}")
        return None
    rid = odoo(model, "create", vals_list=[{"name": nome, **(vals or {})}])[0]
    print(f"  + criado {model} #{rid}: {nome}")
    return rid


def sel(*pares):
    return [(0, 0, {"value": v, "name": n, "sequence": i}) for i, (v, n) in enumerate(pares)]


def campo(xmlid, model, name, ttype, descricao, **extra):
    vals = {"model_id": modelo_id(model), "name": name, "ttype": ttype,
            "field_description": descricao, "state": "manual", **extra}
    existente = odoo("ir.model.fields", "search", domain=[["model", "=", model], ["name", "=", name]])
    if existente:
        print(f"  = campo {model}.{name} já existe")
        return existente[0]
    return garantir(xmlid, "ir.model.fields", vals)


# ---------------------------------------------------------------------------
# 1.1 Estágios, tags e UTM
# ---------------------------------------------------------------------------
ESTAGIOS = [
    ("stage_alvo", "Alvo", False),
    ("stage_aquecendo", "Aquecendo", False),
    ("stage_engajada", "Engajada", False),
    ("stage_em_cadencia", "Em cadência", False),
    ("stage_conversa", "Conversa", False),
    ("stage_reuniao_agendada", "Reunião agendada", False),
    ("stage_reuniao_realizada", "Reunião realizada", False),
    ("stage_nutricao", "Nutrição", True),
    ("stage_descartada", "Descartada", True),
    ("stage_cliente_expansao", "Cliente – expansão", True),
]

TAGS = [("tag_abm", "ABM Sétima"), ("tag_trilha_sem", "Trilha: sem configurador"),
        ("tag_trilha_fraco", "Trilha: configurador fraco"), ("tag_cliente", "Conta cliente")]


def estrutura_pipeline(team_id):
    print("1.1 Estágios, tags e UTM")
    for i, (xid, nome, dobrado) in enumerate(ESTAGIOS):
        garantir(xid, "crm.stage", {"name": nome, "sequence": 200 + i * 10, "fold": dobrado,
                                     "is_won": False, "team_ids": [(6, 0, [team_id])]})
    for xid, nome in TAGS:
        existente = odoo("crm.tag", "search", domain=[["name", "=", nome]])
        if existente:
            print(f"  = tag {nome} já existe")
        else:
            garantir(xid, "crm.tag", {"name": nome})
    por_nome("utm.campaign", "ABM Sétima Montadoras")
    for origem in ("LinkedIn", "Site", "E-mail 1:1"):
        por_nome("utm.source", origem)
    for meio in ("Paid Social", "ABM 1:1"):
        por_nome("utm.medium", meio)


# ---------------------------------------------------------------------------
# 1.5 / 1.6 Modelo de sinal
# ---------------------------------------------------------------------------
PONTOS = {
    "li_impressoes_semana": 5, "li_cliques": 10, "li_reacao_post": 15,
    "li_conexao_aceita": 15, "li_dm_resposta": 30, "visita_dominio": 10,
    "visita_alta_intencao": 15, "email_resposta": 30, "formulario": 50,
    "ligacao_conversa": 30, "outro": 0,
}
TIPOS_SINAL = [
    ("li_impressoes_semana", "Conta com 50+ impressões na semana"),
    ("li_cliques", "Cliques da conta no demográfico"),
    ("li_reacao_post", "Reagiu ou comentou post do especialista"),
    ("li_conexao_aceita", "Conexão aceita"),
    ("li_dm_resposta", "Respondeu DM"),
    ("visita_dominio", "Visita ao site (Apollo)"),
    ("visita_alta_intencao", "Visitou cases, calculadora ou contato"),
    ("email_resposta", "Respondeu e-mail"),
    ("formulario", "Formulário, Lead Gen ou PDF da calculadora"),
    ("ligacao_conversa", "Ligação com conversa"),
    ("outro", "Outro"),
]


def modelo_sinal():
    print("1.5 Modelo Sinal ABM")
    if odoo("ir.model", "search", domain=[["model", "=", "x_abm_sinal"]]):
        print("  = modelo x_abm_sinal já existe")
    else:
        garantir("model_sinal", "ir.model", {
            "name": "Sinal ABM", "model": "x_abm_sinal", "state": "manual",
            "field_id": [(0, 0, {"name": "x_name", "ttype": "char", "field_description": "Resumo",
                                 "state": "manual"})],
        })
    if not APLICAR and not odoo("ir.model", "search", domain=[["model", "=", "x_abm_sinal"]]):
        print("  + criaria os campos do sinal (x_data, x_lead_id, x_partner_id, x_tipo, x_origem, "
              "x_pontos, x_ativo, x_detalhe), acessos e menu")
        return
    m = "x_abm_sinal"
    campo("field_sinal_data", m, "x_data", "datetime", "Data", store=True, readonly=False,
          depends="x_tipo",  # dispara o compute na criação (data padrão = agora)
          compute="for r in self:\n    r['x_data'] = r.x_data or datetime.datetime.now()")
    campo("field_sinal_lead", m, "x_lead_id", "many2one", "Conta", relation="crm.lead",
          required=True, on_delete="cascade")
    campo("field_sinal_partner", m, "x_partner_id", "many2one", "Contato", relation="res.partner",
          on_delete="set null")
    campo("field_sinal_tipo", m, "x_tipo", "selection", "Tipo", required=True,
          selection_ids=sel(*TIPOS_SINAL))
    campo("field_sinal_origem", m, "x_origem", "selection", "Origem", selection_ids=sel(
        ("linkedin_ads", "LinkedIn Ads"), ("linkedin_manual", "LinkedIn (manual)"),
        ("apollo_manual", "Apollo (manual)"), ("site", "Site"), ("email", "E-mail"),
        ("whatsapp", "WhatsApp"), ("formulario", "Formulário"), ("ligacao", "Ligação")))
    # Pesos editáveis aqui (ou em Configurações → Técnico → Campos → x_pontos).
    campo("field_sinal_pontos", m, "x_pontos", "integer", "Pontos", store=True, readonly=True,
          depends="x_tipo",
          compute=f"PONTOS = {PONTOS!r}\nfor r in self:\n    r['x_pontos'] = PONTOS.get(r.x_tipo, 0)")
    campo("field_sinal_ativo", m, "x_ativo", "boolean", "Ativo (conta no score)")
    campo("field_sinal_detalhe", m, "x_detalhe", "text", "Detalhe")
    if APLICAR:
        odoo("ir.default", "set", model_name=m, field_name="x_ativo", value=True)

    mid = modelo_id(m)
    garantir("access_sinal_vendedor", "ir.model.access", {
        "name": "x_abm_sinal vendedor", "model_id": mid,
        "group_id": ref("sales_team.group_sale_salesman"),
        "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": False})
    garantir("access_sinal_admin", "ir.model.access", {
        "name": "x_abm_sinal admin", "model_id": mid, "group_id": ref("base.group_system"),
        "perm_read": True, "perm_write": True, "perm_create": True, "perm_unlink": True})


# ---------------------------------------------------------------------------
# 1.2 / 1.3 / 1.4 Campos na conta, no contato e na atividade
# ---------------------------------------------------------------------------
def campos_conta():
    print("1.2 Campos na conta (crm.lead)")
    m = "crm.lead"
    campo("field_lead_dominio", m, "x_abm_dominio", "char", "ABM · Domínio")
    campo("field_lead_dominios_extra", m, "x_abm_dominios_extra", "char", "ABM · Outros domínios")
    campo("field_lead_linkedin_empresa", m, "x_abm_linkedin_empresa", "char", "ABM · Nome no LinkedIn")
    campo("field_lead_tier", m, "x_abm_tier", "selection", "ABM · Tier",
          selection_ids=sel(("1", "Tier 1"), ("2", "Tier 2"), ("3", "Tier 3")))
    campo("field_lead_trilha", m, "x_abm_trilha", "selection", "ABM · Trilha", selection_ids=sel(
        ("sem_config", "Sem configurador"), ("config_fraco", "Configurador fraco"),
        ("a_definir", "A definir")))
    campo("field_lead_cad_status", m, "x_abm_cadencia_status", "selection", "ABM · Cadência",
          selection_ids=sel(("nao_iniciada", "Não iniciada"), ("ativa", "Ativa"),
                            ("pausada", "Pausada"), ("concluida", "Concluída")))
    campo("field_lead_cad_inicio", m, "x_abm_cadencia_inicio", "date", "ABM · Início da cadência")
    campo("field_lead_onda", m, "x_abm_onda", "integer", "ABM · Onda")
    campo("field_lead_asset", m, "x_abm_asset_url", "char", "ABM · Asset (URL)")
    campo("field_lead_dossie", m, "x_abm_dossie_url", "char", "ABM · Dossiê (URL)")
    campo("field_lead_link_email", m, "x_abm_link_email", "char", "ABM · Link e-mail")
    campo("field_lead_link_linkedin", m, "x_abm_link_linkedin", "char", "ABM · Link LinkedIn")
    campo("field_lead_link_whatsapp", m, "x_abm_link_whatsapp", "char", "ABM · Link WhatsApp")
    if not odoo("ir.model", "search", domain=[["model", "=", "x_abm_sinal"]]):
        print("  + criaria x_abm_sinal_ids, x_abm_score, x_abm_faixa, x_abm_ultimo_sinal_data, "
              "x_abm_ref_inatividade (dependem do modelo de sinal)")
        return
    campo("field_lead_sinais", m, "x_abm_sinal_ids", "one2many", "ABM · Sinais",
          relation="x_abm_sinal", relation_field="x_lead_id")
    campo("field_lead_score", m, "x_abm_score", "integer", "ABM · Score", store=True, readonly=True,
          depends="x_abm_sinal_ids.x_pontos,x_abm_sinal_ids.x_ativo",
          compute="for r in self:\n"
                  "    r['x_abm_score'] = sum(s.x_pontos for s in r.x_abm_sinal_ids if s.x_ativo)")
    campo("field_lead_faixa", m, "x_abm_faixa", "selection", "ABM · Faixa", store=True,
          readonly=True, depends="x_abm_score",
          selection_ids=sel(("fria", "Fria"), ("engajada", "Engajada"), ("quente", "Quente")),
          compute="for r in self:\n"
                  "    s = r.x_abm_score or 0\n"
                  "    r['x_abm_faixa'] = 'quente' if s >= 60 else ('engajada' if s >= 30 else 'fria')")
    campo("field_lead_ultimo_sinal", m, "x_abm_ultimo_sinal_data", "datetime", "ABM · Último sinal",
          store=True, readonly=True, depends="x_abm_sinal_ids.x_data",
          compute="for r in self:\n"
                  "    datas = [s.x_data for s in r.x_abm_sinal_ids if s.x_data]\n"
                  "    r['x_abm_ultimo_sinal_data'] = max(datas) if datas else False")
    campo("field_lead_ref_inatividade", m, "x_abm_ref_inatividade", "date",
          "ABM · Referência de inatividade", store=True, readonly=True,
          depends="x_abm_cadencia_inicio,x_abm_ultimo_sinal_data",
          compute="for r in self:\n"
                  "    datas = [d for d in (r.x_abm_cadencia_inicio,\n"
                  "             r.x_abm_ultimo_sinal_data and r.x_abm_ultimo_sinal_data.date()) if d]\n"
                  "    r['x_abm_ref_inatividade'] = max(datas) if datas else False")


def campos_contato():
    print("1.3 Campos no contato (res.partner)")
    m = "res.partner"
    campo("field_partner_prioridade", m, "x_abm_prioridade", "integer", "ABM · Prioridade")
    campo("field_partner_li_conexao", m, "x_abm_li_conexao", "selection", "ABM · Conexão LinkedIn",
          selection_ids=sel(("nao_enviado", "Não enviado"), ("enviado", "Enviado"),
                            ("aceito", "Aceito"), ("recusado_ou_expirado", "Recusado/expirado")))
    campo("field_partner_canal", m, "x_abm_canal_inicial", "selection", "ABM · Canal inicial",
          selection_ids=sel(("email_linkedin", "E-mail + LinkedIn"),
                            ("linkedin_primeiro", "LinkedIn primeiro"),
                            ("email_arriscado_linkedin", "E-mail arriscado, LinkedIn")))
    campo("field_partner_na_cadencia", m, "x_abm_na_cadencia", "boolean", "ABM · Na cadência")
    campo("field_partner_optout", m, "x_abm_optout", "boolean", "ABM · Opt-out")
    # x_abm_papel já existe; só falta a opção "Fora" que a spec usa.
    papel = odoo("ir.model.fields", "search", domain=[["model", "=", m], ["name", "=", "x_abm_papel"]])[0]
    if odoo("ir.model.fields.selection", "search", domain=[["field_id", "=", papel], ["value", "=", "Fora"]]):
        print("  = opção 'Fora' em x_abm_papel já existe")
    else:
        garantir("sel_papel_fora", "ir.model.fields.selection",
                 {"field_id": papel, "value": "Fora", "name": "Fora", "sequence": 99})

    print("1.4 Campo na atividade (mail.activity)")
    campo("field_activity_partner", "mail.activity", "x_abm_partner_id", "many2one",
          "ABM · Pessoa do comitê", relation="res.partner", on_delete="set null")


# ---------------------------------------------------------------------------
# 1.7 / 1.8 / 1.9 / 1.10 Atividades, modelos de e-mail, planos, rotina
# ---------------------------------------------------------------------------
TIPOS_ATIVIDADE = [
    ("act_dossie", "ABM · Dossiê da conta", "default", "fa-search",
     "Rodar o dossiê de guerrilha, definir a trilha, colar a URL no campo Dossiê."),
    ("act_validar_comite", "ABM · Validar comitê", "default", "fa-users",
     "Confirmar o cargo atual no LinkedIn e ajustar papel e prioridade no comitê (botão Editar comitê)."),
    ("act_asset", "ABM · Preparar asset", "default", "fa-cube",
     "Asset personalizado para o decisor (só após conexão aceita). Alinhar com o cliente/produção "
     "o que será enviado e colar a URL no campo Asset: isso gera a tarefa de envio para a SDR."),
    ("act_iniciar_cadencia", "ABM · Iniciar cadência", "default", "fa-play",
     "Revisar dossiê, trilha e asset. Marcar \"Na cadência\" em até 3 pessoas e mover para Em cadência."),
    ("act_li_interagir", "ABM · LinkedIn – Seguir/Interagir", "default", "fa-linkedin",
     "Seguir e reagir a 1 post relevante. Sem convite."),
    ("act_li_conectar", "ABM · LinkedIn – Conectar", "default", "fa-linkedin",
     "Convite com nota curta citando o dossiê. Ao concluir, marcar Conexão = Enviado."),
    ("act_li_mensagem", "ABM · LinkedIn – Mensagem", "default", "fa-linkedin",
     "Mensagem com valor ou asset. Sem pitch na primeira."),
    ("act_email", "ABM · E-mail", "default", "fa-envelope",
     "Enviar pelo chatter da conta, da caixa do SDR, usando o modelo indicado. "
     "Trocar o destinatário para a pessoa da tarefa."),
    ("act_ligacao", "ABM · Ligação", "phonecall", "fa-phone",
     "Roteiro de ligação e de voicemail."),
    ("act_whatsapp", "ABM · WhatsApp", "default", "fa-whatsapp",
     "Só com conversa prévia ou número vindo de formulário. Enviar pelo DataCrazy."),
    ("act_classificar", "ABM · Classificar resposta", "default", "fa-inbox",
     "Positiva: mover para Conversa. Negativa: marcar opt-out. Ausência: nada."),
    ("act_agendar", "ABM · Agendar reunião", "meeting", "fa-calendar", ""),
    ("act_preparar_reuniao", "ABM · Preparar reunião", "default", "fa-briefcase", ""),
]

NOTA_ROTINA = """
<p><b>Segunda-feira, 20 minutos</b></p>
<ol>
<li><b>LinkedIn Campaign Manager</b>, Dados demográficos → Empresa, últimos 7 dias. Para cada conta
com 50 ou mais impressões, registrar o sinal "Conta com 50+ impressões na semana". Para cada conta
com cliques, registrar "Cliques da conta". Anexar o CSV aqui.</li>
<li><b>Apollo</b>, Visitantes do site, últimos 7 dias. Para cada domínio de conta ABM, registrar
"Visita ao site". Se a visita foi em cases, calculadora ou contato, registrar "Visitou página de
alta intenção".</li>
<li><b>Posts do especialista.</b> Quem do comitê reagiu ou comentou? Registrar "Reagiu ou comentou
post".</li>
<li>Abrir o pipeline ABM e olhar quais contas mudaram de faixa.</li>
</ol>
"""

EMAILS = [
    ("E1", "Observação da conta", "Observação específica da conta (lançamento recente, configurador atual) + link."),
    ("E2", "Prova", "Case VW Tera em 3 linhas + uma pergunta."),
    ("E3", "Oferta", "Convite para 20 min: case + calculadora de ROI (sem asset personalizado)."),
    ("E4", "Encerramento", "Encerramento educado, porta aberta."),
]
TRILHAS = [("sem", "Sem configurador"), ("fraco", "Configurador fraco")]


def atividades_e_modelos(sdr_id):
    print("1.8 Modelos de e-mail (rascunhos, só para envio manual)")
    lead_mid = modelo_id("crm.lead")
    modelos = []
    for codigo, titulo, ideia in EMAILS:
        for slug, trilha in TRILHAS:
            body = (f"<p>[RASCUNHO {codigo} · {trilha} — reescrever. Ideia: {ideia}]</p>"
                    "<p>Olá, <!-- primeira linha personalizada obrigatória --></p>"
                    '<p>Link: <t t-out="object.x_abm_link_email or \'\'"/></p>'
                    '<p t-if="object.x_abm_asset_url">Material: <t t-out="object.x_abm_asset_url"/></p>')
            modelos.append(garantir(f"tmpl_{codigo.lower()}_{slug}", "mail.template", {
                "name": f"ABM · {codigo} · {trilha}", "model_id": lead_mid,
                "subject": f"{{{{ object.partner_id.name or object.name }}}} · {titulo}",
                "body_html": body, "auto_delete": False, "use_default_to": False,
            }))

    print("1.7 Tipos de atividade")
    for xid, nome, cat, icone, nota in TIPOS_ATIVIDADE:
        vals = {"name": nome, "res_model": "crm.lead", "category": cat, "icon": icone,
                "default_note": f"<p>{nota}</p>" if nota else False, "default_user_id": sdr_id}
        if xid == "act_email":
            vals["mail_template_ids"] = [(6, 0, [m for m in modelos if m])]
        garantir(xid, "mail.activity.type", vals)
    rotina = garantir("act_rotina", "mail.activity.type", {
        "name": "ABM · Rotina semanal", "category": "default", "icon": "fa-refresh",
        "default_note": NOTA_ROTINA, "default_user_id": sdr_id,
        "delay_count": 7, "delay_unit": "days", "delay_from": "current_date",
    })
    if rotina and APLICAR:  # encadeada a si mesma: concluir cria a próxima em 7 dias
        odoo("mail.activity.type", "write", ids=[rotina],
             vals={"chaining_type": "trigger", "triggered_next_type_id": rotina})

    print("1.9 Planos de atividade")
    def tpl(xid_tipo, dias, de="after_plan_date", resumo=False):
        return (0, 0, {"activity_type_id": ref(f"{MODULO}.{xid_tipo}"), "delay_count": dias,
                       "delay_unit": "days", "delay_from": de, "responsible_type": "other",
                       "responsible_id": sdr_id, "summary": resumo})
    if APLICAR:
        garantir("plan_preparacao_conta", "mail.activity.plan", {
            "name": "ABM – Preparação da conta", "res_model": "crm.lead",
            "template_ids": [tpl("act_dossie", 0), tpl("act_validar_comite", 1),
                             tpl("act_li_interagir", 2)]})
        garantir("plan_preparacao_reuniao", "mail.activity.plan", {
            "name": "ABM – Preparação de reunião", "res_model": "crm.lead",
            "template_ids": [tpl("act_preparar_reuniao", 1, "before_plan_date"),
                             tpl("act_email", 1, "before_plan_date", "Confirmação")]})
    else:
        print("  + criaria os planos 'ABM – Preparação da conta' e 'ABM – Preparação de reunião'")

    print("1.10 Registro de rotinas")
    parceiro = garantir("partner_rotinas", "res.partner", {"name": "ABM – Rotinas", "is_company": True})
    if parceiro and rotina and APLICAR and not odoo("mail.activity", "search", domain=[
            ["res_model", "=", "res.partner"], ["res_id", "=", parceiro],
            ["activity_type_id", "=", rotina]]):
        import datetime
        hoje = datetime.date.today()
        segunda = hoje + datetime.timedelta(days=(7 - hoje.weekday()) % 7 or 7)
        odoo("mail.activity", "create", vals_list=[{
            "res_model_id": modelo_id("res.partner"), "res_id": parceiro,
            "activity_type_id": rotina, "summary": "Rotina semanal ABM",
            "note": NOTA_ROTINA, "date_deadline": segunda.isoformat(), "user_id": sdr_id,
        }], context={"mail_activity_quick_update": True})
        print(f"  + rotina semanal agendada para {segunda} (SDR)")


FERIADOS = ",".join([
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-04-03", "2026-04-21", "2026-05-01",
    "2026-06-04", "2026-09-07", "2026-10-12", "2026-11-02", "2026-11-15", "2026-11-20",
    "2026-12-25",
    "2027-01-01", "2027-02-08", "2027-02-09", "2027-03-26", "2027-04-21", "2027-05-01",
    "2027-05-27", "2027-09-07", "2027-10-12", "2027-11-02", "2027-11-15", "2027-11-20",
    "2027-12-25",
])


def parametros(team_id, sdr_id):
    print("Parâmetros de sistema")
    for chave, valor in (("abm.feriados", FERIADOS), ("abm.sdr_user_id", str(sdr_id)),
                         ("abm.team_id", str(team_id))):
        if APLICAR:
            odoo("ir.config_parameter", "set_param", key=chave, value=valor)
        print(f"  {'=' if APLICAR else '~'} {chave}")


def main():
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    team = odoo("crm.team", "search_read", domain=[["name", "=", EQUIPE]], fields=["id"])
    sdr = odoo("res.users", "search", domain=[["login", "=", SDR_LOGIN]])
    if len(team) != 1 or len(sdr) != 1:
        raise SystemExit(f"Equipe ou SDR não encontrados: {team} {sdr}")
    team_id, sdr_id = team[0]["id"], sdr[0]
    estrutura_pipeline(team_id)
    modelo_sinal()
    campos_conta()
    campos_contato()
    atividades_e_modelos(sdr_id)
    parametros(team_id, sdr_id)
    if not APLICAR:
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")


if __name__ == "__main__":
    main()
