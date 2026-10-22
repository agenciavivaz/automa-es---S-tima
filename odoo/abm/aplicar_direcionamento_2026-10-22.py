import sys, json, re
sys.path.insert(0, '.')
from o import call

APPLY = '--apply' in sys.argv
md = open('/home/user/automa-es---S-tima/docs/ABM_SETIMA_ANALISE_DIRECIONAMENTO.md').read()
sec62 = md[md.find('### 6.2'):md.find('### 6.3')]
DEFS, LOOP = re.findall(r'```python\n(.*?)```', sec62, re.S)
changes = []


def code(aid):
    return call('ir.actions.server', 'read', ids=[aid], fields=['code'])[0]['code']


def swap(txt, old, new, label):
    n = txt.count(old)
    assert n == 1, '%s: trecho encontrado %s vezes' % (label, n)
    return txt.replace(old, new)


def set_code(aid, new, label):
    compile(new, label, 'exec')
    changes.append(('ir.actions.server', aid, {'code': new}, label))


# ---------- A5 e A14: passos com toque, D1 Conectar, bloco visual ----------
PASSOS_OLD = """    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', ''),
        (1, 'act_email', 'E-mail', 'E1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', ''),
        (5, 'act_email', 'E-mail', 'E2'),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem de valor', ''),
        (11, 'act_email', 'E-mail', 'E3'),
        (14, 'act_li_mensagem', 'LinkedIn – Follow-up', ''),
        (18, 'act_email', 'E-mail', 'E4'),
    ]"""
PASSOS_NEW = """    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', '', 'li_conectar'),
        (1, 'act_email', 'E-mail', 'E1', 'e1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', '', 'li_interagir'),
        (5, 'act_email', 'E-mail', 'E2', 'e2'),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem de valor', '', 'li_valor'),
        (11, 'act_email', 'E-mail', 'E3', 'e3'),
        (14, 'act_li_mensagem', 'LinkedIn – Follow-up', '', 'li_followup'),
        (18, 'act_email', 'E-mail', 'E4', 'e4'),
    ]"""
LOOP_OLD = """        for dia, tipo, canal, email_cod in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito':"""
LOOP_NEW = """        for dia, tipo, canal, email_cod, toque in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao in ('enviado', 'aceito'):"""
LOOP_BODY = LOOP.rstrip('\n') + '\n'


def visual(c, label):
    c = swap(c, PASSOS_OLD, PASSOS_NEW, label + ' passos')
    c = swap(c, LOOP_OLD, LOOP_NEW, label + ' loop')
    ini = c.index("            if tipo == 'act_email':\n                link = conta.x_abm_link_email")
    fim_marca = "sem asset e sem pitch.</i></p>'\n"
    fim = c.index(fim_marca, ini) + len(fim_marca)
    c = c[:ini] + LOOP_BODY + c[fim:]
    c = swap(c, '\nfor conta in records:\n', '\n# --- Direcionamento visual (abm.dir.*) ---\n' + DEFS + '\nfor conta in records:\n', label + ' defs')
    return c


set_code(1329, visual(code(1329), 'A5'), 'A5 · Início da cadência')
set_code(1338, visual(code(1338), 'A14'), 'A14 · Onda 2')

# ---------- A9: encerrar cadência de verdade ----------
c = code(1333)
c = swap(c, """for conta in records:
    conta.write({'stage_id': env.ref('abm_setima.stage_nutricao').id})""",
"""SEM_INTENCAO = ('li_ads_relatorio', 'li_impressoes_semana', 'li_cliques',
                'resposta_automatica', 'resposta_negativa', 'resposta_a_classificar')
for conta in records:
    # Só sinal de intenção depois do início da cadência segura a conta (Ads semanal não conta).
    vivos = conta.x_abm_sinal_ids.filtered(lambda s: s.x_ativo and s.x_tipo not in SEM_INTENCAO
        and s.x_data and conta.x_abm_cadencia_inicio and s.x_data.date() >= conta.x_abm_cadencia_inicio)
    if vivos:
        nota(conta, 'Cadência encerrada no prazo, mas com sinal de intenção: conta mantida para decisão manual.')
        continue
    conta.write({'stage_id': env.ref('abm_setima.stage_nutricao').id})""", 'A9')
set_code(1333, c, 'A9 · Cadência sem sinal')
changes.append(('base.automation', 32, {'trg_date_id': 28708}, 'A9 · data = Início da cadência'))

