"""Análises de pipeline (Fase 1, seção 7.3).

Toda análise declara no output: período coberto, total de registros
considerados, quantos foram descartados por dado faltante e quais equipes
entraram. Análise sem denominador visível não serve.

Nenhuma função daqui escreve: o cliente usado pelo CLI nestes comandos é aberto
como somente leitura (RNF-02).
"""

import logging
from collections import defaultdict
from datetime import datetime

from .domain import combinar_e
from .errors import OdooError, OdooRequestError
from .extract import dominio_periodo
from .models import (
    ALLOWED_TEAM_IDS,
    CAMPO_DATA_PADRAO,
    CAMPOS_ANALISE,
    CRM_LEAD,
    CRM_STAGE,
    DIAS_PARADO_PADRAO,
    MAIL_ACTIVITY,
    MAIL_MESSAGE,
    MAIL_TRACKING_VALUE,
)
from .output import Resultado
from .scope import escopar_dominio_lead
from .utils import (
    dias_entre,
    id_m2o,
    limite_datahora,
    media,
    mediana,
    mes_de,
    normalizar_periodo,
    percentual,
    rotulo_m2o,
)

log = logging.getLogger("odoo.analyze")

GANHO = "ganho"
PERDIDO = "perdido"
ARQUIVADO = "arquivado"
ABERTO = "aberto"


