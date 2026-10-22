import sys, json, html
sys.path.insert(0, '.')
from o import call
APPLY = '--apply' in sys.argv
e = lambda s: html.escape(s or '', quote=False)
SEN = {'C suite': 0, 'Vp': 1, 'Owner': 1, 'Head': 2, 'Director': 2, 'Manager': 3, 'Senior': 4}
ok = lambda p: 0 if p['x_email_status'] in ('Verificado', 'Válido') else 1


def comite(partner_id):
    P = call('res.partner', 'search_read', domain=[['parent_id', '=', partner_id], ['x_abm_optout', '=', False],
                                                   ['x_abm_papel', 'in', ['Decisor', 'Influenciador-chave']]],
             fields=['name', 'function', 'x_abm_papel', 'x_abm_area', 'x_abm_prioridade', 'x_email_status', 'x_abm_senioridade', 'x_linkedin_url'])
    P.sort(key=lambda p: (0 if p['x_abm_papel'] == 'Decisor' else 1, SEN.get(p['x_abm_senioridade'], 5), ok(p), p['name']))
    return [p for p in P if p['x_abm_papel'] == 'Decisor'], [p for p in P if p['x_abm_papel'] == 'Influenciador-chave']


def sugestao(dec, chave):
    escolha = dec[:1]
    for p in dec[1:] + chave:
        if len(escolha) == 3:
            break
        if ok(p) == 0 and p['x_abm_area'] not in [x['x_abm_area'] for x in escolha] + ([] if p['x_abm_papel'] == 'Decisor' else []):
            escolha.append(p)
    for p in dec + chave:
        if len(escolha) == 3:
            break
        if p not in escolha:
            escolha.append(p)
    h = ('<p style="font-weight:bold; margin:0 0 4px">👥 Sugestão para a cadência <span style="font-weight:normal; color:#6b7280; font-size:12px">'
         '(comitê revisado em 22/10 · confirmar e marcar “Na cadência” no contato)</span></p>')
    if not escolha:
        return h + ('<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin-bottom:10px">'
                    '⛔ Comitê sem ninguém de marketing: enriquecimento pedido ao gestor.</div>')
    h += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb; margin-bottom:10px">'
    for p in escolha:
        cor = '#fde8e2; color:#9a3412' if p['x_abm_papel'] == 'Decisor' else '#f3f4f6; color:#374151'
        h += ('<tr><td style="padding:4px 8px"><b>%s</b> — %s</td><td style="padding:4px 8px"><span style="background-color:%s; padding:1px 6px; '
              'border-radius:8px; font-size:11px">%s</span></td><td style="padding:4px 8px; color:#6b7280; font-size:12px">e-mail %s</td></tr>') % (
            e(p['name']), e(p['function']) or '-', cor, e(p['x_abm_papel']), e(p['x_email_status']) or 'sem status')
    return h + '</table>'


def lista_html(dec, chave):
    h = ('<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">'
         '👍 LINKEDIN · SEGUIR E CURTIR <span style="font-weight:normal; color:#dbeafe">· comitê revisado · %s pessoas</span></div>') % (len(dec) + len(chave))
    h += ('<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin:8px 0 10px">'
          '⚠️ O comitê foi revisado: agora os decisores são de <b>marketing</b>. Use o <b>perfil do Savio</b>, <b>pule quem você já segue</b> '
          'e, para os demais, <b>seguir</b> e <b>curtir 1 post</b>. <b>Sem convite</b>: ele entra na cadência, no D3.</div>')
    if not dec:
        h += ('<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin-bottom:10px">'
              '⛔ Comitê sem decisor de marketing.</div>')
    h += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb">'
    for p in dec + chave:
        d = p['x_abm_papel'] == 'Decisor'
        link = ('<a href="%s" target="_blank">LinkedIn</a>' % e(p['x_linkedin_url'])) if p['x_linkedin_url'] else '<span style="color:#7f1d1d">sem LinkedIn</span>'
        h += ('<tr><td style="padding:4px 8px; width:6%%">☐</td><td style="padding:4px 8px"><b>%s</b> — %s</td><td style="padding:4px 8px">'
              '<span style="background-color:%s; padding:1px 6px; border-radius:8px; font-size:11px">%s</span></td><td style="padding:4px 8px">%s</td></tr>') % (
            e(p['name']), e(p['function']) or '-', '#fde8e2; color:#9a3412' if d else '#f3f4f6; color:#374151', e(p['x_abm_papel']), link)
    return h + '</table><p style="margin:6px 0 0; color:#6b7280; font-size:12px">%s decisor(es) + %s influenciador(es)-chave.</p>' % (len(dec), len(chave))


