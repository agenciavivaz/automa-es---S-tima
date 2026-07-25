"""Auxiliares de leitura dos valores que o Odoo devolve."""

from datetime import datetime, timedelta

FORMATO_DATA = "%Y-%m-%d"
FORMATO_DATAHORA = "%Y-%m-%d %H:%M:%S"


def id_m2o(valor):
    """`[12, "Nome"]` → 12; `False`/None → None."""
    if isinstance(valor, (list, tuple)) and valor:
        return valor[0]
    if isinstance(valor, bool):
        return None
    if isinstance(valor, int):
        return valor
    return None


def nome_m2o(valor, padrao=None):
    """`[12, "Nome"]` → "Nome"; `False`/None → `padrao`."""
    if isinstance(valor, (list, tuple)) and len(valor) > 1:
        return valor[1]
    return padrao


def rotulo_m2o(valor, vazio="(sem valor)"):
    return nome_m2o(valor) or vazio


def para_datahora(valor):
    """Converte string do Odoo em datetime; devolve None quando ausente/ inválida."""
    if not valor or valor is True:
        return None
    if isinstance(valor, datetime):
        return valor
    texto = str(valor).strip()
    for formato in (FORMATO_DATAHORA, FORMATO_DATA, "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(texto[:len(formato) + 2].strip(), formato)
        except ValueError:
            continue
    return None


def dias_entre(inicio, fim):
    inicio = para_datahora(inicio)
    fim = para_datahora(fim)
    if not inicio or not fim:
        return None
    return (fim - inicio).total_seconds() / 86400.0


def limite_datahora(dias_atras, referencia=None):
    base = referencia or datetime.now()
    return (base - timedelta(days=dias_atras)).strftime(FORMATO_DATAHORA)


def normalizar_periodo(desde=None, ate=None):
    """`--desde 2026-01-01` → `2026-01-01 00:00:00`; `--ate` vira fim do dia."""
    inicio = None
    fim = None
    if desde:
        texto = str(desde).strip()
        inicio = texto if len(texto) > 10 else f"{texto} 00:00:00"
    if ate:
        texto = str(ate).strip()
        fim = texto if len(texto) > 10 else f"{texto} 23:59:59"
    return inicio, fim


def mediana(valores):
    dados = sorted(v for v in valores if v is not None)
    if not dados:
        return None
    meio = len(dados) // 2
    if len(dados) % 2:
        return dados[meio]
    return (dados[meio - 1] + dados[meio]) / 2


def media(valores):
    dados = [v for v in valores if v is not None]
    if not dados:
        return None
    return sum(dados) / len(dados)


def percentual(parte, total):
    if not total:
        return None
    return 100.0 * parte / total


def mes_de(valor):
    dt = para_datahora(valor)
    return dt.strftime("%Y-%m") if dt else "(sem data)"
