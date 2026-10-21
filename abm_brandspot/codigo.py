"""Código Python (safe_eval do Odoo) das automações e da fila diária do ABM BrandSpot.

É a mesma lógica do ABM Sétima (equipe 20), lida ao vivo do Odoo em 2026-10-21,
com três diferenças:

- parâmetros próprios (`abm_brandspot.*`); feriados continuam em `abm.feriados`;
- xml-ids `abm_brandspot.*` (etapas e tipos de atividade "ABM BrandSpot · …");
- a "trilha" (configurador) dá lugar ao campo **Estúdio interno**
  (`x_abm_estudio`): a preparação cria "Mapear estúdio" quando ele está vazio e o
  modelo de e-mail da cadência sai do estúdio (Já tem / Baixa qualidade / Indefinido).

A13 (sinal expira em 30 dias) é do modelo x_abm_sinal e já vale para as duas
equipes: não é duplicada.
"""

X = "abm_brandspot."

PREAMBULO = """
ICP = env['ir.config_parameter'].sudo()
team_id = int(ICP.get_param('abm_brandspot.team_id'))
sdr_id = int(ICP.get_param('abm_brandspot.sdr_user_id'))
gestor = env['res.users'].browse(int(ICP.get_param('abm_brandspot.gestor_user_id') or 0))
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
# Nenhuma tarefa nasce antes do início do processo (abm_brandspot.inicio).
inicio = ICP.get_param('abm_brandspot.inicio')
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
"""

# Preparação liberada fora da fila (conta engajou antes): mesmas tarefas da fila diária.
PREPARAR = """
def preparar(conta):
    \"\"\"Tarefas de preparação da conta, todas no mesmo dia (mesmas da fila diária).\"\"\"
    etapas = [('abm_brandspot.act_li_interagir', 'LinkedIn – seguir e interagir')]
    # Comitê validado via Apollo (cargo, empresa atual, LinkedIn): 'Validar comitê' só por exceção.
    if not conta.x_abm_comite_validado_em or not conta.x_abm_comite_decisores:
        etapas.insert(0, ('abm_brandspot.act_validar_comite', 'Validar comitê'))
    if not conta.x_abm_estudio:
        etapas.append(('abm_brandspot.act_estudio', 'Mapear estúdio'))
    for xmlid, resumo in etapas:
        conta.with_context(**QUIET).activity_schedule(
            xmlid, date_deadline=uteis[0], user_id=sdr_id,
            summary='[Preparação] %s – %s' % (resumo, conta.name))
    conta.write({'x_abm_preparacao': 'liberada', 'x_abm_preparacao_inicio': uteis[0]})
    nota(conta, 'Conta ficou engajada antes da fila: preparação liberada junto (%s).' % ', '.join([e[1] for e in etapas]))
"""

# Corpo comum da cadência (A5, onda 1, e A14, onda 2): e-mail + LinkedIn, sem ligação/WhatsApp.
CADENCIA = """
    estudio = conta.x_abm_estudio or 'indefinido'
    rotulo = {'tem_estudio': 'Já tem estúdio', 'estudio_baixa': 'Estúdio de baixa qualidade'}.get(estudio, 'Indefinido')
    if not conta.x_abm_estudio:
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_estudio', date_deadline=uteis[0], user_id=sdr_id,
            summary='Mapear estúdio antes do primeiro e-mail')
        notas.append('Estúdio não mapeado: os e-mails usam o modelo "Indefinido" até o campo ser preenchido.')
    # Cadência fria só com e-mail e LinkedIn. Ligação e WhatsApp NÃO entram aqui:
    # só quando a conta fica quente (A4) ou chega formulário (A15).
    # Sem asset na cadência padrão: ele só entra para o decisor após conexão aceita (A11/A16).
    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', ''),
        (1, 'act_email', 'E-mail', 'E1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', ''),
        (5, 'act_email', 'E-mail', 'E2'),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem de valor', ''),
        (11, 'act_email', 'E-mail', 'E3'),
        (14, 'act_li_mensagem', 'LinkedIn – Follow-up', ''),
        (18, 'act_email', 'E-mail', 'E4'),
    ]
    total = 0
    for p in escolhidos:
        for dia, tipo, canal, email_cod in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito':
                continue
            if tipo == 'act_email' and (not p.email or p.x_email_status in ('Inválido', 'Indisponível')):
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
            html += '<p>Dossiê: %s</p>' % (esc(conta.x_abm_dossie_url) or '-')
            if email_cod:
                html += '<p>Estúdio: %s · Modelo: <b>ABM BrandSpot · %s · %s</b></p>' % (rotulo, email_cod, rotulo)
            if tipo == 'act_li_mensagem':
                html += '<p><i>Só se a conexão foi aceita; senão, marcar como feita. Conteúdo de valor (bastidor do showroom, dado de produção de aulas, post), sem asset e sem pitch.</i></p>'
            conta.with_context(**QUIET).activity_schedule(
                'abm_brandspot.' + tipo, date_deadline=uteis[dia - 1], user_id=sdr_id,
                summary='[Cadência] D%s %s – %s (%s)' % (dia, canal, p.name, p.function or '-'),
                note=html, x_abm_partner_id=p.id)
            total += 1
    notas.append('Onda %s: %s na cadência, %s atividade(s) criada(s).' % (
        conta.x_abm_onda, ', '.join(escolhidos.mapped('name')) or 'ninguém', total))
    nota(conta, '<br/>'.join(notas))
"""

