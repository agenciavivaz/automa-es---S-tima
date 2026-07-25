"""Entrypoint da camada Odoo.

    python -m odoo.cli test-connection
    python -m odoo.cli schema fields crm.lead
    python -m odoo.cli extrair crm.lead --desde 2026-01-01
    python -m odoo.cli analisar funil --desde 2026-01-01
    python -m odoo.cli editar crm.lead --ids 1,2 --vals '{"user_id": 7}' --apply
    python -m odoo.cli auditoria

Os comandos de leitura (schema, extrair, analisar) abrem o cliente como
somente leitura: uma tentativa de write/create ali é bloqueada no cliente,
antes de virar requisição (RNF-02).
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from . import audit
from .analyze import Analisador
from .client import cliente_operacional
from .errors import OdooError
from .extract import Extrator
from .models import (
    ALLOWED_TEAM_IDS,
    CAMPO_DATA_PADRAO,
    CRM_TEAM,
    DIAS_PARADO_PADRAO,
    LIMITE_CONFIRMACAO,
    MODELOS_EDITAVEIS,
    MODELOS_EXTRAIVEIS,
)
from .output import (
    Resultado,
    achatar,
    imprimir_resultado,
    salvar_registros,
    salvar_resultado,
)
from .schema import SchemaCache
from .write import Editor

log = logging.getLogger("odoo.cli")


# ---------------------------------------------------------------------------
# Auxiliares de argumento
# ---------------------------------------------------------------------------

def json_ou_arquivo(texto, rotulo):
    """Aceita JSON inline ou @caminho/arquivo.json."""
    if not texto:
        return None
    bruto = texto.strip()
    if bruto.startswith("@"):
        caminho = Path(bruto[1:]).expanduser()
        if not caminho.exists():
            raise OdooError(f"Arquivo de {rotulo} não encontrado: {caminho}")
        bruto = caminho.read_text(encoding="utf-8")
    try:
        return json.loads(bruto)
    except ValueError as exc:
        raise OdooError(f"{rotulo} não é JSON válido: {exc}") from exc


def parse_domain(texto):
    if not texto:
        return None
    dados = json_ou_arquivo(texto, "domain")
    if not isinstance(dados, list):
        raise OdooError('Domain precisa ser uma lista JSON. Ex.: \'[["stage_id","=",5]]\'')
    return [tuple(t) if isinstance(t, list) else t for t in dados]


def parse_ids(texto):
    if not texto:
        return None
    try:
        return [int(parte) for parte in str(texto).replace(";", ",").split(",") if parte.strip()]
    except ValueError as exc:
        raise OdooError(f"Lista de IDs inválida: {texto!r} ({exc})") from exc


def parse_lista(texto):
    if not texto:
        return None
    return [parte.strip() for parte in str(texto).split(",") if parte.strip()]


def contexto_leitura(args, *, somente_leitura=True):
    """Cliente + cache de schema, prontos para uso."""
    cliente = cliente_operacional(somente_leitura=somente_leitura)
    return cliente, SchemaCache(cliente)


def emitir(resultados, args, nome_base):
    """Imprime e salva CSV de cada resultado (RF-11 / seção 7.3)."""
    if args.formato == "json":
        payload = [r.como_dict() for r in resultados]
        print(json.dumps(payload if len(payload) > 1 else payload[0],
                         ensure_ascii=False, indent=2, default=str))
    else:
        for resultado in resultados:
            imprimir_resultado(resultado, formato="tabela")

    if not args.sem_csv:
        for indice, resultado in enumerate(resultados):
            sufixo = "" if indice == 0 else f"_{indice + 1}"
            destino = salvar_resultado(resultado, f"{nome_base}{sufixo}")
            if args.formato != "json":
                print(f"CSV: {destino}")


# ---------------------------------------------------------------------------
# Comandos
# ---------------------------------------------------------------------------

def cmd_test_connection(args):
    """RF-06 — valida as duas chaves e mostra identidade e equipes."""
    print("=== Teste de conexão JSON-2 ===")
    cliente, schema = contexto_leitura(args)
    print(f"URL: {cliente.credentials.url}")
    print(f"Banco: {cliente.credentials.db}")
    print(f"Timeout: {cliente.timeout:.0f}s | tentativas: {cliente.max_tentativas}")

    falhas = []

    print("\n[perfil operacional] ODOO_API_KEY")
    try:
        identidade = cliente.whoami()
        prova = cliente.testar_leitura()
        if identidade["usuario"]:
            print(f"  usuário autenticado: {identidade['usuario']} (id {identidade['usuario_id']})")
        else:
            print("  usuário autenticado: não determinado automaticamente"
                  + (f" — {identidade['observacao']}" if identidade["observacao"] else ""))
        for chave in identidade["chaves"][:5]:
            print(f"  chave: {chave['nome']} | escopo: {chave['escopo']} | "
                  f"expira: {chave['expira_em']} | usuário: {chave['usuario']}")
        print(f"  leitura confirmada: {prova['registros_visiveis']} registro(s) "
              f"visíveis em {prova['model']}")
    except OdooError as exc:
        falhas.append(f"perfil operacional: {exc}")
        print(f"  FALHOU: {exc}")

    print(f"\n[equipes do escopo] {list(ALLOWED_TEAM_IDS)}")
    try:
        campos = schema.filtrar_existentes(CRM_TEAM, ["id", "name", "active", "user_id"])
        equipes = cliente.search_read(
            CRM_TEAM, [("id", "in", list(ALLOWED_TEAM_IDS))], campos,
            limit=len(ALLOWED_TEAM_IDS), context={"active_test": False},
        )
        encontradas = {e["id"] for e in equipes}
        for equipe in sorted(equipes, key=lambda e: e["id"]):
            ativa = "" if equipe.get("active", True) else " [ARQUIVADA]"
            print(f"  {equipe['id']}: {equipe.get('name')}{ativa}")
        ausentes = [i for i in ALLOWED_TEAM_IDS if i not in encontradas]
        if ausentes:
            falhas.append(f"equipes não encontradas ou invisíveis para esta chave: {ausentes}")
            print(f"  FALHOU: equipes {ausentes} não encontradas com esta chave. "
                  "Confirme os IDs e as permissões do usuário de serviço.")
    except OdooError as exc:
        falhas.append(f"equipes: {exc}")
        print(f"  FALHOU: {exc}")

    # Único ponto do CLI que toca o perfil de admin. A variável de ambiente da
    # chave de configuração é nomeada dentro de odoo/config/ e não aqui (RNF-07).
    from .config import VARIAVEL_CHAVE_ADMIN, cliente_admin

    print(f"\n[perfil configuração] {VARIAVEL_CHAVE_ADMIN}")
    try:
        admin = cliente_admin()
        identidade_admin = admin.whoami()
        prova_admin = admin.testar_leitura()
        if identidade_admin["usuario"]:
            print(f"  usuário autenticado: {identidade_admin['usuario']} "
                  f"(id {identidade_admin['usuario_id']})")
        else:
            print("  usuário autenticado: não determinado automaticamente"
                  + (f" — {identidade_admin['observacao']}" if identidade_admin["observacao"] else ""))
        print(f"  leitura confirmada: {prova_admin['registros_visiveis']} registro(s) "
              f"visíveis em {prova_admin['model']}")
    except OdooError as exc:
        print(f"  não disponível: {exc}")
        print("  (as Fases 1 e 2 não precisam desta chave)")

    if falhas:
        print("\nResultado: FALHOU")
        for falha in falhas:
            print(f"  - {falha}")
        return 1
    print("\nResultado: OK")
    return 0


def cmd_schema(args):
    cliente, schema = contexto_leitura(args)
    if args.acao == "fields":
        campos = schema.fields(args.model, refresh=args.refresh)
        alvo = sorted(campos)
        if args.filtro:
            alvo = [c for c in alvo if args.filtro.lower() in c.lower()]
        if args.customizados:
            alvo = [c for c in alvo if c.startswith("x_")]
        linhas = [
            [nome, campos[nome].get("type"), campos[nome].get("string"),
             campos[nome].get("relation") or "", bool(campos[nome].get("required")),
             bool(campos[nome].get("readonly"))]
            for nome in alvo
        ]
        resultado = Resultado(
            f"Campos de {args.model}",
            ["campo", "tipo", "rótulo", "relação", "obrigatório", "somente_leitura"],
            linhas,
            {"modelo": args.model, "campos_listados": len(linhas),
             "campos_no_modelo": len(campos),
             "customizados_x_": len([c for c in campos if c.startswith("x_")])},
            ["Fonte: fields_get da própria base (cache em data/odoo/.schema). "
             "Confirme métodos e assinaturas na página /doc da base."],
        )
        imprimir_resultado(resultado, formato=args.formato)
        return 0

    # acao == "modelos"
    resultado = Resultado(
        "Modelos disponíveis nesta camada",
        ["modelo", "extração", "edição"],
        [[m, "sim", "sim" if m in MODELOS_EDITAVEIS else "não"] for m in MODELOS_EXTRAIVEIS],
        {"equipes_permitidas": list(ALLOWED_TEAM_IDS)},
    )
    imprimir_resultado(resultado, formato=args.formato)
    return 0


def cmd_extrair(args):
    cliente, schema = contexto_leitura(args)
    extrator = Extrator(cliente, schema)
    registros, campos, meta = extrator.extrair(
        args.model,
        campos=parse_lista(args.campos),
        domain=parse_domain(args.domain),
        desde=args.desde,
        ate=args.ate,
        campo_data=args.campo_data,
        limite=args.limite,
    )
    destino = salvar_registros(args.model, registros, campos,
                               formato=args.formato_arquivo)
    meta["arquivo"] = str(destino)

    if args.formato == "json":
        print(json.dumps({"meta": meta, "registros": registros[:args.previa]},
                         ensure_ascii=False, indent=2, default=str))
    else:
        previa = Resultado(
            f"Extração de {args.model}", campos,
            # achatar deixa a prévia igual ao CSV: False vira vazio, m2o vira "id|nome".
            [[achatar(r.get(c)) for c in campos] for r in registros[:args.previa]], meta,
            [f"Mostrando as primeiras {min(args.previa, len(registros))} de "
             f"{len(registros)} linhas. O arquivo tem tudo."],
        )
        imprimir_resultado(previa, formato="tabela")
        print(f"Arquivo: {destino}")
    return 0


def cmd_analisar(args):
    cliente, schema = contexto_leitura(args)
    analisador = Analisador(cliente, schema)
    comum = {
        "desde": args.desde, "ate": args.ate, "campo_data": args.campo_data,
        "tipo": args.tipo, "equipes": parse_ids(args.equipes),
    }
    if args.analise == "funil":
        resultados = analisador.funil(por_equipe=args.por_equipe, **comum)
        nome = "analise_funil"
    elif args.analise == "tempo-estagio":
        resultados = analisador.tempo_em_estagio(**comum)
        nome = "analise_tempo_estagio"
    elif args.analise == "parados":
        resultados = analisador.leads_parados(dias=args.dias, **comum)
        nome = "analise_leads_parados"
    elif args.analise == "origem":
        resultados = analisador.atribuicao_origem(**comum)
        nome = "analise_origem"
    elif args.analise == "ganhos-perdas":
        resultados = analisador.ganhos_perdas(**comum)
        nome = "analise_ganhos_perdas"
    else:  # pragma: no cover - argparse restringe
        raise OdooError(f"Análise desconhecida: {args.analise}")

    emitir(resultados, args, nome)
    return 0


def cmd_editar(args):
    cliente, schema = contexto_leitura(args, somente_leitura=False)
    editor = Editor(cliente, schema, limite_confirmacao=args.limite_confirmacao)
    vals = json_ou_arquivo(args.vals, "vals")
    if not isinstance(vals, dict):
        raise OdooError('--vals precisa ser um objeto JSON. Ex.: \'{"user_id": 7}\'')
    plano = editor.escrever(
        args.model, vals,
        ids=parse_ids(args.ids), domain=parse_domain(args.domain), aplicar=args.apply,
    )
    if args.formato == "json":
        print(json.dumps(plano.como_dict(), ensure_ascii=False, indent=2, default=str))
    else:
        plano.imprimir()
    return 0


def cmd_criar(args):
    cliente, schema = contexto_leitura(args, somente_leitura=False)
    editor = Editor(cliente, schema, limite_confirmacao=args.limite_confirmacao)
    vals = json_ou_arquivo(args.vals, "vals")
    if isinstance(vals, dict):
        vals = [vals]
    if not isinstance(vals, list):
        raise OdooError("--vals precisa ser um objeto ou uma lista de objetos JSON.")
    plano = editor.criar(args.model, vals, aplicar=args.apply)
    if args.formato == "json":
        print(json.dumps(plano.como_dict(), ensure_ascii=False, indent=2, default=str))
    else:
        plano.imprimir()
    return 0


def cmd_auditoria(args):
    entradas = audit.ler(limite=args.limite)
    if args.formato == "json":
        print(json.dumps(entradas, ensure_ascii=False, indent=2, default=str))
        return 0
    resultado = Resultado(
        "Auditoria de escrita",
        ["timestamp", "perfil", "model", "method", "qtd", "ids", "payload"],
        [
            [e.get("timestamp"), e.get("perfil"), e.get("model"), e.get("method"),
             e.get("quantidade"), str(e.get("ids"))[:60],
             json.dumps(e.get("payload"), ensure_ascii=False)[:80]]
            for e in entradas
        ],
        {"arquivo": str(audit.ARQUIVO_AUDITORIA), "entradas_exibidas": len(entradas)},
    )
    imprimir_resultado(resultado, formato="tabela")
    return 0


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def construir_parser():
    parser = argparse.ArgumentParser(
        prog="python -m odoo.cli",
        description="Camada de acesso ao Odoo CRM (JSON-2) — equipes "
                    f"{list(ALLOWED_TEAM_IDS)}.",
    )
    parser.add_argument("--log-level", default=os.environ.get("ODOO_LOG_LEVEL", "INFO"),
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    parser.add_argument("--formato", default="tabela", choices=["tabela", "json"],
                        help="Formato da saída no terminal.")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("test-connection", help="Valida as chaves e as equipes 16/17/21.")

    p_schema = sub.add_parser("schema", help="Introspecção do schema real da base.")
    p_schema.add_argument("acao", choices=["fields", "modelos"])
    p_schema.add_argument("model", nargs="?", default="crm.lead")
    p_schema.add_argument("--filtro", help="Filtra os campos pelo nome.")
    p_schema.add_argument("--customizados", action="store_true",
                          help="Somente campos x_ (customizados da base).")
    p_schema.add_argument("--refresh", action="store_true", help="Ignora o cache em disco.")

    p_extrair = sub.add_parser("extrair", help="Extrai registros para CSV/JSON.")
    p_extrair.add_argument("model", choices=list(MODELOS_EXTRAIVEIS))
    p_extrair.add_argument("--campos", help="Lista separada por vírgula.")
    p_extrair.add_argument("--domain", help='Domain JSON. Ex.: \'[["probability",">",50]]\'')
    p_extrair.add_argument("--desde")
    p_extrair.add_argument("--ate")
    p_extrair.add_argument("--campo-data", default=CAMPO_DATA_PADRAO, dest="campo_data")
    p_extrair.add_argument("--limite", type=int)
    p_extrair.add_argument("--previa", type=int, default=15,
                           help="Linhas mostradas no terminal.")
    p_extrair.add_argument("--formato-arquivo", default="csv", choices=["csv", "json"],
                           dest="formato_arquivo")

    p_analisar = sub.add_parser("analisar", help="Análises de pipeline.")
    p_analisar.add_argument("analise", choices=["funil", "tempo-estagio", "parados",
                                                "origem", "ganhos-perdas"])
    p_analisar.add_argument("--desde")
    p_analisar.add_argument("--ate")
    p_analisar.add_argument("--campo-data", default=CAMPO_DATA_PADRAO, dest="campo_data")
    p_analisar.add_argument("--tipo", default="opportunity",
                            choices=["opportunity", "lead", "todos"])
    p_analisar.add_argument("--equipes", help=f"Subconjunto de {list(ALLOWED_TEAM_IDS)}.")
    p_analisar.add_argument("--por-equipe", action="store_true", dest="por_equipe",
                            help="Segmenta o funil por equipe.")
    p_analisar.add_argument("--dias", type=int, default=DIAS_PARADO_PADRAO,
                            help="Dias sem atividade (análise 'parados').")
    p_analisar.add_argument("--sem-csv", action="store_true", dest="sem_csv")

    p_editar = sub.add_parser("editar", help="Escrita em lote (dry-run por padrão).")
    p_editar.add_argument("model", choices=list(MODELOS_EDITAVEIS))
    p_editar.add_argument("--vals", required=True, help='JSON ou @arquivo.json')
    p_editar.add_argument("--ids", help="IDs separados por vírgula.")
    p_editar.add_argument("--domain", help="Domain JSON (resolvido para IDs antes).")
    p_editar.add_argument("--apply", action="store_true",
                          help="Executa de verdade. Sem isto, é dry-run.")
    p_editar.add_argument("--limite-confirmacao", type=int, default=LIMITE_CONFIRMACAO,
                          dest="limite_confirmacao")

    p_criar = sub.add_parser("criar", help="Criação em lote (dry-run por padrão).")
    p_criar.add_argument("model", choices=list(MODELOS_EDITAVEIS))
    p_criar.add_argument("--vals", required=True, help='JSON (objeto ou lista) ou @arquivo.json')
    p_criar.add_argument("--apply", action="store_true")
    p_criar.add_argument("--limite-confirmacao", type=int, default=LIMITE_CONFIRMACAO,
                         dest="limite_confirmacao")

    p_auditoria = sub.add_parser("auditoria", help="Últimas escritas aplicadas.")
    p_auditoria.add_argument("--limite", type=int, default=20)

    return parser


COMANDOS = {
    "test-connection": cmd_test_connection,
    "schema": cmd_schema,
    "extrair": cmd_extrair,
    "analisar": cmd_analisar,
    "editar": cmd_editar,
    "criar": cmd_criar,
    "auditoria": cmd_auditoria,
}


def main(argv=None):
    load_dotenv()
    parser = construir_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stderr,
    )
    try:
        return COMANDOS[args.comando](args)
    except OdooError as exc:
        # Erro de domínio: mensagem legível, sem stack trace e sem credencial.
        print(f"\nERRO: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        print("\nInterrompido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
