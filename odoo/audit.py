"""Trilha de auditoria de escrita (RF-19 / RF-31).

Uma linha JSON por operação aplicada em ./data/odoo/audit.jsonl:
timestamp, perfil de chave, modelo, método, IDs afetados, payload e resultado.
Dry-run não grava — só o que foi efetivamente aplicado entra aqui.
"""

import json
import os
from datetime import datetime

from .paths import ARQUIVO_AUDITORIA, garantir_diretorio

CHAVES_SENSIVEIS = ("api_key", "apikey", "password", "senha", "token", "secret", "authorization")


def _limpar(valor):
    """Nunca deixa credencial entrar no arquivo de auditoria (RNF-01)."""
    if isinstance(valor, dict):
        limpo = {}
        for chave, item in valor.items():
            if any(s in str(chave).lower() for s in CHAVES_SENSIVEIS):
                limpo[chave] = "***"
            else:
                limpo[chave] = _limpar(item)
        return limpo
    if isinstance(valor, (list, tuple)):
        return [_limpar(v) for v in valor]
    return valor


def registrar(*, perfil, model, method, ids, payload, resultado, extra=None,
              arquivo=None):
    destino = arquivo or ARQUIVO_AUDITORIA
    garantir_diretorio(os.path.dirname(destino) or None)
    entrada = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "perfil": perfil,
        "model": model,
        "method": method,
        "ids": list(ids) if ids else [],
        "quantidade": len(ids) if ids else 0,
        "payload": _limpar(payload),
        "resultado": _limpar(resultado),
    }
    if extra:
        entrada.update(_limpar(extra))
    with open(destino, "a", encoding="utf-8") as arquivo_saida:
        arquivo_saida.write(json.dumps(entrada, ensure_ascii=False, default=str) + "\n")
    return entrada


def ler(limite=20, arquivo=None):
    """Últimas entradas da auditoria (para `python -m odoo.cli auditoria`)."""
    destino = arquivo or ARQUIVO_AUDITORIA
    if not os.path.exists(destino):
        return []
    with open(destino, encoding="utf-8") as arquivo_entrada:
        linhas = [linha.strip() for linha in arquivo_entrada if linha.strip()]
    entradas = []
    for linha in linhas[-limite:]:
        try:
            entradas.append(json.loads(linha))
        except ValueError:
            continue
    return entradas
