"""Backup completo da v1 do Dashboard Inbound (módulo importado `inbound_setima`).

Exporta, somente leitura, todos os registros com external ID do módulo
(menus, actions, views, campos x_, ir.asset, anexos com o código JS/XML/SCSS
realmente publicado) para inbound_v2/backup/AAAAMMDD/.

    python inbound_v2/scripts/backup_v1.py
"""

import base64
import json
import os
from datetime import date

from conexao import cliente

MODULO = "inbound_setima"
PASTA = os.path.join(os.path.dirname(__file__), "..", "backup", date.today().strftime("%Y%m%d"))

CAMPOS = {
    "ir.ui.menu": ["name", "parent_id", "action", "sequence", "group_ids", "active"],
    "ir.actions.client": ["name", "tag", "params", "context", "target", "res_model"],
    "ir.actions.act_window": ["name", "res_model", "view_mode", "domain", "context", "search_view_id", "view_id"],
    "ir.actions.act_window.view": ["sequence", "view_mode", "view_id", "act_window_id"],
    "ir.ui.view": ["name", "model", "type", "inherit_id", "mode", "priority", "arch_db", "active"],
    "ir.model.fields": ["name", "model", "field_description", "ttype", "store", "copied", "tracking", "state"],
    "ir.asset": ["name", "bundle", "directive", "path", "target", "active", "sequence"],
    "ir.attachment": ["name", "url", "mimetype", "file_size", "checksum", "write_date"],
}


def main():
    c = cliente()
    os.makedirs(os.path.join(PASTA, "static"), exist_ok=True)
    imd = c.search_read("ir.model.data", [["module", "=", MODULO]],
                        ["module", "name", "model", "res_id"], order="model,name")
    saida = {"modulo": MODULO, "gerado_em": date.today().isoformat(), "registros": []}
    mod = c.search_read("ir.module.module", [["name", "=", MODULO]],
                        ["name", "installed_version", "imported", "state", "dependencies_id", "write_date"])
    saida["modulo_info"] = mod
    for r in imd:
        campos = CAMPOS.get(r["model"])
        dados = c.read(r["model"], [r["res_id"]], campos) if campos else []
        saida["registros"].append({"xml_id": f"{r['module']}.{r['name']}", "model": r["model"],
                                   "id": r["res_id"], "dados": dados[0] if dados else None})
        if r["model"] == "ir.attachment":
            bruto = c.read("ir.attachment", [r["res_id"]], ["name", "datas"])[0]
            with open(os.path.join(PASTA, "static", bruto["name"]), "wb") as fh:
                fh.write(base64.b64decode(bruto["datas"] or ""))
        if r["model"] == "ir.ui.view" and dados:
            with open(os.path.join(PASTA, f"view_{r['name']}.xml"), "w", encoding="utf-8") as fh:
                fh.write(dados[0]["arch_db"] or "")
    with open(os.path.join(PASTA, "registros_v1.json"), "w", encoding="utf-8") as fh:
        json.dump(saida, fh, ensure_ascii=False, indent=2, default=str)
    print(f"{len(imd)} registros exportados para {os.path.normpath(PASTA)}")


if __name__ == "__main__":
    main()
