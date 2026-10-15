/** @odoo-module **/
// Relatório de resultados · Inbound Sétima — v2 (CRM / Inbound Sétima / Dashboard v2).
// Mesmo mecanismo da v1: tela OWL (ir.actions.client) que lê o CRM ao vivo com a sessão de
// quem vê. Cálculo em calc.js (funções puras), leitura em data.js, renderização aqui.

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
import { router } from "@web/core/browser/router";
import { PRESETS, TIPOS_ACAO, TZ, calcular, periodo, rankEtapas, toUtcSql } from "./calc";
import { MODELO, carregar, carregarComentario } from "./data";

const DIMENSOES = [
    { key: "campanha", label: "Campanha" },
    { key: "conjunto", label: "Conjunto de anúncios" },
    { key: "criativo", label: "Criativo" },
    { key: "plataforma", label: "Plataforma" },
    { key: "etapa", label: "Etapa atual" },
];
const SECOES = [
    { key: "resumo", label: "Resumo", board: true },
    { key: "funil", label: "Funil", board: true },
    { key: "aquisicao", label: "Aquisição", board: true },
    { key: "operacao", label: "Operação", board: false },
    { key: "atividades", label: "Atividades", board: false },
];
const PAGINA = 10;

export const GLOSSARIO = [
    ["Lead inbound", "Registro de crm.lead da equipe Inbound Sétima (id 16), tipo oportunidade, ativo ou perdido — mesmo critério da v1 (RN1)."],
    ["Leads no período", "Leads inbound com data de entrada no período: criação no Pipedrive (x_pipedrive_add_time) para migrados, senão criação no Odoo (create_date). Datas em America/Sao_Paulo."],
    ["MQL", "Lead do período cuja etapa atual é MQL ou posterior, ou ganho (método da v1: etapa atual, não o histórico). Critério de negócio: empresa que investe mais de R$ 100 mil/mês em marketing."],
    ["SQL+", "Lead do período na etapa SQL, Oportunidade Sétima ou ganho."],
    ["Taxa Lead→MQL", "MQL ÷ leads do período (mesma coorte)."],
    ["Reunião agendada", "Evento de agenda ligado a um lead inbound ou atividade do tipo Reunião, criado no período. Só dado estruturado (RN5)."],
    ["Reunião realizada", "Evento já passado e não cancelado, ou atividade Reunião concluída, no período."],
    ["Convite para agendar", "Mensagem/nota pedindo agenda. É uma tentativa: não conta como reunião."],
    ["Tempo até 1º contato", "Mediana, em horas corridas, entre a entrada do lead e o 1º toque de saída (WhatsApp/DataCrazy, e-mail, ligação, convite, reunião ou atividade concluída). Notas de pesquisa/enriquecimento não contam."],
    ["Receita acumulada do processo inbound", "Soma do valor esperado dos negócios ganhos marcados “Originado no Inbound”, em qualquer pipeline, desde a data de início configurada (padrão: 1º contrato). Não muda com o filtro."],
    ["Receita no período", "Mesmo critério, com data do contrato (Data de Ganho, senão data de fechamento do CRM) dentro do período."],
    ["Leads tocados", "Leads inbound com pelo menos uma ação no período, de qualquer data de entrada."],
    ["Parado", "Lead aberto do período sem mudança de etapa há mais de 7 dias e sem atividade futura."],
    ["Sem sucesso", "Ação cujo texto indica tentativa sem resposta (tentativa, sem contato, não atende, sem resposta, inválido) — critério da v1."],
    ["Expansão de conta", "Oportunidades de expansão (ex.: Hyundai no pipeline ABM Sétima) não entram em nenhum número do inbound (RN3)."],
];

