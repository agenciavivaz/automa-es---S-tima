import sys
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
    import dis
    co = compile(new, label, 'exec')
    def walk(c):
        ops = {i.opname for i in dis.get_instructions(c)}
        bad = ops & {'MAKE_CELL', 'LOAD_CLOSURE', 'STORE_DEREF', 'LOAD_DEREF'}
        assert not bad, '%s: %s em %s' % (label, bad, c.co_name)
        for k in c.co_consts:
            if hasattr(k, 'co_code'):
                walk(k)
    walk(co)
    changes.append(('ir.actions.server', aid, {'code': new}, label))


# ---------- Lista nominal da preparação (perfil do Savio) ----------
LISTA_PREP = '''
SEN_PREP = {'C suite': 0, 'Vp': 1, 'Owner': 1, 'Head': 2, 'Director': 2, 'Manager': 3, 'Senior': 4}

def lista_prep(conta):
    """Preparação no LinkedIn: todos os decisores + complemento até o alvo (abm.preparacao_pessoas_*)."""
    ICPp = env['ir.config_parameter'].sudo()
    p_min = int(ICPp.get_param('abm.preparacao_pessoas_min') or 5)
    p_extra = int(ICPp.get_param('abm.preparacao_pessoas_extra') or 3)
    p_max = int(ICPp.get_param('abm.preparacao_pessoas_max') or 8)
    e = lambda s: (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    comite = conta.partner_id.commercial_partner_id.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9 and p.x_abm_papel != 'Fora')
    decisores = comite.filtered(lambda p: p.x_abm_prioridade == 1 or p.x_abm_papel == 'Decisor')
    resto = (comite - decisores).sorted(lambda p: (0 if p.x_abm_papel == 'Influenciador-chave' else 1,
        p.x_abm_prioridade or 3, SEN_PREP.get(p.x_abm_senioridade, 5), 0 if p.x_linkedin_url else 1, p.name or ''))
    alvo = min(max(p_min, len(decisores) + p_extra), p_max)
    lista = decisores | resto[:max(alvo - len(decisores), 0)]
    h = ('<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">'
         '👍 LINKEDIN · SEGUIR E CURTIR <span style="font-weight:normal; color:#dbeafe">· preparação · %s pessoas</span></div>') % len(lista)
    h += ('<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin:8px 0 10px">'
          '⚠️ Use o <b>perfil do Savio</b> (logado no navegador). Para cada pessoa: <b>seguir</b> e <b>curtir 1 post</b>. '
          '<b>Sem convite</b>: o convite entra na cadência, no D3.</div>')
    if not lista:
        return h + '<p style="color:#7f1d1d">Comitê sem pessoas elegíveis: revisar o comitê da conta.</p>'
    h += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb">'
    for p in lista:
        tag = 'Decisor' if p in decisores else (p.x_abm_papel or '-')
        cor = '#fde8e2; color:#9a3412' if p in decisores else '#f3f4f6; color:#374151'
        link = ('<a href="%s" target="_blank">LinkedIn</a>' % e(p.x_linkedin_url)) if p.x_linkedin_url else '<span style="color:#7f1d1d">sem LinkedIn</span>'
        h += ('<tr><td style="padding:4px 8px; width:6%%">☐</td><td style="padding:4px 8px"><b>%s</b> — %s</td>'
              '<td style="padding:4px 8px"><span style="background-color:%s; padding:1px 6px; border-radius:8px; font-size:11px">%s</span></td>'
              '<td style="padding:4px 8px">%s</td></tr>') % (e(p.name), e(p.function) or '-', cor, e(tag), link)
    h += '</table>'
    h += '<p style="margin:6px 0 0; color:#6b7280; font-size:12px">%s decisor(es) + %s do complemento (alvo: mín. %s, máx. %s).</p>' % (
        len(lista & decisores), len(lista - decisores), p_min, p_max)
    return h

'''
NOTA_ARG = "note=(lista_prep(conta) if xmlid == 'abm_setima.act_li_interagir' else False)"

c = code(1324)
c = swap(c, '# próximos dias úteis', LISTA_PREP + '# próximos dias úteis', 'Fila helper')
c = swap(c, "summary='[Preparação] %s – %s' % (resumo, conta.name))",
            "summary='[Preparação] %s – %s' % (resumo, conta.name), " + NOTA_ARG + ")", 'Fila nota')
c = swap(c, 'LinkedIn – seguir e interagir', 'LinkedIn – seguir e curtir (perfil do Savio)', 'Fila rótulo')
set_code(1324, c, 'Fila de preparação · lista nominal')

