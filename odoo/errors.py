"""Exceções da camada de integração com o Odoo.

Nenhuma mensagem de erro daqui pode conter chave de API (RNF-01). O cliente
sanitiza o texto antes de instanciar qualquer uma destas classes.
"""


class OdooError(Exception):
    """Base de todos os erros da camada Odoo."""


class OdooConfigError(OdooError):
    """Variável de ambiente obrigatória ausente ou inválida (RF-03)."""


class OdooTransportError(OdooError):
    """Falha de rede/timeout depois de esgotadas as tentativas (RF-04)."""


class OdooRequestError(OdooError):
    """Erro devolvido pelo endpoint JSON-2 com status HTTP real."""

    def __init__(self, status_code, name, message, *, model=None, method=None, arguments=None):
        self.status_code = status_code
        self.name = name or "Erro"
        self.message = message or ""
        self.model = model
        self.method = method
        self.arguments = arguments or []
        alvo = f"{model}.{method}" if model and method else "chamada JSON-2"
        super().__init__(f"[HTTP {status_code}] {alvo} → {self.name}: {self.message}")


class OdooAuthError(OdooRequestError):
    """401 — chave inválida, revogada ou expirada."""


class OdooPermissionError(OdooRequestError):
    """403 — a chave autenticou, mas o usuário não tem permissão."""


class UnknownFieldError(OdooError):
    """Campo pedido não existe no modelo naquela base (RF-10)."""

    def __init__(self, model, campos_invalidos, sugestoes=None):
        self.model = model
        self.campos_invalidos = list(campos_invalidos)
        self.sugestoes = sugestoes or {}
        partes = []
        for campo in self.campos_invalidos:
            proximos = self.sugestoes.get(campo) or []
            if proximos:
                partes.append(f"'{campo}' (parecidos: {', '.join(proximos)})")
            else:
                partes.append(f"'{campo}' (nenhum campo parecido encontrado)")
        super().__init__(
            f"Campo inexistente em {model}: " + "; ".join(partes) +
            f". Confira os campos reais com: python -m odoo.cli schema fields {model}"
        )


class ScopeViolationError(OdooError):
    """Registro fora das equipes permitidas (RE-03/RE-04)."""

    def __init__(self, model, ids_bloqueados, detalhe=""):
        self.model = model
        self.ids_bloqueados = list(ids_bloqueados)
        super().__init__(
            f"Operação abortada: {len(self.ids_bloqueados)} registro(s) de {model} "
            f"fora das equipes permitidas — IDs {self.ids_bloqueados}. "
            f"{detalhe}".strip()
        )


class ReadOnlyClientError(OdooError):
    """Tentativa de escrita em um cliente aberto como somente leitura (RNF-02)."""


class ConfirmationRequired(OdooError):
    """Operação acima do limite sem confirmação interativa (RF-18)."""