# ---------- A11: asset só a partir de Engajada ----------
c = code(1335)
c = swap(c, "    if decisor and not ja_tem:",
"""    etapas_asset = [env.ref('abm_setima.stage_engajada').id, env.ref('abm_setima.stage_em_cadencia').id,
                    env.ref('abm_setima.stage_conversa').id]
    if decisor and not ja_tem and conta.stage_id.id in etapas_asset:""", 'A11')
set_code(1335, c, 'A11 · Conexão aceita')

# ---------- A15: sem duplicar formulário; cliente vai para o gestor ----------
c = code(1339)
c = swap(c, """    # A tarefa vem ANTES do sinal""",
"""    quem_cad = lead.contact_name or email
    if conta.activity_ids.filtered(lambda a: (a.summary or '').startswith('Formulário:') and quem_cad in (a.summary or '')):
        nota(conta, 'Novo cadastro de %s (lead #%s): já existe tarefa de contato aberta; tarefa e sinal não duplicados.' % (esc(quem_cad), lead.id))
        continue
    dono = gestor.id if (gestor and conta.stage_id == env.ref('abm_setima.stage_cliente_expansao')) else sdr_id
    # A tarefa vem ANTES do sinal""", 'A15 dedupe')
c = swap(c, "'abm_setima.act_ligacao', date_deadline=hoje, user_id=sdr_id,\n        summary='Formulário",
            "'abm_setima.act_ligacao', date_deadline=hoje, user_id=dono,\n        summary='Formulário", 'A15 dono')
set_code(1339, c, 'A15 · Formulário de conta-alvo')

# ---------- A19: texto (e pausa) ----------
c = code(1349)
c = c.replace('Engajada há 5 dias úteis sem iniciar cadência', 'Engajada há 7 dias sem iniciar cadência')
c = swap(c, 'cadência não iniciada em 5 dias úteis', 'cadência não iniciada em 7 dias', 'A19 texto')
set_code(1349, c, 'A19 · texto 7 dias')
changes.append(('base.automation', 42, {'active': False}, 'A19 · pausada até religar A5'))

# ---------- A20: só sinal de intenção (filtro) ----------
changes.append(('base.automation', 43, {'filter_domain':
    "[('team_id', '=', 20), ('stage_id', '=', 87), ('x_abm_sinal_ids', 'any', [('x_ativo', '=', True), "
    "('x_tipo', 'not in', ['li_ads_relatorio', 'li_impressoes_semana', 'li_cliques', "
    "'resposta_automatica', 'resposta_negativa', 'resposta_a_classificar'])])]"}, 'A20 · filtro por intenção'))

# ---------- Fila: reconciliação de trilha ----------
c = code(1324)
c = swap(c, """else:
    tipos_abm = env['mail.activity.type'].search""", """else:
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
    tipos_abm = env['mail.activity.type'].search""", 'Fila')
set_code(1324, c, 'Fila de preparação · reconciliação de trilha')

# ---------- Notas padrão dos tipos de atividade ----------
html_blocks = re.findall(r'```html\n(.*?)```', md[md.find('### 5.3'):md.find('## 6.')], re.S)
for tid, h, label in zip([24, 35, 25, 33], html_blocks, ['Iniciar cadência', 'Definir trilha', 'LinkedIn – Seguir/Interagir', 'Preparar reunião']):
    changes.append(('mail.activity.type', tid, {'default_note': h.strip()}, 'Nota · ' + label))

# ---------- Modelos de e-mail (esqueleto) ----------
Y = lambda t: '<span style="background-color:#fff3a3">[%s]</span>' % t
ASS = '<p><t t-out="object.user_id.name"/><br/>Sétima</p>'
PS = '<p>P.S.: o case do Tera e outros projetos: <a t-att-href="object.x_abm_link_email">setima.cc</a></p>'
E1_SEM = ''.join(['<p>%s,</p>' % Y('Nome'),
    '<p>%s</p>' % Y('1–2 frases: gatilho ou observação da Ficha. Só desta conta.'),
    '<p>%s</p>' % Y('1 frase: o que isso significa para o papel desta pessoa (Ângulo na atividade).'),
    '<p>Fizemos o configurador 3D do VW Tera a partir de um único modelo digital do carro.</p>',
    '<p>%s</p>' % Y('Pergunta: vale eu montar uma prévia do MODELO DA FICHA para você ver como ficaria?'), ASS, PS])
