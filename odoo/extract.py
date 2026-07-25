"""Extração de dados do CRM (Fase 1).

Regras aplicadas aqui:
- RF-07 paginação transparente em lotes de 500;
- RF-08 filtro de período sobre `create_date` por padrão, campo trocável;
- RF-09 lista explícita de campos, nunca "todos";
- RF-10 campos validados contra o `fields_get` real da base antes da chamada;
- RE-02 crm.lead sempre com o filtro de equipes.

Modelos que não têm equipe própria são escopados pelo vínculo com os leads das
equipes permitidas (res.partner, mail.activity). Tabelas de referência
(crm.stage, utm.*, res.users, crm.lost.reason) são lidas inteiras — são listas
de configuração, não dados de cliente — e isso vai declarado no meta.
"""

import logging

from .domain import combinar_e
from .errors import OdooError
from .models import (
    ALLOWED_TEAM_IDS,
    CAMPO_DATA_PADRAO,
    CAMPOS_PADRAO,
    CRM_LEAD,
    CRM_TEAM,
    MAIL_ACTIVITY,
    MODELOS_EXTRAIVEIS,
    RES_PARTNER,
)
from .scope import dominio_equipes_permitidas, escopar_dominio_lead
from .utils import id_m2o, normalizar_periodo

log = logging.getLogger("odoo.extract")

LIMITE_IDS_EM_DOMINIO = 20000


def dominio_periodo(campo_data, desde=None, ate=None):
    inicio, fim = normalizar_periodo(desde, ate)
    filtros = []
    if inicio:
        filtros.append((campo_data, ">=", inicio))
    if fim:
        filtros.append((campo_data, "<=", fim))
    return filtros


class Extrator:
    def __init__(self, client, schema):
        self.client = client
        self.schema = schema

    # -- escopo por modelo -------------------------------------------------

    def _ids_leads_no_escopo(self, domain=None):
        ids = self.client.search(CRM_LEAD, escopar_dominio_lead(domain),
                                 context={"active_test": False})
        if len(ids) > LIMITE_IDS_EM_DOMINIO:
            raise OdooError(
                f"{len(ids)} leads no escopo — recorte o período com --desde/--ate "
                "antes de extrair modelos relacionados (o filtro por IDs fica grande "
                "demais para uma única chamada)."
            )
        return ids

    def dominio_escopado(self, model, domain=None):
        """Aplica o escopo de equipes conforme o modelo."""
        if model == CRM_LEAD:
            return escopar_dominio_lead(domain), "equipes 16/17/21 (filtro direto em team_id)"
        if model == CRM_TEAM:
            return combinar_e(dominio_equipes_permitidas(), domain), "equipes 16/17/21"
        if model == RES_PARTNER:
            leads = self.client.search_read_all(
                CRM_LEAD, escopar_dominio_lead([("partner_id", "!=", False)]),
                ["partner_id"], context={"active_test": False},
            )
            ids = sorted({id_m2o(l.get("partner_id")) for l in leads} - {None})
            return (combinar_e([("id", "in", ids)], domain),
                    f"{len(ids)} contatos vinculados a leads das equipes permitidas")
        if model == MAIL_ACTIVITY:
            ids = self._ids_leads_no_escopo()
            return (combinar_e([("res_model", "=", CRM_LEAD), ("res_id", "in", ids)], domain),
                    f"atividades de {len(ids)} leads das equipes permitidas")
        return (combinar_e(domain),
                "tabela de referência — sem escopo de equipe (leitura completa)")

    # -- extração ----------------------------------------------------------

    def extrair(self, model, *, campos=None, domain=None, desde=None, ate=None,
                campo_data=None, limite=None, ordem="id asc"):
        if model not in MODELOS_EXTRAIVEIS:
            raise OdooError(
                f"Modelo '{model}' não está liberado para extração. "
                f"Disponíveis: {', '.join(MODELOS_EXTRAIVEIS)}"
            )

        campo_data = campo_data or CAMPO_DATA_PADRAO
        if campos:
            campos = self.schema.validar(model, campos)
        else:
            # Lista padrão do modelo, reduzida ao que existe nesta base.
            padrao = CAMPOS_PADRAO.get(model) or ["id", "name"]
            campos = self.schema.filtrar_existentes(model, padrao)
            ausentes = [c for c in padrao if c not in campos]
            if ausentes:
                log.info("Campos do padrão ausentes nesta base e ignorados em %s: %s",
                         model, ", ".join(ausentes))

        filtros_periodo = []
        if desde or ate:
            self.schema.validar(model, [campo_data])
            filtros_periodo = dominio_periodo(campo_data, desde, ate)

        if domain:
            self.schema.validar(model, sorted(_campos_do_domain(domain)))

        escopado, descricao_escopo = self.dominio_escopado(
            model, combinar_e(domain, filtros_periodo)
        )

        registros = self.client.search_read_all(
            model, escopado, campos, order=ordem, limite_total=limite,
            context={"active_test": False} if model == CRM_LEAD else None,
        )

        meta = {
            "modelo": model,
            "escopo": descricao_escopo,
            "equipes_permitidas": list(ALLOWED_TEAM_IDS),
            "periodo": _texto_periodo(campo_data, desde, ate),
            "registros": len(registros),
            "campos": ", ".join(campos),
        }
        return registros, campos, meta


def _campos_do_domain(domain):
    from .domain import campos_referenciados
    return campos_referenciados(domain)


def _texto_periodo(campo_data, desde, ate):
    if not desde and not ate:
        return "sem filtro de período"
    inicio, fim = normalizar_periodo(desde, ate)
    return f"{campo_data} de {inicio or 'início'} até {fim or 'agora'}"
