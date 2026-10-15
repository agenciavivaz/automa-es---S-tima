/** @odoo-module **/
// Resultado comercial · Sétima (CRM / Sétima / Dashboard).
// Mesmo mecanismo do Relatório Inbound: tela OWL (ir.actions.client) que lê o CRM ao vivo
// com a sessão de quem vê. Cálculo em calc.js (funções puras), leitura em data.js.

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { router } from "@web/core/browser/router";
import { PRESETS, PRESET_PADRAO, TZ, calcular, periodo } from "./calc";
import { carregar } from "./data";

const SECOES = [
    { key: "resumo", label: "Resumo" },
    { key: "evolucao", label: "Evolução" },
    { key: "clientes", label: "Clientes e projetos" },
    { key: "tipos", label: "Tipo de projeto" },
    { key: "vendedores", label: "Vendedores", soComVendedores: true },
    { key: "pipeline", label: "Pipeline" },
];

export const GLOSSARIO = [
    ["Base do relatório", "Negócios (crm.lead, tipo oportunidade) da equipe Pipeline Sétima (id 4), ativos e arquivados. Negócios cujo nome começa com “Teste” ficam de fora."],
    ["Receita", "Soma do valor esperado dos negócios ganhos. Entra no período pela data de ganho: campo “Data de Ganho”; senão a data de ganho do Pipedrive (migrados); senão a data de fechamento do CRM. Datas em America/Sao_Paulo."],
    ["Receita acumulada do ano", "Receita de 01/01 até hoje. Fica fixa (não muda com o filtro) e compara com o mesmo intervalo do ano anterior."],
    ["Ticket médio por projeto", "Receita ÷ projetos ganhos com valor. A mediana, ao lado, mostra o projeto típico sem a distorção dos grandes contratos."],
    ["Clientes atendidos", "Empresas distintas (empresa comercial do contato) com pelo menos um ganho no período. “Novo” = primeira vitória do cliente no histórico do CRM dentro do período."],
    ["Taxa de conversão", "Ganhos ÷ (ganhos + perdidos) decididos no período, em quantidade."],
    ["Pipeline gerado", "Valor e quantidade de oportunidades que entraram no período, em qualquer situação atual. Entrada = criação no Pipedrive (migrados), senão criação no Odoo."],
    ["Pipeline aberto", "Oportunidades em andamento hoje. Ponderado = valor × probabilidade de cada negócio."],
    ["Cobertura do pipeline", "Pipeline aberto ÷ receita média mensal dos 12 meses fechados anteriores. Referência usual: 3 meses ou mais."],
    ["Ciclo de venda", "Mediana de dias entre a entrada e o ganho dos projetos ganhos no período."],
    ["Concentração", "Participação do maior cliente e dos 5 maiores na receita do período. Acima de 40% em um único cliente é risco de dependência."],
    ["Tipo de projeto", "Etiqueta “Tipo: …” no negócio, quando existe; senão classificação automática pelo nome do projeto (3D, vídeo, lives, eventos, foto, estratégia, conteúdo, brindes, campanhas, fee). O que não casa vai para “Outros”."],
    ["Comparação", "Mês, trimestre e ano comparam com os mesmos dias do período anterior (ex.: 01/01–15/10 × 01/01–15/10 do ano anterior). Personalizado compara com o intervalo imediatamente anterior de mesma duração."],
];

