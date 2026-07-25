"""Critérios de aceite verificáveis por leitura do código.

RNF-01 (chave nunca no repositório), RNF-02 (Fase 1 não escreve),
RNF-07 / aceite 17 (chave admin só dentro de odoo/config/).
"""

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
PACOTE = RAIZ / "odoo"
ARQUIVOS = sorted(PACOTE.rglob("*.py"))


def fonte(arquivo):
    return arquivo.read_text(encoding="utf-8")


def test_chave_admin_so_e_lida_dentro_de_odoo_config():
    fora = [
        arquivo.relative_to(RAIZ)
        for arquivo in ARQUIVOS
        if "ODOO_ADMIN_API_KEY" in fonte(arquivo)
        and arquivo.parent.name != "config"
    ]
    assert fora == [], f"chave de configuração citada fora de odoo/config/: {fora}"


def test_apenas_um_arquivo_le_a_variavel_admin():
    leitores = [
        arquivo.name for arquivo in ARQUIVOS if "ODOO_ADMIN_API_KEY" in fonte(arquivo)
    ]
    assert leitores == ["credentials.py"]


def test_config_nunca_cai_de_volta_na_chave_operacional():
    texto = fonte(PACOTE / "config" / "credentials.py")
    assert "ODOO_API_KEY" not in texto.replace("ODOO_ADMIN_API_KEY", "")


def test_credenciais_vem_so_do_ambiente():
    """Nenhuma chave literal e nenhum argumento de CLI recebendo chave (RF-02)."""
    suspeitos = []
    padrao = re.compile(r"(api[_-]?key|token|senha|password)\s*=\s*[\"'][^\"'{}$]{12,}[\"']",
                        re.IGNORECASE)
    for arquivo in ARQUIVOS:
        for numero, linha in enumerate(fonte(arquivo).splitlines(), 1):
            if padrao.search(linha) and "os.environ" not in linha and "env.get" not in linha:
                suspeitos.append(f"{arquivo.relative_to(RAIZ)}:{numero}")
    assert suspeitos == [], f"possível credencial literal: {suspeitos}"


def test_cli_nao_aceita_chave_por_argumento():
    texto = fonte(PACOTE / "cli.py")
    assert "--api-key" not in texto
    assert "--chave" not in texto


def test_headers_nunca_sao_logados():
    texto = fonte(PACOTE / "client.py")
    for linha in texto.splitlines():
        if "log." in linha:
            assert "header" not in linha.lower()
            assert "Authorization" not in linha


def test_comandos_de_leitura_abrem_cliente_somente_leitura():
    """Aceite 7: nenhum comando da Fase 1 executa write/create/unlink."""
    texto = fonte(PACOTE / "cli.py")
    for comando in ("def cmd_schema", "def cmd_extrair", "def cmd_analisar"):
        corpo = texto.split(comando, 1)[1].split("\ndef ", 1)[0]
        assert "contexto_leitura(args)" in corpo, f"{comando} não abre cliente de leitura"
        assert "somente_leitura=False" not in corpo


def test_modulos_de_leitura_nao_chamam_escrita():
    for nome in ("extract.py", "analyze.py", "schema.py"):
        texto = fonte(PACOTE / nome)
        for proibido in (".write(", ".create(", ".unlink("):
            assert proibido not in texto, f"{nome} chama {proibido}"


def test_nenhum_unlink_em_todo_o_pacote():
    for arquivo in ARQUIVOS:
        texto = fonte(arquivo)
        assert "def unlink" not in texto
        assert ".unlink(" not in texto


def test_nao_ha_fallback_para_xmlrpc_na_camada_nova():
    for arquivo in ARQUIVOS:
        texto = fonte(arquivo)
        assert "xmlrpc" not in texto.lower()
        assert "/jsonrpc" not in texto


def test_gitignore_cobre_env_e_saidas():
    texto = (RAIZ / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in texto
    assert "data/odoo" in texto or "data/" in texto


def test_env_de_exemplo_nao_tem_chave_real():
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    for linha in texto.splitlines():
        if "API_KEY" in linha and "=" in linha:
            valor = linha.split("=", 1)[1].strip()
            assert valor == "" or valor.startswith(("sua_", "seu_", "cole_", "<")), (
                f"valor suspeito em .env.example: {linha}"
            )
