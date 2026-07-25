"""Constantes de modelos, campos e escopo de equipes.

RE-01 — `ALLOWED_TEAM_IDS` é definido AQUI e em nenhum outro lugar. Qualquer
módulo que precise do escopo importa desta constante.
"""

# ---------------------------------------------------------------------------
# Escopo de equipes (RE-01)
# ---------------------------------------------------------------------------
# Trava de aplicação, não de segurança: quem tem acesso ao repositório pode
# editar esta lista. A trava real é uma ir.rule no usuário de serviço dentro
# do Odoo — ver odoo/README.md.
ALLOWED_TEAM_IDS = (16, 17, 21)

TEAM_FIELD = "team_id"

# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------
CRM_LEAD = "crm.lead"
CRM_STAGE = "crm.stage"
CRM_TEAM = "crm.team"
CRM_TAG = "crm.tag"
CRM_LOST_REASON = "crm.lost.reason"
RES_PARTNER = "res.partner"
RES_USERS = "res.users"
MAIL_ACTIVITY = "mail.activity"
MAIL_MESSAGE = "mail.message"
MAIL_TRACKING_VALUE = "mail.tracking.value"
UTM_SOURCE = "utm.source"
UTM_MEDIUM = "utm.medium"
UTM_CAMPAIGN = "utm.campaign"

# Modelos liberados para extração na Fase 1 (leitura).
MODELOS_EXTRAIVEIS = (
    CRM_LEAD,
    CRM_STAGE,
    CRM_TEAM,
    CRM_TAG,
    CRM_LOST_REASON,
    RES_PARTNER,
    RES_USERS,
    MAIL_ACTIVITY,
    UTM_SOURCE,
    UTM_MEDIUM,
    UTM_CAMPAIGN,
)

# Modelos em que a Fase 2 pode escrever. Nada além disto.
MODELOS_EDITAVEIS = (CRM_LEAD, RES_PARTNER)

# ---------------------------------------------------------------------------
# Métodos
# ---------------------------------------------------------------------------
METODOS_LEITURA = frozenset({
    "search", "read", "search_read", "search_count", "fields_get",
    "read_group", "name_search", "name_get", "context_get", "check_access_rights",
})
METODOS_ESCRITA = frozenset({
    "write", "create", "unlink", "copy", "action_set_won", "action_set_lost",
    "toggle_active", "action_archive", "action_unarchive", "message_post",
})

# ---------------------------------------------------------------------------
# Nomes de parâmetros do JSON-2
# ---------------------------------------------------------------------------
# O JSON-2 só aceita parâmetros nomeados e os nomes precisam bater com a
# assinatura do método no Odoo 19 (RF-21). Centralizados aqui para que uma
# eventual divergência da /doc da base seja corrigida em um único ponto.
PARAM_IDS = "ids"           # recordset em que o método é chamado
PARAM_CONTEXT = "context"
PARAM_DOMAIN = "domain"
PARAM_FIELDS = "fields"
PARAM_LIMIT = "limit"
PARAM_OFFSET = "offset"
PARAM_ORDER = "order"
PARAM_VALS = "vals"         # write(self, vals)
PARAM_VALS_LIST = "vals_list"  # create(self, vals_list)

# ---------------------------------------------------------------------------
# Conjuntos de campos padrão
# ---------------------------------------------------------------------------
# Nunca buscar todos os campos de um modelo (RF-09): toda extração parte de uma
# lista explícita. Estes são os padrões; qualquer campo é validado contra o
# fields_get real da base antes da chamada (RF-10), inclusive customizados x_.
CAMPOS_PADRAO = {
    CRM_LEAD: [
        "id", "name", "type", "active", "partner_id", "partner_name", "contact_name",
        "email_from", "phone", "stage_id", "user_id", "team_id", "expected_revenue",
        "prorated_revenue", "probability", "date_deadline", "create_date", "write_date",
        "date_open", "date_closed", "date_last_stage_update", "day_open", "day_close",
        "source_id", "medium_id", "campaign_id", "lost_reason_id", "tag_ids",
        "activity_date_deadline", "activity_summary", "won_status",
    ],
    CRM_STAGE: ["id", "name", "sequence", "is_won", "team_id", "fold"],
    CRM_TEAM: ["id", "name", "user_id", "active", "company_id"],
    CRM_TAG: ["id", "name"],
    CRM_LOST_REASON: ["id", "name", "active"],
    RES_PARTNER: [
        "id", "name", "is_company", "parent_id", "email", "phone", "mobile",
        "city", "state_id", "country_id", "vat", "user_id", "create_date",
    ],
    RES_USERS: ["id", "name", "login", "active"],
    MAIL_ACTIVITY: [
        "id", "res_model", "res_id", "res_name", "activity_type_id", "summary",
        "date_deadline", "user_id", "create_date",
    ],
    UTM_SOURCE: ["id", "name"],
    UTM_MEDIUM: ["id", "name"],
    UTM_CAMPAIGN: ["id", "name"],
}

# Campos mínimos que as análises precisam (validados na base antes de rodar).
CAMPOS_ANALISE = [
    "id", "name", "type", "active", "stage_id", "user_id", "team_id",
    "expected_revenue", "probability", "create_date", "write_date",
    "date_closed", "date_last_stage_update", "source_id", "medium_id",
    "campaign_id", "lost_reason_id", "activity_date_deadline",
]

# Campo de data padrão para os filtros --desde/--ate (RF-08).
CAMPO_DATA_PADRAO = "create_date"

# ---------------------------------------------------------------------------
# Limites operacionais
# ---------------------------------------------------------------------------
TAMANHO_PAGINA = 500        # RF-07
LIMITE_CONFIRMACAO = 50     # RF-18
DIAS_PARADO_PADRAO = 14     # RF-14
