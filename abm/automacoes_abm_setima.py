#!/usr/bin/env python3
"""
Fase 2 do ABM Sétima: regras de automação A1–A15 (seções 4 e 5 da spec).

Todas nascem DESATIVADAS (active=False). Só fazem o que a spec permite:
mudar campos e estágio, criar/cancelar atividades, criar sinais, adicionar
seguidor e postar NOTA INTERNA. Nenhuma envia e-mail/SMS/WhatsApp nem chama
webhook. Atividades são criadas com mail_activity_quick_update, que suprime
o e-mail de "atividade atribuída".

Adaptações à base real (ver HISTORICO/fase 1):
  - responsável das atividades = SDR (parâmetro abm.sdr_user_id);
  - conta de um contato = oportunidade ABM cujo partner_id é a empresa do
    contato (não existe x_abm_lead_id);
  - A1 não cria as tarefas de preparação: devolve a conta para a fila
    (a ação agendada "ABM · Fila de preparação" libera aos poucos).

Idempotente (external ids abm_setima.auto_*). Uma nova execução atualiza o
código e os filtros, mas nunca ativa nada. Dry-run por padrão; APLICAR=true grava.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, garantir, odoo, ref  # noqa: E402
from estrutura_abm_setima import modelo_id  # noqa: E402

GESTOR_USER_ID = 22  # Diego

# ---------------------------------------------------------------------------
# Trechos comuns (o safe_eval não permite import nem função compartilhada)
# ---------------------------------------------------------------------------
CABECALHO = r'''
ICP = env['ir.config_parameter'].sudo()
team_id = int(ICP.get_param('abm.team_id'))
sdr_id = int(ICP.get_param('abm.sdr_user_id'))
gestor = env['res.users'].browse(int(ICP.get_param('abm.gestor_user_id') or 0))
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
hoje = datetime.date.today()
uteis = []
d = hoje
while len(uteis) < 40:
    if d.weekday() < 5 and d.isoformat() not in feriados:
        uteis.append(d)
    d += datetime.timedelta(days=1)
proximo_util = uteis[1] if uteis[0] == hoje else uteis[0]
QUIET = {'mail_activity_quick_update': True}
esc = lambda s: (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
nota = lambda rec, txt: rec.message_post(body=txt, message_type='comment', subtype_xmlid='mail.mt_note')
'''

# Gera as atividades da cadência para `escolhidos` da `conta` (5.1 passo 4–6).
GERAR_CADENCIA = r'''
    trilha = conta.x_abm_trilha or 'a_definir'
    rotulo = 'Configurador fraco' if trilha == 'config_fraco' else 'Sem configurador'
    if trilha == 'a_definir':
        conta.with_context(**QUIET).activity_schedule(
            'abm_setima.act_dossie', date_deadline=uteis[0], user_id=sdr_id,
            summary='Definir trilha antes do primeiro e-mail')
        notas.append('Trilha a definir: os e-mails usam o modelo "Sem configurador" até a trilha ser definida.')
    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', ''),
        (1, 'act_email', 'E-mail', 'E1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', ''),
        (4, 'act_email', 'E-mail', 'E2'),
        (6, 'act_ligacao', 'Ligação', ''),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem com asset', ''),
        (10, 'act_email', 'E-mail', 'E3'),
        (13, 'act_ligacao', 'Ligação', ''),
        (18, 'act_li_mensagem', 'LinkedIn – Follow-up', ''),
        (21, 'act_email', 'E-mail', 'E4'),
    ]
    total = 0
    for p in escolhidos:
        for dia, tipo, canal, email_cod in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito':
                continue
            if tipo == 'act_email' and (not p.email or p.x_email_status in ('Inválido', 'Indisponível')):
                continue
            if tipo == 'act_ligacao' and not p.phone:
                continue
            if tipo == 'act_email':
                link = conta.x_abm_link_email
            elif tipo.startswith('act_li'):
                link = conta.x_abm_link_linkedin
            else:
                link = ''
            html = '<p><b>%s</b> — %s<br/>Papel: %s · Prioridade: %s</p>' % (
                esc(p.name), esc(p.function), esc(p.x_abm_papel) or '-', p.x_abm_prioridade or '-')
            if p.x_linkedin_url:
                html += '<p>LinkedIn: <a href="%s" target="_blank">%s</a></p>' % (esc(p.x_linkedin_url), esc(p.x_linkedin_url))
            html += '<p>E-mail: %s (%s)<br/>Telefone: %s</p>' % (
                esc(p.email) or '-', esc(p.x_email_status) or 'sem status', esc(p.phone) or '-')
            if link:
                html += '<p>Link da conta: %s</p>' % esc(link)
            html += '<p>Asset: %s<br/>Dossiê: %s</p>' % (esc(conta.x_abm_asset_url) or '-', esc(conta.x_abm_dossie_url) or '-')
            if email_cod:
                html += '<p>Trilha: %s · Modelo: <b>ABM · %s · %s</b></p>' % (rotulo, email_cod, rotulo)
            if tipo == 'act_li_mensagem' and dia in (8, 18):
                html += '<p><i>Só se a conexão foi aceita; senão, marcar como feita.</i></p>'
            conta.with_context(**QUIET).activity_schedule(
                'abm_setima.' + tipo, date_deadline=uteis[dia - 1], user_id=sdr_id,
                summary='[Cadência] D%s %s – %s (%s)' % (dia, canal, p.name, p.function or '-'),
                note=html, x_abm_partner_id=p.id)
            total += 1
    notas.append('Onda %s: %s na cadência, %s atividade(s) criada(s).' % (
        conta.x_abm_onda, ', '.join(escolhidos.mapped('name')) or 'ninguém', total))
    nota(conta, '<br/>'.join(notas))
'''

ELEGIVEIS = r'''
    empresa = conta.partner_id.commercial_partner_id
    elegiveis = empresa.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9 and p.x_abm_papel != 'Fora')
    ordem = lambda p: (p.x_abm_prioridade or 3, 0 if p.x_email_status in ('Verificado', 'Válido') else 1, p.name or '')
'''

CODIGO = {
    # A1 — entrou em Alvo: volta para a fila de preparação
    "a1": CABECALHO + r'''
for conta in records:
    if conta.x_abm_preparacao != 'liberada':
        conta.write({'x_abm_preparacao': 'fila'})
''',
    # A2 / A3 — ficou engajada (score) ou 21 dias aquecendo
    "a2": CABECALHO + r'''
for conta in records:
    conta.write({'stage_id': env.ref('abm_setima.stage_engajada').id})
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_iniciar_cadencia', date_deadline=uteis[0], user_id=sdr_id,
        summary='Iniciar cadência – %s' % conta.name)
''',
    # A4 — conta quente
    "a4": CABECALHO + r'''
for conta in records:
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_ligacao', date_deadline=hoje, user_id=sdr_id,
        summary='Conta quente: ligar para o decisor hoje')
    if gestor:
        conta.message_subscribe(partner_ids=gestor.partner_id.ids)
''',
    # A5 — início da cadência (5.1)
    "a5": CABECALHO + r'''
for conta in records:
    notas = []
''' + ELEGIVEIS + r'''
    escolhidos = elegiveis.filtered(lambda p: p.x_abm_na_cadencia)
    if not escolhidos:
        escolhidos = elegiveis.filtered(lambda p: p.x_abm_prioridade in (1, 2)).sorted(ordem)[:3]
        escolhidos.write({'x_abm_na_cadencia': True})
        notas.append('Ninguém marcado "Na cadência": escolhidos automaticamente %s.' % ', '.join(escolhidos.mapped('name')))
    conta.write({'x_abm_cadencia_status': 'ativa', 'x_abm_cadencia_inicio': hoje, 'x_abm_onda': 1})
''' + GERAR_CADENCIA,
    # A6 — parar cadência (5.2)
    "a6": CABECALHO + r'''
nutricao = env.ref('abm_setima.stage_nutricao')
for conta in records:
    pendentes = conta.activity_ids.filtered(lambda a: (a.summary or '').startswith('[Cadência]'))
    n = len(pendentes)
    pendentes.unlink()
    conta.write({'x_abm_cadencia_status': 'concluida' if conta.stage_id == nutricao else 'pausada'})
    nota(conta, 'Cadência parada (%s): %s atividade(s) cancelada(s).' % (conta.stage_id.name, n))
''',
    # A7 — conversa
    "a7": CABECALHO + r'''
for conta in records:
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_agendar', date_deadline=uteis[0], user_id=sdr_id,
        summary='Agendar reunião – %s' % conta.name)
''',
    # A8 — reunião agendada
    "a8": CABECALHO + r'''
for conta in records:
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_preparar_reuniao', date_deadline=uteis[0], user_id=sdr_id,
        summary='Preparar reunião – %s' % conta.name)
    if gestor:
        conta.message_subscribe(partner_ids=gestor.partner_id.ids)
''',
    # A9 — 35 dias sem sinal em cadência → Nutrição (A6 dispara em seguida)
    "a9": CABECALHO + r'''
for conta in records:
    conta.write({'stage_id': env.ref('abm_setima.stage_nutricao').id})
''',
    # A10 — e-mail recebido (5.3)
    "a10": CABECALHO + r'''
for conta in records:
    msg = conta.message_ids.filtered(lambda m: m.message_type == 'email')[:1]
    if not msg:
        continue
    remetente = (msg.email_from or '').lower()
    if '<' in remetente:
        remetente = remetente.split('<')[-1].split('>')[0]
    dominio = remetente.split('@')[-1] if '@' in remetente else ''
    empresa = conta.partner_id.commercial_partner_id
    contato = env['res.partner']
    if msg.author_id and msg.author_id.commercial_partner_id == empresa and msg.author_id != empresa:
        contato = msg.author_id
    elif remetente:
        contato = empresa.child_ids.filtered(lambda p: (p.email or '').lower() == remetente)[:1]
    dominios = [x.strip().lower() for x in ((conta.x_abm_dominio or '') + ',' + (conta.x_abm_dominios_extra or '')).split(',') if x.strip()]
    if not contato and dominio not in dominios:
        continue
    env['x_abm_sinal'].create({
        'x_name': 'Resposta de e-mail – %s' % (contato.name or remetente),
        'x_lead_id': conta.id, 'x_partner_id': contato.id or False,
        'x_tipo': 'email_resposta', 'x_origem': 'email', 'x_detalhe': msg.subject or ''})
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_classificar', date_deadline=uteis[0], user_id=sdr_id,
        summary='Classificar resposta – %s' % (contato.name or remetente),
        x_abm_partner_id=contato.id or False)
''',
    # A11 — conexão aceita (5.4)
    "a11": CABECALHO + r'''
for p in records:
    conta = env['crm.lead'].search([('team_id', '=', team_id), ('partner_id', '=', p.commercial_partner_id.id)], limit=1)
    if not conta:
        continue
    env['x_abm_sinal'].create({
        'x_name': 'Conexão aceita – %s' % p.name, 'x_lead_id': conta.id, 'x_partner_id': p.id,
        'x_tipo': 'li_conexao_aceita', 'x_origem': 'linkedin_manual'})
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_li_mensagem', date_deadline=proximo_util, user_id=sdr_id,
        summary='[Cadência] Mensagem pós-conexão – %s' % p.name, x_abm_partner_id=p.id)
''',
    # A12 — opt-out (5.5)
    "a12": CABECALHO + r'''
for p in records:
    atividades = env['mail.activity'].search([('x_abm_partner_id', '=', p.id)])
    n = len(atividades)
    atividades.unlink()
    p.write({'x_abm_na_cadencia': False})
    conta = env['crm.lead'].search([('team_id', '=', team_id), ('partner_id', '=', p.commercial_partner_id.id)], limit=1)
    if conta:
        nota(conta, 'Opt-out de %s: %s atividade(s) cancelada(s).' % (esc(p.name), n))
''',
    # A13 — sinal expira
    "a13": r'''
records.write({'x_ativo': False})
''',
    # A14 — onda 2 (5.6)
    "a14": CABECALHO + r'''
for conta in records:
    if conta.x_abm_onda != 1 or not conta.x_abm_cadencia_inicio:
        continue
    respostas = conta.x_abm_sinal_ids.filtered(
        lambda s: s.x_tipo in ('email_resposta', 'li_dm_resposta') and s.x_data and s.x_data.date() >= conta.x_abm_cadencia_inicio)
    if respostas:
        continue
    notas = []
''' + ELEGIVEIS + r'''
    escolhidos = elegiveis.filtered(lambda p: not p.x_abm_na_cadencia and p.x_abm_prioridade in (2, 3)).sorted(ordem)[:2]
    conta.write({'x_abm_onda': 2})
    if not escolhidos:
        nota(conta, 'Onda 2: não há mais contatos elegíveis no comitê.')
        continue
    escolhidos.write({'x_abm_na_cadencia': True})
''' + GERAR_CADENCIA,
    # A15 — formulário de conta-alvo (5.7)
    "a15": CABECALHO + r'''
for lead in records:
    email = (lead.email_from or '').lower()
    if '<' in email:
        email = email.split('<')[-1].split('>')[0]
    if lead.team_id.id == team_id or '@' not in email:
        continue
    dominio = email.split('@')[-1]
    conta = env['crm.lead'].search([('team_id', '=', team_id), '|',
                                    ('x_abm_dominio', '=', dominio),
                                    ('x_abm_dominios_extra', 'ilike', dominio)], limit=1)
    if not conta:
        continue
    env['x_abm_sinal'].create({
        'x_name': 'Formulário – %s' % (lead.contact_name or email), 'x_lead_id': conta.id,
        'x_tipo': 'formulario', 'x_origem': 'formulario',
        'x_detalhe': '%s <%s> · lead #%s' % (lead.contact_name or lead.name, email, lead.id)})
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_ligacao', date_deadline=hoje, user_id=sdr_id,
        summary='Formulário: contato em até 1h útil – %s' % (lead.contact_name or email))
    nota(conta, 'Formulário de %s (%s): <a href="/odoo/crm/%s">lead de inbound #%s</a>.' % (esc(lead.contact_name or lead.name), esc(email), lead.id, lead.id))
    nota(lead, 'Pessoa de conta ABM: <a href="/odoo/crm/%s">%s</a>.' % (conta.id, esc(conta.name)))
''',
}


def regras():
    """Definição das 15 regras. Estágios por id (vindos dos external ids)."""
    s = {k: ref(f"{MODULO}.stage_{k}") for k in (
        "alvo", "aquecendo", "engajada", "em_cadencia", "conversa", "reuniao_agendada",
        "nutricao", "descartada", "cliente_expansao")}
    t = int(odoo("ir.config_parameter", "get_param", key="abm.team_id"))
    equipe = f"('team_id', '=', {t})"

    def entrou(*estagios):
        ids = [s[e] for e in estagios]
        return {"trigger": "on_write", "campos": ["stage_id"],
                "filter_pre_domain": f"[('stage_id', 'not in', {ids})]",
                "filter_domain": f"[{equipe}, ('stage_id', 'in', {ids})]"}

    return [
        ("a1", "A1 · Entrou em Alvo", "crm.lead", entrou("alvo")),
        ("a2", "A2 · Ficou engajada", "crm.lead", {
            "trigger": "on_write", "campos": ["x_abm_faixa"],
            "filter_pre_domain": "[('x_abm_faixa', 'in', [False, 'fria'])]",
            "filter_domain": f"[{equipe}, ('x_abm_faixa', 'in', ['engajada', 'quente']), "
                             f"('stage_id', 'in', {[s['alvo'], s['aquecendo'], s['nutricao']]})]"}),
        ("a3", "A3 · 21 dias aquecendo", "crm.lead", {
            "trigger": "on_time", "data": "date_last_stage_update", "dias": 21,
            "filter_domain": f"[{equipe}, ('stage_id', '=', {s['aquecendo']})]"}),
        ("a4", "A4 · Conta quente", "crm.lead", {
            "trigger": "on_write", "campos": ["x_abm_faixa"],
            "filter_pre_domain": "[('x_abm_faixa', '!=', 'quente')]",
            "filter_domain": f"[{equipe}, ('x_abm_faixa', '=', 'quente'), ('stage_id', 'not in', "
                             f"{[s['conversa'], s['reuniao_agendada'], s['descartada'], s['cliente_expansao']]})]"}),
        ("a5", "A5 · Início da cadência", "crm.lead", entrou("em_cadencia")),
        ("a6", "A6 · Parar cadência", "crm.lead", entrou("conversa", "nutricao", "descartada")),
        ("a7", "A7 · Conversa", "crm.lead", entrou("conversa")),
        ("a8", "A8 · Reunião agendada", "crm.lead", entrou("reuniao_agendada")),
        ("a9", "A9 · Cadência sem sinal", "crm.lead", {
            "trigger": "on_time", "data": "x_abm_ref_inatividade", "dias": 35,
            "filter_domain": f"[{equipe}, ('stage_id', '=', {s['em_cadencia']})]"}),
        ("a10", "A10 · E-mail recebido", "crm.lead", {
            "trigger": "on_message_received", "filter_domain": f"[{equipe}]"}),
        ("a11", "A11 · Conexão aceita", "res.partner", {
            "trigger": "on_write", "campos": ["x_abm_li_conexao"],
            "filter_pre_domain": "[('x_abm_li_conexao', '!=', 'aceito')]",
            "filter_domain": "[('x_abm_li_conexao', '=', 'aceito'), ('parent_id', '!=', False)]"}),
        ("a12", "A12 · Opt-out", "res.partner", {
            "trigger": "on_write", "campos": ["x_abm_optout"],
            "filter_pre_domain": "[('x_abm_optout', '=', False)]",
            "filter_domain": "[('x_abm_optout', '=', True)]"}),
        ("a13", "A13 · Sinal expira", "x_abm_sinal", {
            "trigger": "on_time", "data": "x_data", "dias": 30,
            "filter_domain": "[('x_ativo', '=', True)]"}),
        ("a14", "A14 · Onda 2", "crm.lead", {
            "trigger": "on_time", "data": "x_abm_cadencia_inicio", "dias": 21,
            "filter_domain": f"[{equipe}, ('stage_id', '=', {s['em_cadencia']}), ('x_abm_onda', '=', 1)]"}),
        ("a15", "A15 · Formulário de conta-alvo", "crm.lead", {
            "trigger": "on_create",
            "filter_domain": f"[('team_id', '!=', {t}), ('email_from', '!=', False)]"}),
    ]


def campo_id(model, nome):
    return odoo("ir.model.fields", "search", domain=[["model", "=", model], ["name", "=", nome]])[0]


def main():
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    if APLICAR and not odoo("ir.config_parameter", "get_param", key="abm.gestor_user_id"):
        odoo("ir.config_parameter", "set_param", key="abm.gestor_user_id", value=str(GESTOR_USER_ID))

    for chave, nome, model, cfg in regras():
        mid = modelo_id(model)
        vals = {
            "name": f"ABM · {nome}", "model_id": mid, "trigger": cfg["trigger"],
            "filter_domain": cfg.get("filter_domain", False),
            "filter_pre_domain": cfg.get("filter_pre_domain", False),
            "trigger_field_ids": [(6, 0, [campo_id(model, c) for c in cfg.get("campos", [])])],
        }
        if cfg["trigger"] == "on_time":
            vals.update({"trg_date_id": campo_id(model, cfg["data"]), "trg_date_range": cfg["dias"],
                         "trg_date_range_type": "day", "trg_date_range_mode": "after"})
        codigo = CODIGO["a2" if chave == "a3" else chave]
        existente = ref(f"{MODULO}.auto_{chave}")
        if existente:
            if APLICAR:  # atualiza filtros e código, mas não mexe em active
                odoo("base.automation", "write", ids=[existente], vals=vals)
                srv = odoo("base.automation", "read", ids=[existente], fields=["action_server_ids"])[0]["action_server_ids"]
                odoo("ir.actions.server", "write", ids=srv, vals={"code": codigo})
            print(f"  ~ {nome} atualizada (base.automation #{existente})")
            continue
        garantir(f"auto_{chave}", "base.automation", {
            **vals, "active": False,
            "action_server_ids": [(0, 0, {"name": f"ABM · {nome}", "model_id": mid,
                                          "state": "code", "code": codigo})],
        })
    if not APLICAR:
        print("DRY-RUN: nada foi gravado. Rode com APLICAR=true.")


if __name__ == "__main__":
    main()
