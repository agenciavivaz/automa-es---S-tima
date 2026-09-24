#!/usr/bin/env python3
"""
Fila de preparação das contas ABM Sétima (liberação gradual para a SDR).

Em vez de aplicar o plano "Preparação da conta" nas 26 contas de uma vez
(~100 tarefas no mesmo dia), uma ação agendada dentro do Odoo libera as contas
aos poucos:

  - roda todo dia às 7h; em fim de semana e feriado (abm.feriados) não faz nada;
  - candidatas: contas da equipe ABM em "Alvo" com preparação "Na fila";
  - ordem da fila: tier (1 primeiro) → força do comitê (3 × decisores +
    influenciadores, sem opt-out e sem "fora") → nome;
  - libera até abm.preparacao_contas_dia contas por dia (padrão 2);
  - FREIO: se a SDR já tem abm.preparacao_limite_pendentes (padrão 10) ou mais
    atividades ABM vencidas/para hoje, não libera nada naquele dia;
  - cada conta liberada recebe, em dias úteis: Dossiê (D0), Validar comitê
    (D1), LinkedIn – Seguir/Interagir (D2) e Preparar asset (D5), todas para
    a SDR, sem notificação por e-mail; nota interna na conta.

Com 2 contas/dia a SDR recebe no máximo ~8 tarefas de preparação por dia
(cada conta põe 1 tarefa em 4 dias diferentes).

A ação agendada nasce DESATIVADA (regra 4 da spec). Para simular sem gravar:
    python abm/fila_preparacao_abm_setima.py --simular
Para criar/atualizar os registros no Odoo: APLICAR=true.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, MODULO, garantir, odoo, ref  # noqa: E402
from estrutura_abm_setima import campo, modelo_id, sel  # noqa: E402

PARAMETROS = {"abm.preparacao_contas_dia": "2", "abm.preparacao_limite_pendentes": "10"}

# Código executado pelo Odoo (safe_eval). Sem import nem def: só o que o
# sandbox das ações de servidor permite. Com context abm_simular=True devolve o
# plano numa notificação e não grava nada.
CODIGO = r'''
ICP = env['ir.config_parameter'].sudo()
simular = env.context.get('abm_simular')
hoje = datetime.date.today()
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
team_id = int(ICP.get_param('abm.team_id'))
sdr = env['res.users'].browse(int(ICP.get_param('abm.sdr_user_id')))
por_dia = int(ICP.get_param('abm.preparacao_contas_dia') or 2)
limite = int(ICP.get_param('abm.preparacao_limite_pendentes') or 10)

# próximos dias úteis a partir de hoje (inclusive)
uteis = []
d = hoje
while len(uteis) < 10:
    if d.weekday() < 5 and d.isoformat() not in feriados:
        uteis.append(d)
    d += datetime.timedelta(days=1)

relatorio = []
if uteis[0] != hoje and not simular:
    relatorio.append('Hoje não é dia útil: nada liberado.')
else:
    tipos_abm = env['mail.activity.type'].search([('name', '=like', 'ABM · %')])
    pendentes = env['mail.activity'].search_count([
        ('user_id', '=', sdr.id), ('res_model', '=', 'crm.lead'),
        ('activity_type_id', 'in', tipos_abm.ids), ('date_deadline', '<=', hoje)])
    alvo = env.ref('abm_setima.stage_alvo')
    candidatas = model.search([
        ('team_id', '=', team_id), ('stage_id', '=', alvo.id),
        ('x_abm_preparacao', 'in', [False, 'fila'])])
    fila = []
    for conta in candidatas:
        comite = conta.partner_id.child_ids.filtered(
            lambda p: not p.x_abm_optout and p.x_abm_prioridade in (1, 2))
        forca = 3 * len(comite.filtered(lambda p: p.x_abm_prioridade == 1)) + \
            len(comite.filtered(lambda p: p.x_abm_prioridade == 2))
        tier = int(conta.x_abm_tier or 9)
        fila.append((tier, -forca, conta.name, conta))
    fila.sort(key=lambda x: (x[0], x[1], x[2]))
    relatorio.append('Pendentes da SDR (vencidas/hoje): %s de limite %s' % (pendentes, limite))
    if pendentes >= limite:
        liberar = []
        relatorio.append('Freio ativo: nada liberado hoje.')
    else:
        liberar = [x[3] for x in fila[:por_dia]]
    etapas = [('abm_setima.act_dossie', 0, 'Dossiê da conta'),
              ('abm_setima.act_validar_comite', 1, 'Validar comitê'),
              ('abm_setima.act_li_interagir', 2, 'LinkedIn – seguir e interagir'),
              ('abm_setima.act_asset', 5, 'Preparar asset')]
    for conta in liberar:
        linhas = []
        for xmlid, du, resumo in etapas:
            prazo = uteis[du]
            linhas.append('%s em %s' % (resumo, prazo.strftime('%d/%m')))
            if not simular:
                conta.with_context(mail_activity_quick_update=True).activity_schedule(
                    xmlid, date_deadline=prazo, user_id=sdr.id,
                    summary='[Preparação] %s – %s' % (resumo, conta.name))
        if not simular:
            conta.write({'x_abm_preparacao': 'liberada', 'x_abm_preparacao_inicio': hoje})
            conta.message_post(
                body='Preparação da conta liberada pela fila ABM: %s.' % '; '.join(linhas),
                message_type='comment', subtype_xmlid='mail.mt_note')
        relatorio.append('Liberada: %s (%s)' % (conta.name, '; '.join(linhas)))
    restantes = [x[2] for x in fila if x[3] not in liberar]
    relatorio.append('Na fila (%s): %s' % (len(restantes), ', '.join(restantes)))
log('\n'.join(relatorio))
if simular:
    action = {'type': 'ir.actions.client', 'tag': 'display_notification',
              'params': {'title': 'Fila ABM (simulação)', 'message': '\n'.join(relatorio)}}
'''


def main():
    simular = "--simular" in sys.argv
    print(f"Modo: {'APLICAR' if APLICAR else 'DRY-RUN'}")
    m = "crm.lead"
    campo("field_lead_preparacao", m, "x_abm_preparacao", "selection", "ABM · Preparação",
          selection_ids=sel(("fila", "Na fila"), ("liberada", "Liberada"), ("pular", "Não preparar")))
    campo("field_lead_preparacao_inicio", m, "x_abm_preparacao_inicio", "date",
          "ABM · Preparação liberada em")

    for chave, valor in PARAMETROS.items():
        atual = odoo("ir.config_parameter", "get_param", key=chave)
        if APLICAR and not atual:  # não sobrescreve ajuste feito na tela
            odoo("ir.config_parameter", "set_param", key=chave, value=valor)
        print(f"  {'=' if atual else '+'} {chave} = {atual or valor}")

    acao_vals = {"name": "ABM · Fila de preparação", "model_id": modelo_id(m),
                 "state": "code", "code": CODIGO}
    cron = ref(f"{MODULO}.cron_fila_preparacao")
    if cron:
        if APLICAR:
            srv = odoo("ir.cron", "read", ids=[cron], fields=["ir_actions_server_id"])[0]["ir_actions_server_id"][0]
            odoo("ir.actions.server", "write", ids=[srv], vals={"code": CODIGO})
        print(f"  ~ código da ação agendada atualizado (ir.cron #{cron})")
    else:
        cron = garantir("cron_fila_preparacao", "ir.cron", {
            **acao_vals, "interval_number": 1, "interval_type": "days",
            "nextcall": "2026-09-28 10:00:00",  # 7h de Brasília, próxima segunda
            "user_id": 22, "active": False,
        })

    if APLICAR:
        contas = odoo("crm.lead", "search", domain=[
            ["team_id", "=", int(odoo("ir.config_parameter", "get_param", key="abm.team_id"))],
            ["stage_id", "=", ref(f"{MODULO}.stage_alvo")], ["x_abm_preparacao", "=", False]])
        if contas:
            odoo("crm.lead", "write", ids=contas, vals={"x_abm_preparacao": "fila"})
            print(f"  ~ {len(contas)} contas colocadas na fila")

    if simular and cron:
        srv = odoo("ir.cron", "read", ids=[cron], fields=["ir_actions_server_id"])[0]["ir_actions_server_id"][0]
        r = odoo("ir.actions.server", "run", ids=[srv], context={"abm_simular": True})
        print("\n--- Simulação (nada gravado) ---\n" + r["params"]["message"])


if __name__ == "__main__":
    main()
