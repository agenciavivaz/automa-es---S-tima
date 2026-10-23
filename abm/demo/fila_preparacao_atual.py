
ICP = env['ir.config_parameter'].sudo()
simular = env.context.get('abm_simular')
hoje = datetime.date.today()
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
team_id = int(ICP.get_param('abm.team_id'))
sdr = env['res.users'].browse(int(ICP.get_param('abm.sdr_user_id')))
por_dia = int(ICP.get_param('abm.preparacao_contas_dia') or 4)
limite = int(ICP.get_param('abm.preparacao_limite_pendentes') or 10)


SEN_PREP = {'C suite': 0, 'Vp': 1, 'Owner': 1, 'Head': 2, 'Director': 2, 'Manager': 3, 'Senior': 4}

def lista_prep(conta):
    """Preparação no LinkedIn (perfil do Savio): todos os Decisores + Influenciadores-chave do comitê."""
    e = lambda s: (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    comite = conta.partner_id.commercial_partner_id.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9 and p.x_abm_papel != 'Fora')
    decisores = comite.filtered(lambda p: p.x_abm_papel == 'Decisor' or p.x_abm_prioridade == 1)
    chave = (comite - decisores).filtered(lambda p: p.x_abm_papel == 'Influenciador-chave').sorted(
        lambda p: (SEN_PREP.get(p.x_abm_senioridade, 5), 0 if p.x_linkedin_url else 1, p.name or ''))
    lista = decisores | chave
    h = ('<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">'
         '👍 LINKEDIN · SEGUIR E CURTIR <span style="font-weight:normal; color:#dbeafe">· preparação · %s pessoas</span></div>') % len(lista)
    h += ('<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin:8px 0 10px">'
          '⚠️ Use o <b>perfil do Savio</b> (logado no navegador). Para cada pessoa: <b>seguir</b> e <b>curtir 1 post</b>. '
          '<b>Sem convite</b>: o convite entra na cadência, no D3.</div>')
    if not decisores:
        h += ('<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin-bottom:10px">'
              '⛔ <b>Comitê sem decisor de marketing.</b> Avise o gestor para enriquecer o comitê antes da cadência.</div>')
    if not lista:
        return h
    h += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb">'
    for p in lista:
        dec = p in decisores
        tag = 'Decisor' if dec else 'Influenciador-chave'
        cor = '#fde8e2; color:#9a3412' if dec else '#f3f4f6; color:#374151'
        link = ('<a href="%s" target="_blank">LinkedIn</a>' % e(p.x_linkedin_url)) if p.x_linkedin_url else '<span style="color:#7f1d1d">sem LinkedIn</span>'
        h += ('<tr><td style="padding:4px 8px; width:6%%">☐</td><td style="padding:4px 8px"><b>%s</b> — %s</td>'
              '<td style="padding:4px 8px"><span style="background-color:%s; padding:1px 6px; border-radius:8px; font-size:11px">%s</span></td>'
              '<td style="padding:4px 8px">%s</td></tr>') % (e(p.name), e(p.function) or '-', cor, tag, link)
    h += '</table>'
    h += '<p style="margin:6px 0 0; color:#6b7280; font-size:12px">%s decisor(es) + %s influenciador(es)-chave.</p>' % (
        len(decisores), len(chave))
    return h

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
    # Reconciliação de trilha: campo e tarefa precisam concordar (roda antes do freio).
    act_trilha = env.ref('abm_setima.act_trilha')
    for act in env['mail.activity'].search([('res_model', '=', 'crm.lead'), ('activity_type_id', '=', act_trilha.id)]):
        lead = model.browse(act.res_id)
        if lead.team_id.id == team_id and lead.x_abm_trilha in ('sem_config', 'config_fraco'):
            if not simular:
                act.action_feedback(feedback='Trilha já preenchida; concluída pela rotina diária.')
            relatorio.append('Trilha: tarefa concluída (campo já preenchido) – %s' % lead.name)
    fora = [env.ref('abm_setima.stage_cliente_expansao').id, env.ref('abm_setima.stage_descartada').id]
    for lead in model.search([('team_id', '=', team_id), ('x_abm_preparacao', '=', 'liberada'),
                              ('x_abm_trilha', 'in', [False, 'a_definir']), ('stage_id', 'not in', fora)]):
        if lead.activity_ids.filtered(lambda a: a.activity_type_id == act_trilha):
            continue
        if not simular:
            lead.with_context(mail_activity_quick_update=True).activity_schedule(
                'abm_setima.act_trilha', date_deadline=uteis[2], user_id=sdr.id,
                summary='[Preparação] Definir trilha (reaberta: campo vazio) – %s' % lead.name)
        relatorio.append('Trilha: tarefa reaberta (campo vazio) – %s' % lead.name)
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
        # Força com teto: comitê grande não passa na frente só pelo volume.
        # Até 2 decisores (3 pts cada) + até 4 influenciadores (1 pt cada) = máx. 10.
        forca = 3 * min(len(comite.filtered(lambda p: p.x_abm_prioridade == 1)), 2) + \
            min(len(comite.filtered(lambda p: p.x_abm_prioridade == 2)), 4)
        tier = int(conta.x_abm_tier or 9)
        # Ordem: tier → score (quem já engaja nos anúncios/site primeiro) → força → nome.
        fila.append((tier, -(conta.x_abm_score or 0), -forca, conta.name, conta))
    fila.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    relatorio.append('Pendentes da SDR (vencidas/hoje): %s de limite %s' % (pendentes, limite))
    if pendentes >= limite:
        liberar = []
        relatorio.append('Freio ativo: nada liberado hoje.')
    else:
        liberar = [x[4] for x in fila[:por_dia]]
    # Todas as tarefas de preparação no mesmo dia da liberação.
    for conta in liberar:
        etapas = [('abm_setima.act_li_interagir', 0, 'LinkedIn – seguir e curtir (perfil do Savio)')]
        # Comitê validado via Apollo: 'Validar comitê' só por exceção (sem validação ou sem decisor).
        if not conta.x_abm_comite_validado_em or not conta.x_abm_comite_decisores:
            etapas.insert(0, ('abm_setima.act_validar_comite', 0, 'Validar comitê'))
        if conta.x_abm_trilha in (False, 'a_definir'):
            etapas.append(('abm_setima.act_trilha', 0, 'Definir trilha'))
        linhas = []
        for xmlid, du, resumo in etapas:
            prazo = uteis[du]
            linhas.append('%s em %s' % (resumo, prazo.strftime('%d/%m')))
            if not simular:
                conta.with_context(mail_activity_quick_update=True).activity_schedule(
                    xmlid, date_deadline=prazo, user_id=sdr.id,
                    summary='[Preparação] %s – %s' % (resumo, conta.name), note=(lista_prep(conta) if xmlid == 'abm_setima.act_li_interagir' else False))
        if not simular:
            # Liberada para preparação = começa a aquecer. A etapa Aquecendo liga o
            # relógio de 21 dias da A3 (sem sinal, vai para Engajada sozinha).
            conta.write({'x_abm_preparacao': 'liberada', 'x_abm_preparacao_inicio': hoje,
                         'stage_id': env.ref('abm_setima.stage_aquecendo').id})
            conta.message_post(
                body='Preparação da conta liberada pela fila ABM (conta movida para Aquecendo): %s.' % '; '.join(linhas),
                message_type='comment', subtype_xmlid='mail.mt_note')
        relatorio.append('Liberada: %s (%s)' % (conta.name, '; '.join(linhas)))
    restantes = [x[3] for x in fila if x[4] not in liberar]
    relatorio.append('Na fila (%s): %s' % (len(restantes), ', '.join(restantes)))
log('\n'.join(relatorio))
if simular:
    action = {'type': 'ir.actions.client', 'tag': 'display_notification',
              'params': {'title': 'Fila ABM (simulação)', 'message': '\n'.join(relatorio)}}
