"""Cliente do endpoint JSON-2 do Odoo 19 (RF-01).

    POST https://<base>/json/2/<model>/<method>
    Authorization: Bearer <API_KEY>
    X-Odoo-Database: <DATABASE>
    Content-Type: application/json

Corpo: JSON com parâmetros nomeados (o JSON-2 não aceita posicionais), mais
`ids` (recordset alvo) e `context`. Erros voltam com status HTTP real e payload
`{"name", "message", "arguments", "context", "debug"}`.

XML-RPC e JSON-RPC não são usados aqui e não existe fallback para eles: estão
depreciados e saem do Odoo Online 21.1.
"""

import logging
import os
import random
import time

import requests

from .errors import (
    OdooAuthError,
    OdooConfigError,
    OdooPermissionError,
    OdooRequestError,
    OdooTransportError,
    ReadOnlyClientError,
)
from .models import (
    METODOS_ESCRITA,
    PARAM_CONTEXT,
    PARAM_DOMAIN,
    PARAM_FIELDS,
    PARAM_IDS,
    PARAM_LIMIT,
    PARAM_OFFSET,
    PARAM_ORDER,
    PARAM_VALS,
    PARAM_VALS_LIST,
    TAMANHO_PAGINA,
)
from .utils import id_m2o as _id_m2o, nome_m2o as _nome_m2o

log = logging.getLogger("odoo.client")

TIMEOUT_PADRAO = 30.0          # RF-05
MAX_TENTATIVAS = 3             # RF-04
STATUS_COM_RETRY = frozenset({429, 500, 502, 503, 504})
BACKOFF_BASE = 1.0

PERFIL_OPERACIONAL = "operacional"
PERFIL_ADMIN = "admin"


class OdooCredentials:
    """URL, banco e chave de um perfil. A chave nunca é impressa nem logada."""

    def __init__(self, url, db, api_key, perfil):
        if not url:
            raise OdooConfigError("ODOO_URL não definida. Ex.: https://minhaempresa.odoo.com")
        if not db:
            raise OdooConfigError("ODOO_DB não definida (nome do banco no Odoo Online).")
        if not api_key:
            raise OdooConfigError(
                f"Chave de API do perfil '{perfil}' não definida. "
                "Gere em Configurações → Usuários e Empresas → Usuários → "
                "aba Preferências → Nova chave de API e coloque no .env."
            )
        # A URL copiada do navegador costuma vir com o sufixo /odoo (rota do
        # webclient). O JSON-2 fica na raiz: /odoo/json/2 cai no CSRF do
        # webclient e volta 400 "Session expired".
        url = url.rstrip("/")
        if url.endswith("/odoo"):
            url = url[: -len("/odoo")]
        self.url = url
        self.db = db
        self.api_key = api_key
        self.perfil = perfil

    def __repr__(self):  # nunca expõe a chave
        return f"<OdooCredentials perfil={self.perfil} url={self.url} db={self.db} chave=***>"

    __str__ = __repr__


def credenciais_operacionais(env=None):
    """Perfil operacional — leitura e escrita de registros das equipes permitidas."""
    env = env if env is not None else os.environ
    return OdooCredentials(
        url=env.get("ODOO_URL", "").strip(),
        db=env.get("ODOO_DB", "").strip(),
        api_key=env.get("ODOO_API_KEY", "").strip(),
        perfil=PERFIL_OPERACIONAL,
    )


