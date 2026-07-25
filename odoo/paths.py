"""Caminhos de saída. Tudo cai em ./data/odoo/, que é gitignored."""

import os
import re
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DIRETORIO_DADOS = Path(os.environ.get("ODOO_DATA_DIR", RAIZ / "data" / "odoo"))
ARQUIVO_AUDITORIA = DIRETORIO_DADOS / "audit.jsonl"


def garantir_diretorio(caminho=None):
    destino = Path(caminho or DIRETORIO_DADOS)
    destino.mkdir(parents=True, exist_ok=True)
    return destino


def carimbo():
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def caminho_saida(nome, extensao, *, diretorio=None):
    """./data/odoo/<nome>_<timestamp>.<ext> (RF-11)."""
    seguro = re.sub(r"[^A-Za-z0-9_.-]+", "_", nome).strip("_") or "saida"
    destino = garantir_diretorio(diretorio)
    return destino / f"{seguro}_{carimbo()}.{extensao.lstrip('.')}"
