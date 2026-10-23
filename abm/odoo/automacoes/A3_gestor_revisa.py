
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

# A3 (revisada em 23/10/2026): 21 dias em Aquecendo NÃO move para Engajada.
# Avisa o gestor para rever a conta. Engajada fica só para score >= 30 (A2).
tag_id = int(ICP.get_param('abm.tag_pronta_abordagem_id') or 0)

for conta in records:
    if not gestor:
        continue
    sinais = conta.x_abm_sinal_ids.filtered(lambda s: s.x_ativo)
    intencao = sinais.filtered(lambda s: s.x_origem != 'linkedin_ads')
    pronta = bool(tag_id and tag_id in conta.tag_ids.ids)
    conta.with_context(**QUIET).activity_schedule(
        'abm_setima.act_rotina', date_deadline=uteis[0], user_id=gestor.id,
        summary='[Revisar] 21 dias aquecendo sem engajar – %s' % conta.name,
        note=('<p><b>Score %s</b> (fria) · exposição %.1f · %s sinal(is) fora do Ads nos últimos 30 dias%s.</p>'
              '<p>Decidir: manter aquecendo, trocar a abordagem (trilha, criativo, página no LinkedIn) ou mover para Nutrição.</p>') % (
                  conta.x_abm_score or 0, conta.x_abm_exposicao or 0, len(intencao),
                  ' · já marcada como pronta para abordagem' if pronta else ''))
    nota(conta, '21 dias em Aquecendo sem chegar a 30 pontos: gestor avisado para revisar (a conta continua em Aquecendo).')