ELEGIVEIS = """
    empresa = conta.partner_id.commercial_partner_id
    elegiveis = empresa.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9 and p.x_abm_papel != 'Fora')
    ordem = lambda p: (p.x_abm_prioridade or 3, 0 if p.x_email_status in ('Verificado', 'Válido') else 1, p.name or '')
"""

A1 = """
for conta in records:
    if conta.x_abm_preparacao != 'liberada':
        conta.write({'x_abm_preparacao': 'fila'})
"""

A2 = PREPARAR + """
for conta in records:
    # Formulário ou braço erguido: vai direto para Conversa (A7 cria 'Agendar reunião').
    sinais = conta.x_abm_sinal_ids.filtered(lambda s: s.x_ativo)
    if conta.activity_ids.filtered(lambda a: (a.summary or '').startswith('Formulário:')) or \\
            sinais.filtered(lambda s: s.x_tipo in ('formulario', 'resposta_positiva')):
        conta.write({'stage_id': env.ref('abm_brandspot.stage_conversa').id})
        nota(conta, 'Formulário ou braço erguido: conta movida direto para Conversa.')
        continue
    conta.write({'stage_id': env.ref('abm_brandspot.stage_engajada').id})
    if conta.x_abm_preparacao != 'liberada':
        preparar(conta)
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_iniciar_cadencia', date_deadline=uteis[0], user_id=sdr_id,
        summary='Iniciar cadência – %s' % conta.name)
"""

A3 = PREPARAR + """
for conta in records:
    conta.write({'stage_id': env.ref('abm_brandspot.stage_engajada').id})
    if conta.x_abm_preparacao != 'liberada':
        preparar(conta)
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_iniciar_cadencia', date_deadline=uteis[0], user_id=sdr_id,
        summary='Iniciar cadência – %s' % conta.name)
"""

A4 = """
for conta in records:
    if gestor:
        conta.message_subscribe(partner_ids=gestor.partner_id.ids)
    sinais = conta.x_abm_sinal_ids.filtered(lambda s: s.x_ativo)
    # Formulário: a A15 já criou a tarefa de contato em até 1h com a pessoa que se cadastrou.
    if conta.activity_ids.filtered(lambda a: (a.summary or '').startswith('Formulário:')):
        conta.write({'stage_id': env.ref('abm_brandspot.stage_conversa').id})
        nota(conta, 'Conta quente (score %s) por cadastro: movida para Conversa; seguir a tarefa de contato do formulário.' % conta.x_abm_score)
        continue
    # Braço erguido: a prioridade é responder quem levantou a mão, não ligar para o comitê.
    positivas = sinais.filtered(lambda s: s.x_tipo == 'resposta_positiva').sorted('x_data', reverse=True)
    if positivas:
        quem = positivas[0].x_partner_id
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_agendar', date_deadline=hoje, user_id=sdr_id,
            summary='[Quente] Braço erguido: responder e agendar – %s' % (quem.name or conta.name),
            x_abm_partner_id=quem.id or False,
            note='<p>Resposta positiva. Responder hoje e propor visita ao showroom (ou 20 min online). A conta já foi movida para Conversa.</p>')
        conta.write({'stage_id': env.ref('abm_brandspot.stage_conversa').id})
        continue
    empresa = conta.partner_id.commercial_partner_id
    ativos = empresa.child_ids.filtered(lambda p: not p.x_abm_optout and p.x_abm_prioridade != 9)
    pessoas = ativos.filtered(lambda p: p.x_abm_na_cadencia) or ativos.filtered(lambda p: p.x_abm_prioridade == 1)
    com_telefone = pessoas.filtered(lambda p: p.phone)
    for p in com_telefone:
        base = '<p><b>%s</b> — %s<br/>Telefone: %s</p><p>Conta quente (score %s). Ofereça uma visita ao showroom.</p>' % (
            esc(p.name), esc(p.function), esc(p.phone), conta.x_abm_score)
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_ligacao', date_deadline=hoje, user_id=sdr_id,
            summary='[Quente] Ligar – %s (%s)' % (p.name, p.function or '-'), note=base, x_abm_partner_id=p.id)
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_whatsapp', date_deadline=proximo_util, user_id=sdr_id,
            summary='[Quente] WhatsApp – %s' % p.name, x_abm_partner_id=p.id,
            note=base + '<p><i>Se a ligação não foi atendida. Enviar pelo DataCrazy.</i></p>')
    if not com_telefone:
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_ligacao', date_deadline=hoje, user_id=sdr_id,
            summary='[Quente] Conta quente sem telefone: buscar número do decisor')
"""

