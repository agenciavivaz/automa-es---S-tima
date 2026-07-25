"""Credencial do perfil de configuração (admin).

Separação de privilégio (seção 3 do PRD): a chave de configuração vive apenas
aqui. As Fases 1 e 2 usam exclusivamente a chave operacional e nunca caem de
volta na chave de admin — se ela não estiver definida, os comandos que
dependem dela falham com mensagem clara.
"""

import os

from ..client import PERFIL_ADMIN, OdooClient, OdooCredentials
from ..errors import OdooConfigError

VARIAVEL_CHAVE_ADMIN = "ODOO_ADMIN_API_KEY"


def CHAVE_ADMIN_DISPONIVEL(env=None):  # noqa: N802 — lido como constante no chamador
    env = env if env is not None else os.environ
    return bool(env.get(VARIAVEL_CHAVE_ADMIN, "").strip())


def credenciais_admin(env=None):
    env = env if env is not None else os.environ
    chave = env.get(VARIAVEL_CHAVE_ADMIN, "").strip()
    if not chave:
        raise OdooConfigError(
            f"{VARIAVEL_CHAVE_ADMIN} não definida. Comandos de configuração (Fase 3) "
            "exigem a chave do usuário admin e NUNCA usam a chave operacional como "
            "alternativa. Gere a chave em Configurações → Usuários e Empresas → "
            "Usuários → aba Preferências → Nova chave de API."
        )
    return OdooCredentials(
        url=env.get("ODOO_URL", "").strip(),
        db=env.get("ODOO_DB", "").strip(),
        api_key=chave,
        perfil=PERFIL_ADMIN,
    )


def cliente_admin(*, somente_leitura=True, timeout=None, env=None, session=None):
    """Cliente com a chave de admin. Somente leitura por padrão.

    Escrita de configuração só será liberada quando a Fase 3 for implementada,
    com dry-run padrão, diff e idempotência (RF-23 a RF-31).
    """
    return OdooClient(
        credenciais_admin(env),
        somente_leitura=somente_leitura,
        timeout=timeout,
        session=session,
    )