for aid, nome in [(1326, 'A2'), (1327, 'A3'), (1347, 'A17'), (1350, 'A20')]:
    c = code(aid)
    c = swap(c, 'def preparar(conta):', LISTA_PREP + 'def preparar(conta):', nome + ' helper')
    c = swap(c, "summary='[Preparação] %s – %s' % (resumo, conta.name))",
                "summary='[Preparação] %s – %s' % (resumo, conta.name), " + NOTA_ARG + ")", nome + ' nota')
    c = swap(c, 'LinkedIn – seguir e interagir', 'LinkedIn – seguir e curtir (perfil do Savio)', nome + ' rótulo')
    set_code(aid, c, nome + ' · lista nominal na preparação')

# ---------- Cadência: Conectar no D3, só Decisor e Influenciador-chave ----------
for aid, nome in [(1329, 'A5'), (1338, 'A14')]:
    c = code(aid)
    c = swap(c, "(1, 'act_li_conectar', 'LinkedIn – Conectar', '', 'li_conectar'),",
                "(3, 'act_li_conectar', 'LinkedIn – Conectar', '', 'li_conectar'),", nome + ' D3')
    c = swap(c, """            if tipo == 'act_li_conectar' and p.x_abm_li_conexao in ('enviado', 'aceito'):
                continue""", """            # Convite (perfil do Savio) só para Decisor e Influenciador-chave; sem convite, sem D8/D14.
            convida = p.x_abm_prioridade == 1 or p.x_abm_papel in ('Decisor', 'Influenciador-chave')
            if toque in ('li_conectar', 'li_valor', 'li_followup') and not convida:
                continue
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito':
                continue""", nome + ' regra convite')
    set_code(aid, c, nome + ' · Conectar no D3 para decisores')

# ---------- Notas padrão dos tipos ----------
NOTA_LI = ('<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">'
           '👍 LINKEDIN · SEGUIR E CURTIR</div>'
           '<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px; margin-top:8px">'
           '⚠️ Use o <b>perfil do Savio</b> (logado no navegador). Seguir a pessoa e curtir 1 post. '
           '<b>Sem convite</b>: o convite entra na cadência, no D3.</div>')
changes.append(('mail.activity.type', 25, {'default_note': NOTA_LI}, 'Nota · LinkedIn – Seguir/Interagir'))
nota_ic = call('mail.activity.type', 'read', ids=[24], fields=['default_note'])[0]['default_note']
n_antes = nota_ic.count('<li>')
import re
nota_ic2 = re.sub(r'<li>Decisores com convite de LinkedIn enviado.*?</li>', '', nota_ic, flags=re.S)
assert nota_ic2.count('<li>') == n_antes - 1, 'item 5 do Iniciar cadência não encontrado'
nota_ic2 = nota_ic2.replace('Faça de 1 a 5 e deixe', 'Faça de 1 a 4 e deixe').replace('Com 1 a 6 ok', 'Com 1 a 5 ok')
changes.append(('mail.activity.type', 24, {'default_note': nota_ic2}, 'Nota · Iniciar cadência (sem item de convite)'))

# ---------- Parâmetros ----------
PARAMS = {
    'abm.dir.li_conectar.geral': 'OBJETIVO: convite entre o E1 e o E2.\n'
        '1. Use o **perfil do Savio** (logado no navegador).\n'
        '2. Nota de até 200 caracteres com o gatilho da Ficha ou algo do perfil da pessoa.\n'
        '3. Ao concluir: **Conexão = Enviado** no contato.\n'
        '! Sem link, sem pitch.',
    'abm.dir.li_interagir.geral': 'OBJETIVO: ser visto sem pedir nada.\n'
        '1. Use o **perfil do Savio**.\n'
        '2. Post da pessoa ou da marca sobre produto ou lançamento.\n'
        '3. **Comentário real** (uma frase com opinião ou pergunta) vale mais que curtida.\n'
        '! Nunca citar a Sétima no comentário.',
    'abm.dir.li_valor.geral': 'OBJETIVO: entregar algo útil sem pedir nada.\n'
        '1. Pelo **perfil do Savio** (é com ele que a pessoa está conectada).\n'
        '2. Um trecho do Tera, um dado, uma observação sobre o lançamento dele ou a calculadora de ROI.\n'
        '3. Sem asset personalizado, sem convite de reunião.',
    'abm.dir.li_followup.geral': 'OBJETIVO: retomar o fio e oferecer o espelho.\n'
        '1. Pelo **perfil do Savio**.\n'
        '2. Retome o E3 ou o D8.\n'
        '3. Ofereça o espelho **em uma pergunta**.\n'
        '! Se ele já respondeu em qualquer canal, **não envie**: atualize a conta.',
    'abm.preparacao_pessoas_min': '5',
    'abm.preparacao_pessoas_extra': '3',
    'abm.preparacao_pessoas_max': '8',
}
for k, v in PARAMS.items():
    changes.append(('param', k, v, 'Parâmetro ' + k))

for ch in changes:
    print('-', ch[3])
if APPLY:
    for model, rid, vals, label in changes:
        if model == 'param':
            call('ir.config_parameter', 'set_param', key=rid, value=vals)
        else:
            call(model, 'write', ids=[rid], vals=vals)
        print('OK', label)