A5 = """
for conta in records:
    notas = []
""" + ELEGIVEIS + """
    escolhidos = elegiveis.filtered(lambda p: p.x_abm_na_cadencia)
    if not escolhidos:
        escolhidos = elegiveis.filtered(lambda p: p.x_abm_prioridade in (1, 2)).sorted(ordem)[:3]
        escolhidos.write({'x_abm_na_cadencia': True})
        notas.append('Ninguém marcado "Na cadência": escolhidos automaticamente %s.' % ', '.join(escolhidos.mapped('name')))
    conta.write({'x_abm_cadencia_status': 'ativa', 'x_abm_cadencia_inicio': hoje, 'x_abm_onda': 1})
""" + CADENCIA

A6 = """
nutricao = env.ref('abm_brandspot.stage_nutricao')
for conta in records:
    pendentes = conta.activity_ids.filtered(lambda a: (a.summary or '').startswith('[Cadência]'))
    n = len(pendentes)
    pendentes.unlink()
    conta.write({'x_abm_cadencia_status': 'concluida' if conta.stage_id == nutricao else 'pausada'})
    nota(conta, 'Cadência parada (%s): %s atividade(s) cancelada(s).' % (conta.stage_id.name, n))
"""

A7 = """
for conta in records:
    # Já existe tarefa de contato do formulário ou do braço erguido: não duplicar.
    if conta.activity_ids.filtered(lambda a: (a.summary or '').startswith(('Formulário:', '[Quente] Braço erguido'))):
        continue
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_agendar', date_deadline=uteis[0], user_id=sdr_id,
        summary='Agendar visita ao showroom – %s' % conta.name)
"""

A8 = """
for conta in records:
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_preparar_reuniao', date_deadline=uteis[0], user_id=sdr_id,
        summary='Preparar reunião/visita – %s' % conta.name)
    if gestor:
        conta.message_subscribe(partner_ids=gestor.partner_id.ids)
"""

A9 = """
for conta in records:
    conta.write({'stage_id': env.ref('abm_brandspot.stage_nutricao').id})
"""

