"""Tipos de atividade e modelos de e-mail do ABM BrandSpot.

Os tipos espelham os 16 "ABM · …" da Sétima, com prefixo "ABM BrandSpot · " —
assim o menu Atividades de cada frente mostra só as suas, e a fila diária
consegue somar as duas pelo prefixo "ABM" (a SDR é a mesma).
"Definir trilha" (configurador) vira "Mapear estúdio".

Os e-mails nascem como RASCUNHO (como os da Sétima): A5 e A14 ficam
desligadas até eles serem reescritos e aprovados.
"""

PREFIXO = "ABM BrandSpot · "

# xml-id: (nome, categoria, ícone, res_model, nota, recorrente_em_dias)
TIPOS = {
    "act_dossie": ("Dossiê da conta", "default", "fa-search", "crm.lead",
                   "<p>Rodar o dossiê de guerrilha, mapear o estúdio e colar a URL no campo Dossiê.</p>", 0),
    "act_validar_comite": ("Validar comitê", "default", "fa-users", "crm.lead",
                           "<p>Confirmar o cargo atual no LinkedIn e ajustar papel e prioridade no comitê "
                           "(botão Editar comitê). Para estúdio, o decisor costuma estar em <b>EAD/Educação "
                           "Digital, Produção de Conteúdo/Audiovisual, Inovação acadêmica ou Marketing</b>; "
                           "Compras/Facilities entram como influenciador.</p>", 0),
    "act_asset": ("Preparar asset", "default", "fa-cube", "crm.lead",
                  "<p>Asset = conteúdo de <b>alto valor personalizado</b> para a conta. Como o BrandSpot "
                  "ainda não tem case, o asset é a prova: ex. <b>comparativo construir x alugar estúdio</b> "
                  "para o volume de aulas da conta, <b>convite para gravação-teste</b> no showroom com a "
                  "identidade da instituição, ou vídeo-amostra gravado no estúdio. Colar a URL no campo "
                  "Asset: isso gera a tarefa de envio para a SDR.</p>", 0),
    "act_iniciar_cadencia": ("Iniciar cadência", "default", "fa-play", "crm.lead",
                             "<p>Revisar o estúdio interno (e dossiê/asset, se houver). Marcar “Na cadência” "
                             "em até 3 pessoas e mover para <b>Em cadência</b>.</p><p><b>Atenção:</b> enquanto "
                             "os e-mails E1–E4 estiverem em rascunho a cadência automática fica desligada. Não "
                             "mover para Em cadência até o aviso de que os e-mails estão prontos.</p>", 0),
    "act_li_interagir": ("LinkedIn – Seguir/Interagir", "default", "fa-linkedin", "crm.lead",
                         "<p>Seguir e reagir a 1 post relevante. Sem convite.</p>", 0),
    "act_li_conectar": ("LinkedIn – Conectar", "default", "fa-linkedin", "crm.lead",
                        "<p>Convite com nota curta citando o dossiê. Ao concluir, marcar Conexão = Enviado.</p>", 0),
    "act_li_mensagem": ("LinkedIn – Mensagem", "default", "fa-linkedin", "crm.lead",
                        "<p>Mensagem com valor ou asset. Sem pitch na primeira.</p>", 0),
    "act_email": ("E-mail", "default", "fa-envelope", "crm.lead",
                  "<p>Enviar pelo chatter da conta, da caixa do SDR, usando o modelo indicado. Trocar o "
                  "destinatário para a pessoa da tarefa.</p>", 0),
    "act_ligacao": ("Ligação", "phonecall", "fa-phone", "crm.lead",
                    "<p>Roteiro de ligação e de voicemail. Objetivo: visita ao showroom em São Paulo "
                    "(ou 20 min online).</p>", 0),
    "act_whatsapp": ("WhatsApp", "default", "fa-whatsapp", "crm.lead",
                     "<p>Só com conversa prévia ou número vindo de formulário. Enviar pelo DataCrazy.</p>", 0),
    "act_classificar": ("Classificar resposta", "default", "fa-inbox", "crm.lead",
                        "<p><b>Classifique o sinal de resposta</b> (aba Sinais → altere o Tipo do sinal "
                        "“Resposta recebida (a classificar)”):</p><ul><li><b>Resposta automática, ausência ou "
                        "só “recebido”</b> → 0 pts. Nada a fazer.</li><li><b>Negativa / sem interesse</b> → 0 pts. "
                        "Pediu para não receber? Marcar opt-out no contato.</li><li><b>Genuína sem interesse "
                        "claro</b> → 30 pts. Ex.: fez uma pergunta, encaminhou para outra pessoa, “agora não, me "
                        "procure em X”. Responder e seguir a cadência.</li><li><b>Braço erguido</b> → 60 pts "
                        "(conta fica Quente). Ex.: quer conhecer o showroom, pediu tabela/proposta, aceitou ou "
                        "sugeriu reunião. Responder no mesmo dia e mover para <b>Conversa</b>.</li></ul><p>Resposta "
                        "por <b>DM no LinkedIn</b> ou <b>WhatsApp</b>: registrar você mesma um sinal na aba Sinais "
                        "com o tipo de resposta acima e a origem correta.</p>", 0),
    "act_agendar": ("Agendar reunião", "meeting", "fa-calendar", "crm.lead", False, 0),
    "act_preparar_reuniao": ("Preparar reunião", "default", "fa-briefcase", "crm.lead",
                             "<p>Visita ao showroom: confirmar quem vem, o que querem gravar/transmitir e o "
                             "volume mensal de aulas. Deixar o estúdio montado no formato da conta.</p>", 0),
    "act_estudio": ("Mapear estúdio", "default", "fa-video-camera", "crm.lead",
                    "<p><b>Mapear o estúdio interno da conta</b> (campo Estúdio interno). Tese: a instituição "
                    "já grava/transmite aulas em estúdio próprio e, para ampliar, pode alugar em vez de "
                    "construir.</p><ol><li><b>Site, YouTube e LinkedIn da conta:</b> menções a estúdio "
                    "próprio, “estúdio de gravação”, “produção de conteúdo EAD”, fotos do estúdio, vídeos "
                    "de aula (áudio, luz, cenário, câmeras).</li><li><b>Vagas abertas</b> (LinkedIn/Apollo): "
                    "produtor audiovisual, editor de vídeo, designer instrucional, coordenador de EAD — "
                    "sinal de que a produção está crescendo.</li><li>Escolher: <b>Já tem estúdio interno</b> "
                    "(estrutura profissional: ângulo = ampliar capacidade sem obra/CAPEX), <b>Estúdio interno "
                    "de baixa qualidade</b> (grava, mas amador: ângulo = padrão profissional pronto) ou "
                    "<b>Indefinido</b> (não deu para descobrir).</li><li>Registrar na nota da conta os links "
                    "e prints que justificam (viram a primeira linha personalizada do E1).</li></ol>", 0),
    "act_rotina": ("Rotina semanal", "default", "fa-refresh", False,
                   "<p><b>Segunda-feira, 15 minutos</b></p><ol><li><b>Apollo</b>, Visitantes do site "
                   "(brandspot.com.br), últimos 7 dias. Para cada domínio de conta ABM BrandSpot, registrar "
                   "\"Visita ao site\". Se a visita foi em estúdios, preços ou contato, registrar \"Visitou "
                   "cases, lead magnet ou contato\".</li><li><b>Posts do especialista.</b> Quem do comitê "
                   "reagiu ou comentou? Registrar \"Reagiu ou comentou post\".</li><li>Abrir o pipeline ABM "
                   "BrandSpot e olhar quais contas mudaram de faixa.</li></ol>", 7),
    "act_relatorio_ads": ("Relatório LinkedIn Ads (Claude Code)", "default", "fa-linkedin", "res.partner",
                          "<p><b>Toda segunda-feira</b></p><ol><li>LinkedIn Campaign Manager → campanha "
                          "<b>BrandSpot</b> → <b>Empresas</b> → View <b>Engagement</b>, período <b>Last 30 "
                          "days</b> → <b>Export</b> (CSV).</li><li>Enviar o CSV no Claude Code (repositório "
                          "automa-es---S-tima) pedindo: <i>“atualizar os scores do ABM BrandSpot com o relatório "
                          "do LinkedIn Ads”</i>.</li><li>Mesma régua da Sétima (0–30 pts, foto de 30 dias que "
                          "substitui a da semana anterior).</li><li>Revisar empresas de educação fora do ABM com "
                          "engajamento alto (candidatas a conta-alvo).</li></ol>", 7),
}