E1_FRACO = ''.join(['<p>%s,</p>' % Y('Nome'),
    '<p>%s</p>' % Y('1–2 frases: o que você viu no configurador deles (testado no celular), sem chamar de ruim ou fraco.'),
    '<p>%s</p>' % Y('1 frase: o que isso significa para o papel desta pessoa (Ângulo na atividade).'),
    '<p>%s</p>' % Y('Prova, 1 frase. Padrão: no configurador que fizemos para o VW Tera, interior, rodas e versões ficam no mesmo lugar e rodam no celular. Variante C: o mesmo modelo 3D gera site, social e OOH.'),
    '<p>%s</p>' % Y('Pergunta: quer que eu monte o MODELO DA FICHA nesse padrão para você comparar com o atual?'), ASS, PS])
E2 = ''.join(['<p>%s,</p>' % Y('Nome'),
    '<p>%s</p>' % Y('Meia frase retomando o E1, sem “conforme e-mail anterior”.'),
    '<p>O configurador do VW Tera saiu de um único modelo 3D do carro, e esse mesmo modelo serve para imagens e vídeos, sem nova sessão de foto a cada cor ou versão.</p>',
    '<p>%s</p>' % Y('1 frase ligada à trilha: sem configurador = site e campanha do mesmo modelo; configurador fraco = realismo, interior, celular.'),
    '<p>%s</p>' % Y('Uma pergunta sobre como eles fazem hoje.'), ASS])
E3 = ''.join(['<p>%s,</p>' % Y('Nome'),
    '<p>%s</p>' % Y('Gatilho de reserva da Ficha, 1 frase.'),
    '<p>Fica a sugestão: 20 minutos para eu te mostrar o %s montado em 3D, como a produção funciona e quanto custa cada peça depois que o modelo existe.</p>' % Y('MODELO DA FICHA'),
    '<p>%s</p>' % Y('Objeção provável da Ficha respondida em 1 frase.'),
    '<p>%s</p>' % Y('Duas opções de dia. Ex.: terça ou quinta da semana que vem funciona?'), ASS])
E4 = ''.join(['<p>%s, não quero lotar sua caixa. Se configurador e conteúdo 3D não estão na pauta agora, tudo bem.</p>' % Y('Nome'),
    '<p>Duas saídas: me diz quem cuida disso na <t t-out="object.partner_id.name or object.name"/>, ou eu volto a falar perto do %s. Qual prefere?</p>' % Y('próximo lançamento ou gatilho da Ficha'), ASS])
EMP = '{{ object.partner_id.name or object.name }}'
TPL = {68: ('Uma ideia para o site da ' + EMP, E1_SEM), 69: ('O configurador da ' + EMP, E1_FRACO),
       70: ('Como ficou o configurador do VW Tera', E2), 71: ('Como ficou o configurador do VW Tera', E2),
       72: ('20 minutos com o seu carro em 3D', E3), 73: ('20 minutos com o seu carro em 3D', E3),
       74: ('Encerro por aqui?', E4), 75: ('Encerro por aqui?', E4)}
for tid, (subj, body) in TPL.items():
    changes.append(('mail.template', tid, {'subject': subj, 'body_html': body}, 'Modelo %s' % tid))

# ---------- Parâmetros abm.dir.* ----------
sec7 = md[md.find('## 7.'):]
params = {}
for linha in sec7.split('\n'):
    m = re.match(r'\| `(abm\.[a-z_.0-9]+)` \| (.*) \|$', linha)
    if m:
        partes = re.findall(r'`([^`]*)`', m.group(2))
        params[m.group(1)] = '\n'.join(partes)
E1_BASE = params['abm.dir.e1.sem_config'].split('\n! ')[0]
params['abm.dir.e1.config_fraco'] = E1_BASE + '\n' + params['abm.dir.e1.config_fraco'].split('\n', )[-1] if params['abm.dir.e1.config_fraco'].startswith('!') else E1_BASE + '\n' + params['abm.dir.e1.config_fraco']

params['abm.dir.e1.config_fraco'] = params['abm.dir.e1.config_fraco'].replace('(1 frase, já vem no modelo)', '(1 frase, sugestão entre colchetes no modelo)')
print('parametros:', len(params))
for k, v in params.items():
    changes.append(('param', k, v, 'Parâmetro ' + k))

for ch in changes:
    print('-', ch[3])
json.dump([[c[0], c[1], c[2], c[3]] for c in changes], open('changes.json', 'w'), ensure_ascii=False, indent=1)

if APPLY:
    for model, rid, vals, label in changes:
        if model == 'param':
            call('ir.config_parameter', 'set_param', key=rid, value=vals)
        else:
            call(model, 'write', ids=[rid], vals=vals)
        print('OK', label)