A10 = """
AUTOMATICA = ('resposta automática', 'resposta automatica', 'automatic reply', 'auto-reply', 'autoreply',
              'out of office', 'fora do escritório', 'fora do escritorio', 'ausência', 'ausencia',
              'estou ausente', 'em férias', 'de férias', 'undeliverable', 'não entregue', 'delivery status')
CONFIRMACAO = ('recebid', 'recebi', 'obrigad', 'ok', 'ciente', 'thank', 'receiv', 'grato', 'grata')
ACEITE = ('aceito:', 'accepted:', 'aceitou:')

def texto(html):
    saida, dentro = [], False
    for ch in html or '':
        if ch == '<':
            dentro = True
        elif ch == '>':
            dentro = False
            saida.append(' ')
        elif not dentro:
            saida.append(ch)
    return ' '.join(''.join(saida).split()).lower()

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
    assunto = (msg.subject or '').lower()
    corpo = texto(msg.body)
    quem = contato.name or remetente
    # Corpo curto sem conteúdo além da citação: "recebido", "ok, obrigado".
    curto = corpo.split(' em ')[0].split(' on ')[0]
    palavras = curto.replace(',', ' ').replace('.', ' ').replace('!', ' ').split()
    so_confirmacao = len(palavras) <= 4 and '?' not in curto and any(
        [p.startswith(k) for p in palavras for k in CONFIRMACAO])
    if any([k in assunto or k in corpo[:400] for k in AUTOMATICA]) or so_confirmacao:
        tipo = 'resposta_automatica'
    elif any([assunto.startswith(k) for k in ACEITE]):
        tipo = 'resposta_positiva'
    else:
        tipo = 'resposta_a_classificar'
    if tipo == 'resposta_a_classificar':
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_classificar', date_deadline=uteis[0], user_id=sdr_id,
            summary='Classificar resposta – %s' % quem, x_abm_partner_id=contato.id or False)
    elif tipo == 'resposta_positiva':
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_agendar', date_deadline=hoje, user_id=sdr_id,
            summary='Convite aceito – %s: confirmar e mover para Reunião agendada' % quem,
            x_abm_partner_id=contato.id or False)
    env['x_abm_sinal'].create({
        'x_name': 'Resposta de e-mail – %s' % quem,
        'x_lead_id': conta.id, 'x_partner_id': contato.id or False,
        'x_tipo': tipo, 'x_origem': 'email', 'x_detalhe': msg.subject or ''})
    if tipo == 'resposta_automatica':
        nota(conta, 'Resposta automática/“recebido” de %s: registrada sem pontos.' % esc(quem))
"""

A11 = """
for p in records:
    conta = env['crm.lead'].search([('team_id', '=', team_id), ('partner_id', '=', p.commercial_partner_id.id)], limit=1)
    if not conta:
        continue
    env['x_abm_sinal'].create({
        'x_name': 'Conexão aceita – %s' % p.name, 'x_lead_id': conta.id, 'x_partner_id': p.id,
        'x_tipo': 'li_conexao_aceita', 'x_origem': 'linkedin_manual'})
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_li_mensagem', date_deadline=proximo_util, user_id=sdr_id,
        summary='[Cadência] Mensagem pós-conexão – %s' % p.name, x_abm_partner_id=p.id)
    # Decisor conectado: hora de preparar o asset personalizado da conta.
    decisor = p.x_abm_prioridade == 1 or p.x_abm_papel == 'Decisor'
    ja_tem = env['mail.activity'].search_count([
        ('x_abm_partner_id', '=', p.id), ('activity_type_id', '=', env.ref('abm_brandspot.act_asset').id)])
    if decisor and not ja_tem:
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_asset', date_deadline=uteis[5], user_id=(gestor or env.user).id,
            summary='Asset personalizado – %s (decisor conectado)' % p.name, x_abm_partner_id=p.id)
        nota(conta, 'Decisor %s aceitou a conexão: tarefa de asset personalizado criada.' % esc(p.name))
"""

A12 = """
for p in records:
    atividades = env['mail.activity'].search([('x_abm_partner_id', '=', p.id)])
    n = len(atividades)
    atividades.unlink()
    p.write({'x_abm_na_cadencia': False})
    conta = env['crm.lead'].search([('team_id', '=', team_id), ('partner_id', '=', p.commercial_partner_id.id)], limit=1)
    if conta:
        nota(conta, 'Opt-out de %s: %s atividade(s) cancelada(s).' % (esc(p.name), n))
"""

A14 = """
for conta in records:
    if conta.x_abm_onda != 1 or not conta.x_abm_cadencia_inicio:
        continue
    respostas = conta.x_abm_sinal_ids.filtered(
        lambda s: s.x_tipo in ('email_resposta', 'li_dm_resposta', 'resposta_a_classificar', 'resposta_negativa', 'resposta_neutra', 'resposta_positiva') and s.x_data and s.x_data.date() >= conta.x_abm_cadencia_inicio)
    if respostas:
        continue
    notas = []
""" + ELEGIVEIS + """
    escolhidos = elegiveis.filtered(lambda p: not p.x_abm_na_cadencia and p.x_abm_prioridade in (2, 3)).sorted(ordem)[:2]
    conta.write({'x_abm_onda': 2})
    if not escolhidos:
        nota(conta, 'Onda 2: não há mais contatos elegíveis no comitê.')
        continue
    escolhidos.write({'x_abm_na_cadencia': True})
""" + CADENCIA

