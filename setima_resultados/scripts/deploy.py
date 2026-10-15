"""Deploy idempotente dos módulos importados de dashboard (padrão: `vivaz_setima`).

Mesmo mecanismo do Inbound: zip do módulo (XML + assets, sem Python) enviado por
`base.import.module` com "Forçar init". Os registros têm external ID `vivaz_setima.*`,
então rodar de novo ATUALIZA, nunca duplica.

    python setima_resultados/scripts/deploy.py            # plano (dry-run)
    python setima_resultados/scripts/deploy.py --aplicar  # importa
    python setima_resultados/scripts/deploy.py --modulo=abm_setima_dashboard --aplicar

Exige a chave de um administrador em ODOO_API_KEY. Credenciais nunca são impressas.
"""

import base64
import io
import os
import re
import sys
import zipfile

import requests

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, RAIZ)

from urllib.parse import urlparse  # noqa: E402

from odoo.client import OdooClient, OdooCredentials  # noqa: E402

# --modulo=<nome> publica outro módulo importado com o mesmo processo (ex.: abm_setima_dashboard)
MODULO = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--modulo=")), "vivaz_setima")
PASTA = os.path.join(RAIZ, "odoo_modules", MODULO)
MARCAS = {"vivaz_setima": (".o_vst", "vivaz_setima_dashboard"), "abm_setima_dashboard": (".o_vab", "abm_setima_dashboard")}


def base_url():
    u = urlparse(os.environ.get("ODOO_URL", "").strip())
    return f"{u.scheme}://{u.netloc}" if u.netloc else ""


def cliente(somente_leitura=True):
    cred = OdooCredentials(base_url(), os.environ.get("ODOO_DB", "").strip(),
                           os.environ.get("ODOO_API_KEY", "").strip(), "operacional")
    return OdooClient(cred, somente_leitura=somente_leitura, timeout=300)


def zip_modulo():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, arquivos in os.walk(PASTA):
            for a in sorted(arquivos):
                if a.endswith(".pyc") or a == ".DS_Store":
                    continue
                caminho = os.path.join(base, a)
                z.write(caminho, os.path.relpath(caminho, os.path.dirname(PASTA)))
    return buf.getvalue()


def checar_scss():
    """O Odoo compila SCSS com libsass: min()/max()/clamp() quebram o bundle de TODO o backend."""
    txt = "".join(open(os.path.join(b, f), encoding="utf-8").read()
                  for b, _, fs in os.walk(PASTA) for f in fs if f.endswith(".scss"))
    ruins = re.findall(r"(?<![\w-])(min|max|clamp)\(", txt)
    if ruins:
        sys.exit(f"o SCSS usa {sorted(set(ruins))}() — incompatível com o libsass do Odoo. Deploy cancelado.")


def checar_bundles():
    """Compila CSS e JS do backend no servidor e procura erro de compilação."""
    ok = True
    for ext, marca in zip(("css", "js"), MARCAS[MODULO]):
        r = requests.get(f"{base_url()}/web/assets/debug/web.assets_backend.{ext}", timeout=300)
        erro = "This error occurred while compiling the bundle" in r.text or "Could not get content" in r.text
        tem = marca in r.text
        print(f"{ext.upper()} do backend: HTTP {r.status_code} · erro: {'SIM' if erro else 'não'} · módulo presente: {'sim' if tem else 'não'}")
        ok = ok and r.ok and not erro and tem
    return ok


def main():
    aplicar = "--aplicar" in sys.argv
    c = cliente(somente_leitura=not aplicar)
    mod = c.search_read("ir.module.module", [["name", "=", MODULO]], ["state", "installed_version"])
    print(f"Módulo {MODULO}: {mod[0]['state'] + ' ' + str(mod[0]['installed_version']) if mod else 'não instalado'}")
    checar_scss()
    pacote = zip_modulo()
    print(f"Pacote: {len(pacote) / 1024:.1f} KB")
    if not aplicar:
        print("Dry-run: nada enviado. Use --aplicar para importar.")
        return
    wiz = c.create("base.import.module", {"module_file": base64.b64encode(pacote).decode(), "force": True})
    wid = wiz[0] if isinstance(wiz, list) else wiz
    c.call("base.import.module", "import_module", {"ids": [wid]})
    mod = c.search_read("ir.module.module", [["name", "=", MODULO]], ["state", "installed_version"])
    imd = c.search_read("ir.model.data", [["module", "=", MODULO]], ["model", "name", "res_id"])
    print(f"Depois: {mod[0]['state'] if mod else '?'} · {len(imd)} registros: {sorted(r['name'] for r in imd)}")
    if not checar_bundles() or not mod or mod[0]["state"] != "installed":
        sys.exit(1)


if __name__ == "__main__":
    main()
