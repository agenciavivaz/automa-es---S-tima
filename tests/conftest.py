"""Dublês de HTTP e de cliente. Nenhum teste toca a instância real (RNF-05)."""

import json

import pytest

from odoo.client import OdooClient, OdooCredentials


class RespostaFalsa:
    def __init__(self, status_code=200, payload=None, headers=None, texto=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.reason = "Falso"
        self.text = texto if texto is not None else json.dumps(payload, default=str)
        self.content = self.text.encode()

    def json(self):
        if self._payload is None and self.text:
            return json.loads(self.text)
        return self._payload


class SessaoFalsa:
    """Registra as chamadas e devolve respostas de uma fila ou de um roteador."""

    def __init__(self, respostas=None, roteador=None):
        self.respostas = list(respostas or [])
        self.roteador = roteador
        self.chamadas = []

    def post(self, url, json=None, headers=None, timeout=None):
        self.chamadas.append({"url": url, "body": json, "headers": headers,
                              "timeout": timeout})
        if self.roteador is not None:
            return self.roteador(url, json or {})
        if not self.respostas:
            return RespostaFalsa(200, [])
        resposta = self.respostas.pop(0)
        return resposta

    # -- consultas úteis nos testes ---------------------------------------

    def metodos_chamados(self):
        return [c["url"].rsplit("/json/2/", 1)[-1] for c in self.chamadas]

    def corpos_de(self, model, method):
        alvo = f"/json/2/{model}/{method}"
        return [c["body"] for c in self.chamadas if c["url"].endswith(alvo)]


CHAVE_FALSA = "chave-de-teste-nunca-real"


def credenciais(perfil="operacional", chave=CHAVE_FALSA):
    return OdooCredentials(url="https://exemplo.odoo.com", db="basefalsa",
                           api_key=chave, perfil=perfil)


@pytest.fixture
def sessao():
    return SessaoFalsa()


def montar_cliente(sessao, **kwargs):
    kwargs.setdefault("max_tentativas", 3)
    return OdooClient(credenciais(), session=sessao, **kwargs)


@pytest.fixture
def cliente(sessao):
    return montar_cliente(sessao)


class SchemaFalso:
    """Substitui o SchemaCache sem chamar fields_get pela rede."""

    def __init__(self, campos_por_modelo):
        self.campos_por_modelo = {
            model: {nome: (info if isinstance(info, dict) else {"type": info})
                    for nome, info in campos.items()}
            for model, campos in campos_por_modelo.items()
        }

    def fields(self, model, refresh=False):
        return self.campos_por_modelo.get(model, {})

    def nomes(self, model, refresh=False):
        return set(self.fields(model))

    def validar(self, model, campos, refresh=False):
        import difflib

        from odoo.errors import UnknownFieldError

        disponiveis = self.nomes(model)
        invalidos = [c for c in campos if c.split(".", 1)[0] not in disponiveis and c != "id"]
        if invalidos:
            sugestoes = {
                campo: difflib.get_close_matches(campo, sorted(disponiveis), n=3, cutoff=0.6)
                for campo in invalidos
            }
            raise UnknownFieldError(model, invalidos, sugestoes)
        return list(campos)

    def filtrar_existentes(self, model, campos, refresh=False):
        disponiveis = self.nomes(model)
        return [c for c in campos if c.split(".", 1)[0] in disponiveis or c == "id"]


CAMPOS_LEAD = {
    "id": "integer", "name": "char", "type": "selection", "active": "boolean",
    "partner_id": "many2one", "stage_id": "many2one", "user_id": "many2one",
    "team_id": "many2one", "expected_revenue": "float", "probability": "float",
    "create_date": "datetime", "write_date": "datetime", "date_closed": "datetime",
    "date_last_stage_update": "datetime", "source_id": "many2one",
    "medium_id": "many2one", "campaign_id": "many2one", "lost_reason_id": "many2one",
    "tag_ids": "many2many", "activity_date_deadline": "date", "email_from": "char",
    "phone": "char",
}

CAMPOS_PARTNER = {
    "id": "integer", "name": "char", "email": "char", "phone": "char",
    "user_id": "many2one", "city": "char",
}

CAMPOS_STAGE = {
    "id": "integer", "name": "char", "sequence": "integer", "is_won": "boolean",
    "team_id": "many2one", "fold": "boolean",
}


@pytest.fixture
def schema():
    return SchemaFalso({
        "crm.lead": CAMPOS_LEAD,
        "res.partner": CAMPOS_PARTNER,
        "crm.stage": CAMPOS_STAGE,
        "crm.team": {"id": "integer", "name": "char", "active": "boolean",
                     "user_id": "many2one"},
        "mail.tracking.value": {"id": "integer", "mail_message_id": "many2one",
                                "field_id": "many2one", "old_value_char": "char",
                                "new_value_char": "char", "create_date": "datetime"},
    })


class ClienteFalso:
    """Cliente com respostas pré-programadas por (model, method)."""

    def __init__(self, respostas=None, perfil="operacional"):
        self.respostas = respostas or {}
        self.perfil = perfil
        self.somente_leitura = False
        self.chamadas = []
        self.domains = []
        self.ultimo_domain = None

    def _resposta(self, model, method, padrao=None):
        self.chamadas.append((model, method))
        valor = self.respostas.get((model, method), padrao)
        return valor() if callable(valor) else valor

    def _registrar_domain(self, model, domain):
        self.ultimo_domain = domain
        self.domains.append((model, domain))

    def search(self, model, domain, **kwargs):
        self._registrar_domain(model, domain)
        return self._resposta(model, "search", [])

    def read(self, model, ids, fields, **kwargs):
        registros = self._resposta(model, "read", [])
        return [r for r in registros if r["id"] in list(ids)]

    def search_read(self, model, domain, fields, **kwargs):
        self._registrar_domain(model, domain)
        registros = self._resposta(model, "search_read", [])
        return _filtrar_por_domain(registros, domain)

    def search_read_all(self, model, domain, fields, **kwargs):
        return self.search_read(model, domain, fields, **kwargs)

    def search_count(self, model, domain, **kwargs):
        return len(self.search_read(model, domain, [], **kwargs))

    def fields_get(self, model, **kwargs):
        return self._resposta(model, "fields_get", {})

    def write(self, model, ids, vals, **kwargs):
        self.chamadas.append((model, "write"))
        self.ultima_escrita = {"model": model, "ids": list(ids), "vals": dict(vals)}
        return True

    def create(self, model, vals_list, **kwargs):
        self.chamadas.append((model, "create"))
        self.ultima_criacao = {"model": model, "vals_list": list(vals_list)}
        return [901 + i for i in range(len(vals_list))]


def _filtrar_por_domain(registros, domain):
    """Aplica só os filtros `id in [...]` — suficiente para os testes de escopo."""
    ids_permitidos = None
    for token in domain or []:
        if isinstance(token, (list, tuple)) and len(token) == 3 and token[0] == "id" \
                and token[1] == "in":
            ids_permitidos = set(token[2])
    if ids_permitidos is None:
        return list(registros)
    return [r for r in registros if r.get("id") in ids_permitidos]
