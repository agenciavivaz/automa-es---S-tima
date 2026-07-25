"""Fase 3 — edição de configuração do Odoo (campos, estágios, tags, automações).

Este pacote é o ÚNICO ponto do repositório autorizado a ler a chave de
configuração (perfil admin). Nenhum arquivo fora daqui nomeia essa variável de
ambiente — ela é declarada em `credentials.VARIAVEL_CHAVE_ADMIN`
(RNF-07 / critério de aceite 17).

A aplicação de configuração (`config diff` / `config apply`) ainda NÃO está
implementada, por decisão explícita do PRD: cada fase só começa depois da
anterior estar funcionando e validada contra a base real, e a Fase 3 mexe no
schema de uma base de produção. Ver "Fase 3" em odoo/README.md.

Por ora, este pacote expõe apenas as credenciais de admin, usadas pelo
`test-connection` para validar as duas chaves (RF-06).
"""

from .credentials import (
    CHAVE_ADMIN_DISPONIVEL,
    VARIAVEL_CHAVE_ADMIN,
    cliente_admin,
    credenciais_admin,
)

__all__ = [
    "cliente_admin",
    "credenciais_admin",
    "CHAVE_ADMIN_DISPONIVEL",
    "VARIAVEL_CHAVE_ADMIN",
]
