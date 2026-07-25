"""Edição de dados em lote (Fase 2).

Regras que este módulo garante, sem exceção:
- RF-17 dry-run é o padrão: sem `--apply` nada é enviado ao Odoo;
- RF-18 acima de 50 registros exige confirmação interativa mesmo com `--apply`;
- RF-19 toda escrita aplicada vira linha em ./data/odoo/audit.jsonl;
- RF-20 domain de escrita nunca é vazio e é sempre resolvido para IDs antes;
- RF-22/RE-03 os registros alvo são relidos e a operação inteira aborta se
  algum estiver fora das equipes 16/17/21.

Não existe `unlink` aqui: esta ferramenta não apaga registro.
"""

import logging
import sys

from .domain import descrever, domain_vazio
from .errors import ConfirmationRequired, OdooError
from .models import (
    ALLOWED_TEAM_IDS,
    CRM_LEAD,
    LIMITE_CONFIRMACAO,
    MODELOS_EDITAVEIS,
    RES_PARTNER,
    TEAM_FIELD,
)
from .scope import (
    escopar_dominio_lead,
    equipe_permitida,
    verificar_leads_no_escopo,
    verificar_partners_no_escopo,
    verificar_vals_de_equipe,
)
from .utils import rotulo_m2o
from . import audit

log = logging.getLogger("odoo.write")

MAX_LINHAS_PREVIA = 25


class Plano:
    """O que a operação faria. Em dry-run é tudo o que sai."""

    def __init__(self, model, method, ids, payload, previa=None, meta=None):
        self.model = model
        self.method = method
        self.ids = list(ids)
        self.payload = payload
        self.previa = previa or []
        self.meta = meta or {}
        self.aplicado = False
        self.resultado = None

    def como_dict(self):
        return {
            "model": self.model,
            "method": self.method,
            "ids": self.ids,
            "quantidade": len(self.ids),
            "payload": self.payload,
            "meta": self.meta,
            "previa": self.previa,
            "aplicado": self.aplicado,
            "resultado": self.resultado,
        }

    def imprimir(self):
        titulo = "APLICADO" if self.aplicado else "DRY-RUN (nada foi enviado ao Odoo)"
        print(f"\n=== {self.method} em {self.model} — {titulo} ===")
        print(f"  registros afetados: {len(self.ids)}")
        print(f"  payload: {self.payload}")
        for chave, valor in self.meta.items():
            print(f"  {chave.replace('_', ' ')}: {valor}")
        if self.ids:
            print(f"  ids: {self.ids if len(self.ids) <= 50 else str(self.ids[:50]) + ' …'}")
        for linha in self.previa[:MAX_LINHAS_PREVIA]:
            print(f"    - {linha}")
        if len(self.previa) > MAX_LINHAS_PREVIA:
            print(f"    … mais {len(self.previa) - MAX_LINHAS_PREVIA} registro(s)")
        if not self.aplicado:
            print("  → rode de novo com --apply para executar.")
        print()


def confirmador_terminal(mensagem):
    if not sys.stdin.isatty():
        raise ConfirmationRequired(
            f"{mensagem} — sessão não interativa. Reduza o lote (--ids/--domain mais "
            "restrito), ajuste --limite-confirmacao ou rode em um terminal."
        )
    resposta = input(f"{mensagem} Digite 'confirmo' para seguir: ").strip().lower()
    return resposta == "confirmo"