export class VivazInboundDashboard extends Component {
    static template = "vivaz_inbound.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.presets = PRESETS;
        this.dimensoes = DIMENSOES;
        this.tiposAcao = TIPOS_ACAO;
        this.glossario = GLOSSARIO;
        this.root = useRef("root");
        const url = router.current || {};
        const presetOk = PRESETS.some((p) => p.key === url.period);
        this.state = useState({
            preset: presetOk ? url.period : "this_month",
            from: url.from || "",
            to: url.to || "",
            view: url.view === "board" ? "board" : "completo",
            dim: "campanha",
            sort: "leads",
            sortDir: "desc",
            serie: "leads",
            logTipo: "all",
            logVisiveis: PAGINA,
            abertos: {},
            loading: true,
            error: null,
            raw: null,
            per: null,
            comentario: null,
            podeEditar: false,
            glossarioAberto: false,
            pdfMenu: false,
            secao: "resumo",
            imprimindo: false,
        });
        onWillStart(async () => {
            this.state.podeEditar = await user.hasGroup("sales_team.group_sale_manager");
            await this.load();
        });
        this._onScroll = () => this.spy();
        onMounted(() => this.root.el && this.root.el.addEventListener("scroll", this._onScroll, { passive: true }));
        onWillUnmount(() => this.root.el && this.root.el.removeEventListener("scroll", this._onScroll));
    }

    // ------------------------------------------------------------ estado na URL (§7.1)
    syncUrl() {
        const s = this.state;
        router.replaceState({
            period: s.preset,
            view: s.view,
            from: s.preset === "custom" ? s.from || undefined : undefined,
            to: s.preset === "custom" ? s.to || undefined : undefined,
        });
    }

    // -------------------------------------------------------------------- dados
    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const per = periodo(this.state.preset, this.state.from, this.state.to);
            const [raw, comentario] = await Promise.all([carregar(this.orm, per), carregarComentario(this.orm, per)]);
            raw.loadedAt = globalThis.luxon.DateTime.now().setZone(TZ);
            Object.assign(this.state, { raw, per, comentario, logVisiveis: PAGINA, abertos: {} });
            if (this.state.preset === "custom" && !this.state.from) {
                this.state.from = per.start.toISODate();
                this.state.to = per.end.toISODate();
            }
        } catch (e) {
            this.state.error = (e && (e.data?.message || e.message)) || String(e);
        } finally {
            this.state.loading = false;
            this.syncUrl();
        }
    }

    get relatorio() {
        if (!this.state.raw) return null;
        return calcular(this.state.raw, this.state.per, {
            dim: this.state.dim, sort: this.state.sort, sortDir: this.state.sortDir,
            serie: this.state.serie, logTipo: this.state.logTipo,
        });
    }

    get board() {
        return this.state.view === "board";
    }
    get secoes() {
        return SECOES.filter((s) => !this.board || s.board);
    }
    get atualizado() {
        return this.state.raw ? this.state.raw.loadedAt.toFormat("HH:mm") : "";
    }
    get mostrarComentario() {
        return !!(this.state.comentario && this.state.comentario.x_texto) || (this.state.podeEditar && !this.state.imprimindo);
    }
    get comentarioAutor() {
        const c = this.state.comentario;
        if (!c) return "";
        const quem = c.write_uid ? c.write_uid[1].split(" ")[0] : "";
        const quando = globalThis.luxon.DateTime.fromSQL(c.write_date, { zone: "utc" }).setZone(TZ).toFormat("dd/MM");
        return [quem, quando].filter(Boolean).join(" · ");
    }

    // ------------------------------------------------------------------ filtros
    async onPreset(key) {
        this.state.preset = key;
        if (key === "custom") {
            const per = this.state.per;
            this.state.from = this.state.from || (per && per.start ? per.start.toISODate() : "");
            this.state.to = this.state.to || (per ? per.end.toISODate() : "");
        }
        await this.load();
    }
    async onCustomDate(field, ev) {
        this.state[field] = ev.target.value;
        this.state.preset = "custom";
        if (this.state.from && this.state.to) await this.load();
    }
    setView(v) {
        this.state.view = v;
        this.syncUrl();
    }
    onDim(key) {
        this.state.dim = key;
        this.state.sort = "leads";
        this.state.sortDir = "desc";
    }
    onSort(key) {
        if (this.state.sort === key) this.state.sortDir = this.state.sortDir === "desc" ? "asc" : "desc";
        else {
            this.state.sort = key;
            this.state.sortDir = key === "key" ? "asc" : "desc";
        }
    }
    sortIcon(key) {
        if (this.state.sort !== key) return "fa-sort o_vin_sort_off";
        return this.state.sortDir === "desc" ? "fa-sort-desc" : "fa-sort-asc";
    }
    onLogTipo(key) {
        this.state.logTipo = key;
        this.state.logVisiveis = PAGINA; // filtro reinicia a paginação (A1)
    }
    carregarMais() {
        this.state.logVisiveis += PAGINA;
    }
    toggleTexto(key) {
        this.state.abertos[key] = !this.state.abertos[key];
    }
    logVisivel(r) {
        const itens = r.log.slice(0, this.state.logVisiveis);
        return itens.map((it, i) => ({ ...it, novoDia: i === 0 || itens[i - 1].dia !== it.dia }));
    }

    // ------------------------------------------------------------- navegação
    irPara(key) {
        const el = this.root.el && this.root.el.querySelector(`#vin_${key}`);
        if (el) {
            this.root.el.scrollTo({ top: el.offsetTop - 56, behavior: "smooth" });
            this.state.secao = key;
        }
    }
    spy() {
        const rootEl = this.root.el;
        if (!rootEl) return;
        let atual = this.secoes[0].key;
        for (const s of this.secoes) {
            const el = rootEl.querySelector(`#vin_${s.key}`);
            if (el && el.offsetTop - 80 <= rootEl.scrollTop) atual = s.key;
        }
        if (atual !== this.state.secao) this.state.secao = atual;
    }

    // ------------------------------------------------------------------- PDF (§7.10)
    async exportarPdf(modo) {
        this.state.pdfMenu = false;
        const anterior = this.state.view;
        this.state.view = modo;
        this.state.imprimindo = true;
        await new Promise((ok) => setTimeout(ok, 250));
        try {
            window.print();
        } finally {
            this.state.imprimindo = false;
            this.state.view = anterior;
        }
    }

    // ------------------------------------------------------------- abrir no Odoo
    abrirLeads(titulo, ids) {
        this.action.doAction({
            type: "ir.actions.act_window", name: titulo, res_model: "crm.lead",
            domain: [["id", "in", ids]], views: [[false, "list"], [false, "kanban"], [false, "form"]],
            context: { active_test: false }, target: "current",
        });
    }
    abrirLead(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "crm.lead", res_id: id,
            views: [[false, "form"]], target: "current", context: { active_test: false },
        });
    }
    abrirKpi(key) {
        const r = this.relatorio;
        const per = this.state.per;
        const leads = this.state.raw.leads;
        const ids = (fn) => leads.filter(fn).map((l) => l.id);
        if (key === "leads") this.abrirLeads(`Leads · ${per.label}`, ids(() => true));
        else if (key === "mql" || key === "sql") {
            const nome = key === "mql" ? "MQL" : "SQL";
            const i = r.funil.findIndex((s) => s.name.toUpperCase().startsWith(nome));
            this.abrirStep(i);
        } else if (key === "reunioes") {
            this.action.doAction({
                type: "ir.actions.act_window", name: `Reuniões · ${per.label}`, res_model: "calendar.event",
                domain: [["opportunity_id", "in", this.state.raw.todosIds],
                    ...(per.start ? [["create_date", ">=", toUtcSql(per.start)]] : []), ["create_date", "<=", toUtcSql(per.end)]],
                views: [[false, "list"], [false, "form"]], target: "current",
            });
        } else if (key === "contato") this.irPara("operacao");
    }
    abrirStep(i) {
        if (i < 0) return;
        const s = this.relatorio.funil[i];
        const { leads, stages } = this.state.raw; // leads = coorte do período (data.js)
        const rank = rankEtapas(stages);
        const ids = leads.filter((l) => (l.won_status === "won" ? stages.length : rank(l.stage_id)) >= s.idx && (s.key !== "won" || l.won_status === "won")).map((l) => l.id);
        this.abrirLeads(`${s.name}${s.key === "won" ? "" : "+"} · ${this.state.per.label}`, ids);
    }
    abrirLinha(linha) {
        this.abrirLeads(`${linha.key} · ${this.state.per.label}`, linha.ids);
    }
    abrirContratos(ids) {
        this.abrirLeads("Receita acumulada do processo inbound", ids);
    }
    verTodasNoOdoo() {
        const per = this.state.per;
        this.action.doAction({
            type: "ir.actions.act_window", name: `Registro de atividades · ${per.label}`, res_model: "mail.message",
            domain: [["model", "=", "crm.lead"], ["res_id", "in", this.state.raw.todosIds], ["message_type", "in", ["comment", "email"]],
                ...(per.start ? [["date", ">=", toUtcSql(per.start)]] : []), ["date", "<=", toUtcSql(per.end)]],
            views: [[false, "list"], [false, "form"]], target: "current",
        });
    }
    editarComentario() {
        const per = this.state.per;
        const c = this.state.comentario;
        const mensal = ["this_month", "prev_month"].includes(this.state.preset);
        const ini = mensal ? per.start.startOf("month") : per.start;
        const fim = mensal ? per.start.endOf("month") : per.end;
        this.action.doAction({
            type: "ir.actions.act_window", name: "Próximos passos · Vivaz", res_model: MODELO.comentario,
            res_id: c ? c.id : false, views: [[false, "form"]], target: "new",
            context: c ? {} : { default_x_data_inicio: ini.toISODate(), default_x_data_fim: fim.toISODate(), default_x_name: per.label },
        }, {
            onClose: async () => {
                this.state.comentario = await carregarComentario(this.orm, this.state.per);
            },
        });
    }
}

registry.category("actions").add("vivaz_inbound_dashboard_v2", VivazInboundDashboard);