export class VivazSetimaDashboard extends Component {
    static template = "vivaz_setima.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.presets = PRESETS;
        this.glossario = GLOSSARIO;
        this.root = useRef("root");
        const url = router.current || {};
        this.state = useState({
            preset: PRESETS.some((p) => p.key === url.period) ? url.period : PRESET_PADRAO,
            from: url.from || "",
            to: url.to || "",
            serie: "receita",
            clientesTodos: false,
            loading: true,
            error: null,
            raw: null,
            per: null,
            loadedAt: null,
            glossarioAberto: false,
            secao: "resumo",
        });
        onWillStart(() => this.load());
        this._onScroll = () => this.spy();
        onMounted(() => this.root.el && this.root.el.addEventListener("scroll", this._onScroll, { passive: true }));
        onWillUnmount(() => this.root.el && this.root.el.removeEventListener("scroll", this._onScroll));
    }

    syncUrl() {
        const s = this.state;
        router.replaceState({
            period: s.preset,
            from: s.preset === "custom" ? s.from || undefined : undefined,
            to: s.preset === "custom" ? s.to || undefined : undefined,
        });
    }

    // -------------------------------------------------------------------- dados
    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            // o pipeline inteiro vem numa leitura; trocar o filtro só recalcula
            const raw = await carregar(this.orm);
            Object.assign(this.state, { raw, loadedAt: globalThis.luxon.DateTime.now().setZone(TZ) });
            this.aplicarPeriodo();
        } catch (e) {
            this.state.error = (e && (e.data?.message || e.message)) || String(e);
        } finally {
            this.state.loading = false;
        }
    }
    aplicarPeriodo() {
        const per = periodo(this.state.preset, this.state.from, this.state.to);
        this.state.per = per;
        if (this.state.preset === "custom" && !this.state.from && per.start) {
            this.state.from = per.start.toISODate();
            this.state.to = per.end.toISODate();
        }
        this.syncUrl();
    }

    get relatorio() {
        const { raw, per, serie, clientesTodos } = this.state;
        if (!raw || !per) return null;
        const c = this._cache;
        if (!c || c.raw !== raw || c.per !== per || c.serie !== serie || c.clientesTodos !== clientesTodos) {
            this._cache = { raw, per, serie, clientesTodos, r: calcular(raw, per, { serie, clientesTodos }) };
        }
        return this._cache.r;
    }
    get secoes() {
        const r = this.relatorio;
        return SECOES.filter((s) => !s.soComVendedores || (r && r.mostrarVendedores));
    }
    get atualizado() {
        return this.state.loadedAt ? this.state.loadedAt.toFormat("HH:mm") : "";
    }

    // ------------------------------------------------------------------ filtros
    onPreset(key) {
        this.state.preset = key;
        if (key === "custom") {
            const per = this.state.per;
            this.state.from = this.state.from || (per && per.start ? per.start.toISODate() : "");
            this.state.to = this.state.to || (per ? per.end.toISODate() : "");
        }
        this.state.clientesTodos = false;
        this.aplicarPeriodo();
    }
    onCustomDate(field, ev) {
        this.state[field] = ev.target.value;
        this.state.preset = "custom";
        if (this.state.from && this.state.to) this.aplicarPeriodo();
    }

    // ------------------------------------------------------------- navegação
    irPara(key) {
        const el = this.root.el && this.root.el.querySelector(`#vst_${key}`);
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
            const el = rootEl.querySelector(`#vst_${s.key}`);
            if (el && el.offsetTop - 80 <= rootEl.scrollTop) atual = s.key;
        }
        if (atual !== this.state.secao) this.state.secao = atual;
    }
    exportarPdf() {
        window.print(); // A4 paisagem, só o relatório (regras @media print do SCSS)
    }

    // ------------------------------------------------------------- abrir no Odoo
    abrirNegocios(titulo, ids) {
        if (!ids || !ids.length) return;
        this.action.doAction({
            type: "ir.actions.act_window", name: titulo, res_model: "crm.lead",
            domain: [["id", "in", ids]], views: [[false, "list"], [false, "kanban"], [false, "form"]],
            context: { active_test: false }, target: "current",
        });
    }
    abrirNegocio(id) {
        this.action.doAction({
            type: "ir.actions.act_window", res_model: "crm.lead", res_id: id,
            views: [[false, "form"]], target: "current", context: { active_test: false },
        });
    }
    abrirKpi(k) {
        this.abrirNegocios(`${k.label} · ${this.state.per.label}`, k.ids);
    }
}

registry.category("actions").add("vivaz_setima_dashboard", VivazSetimaDashboard);
