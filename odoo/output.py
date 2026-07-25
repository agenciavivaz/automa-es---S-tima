"""Saída: tabela no terminal, CSV e JSON.

Toda análise carrega um bloco de metadados com período, total considerado,
descartados e equipes — análise sem denominador visível não serve (seção 7.3).
"""

import csv
import json
from dataclasses import dataclass, field

from .paths import caminho_saida


@dataclass
class Resultado:
    """Tabela + denominador. É o que todo comando de análise devolve."""

    titulo: str
    colunas: list
    linhas: list
    meta: dict = field(default_factory=dict)
    notas: list = field(default_factory=list)
    # Corta a exibição no terminal sem mexer no CSV, que sai completo.
    limite_exibicao: int = None

    def como_dict(self):
        return {
            "titulo": self.titulo,
            "meta": self.meta,
            "notas": self.notas,
            "colunas": self.colunas,
            "linhas": [dict(zip(self.colunas, linha)) for linha in self.linhas],
        }


def formatar_valor(valor):
    if valor is None:
        return "—"
    if isinstance(valor, bool):
        return "sim" if valor else "não"
    if isinstance(valor, float):
        return f"{valor:,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")
    if isinstance(valor, (list, tuple)):
        return ", ".join(str(v) for v in valor)
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    return str(valor)


def montar_tabela(colunas, linhas):
    cabecalhos = [str(c) for c in colunas]
    corpo = [[formatar_valor(v) for v in linha] for linha in linhas]
    larguras = [len(c) for c in cabecalhos]
    for linha in corpo:
        for indice, celula in enumerate(linha):
            if indice < len(larguras):
                larguras[indice] = max(larguras[indice], len(celula))

    def formatar_linha(celulas):
        return "  ".join(str(c).ljust(larguras[i]) for i, c in enumerate(celulas))

    saida = [formatar_linha(cabecalhos), "  ".join("-" * l for l in larguras)]
    saida.extend(formatar_linha(linha) for linha in corpo)
    return "\n".join(saida)


def imprimir_resultado(resultado, *, formato="tabela"):
    if formato == "json":
        print(json.dumps(resultado.como_dict(), ensure_ascii=False, indent=2, default=str))
        return

    print(f"\n=== {resultado.titulo} ===")
    if resultado.meta:
        print(bloco_denominador(resultado.meta))
    for nota in resultado.notas:
        print(f"  ! {nota}")
    if resultado.linhas:
        limite = resultado.limite_exibicao
        exibidas = resultado.linhas[:limite] if limite else resultado.linhas
        print()
        print(montar_tabela(resultado.colunas, exibidas))
        if limite and len(resultado.linhas) > limite:
            print(f"\n… {len(resultado.linhas) - limite} linha(s) a mais — "
                  "o CSV sai completo.")
    else:
        print("\n(nenhuma linha)")
    print()


def bloco_denominador(meta):
    linhas = []
    for chave, valor in meta.items():
        rotulo = chave.replace("_", " ")
        linhas.append(f"  {rotulo}: {formatar_valor(valor)}")
    return "\n".join(linhas)


def achatar(valor):
    """Valor do Odoo → célula de CSV."""
    if isinstance(valor, (list, tuple)):
        if len(valor) == 2 and isinstance(valor[0], int) and isinstance(valor[1], str):
            return f"{valor[0]}|{valor[1]}"
        return ", ".join(str(achatar(v)) for v in valor)
    if valor is False or valor is None:
        return ""
    if isinstance(valor, dict):
        return json.dumps(valor, ensure_ascii=False)
    return valor


def salvar_csv(nome, colunas, linhas, *, diretorio=None):
    destino = caminho_saida(nome, "csv", diretorio=diretorio)
    with destino.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow(colunas)
        for linha in linhas:
            escritor.writerow([achatar(v) for v in linha])
    return destino


def salvar_json(nome, dados, *, diretorio=None):
    destino = caminho_saida(nome, "json", diretorio=diretorio)
    destino.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    return destino


def salvar_registros(nome, registros, campos, *, formato="csv", diretorio=None):
    """Exporta registros crus de extração (RF-11)."""
    if formato == "json":
        return salvar_json(nome, registros, diretorio=diretorio)
    linhas = [[registro.get(campo) for campo in campos] for registro in registros]
    return salvar_csv(nome, campos, linhas, diretorio=diretorio)


def salvar_resultado(resultado, nome, *, diretorio=None):
    """CSV da análise com o denominador no topo, como comentário."""
    destino = caminho_saida(nome, "csv", diretorio=diretorio)
    with destino.open("w", newline="", encoding="utf-8-sig") as arquivo:
        escritor = csv.writer(arquivo, delimiter=";")
        escritor.writerow([f"# {resultado.titulo}"])
        for chave, valor in resultado.meta.items():
            escritor.writerow([f"# {chave.replace('_', ' ')}", achatar(valor)])
        for nota in resultado.notas:
            escritor.writerow([f"# nota", nota])
        escritor.writerow([])
        escritor.writerow(resultado.colunas)
        for linha in resultado.linhas:
            escritor.writerow([achatar(v) for v in linha])
    return destino
