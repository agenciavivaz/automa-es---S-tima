"""Chamadas ao endpoint JSON-2 do Odoo (mesmo padrão de criar_contas_abm.py)."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()


class Odoo:
    def __init__(self):
        # ODOO_URL pode vir com "/odoo" no fim (URL do navegador): o JSON-2 fica na raiz.
        self.url = re.sub(r"/odoo$", "", os.environ["ODOO_URL"].strip().rstrip("/"))
        self.headers = {"Authorization": "Bearer " + os.environ["ODOO_API_KEY"],
                        "X-Odoo-Database": os.environ["ODOO_DB"]}

    def call(self, model, method, **params):
        r = requests.post(f"{self.url}/json/2/{model}/{method}", headers=self.headers,
                          json=params, timeout=120)
        if r.status_code != 200:
            raise RuntimeError(f"{model}.{method}: HTTP {r.status_code} {r.text[:500]}")
        return r.json()
