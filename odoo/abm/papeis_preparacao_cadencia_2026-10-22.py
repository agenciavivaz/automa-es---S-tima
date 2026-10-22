import sys, json, re, dis
sys.path.insert(0, '.')
from o import call
APPLY = '--apply' in sys.argv
changes = []

def code(aid):
    return call('ir.actions.server', 'read', ids=[aid], fields=['code'])[0]['code']

def swap(txt, old, new, label):
    n = txt.count(old)
    assert n == 1, '%s: trecho encontrado %s vezes' % (label, n)
    return txt.replace(old, new)

def set_code(aid, new, label):
    co = compile(new, label, 'exec')
    def walk(c):
        bad = {i.opname for i in dis.get_instructions(c)} & {'MAKE_CELL', 'LOAD_CLOSURE', 'STORE_DEREF', 'LOAD_DEREF'}
        assert not bad, '%s: %s em %s' % (label, bad, c.co_name)
        for k in c.co_consts:
            if hasattr(k, 'co_code'):
                walk(k)
    walk(co)
    changes.append(('ir.actions.server', aid, {'code': new}, label))

NOVA = '''def lista_prep(conta):
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

'''
for aid, nome in [(1324, 'Fila'), (1326, 'A2'), (1327, 'A3'), (1347, 'A17'), (1350, 'A20')]:
    c = code(aid)
    ini = c.index('def lista_prep(conta):')
    fim = c.index('    return h\n\n', ini) + len('    return h\n\n')
    c = c[:ini] + NOVA + c[fim:]
    assert c.count('def lista_prep') == 1 and 'preparacao_pessoas' not in c
    set_code(aid, c, nome + ' · lista Decisores + Influenciadores-chave')

c = code(1329)
c = swap(c, "escolhidos = elegiveis.filtered(lambda p: p.x_abm_prioridade in (1, 2)).sorted(ordem)[:3]",
         "escolhidos = elegiveis.filtered(lambda p: p.x_abm_prioridade == 1 or p.x_abm_papel in ('Decisor', 'Influenciador-chave')).sorted(ordem)[:3]", 'A5 seleção')
set_code(1329, c, 'A5 · seleção automática só Decisor e Influenciador-chave')
c = code(1338)
c = swap(c, "escolhidos = elegiveis.filtered(lambda p: not p.x_abm_na_cadencia and p.x_abm_prioridade in (2, 3)).sorted(ordem)[:2]",
         "escolhidos = elegiveis.filtered(lambda p: not p.x_abm_na_cadencia and p.x_abm_papel in ('Decisor', 'Influenciador-chave')).sorted(ordem)[:2]", 'A14 seleção')
set_code(1338, c, 'A14 · Onda 2 sem Aprovadores')

NOTA_VC = ('<div style="background-color:#7c3aed; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">👥 VALIDAR COMITÊ</div>'
  '<p style="margin:8px 0 4px">Confirme o cargo atual no LinkedIn e ajuste <b>papel</b> e <b>prioridade</b> (botão Editar comitê):</p>'
  '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb">'
  '<tr><td style="background-color:#fde8e2; padding:4px 8px; width:30%"><b>Decisor</b> · P1</td><td style="padding:4px 8px">Diretor, Head, VP ou CMO de marketing, comunicação, marca ou marketing de produto; cargo que acumula marketing. Sem líder de marketing: o gerente de marketing mais sênior.</td></tr>'
  '<tr><td style="background-color:#f3f4f6; padding:4px 8px"><b>Influenciador-chave</b> · P2</td><td style="padding:4px 8px">Gerentes de marketing, mkt de produto, comunicação, branding, CRM, e-commerce, digital e CX; líderes de produto e de site/digital.</td></tr>'
  '<tr><td style="background-color:#f9fafb; padding:4px 8px"><b>Influenciador</b> · P2/P3</td><td style="padding:4px 8px">Coordenadores, especialistas e analistas de marketing; gerentes de produto. Fora da cadência.</td></tr>'
  '<tr><td style="background-color:#f9fafb; padding:4px 8px"><b>Aprovador</b> · P3</td><td style="padding:4px 8px">CEO, presidente, VP geral, gerente geral, financeiro, compras e comercial. Só para escalada; fora da cadência.</td></tr>'
  '</table>'
  '<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin-top:8px">⛔ Sem ninguém de marketing no comitê: avise o gestor para enriquecer antes da cadência.</div>')
changes.append(('mail.activity.type', 22, {'default_note': NOTA_VC}, 'Nota · Validar comitê'))

for ch in changes:
    print('-', ch[3])
if APPLY:
    for model, rid, vals, label in changes:
        call(model, 'write', ids=[rid], vals=vals); print('OK', label)
    pids = [p['id'] for p in call('ir.config_parameter', 'search_read', domain=[['key', 'like', 'abm.preparacao_pessoas_']], fields=['id'])]
    if pids:
        call('ir.config_parameter', 'unlink', ids=pids); print('OK parâmetros de volume removidos:', len(pids))