A15 = """
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
    # A tarefa vem ANTES do sinal: o sinal (60 pts) deixa a conta Quente e a A4
    # reconhece a tarefa "Formulário:" para não duplicar ligações.
    conta.with_context(**QUIET).activity_schedule(
        'abm_brandspot.act_ligacao', date_deadline=hoje, user_id=sdr_id,
        summary='Formulário: contato em até 1h útil – %s' % (lead.contact_name or email))
    env['x_abm_sinal'].create({
        'x_name': 'Cadastro – %s' % (lead.contact_name or email), 'x_lead_id': conta.id,
        'x_tipo': 'formulario', 'x_origem': 'formulario',
        'x_detalhe': '%s <%s> · lead #%s' % (lead.contact_name or lead.name, email, lead.id)})
    nota(conta, 'Cadastro de %s (%s): <a href="/odoo/crm/%s">lead de inbound #%s</a>.' % (esc(lead.contact_name or lead.name), esc(email), lead.id, lead.id))
    nota(lead, 'Pessoa de conta ABM BrandSpot: <a href="/odoo/crm/%s">%s</a>.' % (conta.id, esc(conta.name)))
"""

A16 = """
for conta in records:
    empresa = conta.partner_id.commercial_partner_id
    decisores = empresa.child_ids.filtered(
        lambda p: not p.x_abm_optout and p.x_abm_li_conexao == 'aceito'
        and (p.x_abm_prioridade == 1 or p.x_abm_papel == 'Decisor'))
    for p in decisores:
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_li_mensagem', date_deadline=proximo_util, user_id=sdr_id,
            summary='[Cadência] Enviar asset – %s' % p.name, x_abm_partner_id=p.id,
            note='<p>Asset: %s</p><p>Mensagem curta no LinkedIn, oferecendo uma visita ao showroom para mostrar.</p>' % esc(conta.x_abm_asset_url))
    if not decisores:
        conta.with_context(**QUIET).activity_schedule(
            'abm_brandspot.act_li_mensagem', date_deadline=proximo_util, user_id=sdr_id,
            summary='Asset pronto: definir para quem enviar – %s' % conta.name)
"""

