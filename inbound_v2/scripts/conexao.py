"""Conexão JSON-2 usada pelos scripts do Dashboard Inbound v2.

Reaproveita o cliente de `odoo/client.py`. Credenciais só das variáveis de
ambiente (ODOO_URL, ODOO_DB, ODOO_API_KEY): nunca impressas, logadas ou
gravadas. Se ODOO_URL vier com caminho (ex.: https://x.odoo.com/odoo), o
endpoint JSON-2 usa só esquema + host.
"""

import os
import sys
from urllib.parse import urlparse

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if RAIZ not in sys.path:
    sys.path.insert(0, RAIZ)

from odoo.client import OdooClient, OdooCredentials  # noqa: E402


def base_url():
    u = urlparse(os.environ.get("ODOO_URL", "").strip())
    return f"{u.scheme}://{u.netloc}" if u.netloc else ""


def cliente(somente_leitura=True, timeout=120):
    cred = OdooCredentials(
        base_url(),
        os.environ.get("ODOO_DB", "").strip(),
        os.environ.get("ODOO_API_KEY", "").strip(),
        "operacional",
    )
    return OdooClient(cred, somente_leitura=somente_leitura, timeout=timeout)
