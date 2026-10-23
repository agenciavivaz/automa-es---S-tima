
ICP = env['ir.config_parameter'].sudo()
team_id = int(ICP.get_param('abm.team_id'))
sdr_id = int(ICP.get_param('abm.sdr_user_id'))
gestor = env['res.users'].browse(int(ICP.get_param('abm.gestor_user_id') or 0))
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
# Nenhuma tarefa nasce antes do início do processo (abm.inicio).
inicio = ICP.get_param('abm.inicio')
hoje = datetime.date.today()
if inicio:
    hoje = max(hoje, datetime.datetime.strptime(inicio, '%Y-%m-%d').date())
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

# A17 (revisada em 23/10/2026): exposição alta NÃO move para Engajada.
# Marca a conta como pronta para abordagem e antecipa o convite de LinkedIn
# para os decisores. Engajada fica só para score >= 30 (A2).
tag_id = int(ICP.get_param('abm.tag_pronta_abordagem_id') or 0)
esc_url = lambda s: esc(s).replace('"', '&quot;')

for conta in records:
    if tag_id and tag_id not in conta.tag_ids.ids:
        conta.write({'tag_ids': [(4, tag_id)]})
    comite = conta.partner_id.commercial_partner_id.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9 and p.x_abm_papel != 'Fora')
    decisores = comite.filtered(lambda p: p.x_abm_papel == 'Decisor' or p.x_abm_prioridade == 1)
    pendentes = decisores.filtered(lambda p: p.x_abm_li_conexao in (False, 'nao_enviado'))
    tipo = env.ref('abm_setima.act_li_conectar')
    ja_tem = conta.activity_ids.filtered(lambda a: a.activity_type_id == tipo)
    if pendentes and not ja_tem:
        h = ('<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">'
             '🤝 LINKEDIN · CONECTAR DECISORES <span style="font-weight:normal; color:#dbeafe">· pronta para abordagem · %s pessoas</span></div>') % len(pendentes)
        h += ('<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin:8px 0 10px">'
              '⚠️ Esta conta já viu bastante anúncio (%.1f impressões por pessoa do comitê em 30 dias): o convite foi '
              '<b>antecipado</b> e não espera a cadência.<br/>Use o <b>perfil do Savio</b>. Nota de até 200 caracteres com algo '
              'do perfil da pessoa ou da Ficha. <b>Sem link, sem pitch.</b> Depois de enviar: <b>Conexão = Enviado</b> no contato.</div>'
              ) % (conta.x_abm_exposicao or 0)
        h += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb">'
        for p in pendentes:
            link = ('<a href="%s" target="_blank">LinkedIn</a>' % esc_url(p.x_linkedin_url)) if p.x_linkedin_url else '<span style="color:#7f1d1d">sem LinkedIn</span>'
            h += ('<tr><td style="padding:4px 8px; width:6%%">☐</td><td style="padding:4px 8px"><b>%s</b> — %s</td>'
                  '<td style="padding:4px 8px">%s</td></tr>') % (esc(p.name), esc(p.function) or '-', link)
        h += '</table>'
        conta.with_context(**QUIET).activity_schedule(
            'abm_setima.act_li_conectar', date_deadline=uteis[0], user_id=sdr_id,
            summary='[Pronta p/ abordagem] LinkedIn – conectar decisores – %s' % conta.name, note=h)
    elif not decisores and gestor:
        conta.with_context(**QUIET).activity_schedule(
            'abm_setima.act_rotina', date_deadline=uteis[0], user_id=gestor.id,
            summary='[Comitê] Pronta para abordagem sem decisor – enriquecer – %s' % conta.name)
    nota(conta, 'Exposição %.1f impressões por pessoa do comitê (≥ 4) após 14 dias aquecendo: conta <b>pronta para abordagem</b> '
                '(continua em Aquecendo; Engajada só com score ≥ 30). %s' % (
                    conta.x_abm_exposicao or 0,
                    ('Convite de LinkedIn antecipado para %s decisor(es).' % len(pendentes)) if pendentes and not ja_tem
                    else ('Sem decisor no comitê: gestor avisado.' if not decisores else 'Convites já enviados ou tarefa já aberta.')))