class Editor:
    def __init__(self, client, schema, *, limite_confirmacao=LIMITE_CONFIRMACAO,
                 confirmador=confirmador_terminal):
        if client.somente_leitura:
            raise OdooError("Editor exige um cliente com escrita habilitada.")
        self.client = client
        self.schema = schema
        self.limite_confirmacao = int(limite_confirmacao)
        self.confirmador = confirmador

    # -- validações --------------------------------------------------------

    def _validar_modelo(self, model):
        if model not in MODELOS_EDITAVEIS:
            raise OdooError(
                f"Modelo '{model}' não é editável por esta ferramenta. "
                f"Permitidos: {', '.join(MODELOS_EDITAVEIS)}."
            )

    def _validar_vals(self, model, vals):
        if not isinstance(vals, dict) or not vals:
            raise OdooError("Payload de escrita vazio: informe ao menos um campo.")
        self.schema.validar(model, sorted(vals))
        somente_leitura = [
            campo for campo in vals
            if (self.schema.fields(model).get(campo) or {}).get("readonly")
        ]
        if somente_leitura:
            log.warning("Campos marcados como readonly no schema: %s — o Odoo pode recusar.",
                        ", ".join(somente_leitura))
        if model == CRM_LEAD:
            verificar_vals_de_equipe(vals)

    def resolver_ids(self, model, *, ids=None, domain=None):
        """IDs explícitos ou domain resolvido para IDs — nunca escrita por domain (RF-20)."""
        if ids and domain:
            raise OdooError("Informe --ids OU --domain, não os dois.")
        if ids:
            return [int(i) for i in ids]
        if domain is None:
            raise OdooError("Informe --ids ou --domain para selecionar os registros.")
        if domain_vazio(domain):
            raise OdooError(
                "Domain vazio em operação de escrita é proibido: atingiria a tabela "
                "inteira e o Odoo não tem desfazer (RF-20)."
            )
        self.schema.validar(model, sorted(_campos_do_domain(domain)))
        if model == CRM_LEAD:
            alvo = escopar_dominio_lead(domain)
        else:
            alvo = domain
        encontrados = self.client.search(model, alvo, context={"active_test": False})
        if not encontrados:
            raise OdooError(f"Nenhum registro de {model} casa com {descrever(domain)}.")
        return encontrados

    def _verificar_escopo(self, model, ids):
        if model == CRM_LEAD:
            return verificar_leads_no_escopo(self.client, ids)
        if model == RES_PARTNER:
            return verificar_partners_no_escopo(self.client, ids)
        raise OdooError(f"Sem regra de escopo definida para {model} — escrita bloqueada.")

    def _previa(self, model, ids, vals):
        """Estado atual dos campos que serão alterados: antes → depois."""
        campos = ["id", "name"] + [c for c in vals if c not in ("id", "name")]
        campos = self.schema.filtrar_existentes(model, campos)
        atuais = self.client.read(model, ids[:MAX_LINHAS_PREVIA], campos,
                                  context={"active_test": False})
        linhas = []
        for registro in atuais:
            mudancas = []
            for campo, novo in vals.items():
                atual = registro.get(campo)
                if isinstance(atual, (list, tuple)):
                    atual = rotulo_m2o(atual, str(atual))
                mudancas.append(f"{campo}: {atual!r} → {novo!r}")
            linhas.append(f"#{registro['id']} {registro.get('name')}: " + "; ".join(mudancas))
        return linhas

    # -- operações ---------------------------------------------------------

    def escrever(self, model, vals, *, ids=None, domain=None, aplicar=False):
        self._validar_modelo(model)
        self._validar_vals(model, vals)
        alvos = self.resolver_ids(model, ids=ids, domain=domain)
        escopo = self._verificar_escopo(model, alvos)  # RE-03: aborta tudo se algum estiver fora

        plano = Plano(
            model, "write", alvos, dict(vals),
            previa=self._previa(model, alvos, vals),
            meta={
                "escopo_verificado": f"{len(escopo)} registro(s) dentro das equipes "
                                     f"{list(ALLOWED_TEAM_IDS)}",
                "selecao": descrever(domain) if domain else "ids explícitos",
                "perfil_de_chave": self.client.perfil,
            },
        )
        if not aplicar:
            return plano

        self._confirmar(plano)
        resultado = self.client.write(model, alvos, vals)
        plano.aplicado = True
        plano.resultado = resultado
        audit.registrar(
            perfil=self.client.perfil, model=model, method="write", ids=alvos,
            payload=vals, resultado=resultado,
            extra={"selecao": plano.meta["selecao"]},
        )
        return plano

    def criar(self, model, vals_list, *, aplicar=False):
        self._validar_modelo(model)
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        if not vals_list:
            raise OdooError("Nada para criar: lista de valores vazia.")
        for vals in vals_list:
            self._validar_vals(model, vals)
        if model == CRM_LEAD:
            for indice, vals in enumerate(vals_list):
                if TEAM_FIELD not in vals:
                    raise OdooError(
                        f"Registro {indice + 1}: '{TEAM_FIELD}' é obrigatório na criação de "
                        f"lead — sem equipe o registro nasce fora do escopo (RE-04). "
                        f"Equipes permitidas: {list(ALLOWED_TEAM_IDS)}."
                    )
                if not equipe_permitida(vals[TEAM_FIELD]):
                    raise OdooError(
                        f"Registro {indice + 1}: team_id={vals[TEAM_FIELD]!r} fora de "
                        f"{list(ALLOWED_TEAM_IDS)}."
                    )

        plano = Plano(
            model, "create", [], vals_list,
            previa=[f"novo {model}: {vals}" for vals in vals_list],
            meta={"registros_a_criar": len(vals_list),
                  "perfil_de_chave": self.client.perfil},
        )
        if not aplicar:
            return plano

        self._confirmar(plano, quantidade=len(vals_list))
        resultado = self.client.create(model, vals_list)
        criados = resultado if isinstance(resultado, list) else [resultado]
        plano.aplicado = True
        plano.resultado = criados
        plano.ids = [i for i in criados if isinstance(i, int)]
        audit.registrar(
            perfil=self.client.perfil, model=model, method="create", ids=plano.ids,
            payload=vals_list, resultado=criados,
        )
        return plano

    def _confirmar(self, plano, quantidade=None):
        total = quantidade if quantidade is not None else len(plano.ids)
        if total <= self.limite_confirmacao:
            return
        mensagem = (f"Esta operação afeta {total} registros de {plano.model} "
                    f"(limite de confirmação: {self.limite_confirmacao}).")
        if not self.confirmador(mensagem):
            raise ConfirmationRequired(f"{mensagem} Confirmação negada — nada foi enviado.")


def _campos_do_domain(domain):
    from .domain import campos_referenciados
    return campos_referenciados(domain)
