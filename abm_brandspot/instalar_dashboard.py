"""
Importa (ou atualiza) o módulo odoo_modules/abm_brandspot_dashboard no Odoo.

Mesmo processo dos dashboards da Sétima: zip do módulo (XML + assets, sem Python)
enviado por `base.import.module` com "Forçar init"; depois confere se o CSS e o JS
do backend ainda compilam no servidor (um erro de bundle derruba o backend inteiro).
Exige que o menu abm_brandspot.menu_pipeline exista (python -m abm_brandspot.estrutura).

Uso (na raiz do repositório):
    python -m abm_brandspot.instalar_dashboard            # só monta o pacote
    python -m abm_brandspot.instalar_dashboard --aplicar  # importa
"""

import argparse
import base64
import io
import re
import sys
import zipfile
from pathlib import Path

import requests

from ._odoo import Odoo

MODULO = "abm_brandspot_dashboard"
PASTA = Path(__file__).resolve().parent.parent / "odoo_modules" / MODULO


def zip_modulo():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for caminho in sorted(PASTA.rglob("*")):
            if caminho.is_file() and caminho.suffix != ".pyc":
                z.write(caminho, caminho.relative_to(PASTA.parent))
    return buf.getvalue()


def checar_scss():
    """O Odoo compila SCSS com libsass: min()/max()/clamp() quebram o bundle de todo o backend."""
    txt = "".join(p.read_text(encoding="utf-8") for p in PASTA.rglob("*.scss"))
    ruins = re.findall(r"(?<![\w-])(min|max|clamp)\(", txt)
    if ruins:
        sys.exit(f"o SCSS usa {sorted(set(ruins))}() — incompatível com o libsass do Odoo.")


def checar_bundles(url):
    ok = True
    for ext in ("css", "js"):
        r = requests.get(f"{url}/web/assets/debug/web.assets_backend.{ext}", timeout=300)
        erro = "This error occurred while compiling the bundle" in r.text or "Could not get content" in r.text
        marca = "o_vab" if ext == "css" else MODULO
        print(f"{ext.upper()} do backend: HTTP {r.status_code} · erro: {'SIM' if erro else 'não'} · "
              f"módulo presente: {'sim' if marca in r.text else 'não'}")
        ok = ok and r.ok and not erro and marca in r.text
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    odoo = Odoo()
    checar_scss()
    pacote = zip_modulo()
    print(f"Pacote {MODULO}: {len(pacote) / 1024:.1f} KB")
    if not args.aplicar:
        print("Simulação: nada enviado. Use --aplicar para importar.")
        return
    wid = odoo.call("base.import.module", "create",
                    vals_list=[{"module_file": base64.b64encode(pacote).decode(), "force": True}])[0]
    odoo.call("base.import.module", "import_module", ids=[wid])
    mod = odoo.call("ir.module.module", "search_read", domain=[["name", "=", MODULO]],
                    fields=["state", "latest_version"])
    print(f"Módulo: {mod[0]['state']} {mod[0]['latest_version']}" if mod else "Módulo não encontrado")
    if not checar_bundles(odoo.url) or not mod or mod[0]["state"] != "installed":
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
