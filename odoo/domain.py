"""Manipulação de domains Odoo em notação polonesa.

Combinar domains por concatenação ingênua (`[leaf] + domain`) produz domain
malformado quando o domain original tem mais de uma folha ou usa operadores.
Reimplementamos aqui a normalização do Odoo para que a injeção automática do
filtro de equipe (RE-02) seja sempre correta e testável.
"""

from .errors import OdooError

AND = "&"
OR = "|"
NOT = "!"
ARIDADE = {NOT: 1, AND: 2, OR: 2}

FOLHA_VERDADEIRA = (1, "=", 1)
FOLHA_FALSA = (0, "=", 1)


def eh_folha(token):
    return (
        isinstance(token, (list, tuple))
        and len(token) == 3
        and isinstance(token[1], str)
    )


def normalizar(domain):
    """Devolve o domain em forma normalizada (operadores explícitos).

    Aceita a notação com AND implícito usada no dia a dia
    (`[("a","=",1), ("b","=",2)]`) e devolve `["&", ("a","=",1), ("b","=",2)]`.
    """
    if domain is None:
        return [FOLHA_VERDADEIRA]
    if not isinstance(domain, (list, tuple)):
        raise OdooError(f"Domain precisa ser lista, recebido {type(domain).__name__}")
    if len(domain) == 0:
        return [FOLHA_VERDADEIRA]

    resultado = []
    esperados = 1
    for token in domain:
        if esperados == 0:
            # AND implícito entre expressões consecutivas.
            resultado.insert(0, AND)
            esperados = 1
        if eh_folha(token):
            esperados -= 1
            resultado.append(tuple(token))
        elif token in ARIDADE:
            esperados += ARIDADE[token] - 1
            resultado.append(token)
        else:
            raise OdooError(f"Token inválido em domain: {token!r}")
    if esperados:
        raise OdooError(f"Domain incompleto: faltam {esperados} expressão(ões) em {domain!r}")
    return resultado


def combinar_e(*domains):
    """AND lógico entre domains, cada um normalizado antes."""
    partes = []
    for domain in domains:
        if domain is None:
            continue
        normalizado = normalizar(domain)
        if normalizado == [FOLHA_VERDADEIRA]:
            continue
        partes.append(normalizado)
    if not partes:
        return [FOLHA_VERDADEIRA]
    resultado = [AND] * (len(partes) - 1)
    for parte in partes:
        resultado.extend(parte)
    return resultado


def campos_referenciados(domain):
    """Nomes de campo citados no domain (usado para validar contra fields_get)."""
    nomes = set()
    for token in normalizar(domain):
        if eh_folha(token) and isinstance(token[0], str):
            # 'partner_id.country_id' → valida só a primeira parte.
            nomes.add(token[0].split(".", 1)[0])
    return nomes


def domain_vazio(domain):
    """True quando o domain não restringe nada — proibido em escrita (RF-20)."""
    return normalizar(domain) == [FOLHA_VERDADEIRA]


def descrever(domain):
    """Representação curta e legível para log e dry-run."""
    return repr([list(t) if isinstance(t, tuple) else t for t in normalizar(domain)])
