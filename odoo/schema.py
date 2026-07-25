"""Introspecção de schema: cache de `fields_get` em disco e validação de campos.

RNF-03 — chamada de rede custa; o resultado do `fields_get` de cada modelo é
cacheado em disco com TTL.
RF-10 — campo pedido que não existe na base vira erro nomeando o campo e
sugerindo os parecidos, nunca uma exceção genérica de HTTP.
"""

import difflib
import json
import logging
import os
import time
from pathlib import Path

from .errors import UnknownFieldError
from .paths import DIRETORIO_DADOS

log = logging.getLogger("odoo.schema")

TTL_PADRAO_SEGUNDOS = 24 * 3600
DIRETORIO_CACHE = DIRETORIO_DADOS / ".schema"

ATRIBUTOS = ["string", "type", "relation", "required", "readonly", "store", "selection"]


class SchemaCache:
    """`fields_get` por modelo, com cache em disco."""

    def __init__(self, client, *, ttl=None, diretorio=None):
        self.client = client
        self.ttl = float(ttl if ttl is not None
                         else os.environ.get("ODOO_SCHEMA_TTL", TTL_PADRAO_SEGUNDOS))
        self.diretorio = Path(diretorio or DIRETORIO_CACHE)
        self._memoria = {}

    def _arquivo(self, model):
        return self.diretorio / f"{model}.json"

    def fields(self, model, *, refresh=False):
        if not refresh and model in self._memoria:
            return self._memoria[model]

        arquivo = self._arquivo(model)
        if not refresh and arquivo.exists():
            idade = time.time() - arquivo.stat().st_mtime
            if idade < self.ttl:
                try:
                    dados = json.loads(arquivo.read_text(encoding="utf-8"))
                    self._memoria[model] = dados
                    return dados
                except (ValueError, OSError):
                    log.debug("Cache de schema inválido para %s, recarregando.", model)

        dados = self.client.fields_get(model, attributes=ATRIBUTOS)
        self._memoria[model] = dados
        try:
            self.diretorio.mkdir(parents=True, exist_ok=True)
            arquivo.write_text(json.dumps(dados, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        except OSError as exc:
            log.debug("Não foi possível gravar cache de schema de %s: %s", model, exc)
        return dados

    def nomes(self, model, *, refresh=False):
        return set(self.fields(model, refresh=refresh))

    def existe(self, model, campo, *, refresh=False):
        return campo.split(".", 1)[0] in self.nomes(model, refresh=refresh)

    def validar(self, model, campos, *, refresh=False):
        """Levanta UnknownFieldError nomeando os campos inexistentes (RF-10)."""
        disponiveis = self.nomes(model, refresh=refresh)
        invalidos = []
        for campo in campos:
            base = campo.split(".", 1)[0]
            if base not in disponiveis and base != "id":
                invalidos.append(campo)
        if invalidos:
            sugestoes = {
                campo: difflib.get_close_matches(campo.split(".", 1)[0],
                                                 sorted(disponiveis), n=3, cutoff=0.6)
                for campo in invalidos
            }
            raise UnknownFieldError(model, invalidos, sugestoes)
        return list(campos)

    def filtrar_existentes(self, model, campos, *, refresh=False):
        """Subconjunto dos campos que existem — para listas padrão otimistas.

        Usado só onde a ausência de um campo é esperada (campo que existe em
        umas bases e não em outras). Campo pedido explicitamente pelo usuário
        passa por `validar`, que falha em vez de descartar em silêncio.
        """
        disponiveis = self.nomes(model, refresh=refresh)
        return [c for c in campos if c.split(".", 1)[0] in disponiveis or c == "id"]

    def tipo(self, model, campo):
        return (self.fields(model).get(campo) or {}).get("type")

    def rotulo(self, model, campo):
        return (self.fields(model).get(campo) or {}).get("string") or campo

    def campos_customizados(self, model):
        return sorted(c for c in self.nomes(model) if c.startswith("x_"))
