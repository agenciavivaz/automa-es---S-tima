#!/usr/bin/env python3
"""
Importa (ou reimporta) o módulo de dados abm_setima_ui no Odoo Online.

É um módulo sem Python: só um SCSS que estiliza as telas do ABM Setima
(classe o_abm_setima). O Odoo Online aceita esse tipo de módulo pelo
base_import_module. Para desfazer: Apps → "ABM Sétima – visual" → Desinstalar.

Antes de importar, compile o SCSS localmente com Bootstrap 5.3 (erro de SCSS
quebra o bundle de estilos do Odoo inteiro).

Alternativa manual: Apps → Importar módulo → enviar abm_setima_ui.zip.

Dry-run por padrão (só gera o .zip); APLICAR=true importa.
"""

import base64
import io
import os
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from criar_visoes_abm_setima import APLICAR, odoo  # noqa: E402

PASTA = os.path.join(os.path.dirname(__file__), "modulo")
MODULO = "abm_setima_ui"
ZIP = os.path.join(PASTA, f"{MODULO}.zip")


def empacotar() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for raiz, _, arquivos in os.walk(os.path.join(PASTA, MODULO)):
            for nome in arquivos:
                caminho = os.path.join(raiz, nome)
                z.write(caminho, os.path.relpath(caminho, PASTA))
    return buf.getvalue()


def main():
    dados = empacotar()
    with open(ZIP, "wb") as f:
        f.write(dados)
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        print("Pacote:", ZIP, z.namelist())
    if not APLICAR:
        print("DRY-RUN: nada foi importado. Rode com APLICAR=true ou importe o .zip pela tela.")
        return
    wiz = odoo("base.import.module", "create", vals_list=[{
        "module_file": base64.b64encode(dados).decode(), "force": True}])[0]
    r = odoo("base.import.module", "import_module", ids=[wiz])
    msg = odoo("base.import.module", "read", ids=[wiz], fields=["import_message"])[0]["import_message"]
    print("Resultado:", msg or r)
    print(odoo("ir.module.module", "search_read", domain=[["name", "=", MODULO]], fields=["name", "state"]))
    print(odoo("ir.asset", "search_read", domain=[["path", "like", MODULO]], fields=["bundle", "path", "active"]))


if __name__ == "__main__":
    main()