class OdooClient:
    """Chamadas ao JSON-2 com retry, timeout e erros legíveis."""

    def __init__(self, credentials, *, timeout=None, max_tentativas=MAX_TENTATIVAS,
                 somente_leitura=False, contexto_padrao=None, session=None):
        self.credentials = credentials
        self.timeout = float(timeout if timeout is not None
                             else os.environ.get("ODOO_TIMEOUT", TIMEOUT_PADRAO))
        self.max_tentativas = max(1, int(max_tentativas))
        self.somente_leitura = somente_leitura
        self.contexto_padrao = dict(contexto_padrao or {})
        self.session = session or requests.Session()

    # -- infraestrutura ----------------------------------------------------

    @property
    def perfil(self):
        return self.credentials.perfil

    def _headers(self):
        # Montados a cada chamada e nunca logados (RNF-04).
        return {
            "Authorization": f"Bearer {self.credentials.api_key}",
            "X-Odoo-Database": self.credentials.db,
            "Content-Type": "application/json",
        }

    def _sanitizar(self, texto):
        """Blindagem contra a chave vazar em mensagem de erro (RNF-01)."""
        if not texto:
            return ""
        return str(texto).replace(self.credentials.api_key, "***")

    def _erro(self, resposta, model, method):
        try:
            payload = resposta.json()
        except ValueError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        nome = payload.get("name") or resposta.reason or "Erro"
        mensagem = self._sanitizar(payload.get("message") or resposta.text[:500])
        argumentos = payload.get("arguments") or []
        status = resposta.status_code

        if status == 401:
            return OdooAuthError(
                status, nome,
                f"{mensagem} — chave inválida, revogada ou expirada "
                f"(perfil '{self.perfil}'; chaves de usuário comum expiram em até 90 dias).",
                model=model, method=method, arguments=argumentos,
            )
        if status == 403:
            return OdooPermissionError(
                status, nome,
                f"{mensagem} — a chave autenticou, mas o usuário do perfil "
                f"'{self.perfil}' não tem permissão para {model}.{method}.",
                model=model, method=method, arguments=argumentos,
            )
        return OdooRequestError(status, nome, mensagem, model=model, method=method,
                                arguments=argumentos)

    def _espera(self, tentativa, resposta=None):
        if resposta is not None:
            cabecalho = resposta.headers.get("Retry-After")
            if cabecalho:
                try:
                    return min(float(cabecalho), 60.0)
                except ValueError:
                    pass
        return BACKOFF_BASE * (2 ** (tentativa - 1)) + random.uniform(0, 0.25)

    def call(self, model, method, params=None, *, context=None):
        """Chamada crua ao JSON-2. Devolve o resultado já desserializado."""
        if self.somente_leitura and method in METODOS_ESCRITA:
            raise ReadOnlyClientError(
                f"Cliente aberto como somente leitura: {model}.{method} bloqueado. "
                "Comandos de análise e extração nunca escrevem (RNF-02)."
            )

        corpo = dict(params or {})
        contexto = {**self.contexto_padrao, **(context or {})}
        if contexto:
            corpo[PARAM_CONTEXT] = contexto

        url = f"{self.credentials.url}/json/2/{model}/{method}"
        log.debug("JSON-2 %s.%s params=%s", model, method,
                  {k: v for k, v in corpo.items() if k != PARAM_CONTEXT})

        ultima_excecao = None
        for tentativa in range(1, self.max_tentativas + 1):
            try:
                resposta = self.session.post(
                    url, json=corpo, headers=self._headers(), timeout=self.timeout
                )
            except requests.RequestException as exc:
                ultima_excecao = OdooTransportError(
                    f"Falha de rede em {model}.{method}: {self._sanitizar(exc)}"
                )
                if tentativa == self.max_tentativas:
                    raise ultima_excecao from exc
                time.sleep(self._espera(tentativa))
                continue

            if resposta.status_code in STATUS_COM_RETRY and tentativa < self.max_tentativas:
                espera = self._espera(tentativa, resposta)
                log.warning("HTTP %s em %s.%s — tentativa %s/%s, aguardando %.1fs",
                            resposta.status_code, model, method, tentativa,
                            self.max_tentativas, espera)
                time.sleep(espera)
                continue

            if resposta.status_code >= 400:
                # Sem retry em 4xx que não seja 429 (RF-04).
                raise self._erro(resposta, model, method)

            if not resposta.content:
                return None
            try:
                return resposta.json()
            except ValueError as exc:
                raise OdooRequestError(
                    resposta.status_code, "RespostaInvalida",
                    f"Resposta não-JSON do endpoint: {self._sanitizar(resposta.text[:200])}",
                    model=model, method=method,
                ) from exc

        raise ultima_excecao or OdooTransportError(
            f"{model}.{method} falhou após {self.max_tentativas} tentativas."
        )

    # -- métodos ORM -------------------------------------------------------

    def search(self, model, domain, *, limit=None, offset=None, order=None, context=None):
        params = {PARAM_DOMAIN: _serializar_domain(domain)}
        if limit is not None:
            params[PARAM_LIMIT] = limit
        if offset:
            params[PARAM_OFFSET] = offset
        if order:
            params[PARAM_ORDER] = order
        return self.call(model, "search", params, context=context) or []

    def read(self, model, ids, fields, *, context=None):
        if not ids:
            return []
        return self.call(model, "read",
                         {PARAM_IDS: list(ids), PARAM_FIELDS: list(fields)},
                         context=context) or []

    def search_read(self, model, domain, fields, *, limit=None, offset=None,
                    order=None, context=None):
        """Uma página. Para o conjunto completo use `search_read_all` (RF-07)."""
        params = {
            PARAM_DOMAIN: _serializar_domain(domain),
            PARAM_FIELDS: list(fields),
        }
        if limit is not None:
            params[PARAM_LIMIT] = limit
        if offset:
            params[PARAM_OFFSET] = offset
        if order:
            params[PARAM_ORDER] = order
        return self.call(model, "search_read", params, context=context) or []

    def search_read_all(self, model, domain, fields, *, order="id asc",
                        tamanho_pagina=TAMANHO_PAGINA, context=None, limite_total=None):
        """search_read paginado. A paginação é invisível para o chamador (RF-07)."""
        registros = []
        offset = 0
        while True:
            tamanho = tamanho_pagina
            if limite_total is not None:
                restante = limite_total - len(registros)
                if restante <= 0:
                    break
                tamanho = min(tamanho_pagina, restante)
            pagina = self.search_read(model, domain, fields, limit=tamanho,
                                      offset=offset, order=order, context=context)
            registros.extend(pagina)
            if len(pagina) < tamanho:
                break
            offset += tamanho
        return registros

    def search_count(self, model, domain, *, context=None):
        return self.call(model, "search_count",
                         {PARAM_DOMAIN: _serializar_domain(domain)}, context=context) or 0

    def fields_get(self, model, *, attributes=None, context=None):
        params = {}
        if attributes:
            params["attributes"] = list(attributes)
        return self.call(model, "fields_get", params, context=context) or {}

    def write(self, model, ids, vals, *, context=None):
        """write(self, vals) — `ids` seleciona o recordset (Fase 2)."""
        return self.call(model, "write",
                         {PARAM_IDS: list(ids), PARAM_VALS: dict(vals)},
                         context=context)

    def create(self, model, vals_list, *, context=None):
        """create(self, vals_list) — devolve os IDs criados (Fase 2)."""
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        return self.call(model, "create",
                         {PARAM_VALS_LIST: [dict(v) for v in vals_list]},
                         context=context)

    # -- identidade --------------------------------------------------------

    def whoami(self):
        """Identidade do usuário dono da chave, em melhor esforço.

        O JSON-2 não expõe um endpoint de sessão. `res.users.apikeys` é filtrado
        por regra de registro para as chaves do próprio usuário, o que identifica
        usuários de serviço com precisão; um admin enxerga as chaves de todos e o
        resultado fica ambíguo — nesse caso devolvemos `usuario=None` e quem
        chama reporta a ambiguidade em vez de inventar um nome.
        """
        info = {"perfil": self.perfil, "usuario": None, "usuario_id": None,
                "chaves": [], "ambiguo": False, "observacao": ""}
        try:
            chaves = self.search_read(
                "res.users.apikeys", [],
                ["id", "user_id", "name", "scope", "expiration_date"],
                limit=50, order="id desc",
            )
        except OdooRequestError as exc:
            info["observacao"] = f"não foi possível ler res.users.apikeys: {exc.name}"
            chaves = []

        info["chaves"] = [
            {
                "nome": c.get("name"),
                "escopo": c.get("scope") or "completo",
                "expira_em": c.get("expiration_date") or "sem expiração",
                "usuario": _nome_m2o(c.get("user_id")),
            }
            for c in chaves
        ]
        usuarios = {_id_m2o(c.get("user_id")) for c in chaves if c.get("user_id")}
        usuarios.discard(None)
        if len(usuarios) == 1:
            uid = usuarios.pop()
            info["usuario_id"] = uid
            info["usuario"] = next(
                (_nome_m2o(c.get("user_id")) for c in chaves if _id_m2o(c.get("user_id")) == uid),
                None,
            )
        elif len(usuarios) > 1:
            info["ambiguo"] = True
            info["observacao"] = (
                "a chave enxerga chaves de API de vários usuários (perfil com direitos "
                "de administrador), então a identidade não pode ser deduzida por aqui"
            )
        return info

    def testar_leitura(self, model=None):
        """Prova que a chave autentica e lê: devolve a contagem de um modelo leve."""
        from .models import CRM_TEAM
        alvo = model or CRM_TEAM
        return {"model": alvo, "registros_visiveis": self.search_count(alvo, [])}


def cliente_operacional(*, somente_leitura=False, timeout=None, env=None, session=None):
    """Cliente do perfil operacional (ODOO_API_KEY).

    A chave de configuração (admin) NÃO é lida aqui — ela só existe dentro de
    `odoo/config/` (RNF-07).
    """
    return OdooClient(
        credenciais_operacionais(env),
        somente_leitura=somente_leitura,
        timeout=timeout,
        session=session,
    )


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _serializar_domain(domain):
    """Tuplas viram listas — JSON não tem tupla."""
    if domain is None:
        return []
    return [list(token) if isinstance(token, (list, tuple)) else token for token in domain]