# Atividades sugeridas nos planos (mesmos dois planos da Sétima).
PLANOS = {
    "plan_preparacao_conta": ("ABM BrandSpot – Preparação da conta", [
        ("act_validar_comite", 0, "after_plan_date", False),
        ("act_li_interagir", 1, "after_plan_date", False),
        ("act_estudio", 1, "after_plan_date", False),
    ]),
    "plan_preparacao_reuniao": ("ABM BrandSpot – Preparação de reunião", [
        ("act_preparar_reuniao", 1, "before_plan_date", False),
        ("act_email", 1, "before_plan_date", "Confirmação"),
    ]),
}

# Situações do estúdio → rótulo do modelo de e-mail.
ESTUDIOS = [
    ("tem_estudio", "Já tem estúdio"),
    ("estudio_baixa", "Estúdio de baixa qualidade"),
    ("indefinido", "Indefinido"),
]

# (código, assunto, ideia por situação)
EMAILS = [
    ("E1", "Observação da conta", {
        "tem_estudio": "Observação específica: o estúdio que vocês já têm (link/print do dossiê). Pergunta: "
                       "quando a grade de gravações aperta, como vocês ampliam sem obra?",
        "estudio_baixa": "Observação específica: as aulas gravadas que vimos (link). Elogio + ponto concreto "
                         "(áudio, luz, cenário). Pergunta: já pensaram em gravar parte da grade em estúdio "
                         "profissional sem montar um?",
        "indefinido": "Observação específica da conta (cursos EAD, lançamento, expansão). Pergunta aberta: "
                      "onde vocês gravam/transmitem as aulas hoje?",
    }),
    ("E2", "Estrutura", {
        "tem_estudio": "Sem case ainda: a prova é a estrutura. 3 linhas sobre o estúdio do BrandSpot pronto "
                       "para gravar/transmitir aulas + custo de construir x alugar.",
        "estudio_baixa": "Sem case ainda: a prova é a estrutura. 3 linhas sobre o padrão de produção "
                         "(câmeras, luz, áudio, cenário) já montado no BrandSpot.",
        "indefinido": "Sem case ainda: a prova é a estrutura. 3 linhas sobre o estúdio do BrandSpot para "
                      "aulas (gravação e transmissão) + uma pergunta.",
    }),
    ("E3", "Convite ao showroom", {
        "tem_estudio": "Convite para conhecer o showroom em São Paulo (ou 20 min online): capacidade extra "
                       "sob demanda para os picos de gravação.",
        "estudio_baixa": "Convite para conhecer o showroom em São Paulo ou para uma gravação-teste de uma aula "
                         "com a identidade da instituição.",
        "indefinido": "Convite para conhecer o showroom em São Paulo (ou 20 min online).",
    }),
    ("E4", "Encerramento", {
        "tem_estudio": "Encerramento educado, porta aberta (quando precisarem de mais estúdio).",
        "estudio_baixa": "Encerramento educado, porta aberta (gravação-teste continua de pé).",
        "indefinido": "Encerramento educado, porta aberta.",
    }),
]


def corpo_email(codigo, rotulo, ideia):
    return (
        f"<p>[RASCUNHO {codigo} · {rotulo} — reescrever. Ideia: {ideia}]</p>"
        "<p>Olá, <!-- primeira linha personalizada obrigatória --></p>"
        "<p>Link: <t t-out=\"object.x_abm_link_email or ''\"/></p>"
        "<p t-if=\"object.x_abm_asset_url\">Material: <t t-out=\"object.x_abm_asset_url\"/></p>"
    )
