"""Camada de integração com o Odoo CRM via JSON-2 (Odoo 19).

Ferramental interno: extração, análise de pipeline e edição de dados das
equipes de venda 16, 17 e 21. Não altera as automações já existentes no
repositório (RNF-06).

Uso: `python -m odoo.cli --help` ou, dentro do Claude Code, os comandos
listados em odoo/README.md.
"""

from .models import ALLOWED_TEAM_IDS

__all__ = ["ALLOWED_TEAM_IDS"]