# 5) Fichas
fichas = call('crm.lead', 'search_read', domain=[['team_id', '=', 20], '|', ['x_abm_dossie_url', '!=', False], ['name', '=', 'Stara']],
              fields=['id', 'name', 'description', 'partner_id'])
INI = '<p style="font-weight:bold; margin:0 0 4px">👥 Sugestão'
FIM = '<p style="margin:0; color:#6b7280; font-size:12px">'
plano_f = []
for l in fichas:
    d = l['description']
    i = d.index(INI); j = d.index(FIM, i)
    dec, chave = comite(l['partner_id'][0])
    plano_f.append((l['id'], l['name'], d[:i] + sugestao(dec, chave) + d[j:], [p['name'] for p in dec], len(chave)))
for _, n, _, dec, nc in plano_f:
    print('FICHA', n, '| decisores:', dec, '| inf-chave:', nc)

# 6) Complemento da preparação (15 contas próximas da cadência)
ORDEM = [('Honda Brasil', '2026-10-23'), ('Marcopolo S.A.', '2026-10-23'), ('Jacto', '2026-10-23'),
         ('Randoncorp', '2026-10-26'), ('CNH', '2026-10-26'), ('Nissan do Brasil', '2026-10-26'),
         ('John Deere', '2026-10-27'), ('Stellantis South America', '2026-10-27'), ('AGCO Corporation', '2026-10-27'),
         ('Toyota do Brasil', '2026-10-28'), ('Grupo Yamaha Brasil', '2026-10-28'), ('BYD Brasil', '2026-10-28'),
         ('Ford Brasil', '2026-10-29'), ('Mitsubishi Motors Brasil', '2026-10-29'), ('Zeekr International', '2026-10-29')]
plano_c = []
for nome, prazo in ORDEM:
    l = call('crm.lead', 'search_read', domain=[['team_id', '=', 20], ['name', '=', nome]], fields=['id', 'partner_id', 'stage_id'])[0]
    dec, chave = comite(l['partner_id'][0])
    plano_c.append((l['id'], nome, prazo, lista_html(dec, chave), len(dec) + len(chave)))
    print('COMPLEMENTO', prazo, nome, '|', l['stage_id'][1], '|', len(dec), 'dec +', len(chave), 'chave')

# 7) Enriquecimento (contas sem ninguém de marketing)
sem = []
for l in call('crm.lead', 'search_read', domain=[['team_id', '=', 20], ['stage_id', 'in', [87, 88, 89, 90]]], fields=['id', 'name', 'partner_id']):
    if l['partner_id'] and not comite(l['partner_id'][0])[0]:
        sem.append((l['id'], l['name']))
print('ENRIQUECER', sem)

if APPLY:
    for lid, n, nova, _, _ in plano_f:
        call('crm.lead', 'write', ids=[lid], vals={'description': nova})
    print('OK fichas:', len(plano_f))
    for lid, n, prazo, nota, _ in plano_c:
        call('crm.lead', 'activity_schedule', ids=[lid], act_type_xmlid='abm_setima.act_li_interagir', date_deadline=prazo, user_id=31,
             summary='[Preparação] LinkedIn – seguir e curtir: comitê revisado – %s' % n, note=nota,
             context={'mail_activity_quick_update': True})
    print('OK complementos:', len(plano_c))
    for lid, n in sem:
        call('crm.lead', 'activity_schedule', ids=[lid], act_type_xmlid='abm_setima.act_validar_comite', date_deadline='2026-10-26', user_id=22,
             summary='Enriquecer comitê: sem ninguém de marketing – %s' % n,
             note='<p>⛔ <b>Comitê sem ninguém de marketing.</b> Buscar no Apollo ou no LinkedIn a liderança de marketing, comunicação ou marca da operação brasileira '
                  '(diretor, head ou gerente) e incluir no comitê como Decisor ou Influenciador-chave.</p>',
             context={'mail_activity_quick_update': True})
    print('OK enriquecimento:', len(sem))
json.dump({'complemento': [(a, b, c) for a, b, c, _, _ in plano_c], 'enriquecer': sem}, open('etapa567_plano.json', 'w'), ensure_ascii=False)