class Analisador:
    def __init__(self, client, schema, *, agora=None):
        self.client = client
        self.schema = schema
        self.agora = agora or datetime.now()
        self._estagios = None

    # -- carregamento comum ------------------------------------------------

    def estagios(self):
        if self._estagios is None:
            campos = self.schema.filtrar_existentes(
                CRM_STAGE, ["id", "name", "sequence", "is_won", "team_id", "fold"]
            )
            registros = self.client.search_read_all(CRM_STAGE, [], campos, order="sequence asc")
            self._estagios = {r["id"]: r for r in registros}
        return self._estagios

    def estagios_de_ganho(self):
        return {i for i, e in self.estagios().items() if e.get("is_won")}

    def carregar_leads(self, *, desde=None, ate=None, campo_data=CAMPO_DATA_PADRAO,
                       tipo="opportunity", equipes=None, filtros=None, campos=None):
        """Leads no escopo, com os arquivados incluídos (perdido é arquivado)."""
        campos = self.schema.filtrar_existentes(CRM_LEAD, campos or CAMPOS_ANALISE)
        if desde or ate:
            self.schema.validar(CRM_LEAD, [campo_data])

        extras = list(filtros or [])
        if tipo and tipo != "todos":
            if "type" in self.schema.nomes(CRM_LEAD):
                extras.append(("type", "=", tipo))
        if equipes:
            invalidas = [e for e in equipes if e not in ALLOWED_TEAM_IDS]
            if invalidas:
                raise OdooError(
                    f"Equipe(s) {invalidas} fora do escopo permitido {list(ALLOWED_TEAM_IDS)}."
                )
            extras.append(("team_id", "in", list(equipes)))

        dominio = escopar_dominio_lead(
            combinar_e(extras, dominio_periodo(campo_data, desde, ate))
        )
        leads = self.client.search_read_all(
            CRM_LEAD, dominio, campos, context={"active_test": False}
        )

        # Denominador: quantos registros existem no escopo antes do filtro de tipo.
        total_sem_tipo = self.client.search_count(
            CRM_LEAD,
            escopar_dominio_lead(combinar_e(
                [f for f in extras if f[0] != "type"],
                dominio_periodo(campo_data, desde, ate),
            )),
            context={"active_test": False},
        )

        meta = {
            "periodo": _texto_periodo(campo_data, desde, ate),
            "equipes_consideradas": list(equipes) if equipes else list(ALLOWED_TEAM_IDS),
            "tipo_de_registro": tipo,
            "registros_considerados": len(leads),
            "registros_no_escopo_sem_filtro_de_tipo": total_sem_tipo,
        }
        notas = []
        if not leads and total_sem_tipo:
            notas.append(
                f"Nenhum registro com type='{tipo}', mas há {total_sem_tipo} no escopo. "
                "Rode com --tipo lead ou --tipo todos."
            )
        return leads, meta, notas

    def classificar(self, lead):
        ganhos = self.estagios_de_ganho()
        estagio = id_m2o(lead.get("stage_id"))
        probabilidade = lead.get("probability") or 0
        if estagio in ganhos or probabilidade >= 100:
            return GANHO
        if lead.get("active") is False:
            return PERDIDO if id_m2o(lead.get("lost_reason_id")) else ARQUIVADO
        return ABERTO

    # -- RF-12 funil por estágio ------------------------------------------

    def funil(self, *, desde=None, ate=None, campo_data=CAMPO_DATA_PADRAO,
              tipo="opportunity", equipes=None, por_equipe=False):
        leads, meta, notas = self.carregar_leads(
            desde=desde, ate=ate, campo_data=campo_data, tipo=tipo, equipes=equipes
        )
        estagios = self.estagios()

        grupos = defaultdict(lambda: {"leads": 0, "valor": 0.0, "ganhos": 0})
        sem_estagio = 0
        for lead in leads:
            estagio_id = id_m2o(lead.get("stage_id"))
            if estagio_id is None:
                sem_estagio += 1
                continue
            chave = (id_m2o(lead.get("team_id")) if por_equipe else None, estagio_id)
            grupo = grupos[chave]
            grupo["leads"] += 1
            grupo["valor"] += float(lead.get("expected_revenue") or 0)
            if self.classificar(lead) == GANHO:
                grupo["ganhos"] += 1

        def sequencia(chave):
            estagio = estagios.get(chave[1], {})
            return (chave[0] or 0, estagio.get("sequence") or 0, chave[1])

        colunas = (["equipe"] if por_equipe else []) + [
            "seq", "estagio", "leads", "valor_total", "valor_medio",
            "conversao_do_anterior_%", "ganhos",
        ]
        linhas = []
        anterior_por_equipe = {}
        for chave in sorted(grupos, key=sequencia):
            equipe_id, estagio_id = chave
            estagio = estagios.get(estagio_id, {})
            grupo = grupos[chave]
            anterior = anterior_por_equipe.get(equipe_id)
            conversao = percentual(grupo["leads"], anterior) if anterior else None
            linha = []
            if por_equipe:
                linha.append(_nome_equipe(leads, equipe_id))
            linha += [
                estagio.get("sequence"),
                estagio.get("name") or f"estágio {estagio_id}",
                grupo["leads"],
                round(grupo["valor"], 2),
                round(grupo["valor"] / grupo["leads"], 2) if grupo["leads"] else 0.0,
                round(conversao, 1) if conversao is not None else None,
                grupo["ganhos"],
            ]
            linhas.append(linha)
            anterior_por_equipe[equipe_id] = grupo["leads"]

        meta["descartados_sem_estagio"] = sem_estagio
        meta["estagios_com_registro"] = len(grupos)
        notas.append(
            "Conversão é a razão entre a contagem de um estágio e a do estágio "
            "imediatamente anterior na sequência, sobre o corte atual do funil — "
            "não é coorte por lead."
        )
        return [Resultado("Funil por estágio", colunas, linhas, meta, notas)]

    # -- RF-13 tempo em estágio -------------------------------------------

    def tempo_em_estagio(self, *, desde=None, ate=None, campo_data=CAMPO_DATA_PADRAO,
                         tipo="opportunity", equipes=None):
        leads, meta, notas = self.carregar_leads(
            desde=desde, ate=ate, campo_data=campo_data, tipo=tipo, equipes=equipes
        )
        ids = [lead["id"] for lead in leads]
        duracoes, metodo, aviso = self._duracoes_por_estagio(ids, leads)
        if aviso:
            notas.append(aviso)

        colunas = ["estagio", "observacoes", "media_dias", "mediana_dias",
                   "min_dias", "max_dias"]
        linhas = []
        estagios = self.estagios()
        ordem = {e.get("name") or str(i): e.get("sequence") or 0 for i, e in estagios.items()}
        for nome in sorted(duracoes, key=lambda n: (ordem.get(n, 999), n)):
            valores = duracoes[nome]
            if not valores:
                continue
            linhas.append([
                nome,
                len(valores),
                round(media(valores) or 0, 1),
                round(mediana(valores) or 0, 1),
                round(min(valores), 1),
                round(max(valores), 1),
            ])

        meta["metodo"] = metodo
        meta["leads_com_medicao"] = sum(len(v) for v in duracoes.values())
        meta["descartados_sem_data"] = len(leads) - len({
            l["id"] for l in leads if l.get("date_last_stage_update") or l.get("create_date")
        })
        return [Resultado("Tempo em estágio", colunas, linhas, meta, notas)]

    def _duracoes_por_estagio(self, ids, leads):
        """Preferência: histórico de mail.tracking.value; queda: date_last_stage_update."""
        if ids:
            try:
                duracoes = self._duracoes_por_tracking(ids)
                if duracoes:
                    return (
                        duracoes,
                        "mail.tracking.value (histórico real de mudança de estágio)",
                        "Mede intervalos fechados: só entra estágio que o lead chegou a deixar.",
                    )
            except (OdooRequestError, OdooError) as exc:
                log.info("Histórico de tracking indisponível (%s) — usando fallback.", exc)

        duracoes = defaultdict(list)
        for lead in leads:
            referencia = lead.get("date_last_stage_update") or lead.get("create_date")
            dias = dias_entre(referencia, self.agora)
            if dias is None:
                continue
            nome = rotulo_m2o(lead.get("stage_id"), "(sem estágio)")
            duracoes[nome].append(dias)
        return (
            duracoes,
            "date_last_stage_update (fallback)",
            "LIMITAÇÃO: sem acesso a mail.tracking.value, mede apenas há quantos dias "
            "o lead está no estágio ATUAL — não o tempo histórico em cada estágio.",
        )

    def _duracoes_por_tracking(self, ids):
        campos_tracking = self.schema.nomes(MAIL_TRACKING_VALUE)
        campo_de = next((c for c in ("old_value_char", "old_value") if c in campos_tracking), None)
        campo_para = next((c for c in ("new_value_char", "new_value") if c in campos_tracking), None)
        if not campo_de or not campo_para or "mail_message_id" not in campos_tracking:
            raise OdooError("mail.tracking.value sem os campos esperados nesta base.")

        if "field_id" in campos_tracking:
            filtro_campo = ("field_id.name", "=", "stage_id")
        elif "field" in campos_tracking:
            filtro_campo = ("field", "=", "stage_id")
        else:
            raise OdooError("mail.tracking.value sem referência ao campo alterado.")

        registros = self.client.search_read_all(
            MAIL_TRACKING_VALUE,
            [
                filtro_campo,
                ("mail_message_id.model", "=", CRM_LEAD),
                ("mail_message_id.res_id", "in", list(ids)),
            ],
            ["id", "mail_message_id", campo_de, campo_para, "create_date"],
            order="id asc",
        )
        if not registros:
            return {}

        mensagens = self.client.search_read_all(
            MAIL_MESSAGE,
            [("id", "in", [id_m2o(r.get("mail_message_id")) for r in registros])],
            ["id", "res_id", "date"],
        )
        res_por_mensagem = {m["id"]: m.get("res_id") for m in mensagens}

        transicoes = defaultdict(list)
        for registro in registros:
            mensagem = id_m2o(registro.get("mail_message_id"))
            lead_id = res_por_mensagem.get(mensagem)
            if not lead_id:
                continue
            transicoes[lead_id].append({
                "de": registro.get(campo_de),
                "para": registro.get(campo_para),
                "em": registro.get("create_date"),
            })

        criacao = {
            lead["id"]: lead.get("create_date")
            for lead in self.client.search_read_all(
                CRM_LEAD, escopar_dominio_lead([("id", "in", list(transicoes))]),
                ["id", "create_date"], context={"active_test": False},
            )
        }

        duracoes = defaultdict(list)
        for lead_id, eventos in transicoes.items():
            eventos.sort(key=lambda e: e["em"] or "")
            anterior = criacao.get(lead_id)
            for evento in eventos:
                nome_estagio = evento["de"]
                dias = dias_entre(anterior, evento["em"])
                if nome_estagio and dias is not None and dias >= 0:
                    duracoes[str(nome_estagio)].append(dias)
                anterior = evento["em"]
        return duracoes

    # -- RF-14 leads parados ----------------------------------------------

    def leads_parados(self, *, dias=DIAS_PARADO_PADRAO, desde=None, ate=None,
                      campo_data=CAMPO_DATA_PADRAO, tipo="opportunity", equipes=None):
        leads, meta, notas = self.carregar_leads(
            desde=desde, ate=ate, campo_data=campo_data, tipo=tipo, equipes=equipes,
            filtros=[("active", "=", True)],
        )
        abertos = [lead for lead in leads if self.classificar(lead) == ABERTO]
        ids = [lead["id"] for lead in abertos]
        corte = limite_datahora(dias, self.agora)

        com_mensagem, metodo_mensagem = self._leads_com_mensagem_recente(ids, corte)
        com_atividade = self._leads_com_atividade_pendente(ids)

        parados = []
        descartados = 0
        for lead in abertos:
            lead_id = lead["id"]
            if lead_id in com_mensagem or lead_id in com_atividade:
                continue
            referencia = lead.get("write_date") or lead.get("date_last_stage_update") \
                or lead.get("create_date")
            inativo_ha = dias_entre(referencia, self.agora)
            if inativo_ha is None:
                descartados += 1
                continue
            if inativo_ha < dias:
                continue
            parados.append((lead, inativo_ha))

        por_responsavel = defaultdict(lambda: {"leads": 0, "valor": 0.0, "dias": []})
        for lead, inativo_ha in parados:
            grupo = por_responsavel[rotulo_m2o(lead.get("user_id"), "(sem responsável)")]
            grupo["leads"] += 1
            grupo["valor"] += float(lead.get("expected_revenue") or 0)
            grupo["dias"].append(inativo_ha)

        colunas = ["responsavel", "leads_parados", "valor_total", "media_dias_parado",
                   "max_dias_parado"]
        linhas = [
            [
                nome,
                grupo["leads"],
                round(grupo["valor"], 2),
                round(media(grupo["dias"]) or 0, 1),
                round(max(grupo["dias"]), 1),
            ]
            for nome, grupo in sorted(por_responsavel.items(),
                                      key=lambda item: -item[1]["leads"])
        ]

        meta["oportunidades_abertas"] = len(abertos)
        meta["limite_dias_sem_atividade"] = dias
        meta["parados"] = len(parados)
        meta["descartados_sem_data"] = descartados
        meta["criterio_de_atividade"] = metodo_mensagem
        notas.append(
            "Considera-se com atividade o lead que teve mensagem no chatter dentro do "
            f"período de {dias} dias OU tem atividade agendada pendente."
        )

        detalhe = Resultado(
            "Leads parados — detalhe",
            ["id", "lead", "responsavel", "estagio", "valor", "dias_parado", "ultima_alteracao"],
            [
                [
                    lead["id"], lead.get("name"),
                    rotulo_m2o(lead.get("user_id"), "(sem responsável)"),
                    rotulo_m2o(lead.get("stage_id"), "(sem estágio)"),
                    float(lead.get("expected_revenue") or 0),
                    round(inativo_ha, 1),
                    lead.get("write_date"),
                ]
                for lead, inativo_ha in sorted(parados, key=lambda item: -item[1])
            ],
            {"parados": len(parados), "limite_dias_sem_atividade": dias},
            limite_exibicao=25,
        )
        return [Resultado("Leads parados por responsável", colunas, linhas, meta, notas),
                detalhe]

    def _leads_com_mensagem_recente(self, ids, corte):
        if not ids:
            return set(), "sem leads abertos no recorte"
        try:
            mensagens = self.client.search_read_all(
                MAIL_MESSAGE,
                [("model", "=", CRM_LEAD), ("res_id", "in", list(ids)), ("date", ">=", corte)],
                ["id", "res_id"],
            )
            return {m["res_id"] for m in mensagens}, "mail.message + mail.activity"
        except (OdooRequestError, OdooError) as exc:
            log.info("mail.message indisponível (%s) — usando write_date.", exc)
            return set(), "write_date (mail.message indisponível para esta chave)"

    def _leads_com_atividade_pendente(self, ids):
        if not ids:
            return set()
        try:
            atividades = self.client.search_read_all(
                MAIL_ACTIVITY,
                [("res_model", "=", CRM_LEAD), ("res_id", "in", list(ids))],
                ["id", "res_id"],
            )
            return {a["res_id"] for a in atividades}
        except (OdooRequestError, OdooError) as exc:
            log.info("mail.activity indisponível (%s).", exc)
            return set()

    # -- RF-15 atribuição por origem --------------------------------------

    def atribuicao_origem(self, *, desde=None, ate=None, campo_data=CAMPO_DATA_PADRAO,
                          tipo="opportunity", equipes=None):
        leads, meta, notas = self.carregar_leads(
            desde=desde, ate=ate, campo_data=campo_data, tipo=tipo, equipes=equipes
        )
        dimensoes = [("source_id", "origem"), ("medium_id", "meio"), ("campaign_id", "campanha")]
        disponiveis = self.schema.nomes(CRM_LEAD)
        ausentes = [campo for campo, _ in dimensoes if campo not in disponiveis]
        if ausentes:
            notas.append(f"Campos ausentes nesta base e ignorados: {', '.join(ausentes)}")

        colunas = ["dimensao", "valor", "leads", "valor_total", "ganhos", "perdidos",
                   "taxa_ganho_%", "valor_ganho"]
        linhas = []
        sem_atribuicao = {}
        for campo, rotulo in dimensoes:
            if campo not in disponiveis:
                continue
            grupos = defaultdict(lambda: {"leads": 0, "valor": 0.0, "ganhos": 0,
                                          "perdidos": 0, "valor_ganho": 0.0})
            for lead in leads:
                chave = rotulo_m2o(lead.get(campo), "(sem atribuição)")
                if chave == "(sem atribuição)":
                    sem_atribuicao[rotulo] = sem_atribuicao.get(rotulo, 0) + 1
                grupo = grupos[chave]
                grupo["leads"] += 1
                valor = float(lead.get("expected_revenue") or 0)
                grupo["valor"] += valor
                situacao = self.classificar(lead)
                if situacao == GANHO:
                    grupo["ganhos"] += 1
                    grupo["valor_ganho"] += valor
                elif situacao == PERDIDO:
                    grupo["perdidos"] += 1
            for chave, grupo in sorted(grupos.items(), key=lambda item: -item[1]["leads"]):
                decididos = grupo["ganhos"] + grupo["perdidos"]
                linhas.append([
                    rotulo, chave, grupo["leads"], round(grupo["valor"], 2),
                    grupo["ganhos"], grupo["perdidos"],
                    round(percentual(grupo["ganhos"], decididos), 1) if decididos else None,
                    round(grupo["valor_ganho"], 2),
                ])

        meta["registros_sem_atribuicao_por_dimensao"] = {
            rotulo: sem_atribuicao.get(rotulo, 0) for _, rotulo in dimensoes
        }
        notas.append("Taxa de ganho = ganhos / (ganhos + perdidos). Leads ainda abertos "
                     "ficam fora do denominador da taxa, mas contam em 'leads'.")
        return [Resultado("Atribuição por origem, meio e campanha", colunas, linhas, meta, notas)]

    # -- RF-16 ganhos e perdas --------------------------------------------

    def ganhos_perdas(self, *, desde=None, ate=None, campo_data=CAMPO_DATA_PADRAO,
                      tipo="opportunity", equipes=None):
        leads, meta, notas = self.carregar_leads(
            desde=desde, ate=ate, campo_data=campo_data, tipo=tipo, equipes=equipes
        )
        por_mes = defaultdict(lambda: {"total": 0, "ganhos": 0, "perdidos": 0,
                                       "abertos": 0, "valor_ganho": 0.0, "valor_perdido": 0.0})
        motivos = defaultdict(lambda: {"leads": 0, "valor": 0.0})
        sem_data = 0
        arquivados = 0

        for lead in leads:
            referencia = lead.get(campo_data) or lead.get("create_date")
            if not referencia:
                sem_data += 1
                continue
            grupo = por_mes[mes_de(referencia)]
            grupo["total"] += 1
            valor = float(lead.get("expected_revenue") or 0)
            situacao = self.classificar(lead)
            if situacao == GANHO:
                grupo["ganhos"] += 1
                grupo["valor_ganho"] += valor
            elif situacao == PERDIDO:
                grupo["perdidos"] += 1
                grupo["valor_perdido"] += valor
                chave = rotulo_m2o(lead.get("lost_reason_id"), "(sem motivo informado)")
                motivos[chave]["leads"] += 1
                motivos[chave]["valor"] += valor
            elif situacao == ARQUIVADO:
                arquivados += 1
            else:
                grupo["abertos"] += 1

        colunas = ["mes", "registros", "ganhos", "perdidos", "abertos",
                   "taxa_ganho_%", "valor_ganho", "valor_perdido"]
        linhas = []
        for mes in sorted(por_mes):
            grupo = por_mes[mes]
            decididos = grupo["ganhos"] + grupo["perdidos"]
            linhas.append([
                mes, grupo["total"], grupo["ganhos"], grupo["perdidos"], grupo["abertos"],
                round(percentual(grupo["ganhos"], decididos), 1) if decididos else None,
                round(grupo["valor_ganho"], 2), round(grupo["valor_perdido"], 2),
            ])

        meta["descartados_sem_data"] = sem_data
        meta["arquivados_sem_motivo_de_perda"] = arquivados
        meta["campo_de_agrupamento"] = campo_data
        notas.append("Ganho = estágio com is_won ou probabilidade 100. "
                     "Perdido = registro arquivado com motivo de perda preenchido. "
                     "Arquivado sem motivo é contado à parte, não como perda.")

        total_perdidos = sum(m["leads"] for m in motivos.values())
        ranking = Resultado(
            "Motivos de perda (ranking)",
            ["motivo", "leads", "% das perdas", "valor_perdido"],
            [
                [
                    motivo, dados["leads"],
                    round(percentual(dados["leads"], total_perdidos), 1) if total_perdidos else None,
                    round(dados["valor"], 2),
                ]
                for motivo, dados in sorted(motivos.items(), key=lambda item: -item[1]["leads"])
            ],
            {"perdas_no_periodo": total_perdidos, "periodo": meta["periodo"],
             "equipes_consideradas": meta["equipes_consideradas"]},
        )
        return [Resultado("Ganhos e perdas por período", colunas, linhas, meta, notas), ranking]


def _texto_periodo(campo_data, desde, ate):
    if not desde and not ate:
        return "sem filtro de período (base inteira no escopo)"
    inicio, fim = normalizar_periodo(desde, ate)
    return f"{campo_data} de {inicio or 'início'} até {fim or 'agora'}"


def _nome_equipe(leads, equipe_id):
    for lead in leads:
        if id_m2o(lead.get("team_id")) == equipe_id:
            return rotulo_m2o(lead.get("team_id"), str(equipe_id))
    return str(equipe_id)