# Fila diária de preparação. Diferença para a Sétima: o freio conta as tarefas
# ABM vencidas/hoje da SDR nas DUAS frentes ("ABM%"), porque a SDR é a mesma.
FILA = """
ICP = env['ir.config_parameter'].sudo()
simular = env.context.get('abm_simular')
hoje = datetime.date.today()
inicio = ICP.get_param('abm_brandspot.inicio')
feriados = set((ICP.get_param('abm.feriados') or '').split(','))
team_id = int(ICP.get_param('abm_brandspot.team_id'))
sdr = env['res.users'].browse(int(ICP.get_param('abm_brandspot.sdr_user_id')))
por_dia = int(ICP.get_param('abm_brandspot.preparacao_contas_dia') or 4)
limite = int(ICP.get_param('abm_brandspot.preparacao_limite_pendentes') or 10)

# próximos dias úteis a partir de hoje (inclusive)
uteis = []
d = hoje
while len(uteis) < 10:
    if d.weekday() < 5 and d.isoformat() not in feriados:
        uteis.append(d)
    d += datetime.timedelta(days=1)

relatorio = []
if inicio and hoje.isoformat() < inicio and not simular:
    relatorio.append('Antes do início do processo (%s): nada liberado.' % inicio)
elif uteis[0] != hoje and not simular:
    relatorio.append('Hoje não é dia útil: nada liberado.')
else:
    tipos_abm = env['mail.activity.type'].search([('name', '=like', 'ABM%')])
    pendentes = env['mail.activity'].search_count([
        ('user_id', '=', sdr.id), ('res_model', '=', 'crm.lead'),
        ('activity_type_id', 'in', tipos_abm.ids), ('date_deadline', '<=', hoje)])
    alvo = env.ref('abm_brandspot.stage_alvo')
    candidatas = model.search([
        ('team_id', '=', team_id), ('stage_id', '=', alvo.id),
        ('x_abm_preparacao', 'in', [False, 'fila'])])
    fila = []
    for conta in candidatas:
        comite = conta.partner_id.child_ids.filtered(
            lambda p: not p.x_abm_optout and p.x_abm_prioridade in (1, 2))
        # Força com teto: comitê grande não passa na frente só pelo volume.
        # Até 2 decisores (3 pts cada) + até 4 influenciadores (1 pt cada) = máx. 10.
        forca = 3 * min(len(comite.filtered(lambda p: p.x_abm_prioridade == 1)), 2) + \\
            min(len(comite.filtered(lambda p: p.x_abm_prioridade == 2)), 4)
        tier = int(conta.x_abm_tier or 9)
        # Ordem: tier → score (quem já engaja nos anúncios/site primeiro) → força → nome.
        fila.append((tier, -(conta.x_abm_score or 0), -forca, conta.name, conta))
    fila.sort(key=lambda x: (x[0], x[1], x[2], x[3]))
    relatorio.append('Pendentes ABM da SDR, Sétima + BrandSpot (vencidas/hoje): %s de limite %s' % (pendentes, limite))
    if pendentes >= limite:
        liberar = []
        relatorio.append('Freio ativo: nada liberado hoje.')
    else:
        liberar = [x[4] for x in fila[:por_dia]]
    # Todas as tarefas de preparação no mesmo dia da liberação.
    for conta in liberar:
        etapas = [('abm_brandspot.act_li_interagir', 0, 'LinkedIn – seguir e interagir')]
        # Comitê validado via Apollo: 'Validar comitê' só por exceção (sem validação ou sem decisor).
        if not conta.x_abm_comite_validado_em or not conta.x_abm_comite_decisores:
            etapas.insert(0, ('abm_brandspot.act_validar_comite', 0, 'Validar comitê'))
        if not conta.x_abm_estudio:
            etapas.append(('abm_brandspot.act_estudio', 0, 'Mapear estúdio'))
        linhas = []
        for xmlid, du, resumo in etapas:
            prazo = uteis[du]
            linhas.append('%s em %s' % (resumo, prazo.strftime('%d/%m')))
            if not simular:
                conta.with_context(mail_activity_quick_update=True).activity_schedule(
                    xmlid, date_deadline=prazo, user_id=sdr.id,
                    summary='[Preparação] %s – %s' % (resumo, conta.name))
        if not simular:
            # Liberada para preparação = começa a aquecer. A etapa Aquecendo liga o
            # relógio de 21 dias da A3 (sem sinal, vai para Engajada sozinha).
            conta.write({'x_abm_preparacao': 'liberada', 'x_abm_preparacao_inicio': hoje,
                         'stage_id': env.ref('abm_brandspot.stage_aquecendo').id})
            conta.message_post(
                body='Preparação da conta liberada pela fila ABM (conta movida para Aquecendo): %s.' % '; '.join(linhas),
                message_type='comment', subtype_xmlid='mail.mt_note')
        relatorio.append('Liberada: %s (%s)' % (conta.name, '; '.join(linhas)))
    restantes = [x[3] for x in fila if x[4] not in liberar]
    relatorio.append('Na fila (%s): %s' % (len(restantes), ', '.join(restantes)))
log('\\n'.join(relatorio))
if simular:
    action = {'type': 'ir.actions.client', 'tag': 'display_notification',
              'params': {'title': 'Fila ABM BrandSpot (simulação)', 'message': '\\n'.join(relatorio)}}
"""

COMITE = """
empresa = record.partner_id.commercial_partner_id
action = {
    'type': 'ir.actions.act_window',
    'name': 'Comitê · %s' % (empresa.name or record.name),
    'res_model': 'res.partner',
    'view_mode': 'list,form',
    'views': [(__VIEW_COMITE__, 'list'), (False, 'form')],
    'domain': [('parent_id', '=', empresa.id)],
    'context': {'default_parent_id': empresa.id, 'default_type': 'contact',
                'default_is_company': False, 'default_category_id': [__CATEGORIA__]},
    'target': 'current',
}
"""

# Cor do card (campo compartilhado): "cliente" vale para as duas equipes.
COR_CARD = """
clientes = [self.env.ref(x, raise_if_not_found=False) for x in
            ('abm_setima.stage_cliente_expansao', 'abm_brandspot.stage_cliente_expansao')]
clientes = [c.id for c in clientes if c]
for r in self:
    r['x_abm_cor'] = 'cliente' if r.stage_id.id in clientes else (r.x_abm_faixa or 'fria')
"""


def com_preambulo(corpo):
    return PREAMBULO + "\n" + corpo
