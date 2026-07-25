"""Escopo de equipes — a trava que atravessa todas as fases (RE-01 a RE-04).

RE-02 — toda query em crm.lead recebe o filtro de equipe automaticamente. Não
existe flag para desligar: o filtro é aplicado dentro das funções de acesso,
não pelo chamador.
RE-03 — antes de qualquer escrita, os registros alvo são relidos e a operação
inteira é abortada se algum estiver fora do escopo. Nada de filtrar em silêncio
e seguir com o resto.
RE-04 — `team_id` vazio conta como FORA do escopo.

Limitação honesta: isto é trava de aplicação. A trava real é uma `ir.rule` no
usuário de serviço dentro do Odoo (ver odoo/README.md).
"""

from .domain import combinar_e
from .errors import ScopeViolationError
from .models import ALLOWED_TEAM_IDS, CRM_LEAD, RES_PARTNER, TEAM_FIELD
from .utils import id_m2o as _id_m2o

FILTRO_EQUIPES = [(TEAM_FIELD, "in", list(ALLOWED_TEAM_IDS))]


def dominio_equipes():
    return [tuple(FILTRO_EQUIPES[0])]


def escopar_dominio_lead(domain=None):
    """AND do domain do chamador com o filtro de equipes (RE-02)."""
    return combinar_e(dominio_equipes(), domain)


def dominio_equipes_permitidas():
    """Domain para crm.team restrito aos IDs permitidos."""
    return [("id", "in", list(ALLOWED_TEAM_IDS))]


def equipe_permitida(team_id):
    """RE-04: None/False/0 é fora do escopo."""
    identificador = _id_m2o(team_id)
    return identificador in ALLOWED_TEAM_IDS


def verificar_leads_no_escopo(client, ids):
    """Relê os leads e aborta a operação inteira se algum estiver fora (RE-03).

    Devolve o mapa {id: team_id} dos registros verificados.
    """
    ids = [int(i) for i in ids]
    if not ids:
        return {}

    # active_test=False para que lead perdido/arquivado também seja verificado
    # em vez de sumir da leitura e ser tratado como "inexistente".
    registros = client.search_read(
        CRM_LEAD, [("id", "in", ids)], ["id", TEAM_FIELD],
        limit=len(ids), context={"active_test": False},
    )
    encontrados = {r["id"]: _id_m2o(r.get(TEAM_FIELD)) for r in registros}

    inexistentes = [i for i in ids if i not in encontrados]
    fora = [i for i, team in encontrados.items() if team not in ALLOWED_TEAM_IDS]

    if inexistentes or fora:
        detalhe = []
        if fora:
            equipes = sorted({str(encontrados[i]) for i in fora})
            detalhe.append(f"equipes encontradas: {', '.join(equipes)} "
                           f"(permitidas: {list(ALLOWED_TEAM_IDS)}; sem equipe = fora do escopo)")
        if inexistentes:
            detalhe.append(f"IDs inexistentes ou invisíveis para esta chave: {inexistentes}")
        raise ScopeViolationError(CRM_LEAD, sorted(fora) + sorted(inexistentes),
                                  " | ".join(detalhe))
    return encontrados


def verificar_partners_no_escopo(client, ids):
    """res.partner não tem team_id.

    O vínculo com o escopo é indireto: o contato precisa estar ligado a pelo
    menos um lead de uma equipe permitida. Contato sem nenhum lead no escopo é
    tratado como fora (mesmo critério de RE-04: ausência não libera).
    """
    ids = [int(i) for i in ids]
    if not ids:
        return {}

    vinculos = client.search_read_all(
        CRM_LEAD,
        escopar_dominio_lead([("partner_id", "in", ids)]),
        ["id", "partner_id"],
        context={"active_test": False},
    )
    com_lead = {}
    for registro in vinculos:
        partner = _id_m2o(registro.get("partner_id"))
        if partner is not None:
            com_lead.setdefault(partner, []).append(registro["id"])

    fora = [i for i in ids if i not in com_lead]
    if fora:
        raise ScopeViolationError(
            RES_PARTNER, fora,
            "contato sem nenhum lead nas equipes permitidas "
            f"{list(ALLOWED_TEAM_IDS)} — edição bloqueada.",
        )
    return com_lead


def verificar_vals_de_equipe(vals):
    """Impede mover um registro para fora do escopo pela própria escrita."""
    if TEAM_FIELD in vals and not equipe_permitida(vals[TEAM_FIELD]):
        raise ScopeViolationError(
            CRM_LEAD, [],
            f"o payload tenta gravar {TEAM_FIELD}={vals[TEAM_FIELD]!r}, fora de "
            f"{list(ALLOWED_TEAM_IDS)}. Mover registro para fora do escopo não é "
            "permitido por esta ferramenta.",
        )
