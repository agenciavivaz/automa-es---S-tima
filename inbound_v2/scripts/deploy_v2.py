"""Deploy idempotente do Dashboard Inbound v2 (módulo importado `vivaz_inbound`).

Mesmo mecanismo da v1: zip do módulo de dados (XML + assets, sem Python) enviado por
`base.import.module` com "Forçar init". Todo artefato ganha external ID `vivaz_inbound.*`
(ir.model.data), então rodar de novo ATUALIZA os mesmos registros, nunca duplica.
Dados com noupdate (apelidos, ajuste) não são sobrescritos.

    python inbound_v2/scripts/deploy_v2.py            # mostra o plano (dry-run)
    python inbound_v2/scripts/deploy_v2.py --aplicar  # importa

Depois de importar, confere: módulo instalado, contagem de registros por modelo, nenhum
registro duplicado e a v1 (`inbound_setima`) sem nenhuma alteração (write_date).
Exige a chave de um administrador (ODOO_API_KEY). Credenciais nunca são impressas.
"""

import base64
import io
import os
import re
import sys
import zipfile
from collections import Counter

import requests

from conexao import base_url, cliente

MODULO = "vivaz_inbound"
RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PASTA = os.path.join(RAIZ, "odoo_modules", MODULO)


def zip_modulo():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _, arquivos in os.walk(PASTA):
            for a in sorted(arquivos):
                if a.endswith((".pyc",)) or a == ".DS_Store":
                    continue
                caminho = os.path.join(base, a)
                z.write(caminho, os.path.relpath(caminho, os.path.dirname(PASTA)))
    return buf.getvalue()


def checar_scss():
    """O Odoo compila SCSS com libsass: min()/max()/clamp() do CSS quebram o bundle de TODO o backend."""
    txt = open(os.path.join(PASTA, "static", "src", "dashboard.scss"), encoding="utf-8").read()
    ruins = re.findall(r"(?<![\w-])(min|max|clamp)\(", txt)
    if ruins:
        sys.exit(f"dashboard.scss usa {sorted(set(ruins))}() — incompatível com o libsass do Odoo. Deploy cancelado.")


def checar_bundle_css():
    """Compila o CSS do backend no servidor (rota pública de assets, modo debug) e procura erro."""
    r = requests.get(f"{base_url()}/web/assets/debug/web.assets_backend.css", timeout=300)
    erro = "This error occurred while compiling the bundle" in r.text
    tem_v2 = ".o_vin" in r.text
    print(f"CSS do backend: HTTP {r.status_code} · erro de compilação: {'SIM' if erro else 'não'} · estilos v2: {'sim' if tem_v2 else 'não'}")
    return not erro and tem_v2


def estado(c):
    imd = c.search_read("ir.model.data", [["module", "=", MODULO]], ["model", "name", "res_id"])
    mod = c.search_read("ir.module.module", [["name", "=", MODULO]], ["state", "installed_version"])
    return imd, (mod[0] if mod else None)


def assinatura_v1(c):
    """write_date de cada registro da v1 — tem que ficar idêntico depois do deploy."""
    imd = c.search_read("ir.model.data", [["module", "=", "inbound_setima"]], ["model", "res_id", "name"])
    sig = {}
    for r in imd:
        dados = c.read(r["model"], [r["res_id"]], ["write_date"])
        sig[f"{r['model']}:{r['name']}"] = dados[0]["write_date"] if dados else None
    return sig


def main():
    aplicar = "--aplicar" in sys.argv
    c = cliente(somente_leitura=not aplicar, timeout=300)
    imd, mod = estado(c)
    print(f"Módulo {MODULO}: {mod['state'] + ' ' + mod['installed_version'] if mod else 'não instalado'}"
          f" · {len(imd)} registros com external ID")
    checar_scss()
    pacote = zip_modulo()
    print(f"Pacote: {len(pacote) / 1024:.1f} KB")
    if not aplicar:
        print("Dry-run: nada enviado. Use --aplicar para importar.")
        return
    antes_v1 = assinatura_v1(c)
    wiz = c.create("base.import.module", {"module_file": base64.b64encode(pacote).decode(), "force": True})
    wid = wiz[0] if isinstance(wiz, list) else wiz
    c.call("base.import.module", "import_module", {"ids": [wid]})
    msg = c.read("base.import.module", [wid], ["import_message", "state"])
    print("Importação:", (msg[0].get("import_message") or msg[0].get("state") or "").strip()[:300] if msg else "ok")

    imd, mod = estado(c)
    print(f"Depois: {mod['state']} {mod['installed_version']} · {len(imd)} registros com external ID")
    for model, n in sorted(Counter(r["model"] for r in imd).items()):
        print(f"  {model}: {n}")
    dup = [k for k, n in Counter((r["model"], r["name"]) for r in imd).items() if n > 1]
    modelos = c.search_read("ir.model", [["model", "like", "x_vivaz_inb_"]], ["model"])
    print(f"Modelos de configuração: {sorted(m['model'] for m in modelos)}")
    for m in modelos:
        print(f"  {m['model']}: {c.search_count(m['model'], [], context={'active_test': False})} registros")
    depois_v1 = assinatura_v1(c)
    # F5 (aprovada em 15/10/2026): o menu "Dashboard" da v1 é arquivado de propósito pelo módulo v2.
    esperado = {"ir.ui.menu:menu_dashboard"}
    alterados = [k for k in antes_v1 if antes_v1[k] != depois_v1.get(k) and k not in esperado]
    print("Duplicados:", dup or "nenhum")
    print("v1 (inbound_setima) alterada:", alterados or "não")
    css_ok = checar_bundle_css()
    if dup or alterados or not css_ok or not mod or mod["state"] != "installed":
        sys.exit(1)


if __name__ == "__main__":
    main()
