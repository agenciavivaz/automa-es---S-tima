/** @odoo-module **/
// Dashboard estratégico do ABM Sétima (CRM / ABM Setima / Dashboard).
// Lê ao vivo crm.lead (equipe ABM Setima) e x_abm_sinal com a sessão do próprio usuário:
// nada é copiado nem gravado.
//
// Leitura para o board: separa as duas naturezas de sinal.
//  - LinkedIn Ads · relatório 30d é uma FOTO semanal de cada conta (nível de engajamento,
//    interações, exposição). Repete toda semana, então nunca é somado: vale a última leitura.
//  - Sinais de intenção são ações de pessoas das contas (visita, formulário, resposta, follow…).

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { router } from "@web/core/browser/router";

const { DateTime } = luxon;

const TEAM_ID = 20; // crm.team "ABM Setima" (ir.config_parameter abm.team_id)
const SCORE_MAX = 90; // mesma régua do campo x_abm_score_pct
const LI_RELATORIO = "li_ads_relatorio";
const ENCERRADAS = ["Descartada", "Cliente – expansão"];

const PRESETS = [
    { key: "7d", label: "7 dias" },
    { key: "30d", label: "30 dias" },
    { key: "90d", label: "90 dias" },
    { key: "month", label: "Este mês" },
    { key: "prev_month", label: "Mês anterior" },
    { key: "all", label: "Tudo" },
    { key: "custom", label: "Personalizado" },
];

const FAIXAS = [
    { key: "fria", label: "Fria", hint: "< 30", color: "#94a3b8" },
    { key: "engajada", label: "Engajada", hint: "30–59", color: "#b45309" },
    { key: "quente", label: "Quente", hint: "≥ 60", color: "#b91c1c" },
];

const ORIGENS = {
    linkedin_ads: { label: "LinkedIn Ads", color: "#1d4ed8" },
    linkedin_manual: { label: "LinkedIn (manual)", color: "#0e7490" },
    apollo_manual: { label: "Apollo", color: "#6d28d9" },
    site: { label: "Site", color: "#047857" },
    email: { label: "E-mail", color: "#b45309" },
    whatsapp: { label: "WhatsApp", color: "#4d7c0f" },
    formulario: { label: "Formulário", color: "#be185d" },
    ligacao: { label: "Ligação", color: "#9a3412" },
    false: { label: "Sem origem", color: "#94a3b8" },
};

const TIPOS = {
    li_ads_relatorio: "LinkedIn Ads · relatório 30d",
    li_impressoes_semana: "LinkedIn · 50+ impressões",
    li_cliques: "LinkedIn · cliques",
    li_reacao_post: "Reagiu a post do especialista",
    li_conexao_aceita: "Conexão aceita",
    li_seguiu_pagina: "Seguiu a página da Sétima",
    li_dm_resposta: "Respondeu DM",
    visita_dominio: "Visitou o site",
    visita_alta_intencao: "Visita de alta intenção",
    email_resposta: "Respondeu e-mail",
    formulario: "Formulário / lead magnet",
    ligacao_conversa: "Ligação com conversa",
    resposta_a_classificar: "Resposta a classificar",
    resposta_automatica: "Resposta automática",
    resposta_negativa: "Resposta negativa",
    resposta_neutra: "Resposta neutra",
    resposta_positiva: "Braço erguido",
    outro: "Outro",
};
const TIPOS_RESPOSTA = new Set([
    "resposta_a_classificar", "resposta_negativa", "resposta_neutra",
    "resposta_positiva", "email_resposta", "li_dm_resposta",
]);

const CADENCIA = {
    nao_iniciada: { label: "Não iniciada", color: "#cbd5e1" },
    ativa: { label: "Ativa", color: "#047857" },
    pausada: { label: "Pausada", color: "#b45309" },
    concluida: { label: "Concluída", color: "#1d4ed8" },
    false: { label: "Sem status", color: "#e3e6ea" },
};

const SECOES = [
    { key: "resumo", label: "Resumo" },
    { key: "sinais", label: "Sinais de intenção" },
    { key: "jornada", label: "Jornada das contas" },
    { key: "contas", label: "Visão por conta" },
];

const ORDENS = [
    ["score", "Score"],
    ["intencao", "Intenção no período"],
    ["midia", "Frequência de mídia"],
    ["nome", "Nome"],
];

const GLOSSARIO = [
    ["Contas no programa", "Oportunidades da equipe ABM Setima (id 20). O filtro de tier vale para todo o painel."],
    ["Novas contas", "Contas criadas no período (data de criação no CRM). Explicam quedas de percentual: conta nova entra sem histórico de sinais."],
    ["Cobertura", "% das contas com pelo menos um sinal que pontuou no período (inclui o relatório 30d do LinkedIn Ads quando ele pontua). Compara com o período anterior usando a base que existia na época; “sem as novas” tira do cálculo as contas criadas no período."],
    ["Sinal de intenção", "Ação de alguém da conta registrada em x_abm_sinal: visita ao site ou ao perfil, follow, reação, formulário, resposta, ligação. Não inclui o relatório do LinkedIn Ads."],
    ["Respostas", "Respostas genuínas a e-mail ou DM (automáticas ficam fora). Braço erguido = resposta positiva."],
    ["Score e temperatura", "Soma dos pontos dos sinais ativos (expiram em 30 dias), régua de 0 a 90. Fria < 30, engajada 30–59, quente ≥ 60."],
    ["Frequência de mídia", "Impressões do LinkedIn Ads na empresa ÷ público estimado na segmentação (pessoas no Brasil com os cargos da campanha, contadas no Apollo e calibradas pelo público total do LinkedIn). Faixas: < 2× baixa, 2–4× construindo, 4–8× ideal, > 8× saturando. Informativo: não entra no score."],
    ["Comitê", "Decisores mapeados sobre o total de pessoas do comitê de compra da conta."],
    ["Comparação", "Os indicadores comparam com o período imediatamente anterior de mesma duração."],
];

const LEAD_FIELDS = [
    "name", "stage_id", "create_date", "x_abm_score", "x_abm_tier", "x_abm_faixa",
    "x_abm_cadencia_status", "x_abm_ultimo_sinal_data", "x_abm_segmento",
    "x_abm_comite_total", "x_abm_comite_decisores",
    "x_abm_midia_freq", "x_abm_midia_impressoes", "x_abm_midia_publico", "x_abm_midia_periodo",
];
const SINAL_FIELDS = ["x_name", "x_detalhe", "x_data", "x_lead_id", "x_origem", "x_tipo", "x_pontos", "x_ativo"];

const SQL = "yyyy-MM-dd HH:mm:ss";
const toUtcSql = (dt) => dt.toUTC().toFormat(SQL);
const fromUtcSql = (s) => (s ? DateTime.fromSQL(s, { zone: "utc" }).toLocal() : null);
const fromDate = (s) => (s ? DateTime.fromISO(s) : null);
const fmtInt = (n) => (n || 0).toLocaleString("pt-BR");
const pct = (a, b) => (b ? Math.round((a * 100) / b) : 0);

// "Outro" é desmembrado pelo começo do resumo ("Visitou o perfil do especialista – …").
const tipoChave = (s) => {
    if (s.x_tipo !== "outro") return s.x_tipo || "false";
    const acao = (s.x_name || "").split(/\s+[–-]\s+/)[0].trim();
    return acao ? `outro:${acao}` : "outro";
};
const tipoLabel = (key) => (key.startsWith("outro:") ? key.slice(6) : TIPOS[key] || key || "—");
// Frequência de mídia (x_abm_midia_*): impressões ÷ público estimado na segmentação.
const MIDIA_FAIXAS = [
    { max: 2, key: "baixa", label: "baixa" },
    { max: 4, key: "construindo", label: "construindo" },
    { max: 8, key: "ideal", label: "ideal" },
    { max: Infinity, key: "saturando", label: "saturando" },
];
const midiaInfo = (l) => {
    const f = l.x_abm_midia_freq;
    if (!f && !l.x_abm_midia_impressoes) {
        return { freq: null, texto: "—", faixa: null, titulo: "Sem medição de mídia para esta conta" };
    }
    const faixa = f ? MIDIA_FAIXAS.find((x) => f < x.max) : null;
    return {
        freq: f || null,
        texto: f ? `${f.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}×` : "n/d",
        faixa,
        titulo: `${(l.x_abm_midia_impressoes || 0).toLocaleString("pt-BR")} impressões ÷ ${(l.x_abm_midia_publico || 0).toLocaleString("pt-BR")} pessoas estimadas na segmentação` +
            (l.x_abm_midia_periodo ? ` · ${l.x_abm_midia_periodo}` : ""),
    };
};

export class AbmSetimaDashboard extends Component {
    static template = "abm_setima_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.presets = PRESETS;
        this.ordens = ORDENS;
        this.glossario = GLOSSARIO;
        this.scoreMax = SCORE_MAX;
        this.root = useRef("root");
        const url = router.current || {};
        const presetUrl = PRESETS.some((p) => p.key === url.period && p.key !== "custom") ? url.period : "30d";
        this.state = useState({
            preset: presetUrl,
            secao: "resumo",
            glossarioAberto: false,
            contasTodas: false,
            from: "",
            to: "",
            tier: "all",
            sort: "score",
            loading: true,
            error: null,
            raw: null,
        });
        this._setPresetDates(presetUrl);
        onWillStart(() => this.load());
        this._onScroll = () => this.spy();
        onMounted(() => this.root.el && this.root.el.addEventListener("scroll", this._onScroll, { passive: true }));
        onWillUnmount(() => this.root.el && this.root.el.removeEventListener("scroll", this._onScroll));
    }

    get secoes() {
        return SECOES;
    }
    irPara(key) {
        const el = this.root.el && this.root.el.querySelector(`#vas_${key}`);
        if (el) {
            this.root.el.scrollTo({ top: el.offsetTop - 56, behavior: "smooth" });
            this.state.secao = key;
        }
    }
    spy() {
        const rootEl = this.root.el;
        if (!rootEl) return;
        let atual = SECOES[0].key;
        for (const s of SECOES) {
            const el = rootEl.querySelector(`#vas_${s.key}`);
            if (el && el.offsetTop - 80 <= rootEl.scrollTop) atual = s.key;
        }
        if (atual !== this.state.secao) this.state.secao = atual;
    }
    exportarPdf() {
        window.print();
    }

    // ------------------------------------------------------------ período
    _setPresetDates(key) {
        const today = DateTime.local().startOf("day");
        let from = null;
        let to = today;
        if (key === "7d") from = today.minus({ days: 6 });
        else if (key === "30d") from = today.minus({ days: 29 });
        else if (key === "90d") from = today.minus({ days: 89 });
        else if (key === "month") from = today.startOf("month");
        else if (key === "prev_month") {
            from = today.minus({ months: 1 }).startOf("month");
            to = from.endOf("month").startOf("day");
        }
        if (key === "all") {
            this.state.from = "";
            this.state.to = today.toISODate();
        } else if (key !== "custom") {
            this.state.from = from.toISODate();
            this.state.to = to.toISODate();
        }
    }

    get period() {
        const end = (fromDate(this.state.to) || DateTime.local()).endOf("day");
        const start = this.state.from ? fromDate(this.state.from).startOf("day") : null;
        let prevStart = null;
        let prevEnd = null;
        if (start) {
            const days = Math.round(end.diff(start, "days").days);
            prevEnd = start.minus({ milliseconds: 1 });
            prevStart = start.minus({ days });
        }
        return { start, end, prevStart, prevEnd };
    }

    get periodLabel() {
        const { start, end } = this.period;
        const f = (d) => d.toFormat("dd/MM/yyyy");
        return start ? `${f(start)} – ${f(end)}` : `Desde o início – ${f(end)}`;
    }

    get prevLabel() {
        const { prevStart, prevEnd } = this.period;
        const f = (d) => d.toFormat("dd/MM/yyyy");
        return prevStart ? `${f(prevStart)} – ${f(prevEnd)}` : null;
    }

    async onPreset(key) {
        this.state.preset = key;
        if (key !== "custom") {
            this._setPresetDates(key);
            router.replaceState({ period: key });
            await this.load();
        }
    }

    async onCustomDate(field, ev) {
        this.state[field] = ev.target.value;
        this.state.preset = "custom";
        if (this.state.to && (!this.state.from || this.state.from <= this.state.to)) {
            await this.load();
        }
    }

    onSort(key) {
        this.state.sort = key;
    }

    // -------------------------------------------------------------- dados
    async load() {
        this.state.loading = true;
        this.state.error = null;
        const { start, end, prevStart } = this.period;
        const lower = prevStart || start;
        try {
            const team = [["x_lead_id.team_id", "=", TEAM_ID]];
            // relatórios do LinkedIn: só a janela (período + anterior); intenção: histórico todo (é pouco
            // volume e dá o "último sinal de intenção" real de cada conta).
            const relDomain = [...team, ["x_tipo", "=", LI_RELATORIO], ["x_data", "<=", toUtcSql(end)]];
            if (lower) relDomain.push(["x_data", ">=", toUtcSql(lower)]);
            const [leads, relatorios, intencao] = await Promise.all([
                this.orm.searchRead(
                    "crm.lead",
                    [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"]],
                    LEAD_FIELDS,
                    { order: "x_abm_score desc, name" }
                ),
                this.orm.searchRead("x_abm_sinal", relDomain, SINAL_FIELDS, { order: "x_data desc" }),
                this.orm.searchRead(
                    "x_abm_sinal",
                    [...team, ["x_tipo", "!=", LI_RELATORIO], ["x_data", "<=", toUtcSql(end)]],
                    SINAL_FIELDS,
                    { order: "x_data desc" }
                ),
            ]);
            const stageIds = [...new Set(leads.map((l) => l.stage_id && l.stage_id[0]).filter(Boolean))];
            const stages = await this.orm.searchRead(
                "crm.stage",
                ["|", ["team_ids", "in", [TEAM_ID]], ["id", "in", stageIds]],
                ["name", "sequence"],
                { order: "sequence, id" }
            );
            this.state.raw = { leads, relatorios, intencao, stages, loadedAt: DateTime.local() };
        } catch (e) {
            this.state.error = (e && (e.data?.message || e.message)) || String(e);
        } finally {
            this.state.loading = false;
        }
    }

    // ----------------------------------------------------------- métricas
    get metrics() {
        const raw = this.state.raw;
        if (!raw) {
            return null;
        }
        const { start, end, prevStart, prevEnd } = this.period;
        const tier = this.state.tier;
        const today = DateTime.local().startOf("day");
        const inRange = (dt, a, b) => dt && (!a || dt >= a) && dt <= b;
        const stageName = (l) => (l.stage_id ? l.stage_id[1] : "");

        const leads = raw.leads
            .filter((l) => tier === "all" || l.x_abm_tier === tier)
            .map((l) => ({ ...l, criada: fromUtcSql(l.create_date) }));
        const leadIds = new Set(leads.map((l) => l.id));
        const daBase = (s) => s.x_lead_id && leadIds.has(s.x_lead_id[0]);
        const comData = (s) => ({ ...s, dt: fromUtcSql(s.x_data), tipoKey: tipoChave(s) });
        const relAll = raw.relatorios.filter(daBase).map(comData);
        const intAll = raw.intencao.filter(daBase).map(comData);
        const rel = relAll.filter((s) => inRange(s.dt, start, end));
        const relPrev = prevStart ? relAll.filter((s) => inRange(s.dt, prevStart, prevEnd)) : null;
        const intencao = intAll.filter((s) => inRange(s.dt, start, end));
        const intencaoPrev = prevStart ? intAll.filter((s) => inRange(s.dt, prevStart, prevEnd)) : null;

        // ---------- base e novas contas
        const novas = leads.filter((l) => inRange(l.criada, start, end));
        const novasIds = new Set(novas.map((l) => l.id));
        const novasPrev = prevStart ? leads.filter((l) => inRange(l.criada, prevStart, prevEnd)) : null;
        const baseInicio = start ? leads.filter((l) => l.criada < start).length : 0;
        const basePrev = prevEnd ? leads.filter((l) => l.criada <= prevEnd) : null;

        // ---------- cobertura: contas com sinal que pontuou
        const pontuou = (lista) => new Set(lista.filter((s) => (s.x_pontos || 0) > 0).map((s) => s.x_lead_id[0]));
        const cobertas = pontuou([...rel, ...intencao]);
        const cobertasAntigas = [...cobertas].filter((id) => !novasIds.has(id)).length;
        const antigas = leads.length - novas.length;
        const coberturaPct = pct(cobertas.size, leads.length);
        let coberturaPrevPct = null;
        if (relPrev && basePrev && basePrev.length) {
            const idsPrev = new Set(basePrev.map((l) => l.id));
            const cobPrev = [...pontuou([...relPrev, ...intencaoPrev])].filter((id) => idsPrev.has(id)).length;
            coberturaPrevPct = pct(cobPrev, basePrev.length);
        }

        // ---------- variações
        const prevLabel = this.prevLabel;
        const delta = (cur, prev, { unidade = "", pctMin = 10, neutro = false } = {}) => {
            if (prev === null || prev === undefined) return null;
            const d = cur - prev;
            const usaPct = !unidade && prev >= pctMin;
            const sinal = d > 0 ? `+${fmtInt(d)}${unidade}` : d < 0 ? `–${fmtInt(-d)}${unidade}` : `0${unidade}`;
            return {
                texto: usaPct && d !== 0 ? `${sinal} (${d > 0 ? "+" : "–"}${Math.abs(pct(d, prev))}%)` : sinal,
                seta: d > 0 ? "fa-arrow-up" : d < 0 ? "fa-arrow-down" : "fa-minus",
                classe: neutro || d === 0 || (!unidade && !usaPct) ? "neutro" : d > 0 ? "bom" : "ruim",
                tooltip: `${prevLabel}: ${fmtInt(prev)}${unidade}`,
            };
        };

        // ---------- KPIs
        const respostas = intencao.filter((s) => TIPOS_RESPOSTA.has(s.x_tipo));
        const bracos = intencao.filter((s) => s.x_tipo === "resposta_positiva").length;
        const pontosInt = intencao.reduce((t, s) => t + (s.x_pontos || 0), 0);
        const contasInt = new Set(intencao.map((s) => s.x_lead_id[0])).size;
        const aquecidas = leads.filter((l) => ["engajada", "quente"].includes(l.x_abm_faixa));
        const scoreMedio = leads.length
            ? Math.round(leads.reduce((t, l) => t + (l.x_abm_score || 0), 0) / leads.length) : 0;
        const kpis = [
            {
                key: "contas", icon: "fa-building-o", label: "Contas no programa", value: fmtInt(leads.length),
                sub: start ? `eram ${fmtInt(baseInicio)} no início do período` : "base atual",
                delta: null, click: "contas",
                info: "Oportunidades da equipe ABM Setima hoje (respeita o filtro de tier).",
            },
            {
                key: "novas", icon: "fa-plus-circle", label: "Novas contas", value: fmtInt(novas.length),
                sub: start && baseInicio ? `+${pct(novas.length, baseInicio)}% sobre a base` : "criadas no período",
                delta: delta(novas.length, novasPrev && novasPrev.length, { neutro: true }), click: "novas", destaque: novas.length > 0,
                info: "Contas criadas no período. Entram sem histórico de sinais e por isso puxam a cobertura para baixo.",
            },
            {
                key: "cobertura", icon: "fa-bullseye", label: "Cobertura", value: `${coberturaPct}%`,
                sub: novas.length
                    ? `${cobertas.size} de ${leads.length} · ${pct(cobertasAntigas, antigas)}% sem as novas`
                    : `${cobertas.size} de ${leads.length} contas`,
                delta: delta(coberturaPct, coberturaPrevPct, { unidade: " p.p." }), click: "cobertura",
                info: "Contas com pelo menos um sinal que pontuou no período, sobre a base. A comparação usa a base que existia no período anterior.",
            },
            {
                key: "intencao", icon: "fa-hand-pointer-o", label: "Sinais de intenção", value: fmtInt(intencao.length),
                sub: `${contasInt} conta(s) · ${fmtInt(pontosInt)} pts`,
                delta: delta(intencao.length, intencaoPrev && intencaoPrev.length), click: "intencao",
                info: "Ações de pessoas das contas (visitas, follow, formulários, respostas…). Não inclui o relatório semanal do LinkedIn Ads.",
            },
            {
                key: "respostas", icon: "fa-reply", label: "Respostas", value: fmtInt(respostas.length),
                sub: `${bracos} braço(s) erguido(s)`,
                delta: delta(respostas.length, intencaoPrev && intencaoPrev.filter((s) => TIPOS_RESPOSTA.has(s.x_tipo)).length),
                click: "respostas",
                info: "Respostas genuínas a e-mail ou DM (respostas automáticas ficam fora). Braço erguido = resposta positiva.",
            },
            {
                key: "aquecidas", icon: "fa-fire", label: "Engajadas ou quentes", value: fmtInt(aquecidas.length),
                sub: `${pct(aquecidas.length, leads.length)}% da base · score médio ${scoreMedio}`,
                delta: null, click: "aquecidas",
                info: "Contas com score ≥ 30 hoje (não depende do período).",
            },
        ];

        // ---------- tipos de sinal de intenção ("Outro" desmembrado)
        const tiposMap = new Map();
        for (const s of intencao) {
            const r = tiposMap.get(s.tipoKey) || { key: s.tipoKey, count: 0, pontos: 0, contas: new Set() };
            r.count += 1;
            r.pontos += s.x_pontos || 0;
            r.contas.add(s.x_lead_id[0]);
            tiposMap.set(s.tipoKey, r);
        }
        const tiposArr = [...tiposMap.values()].sort((a, b) => b.contas.size - a.contas.size || b.pontos - a.pontos);
        const maxTipo = Math.max(1, ...tiposArr.map((t) => t.contas.size));
        const tipos = tiposArr.map((t) => ({
            key: t.key, label: tipoLabel(t.key), count: t.count, pontos: t.pontos, contas: t.contas.size,
            width: pct(t.contas.size, maxTipo), resposta: TIPOS_RESPOSTA.has(t.key) || t.key === "resposta_automatica",
            tipo: t.key.startsWith("outro:") ? "outro" : t.key,
            nome: t.key.startsWith("outro:") ? t.key.slice(6) : null,
        }));

        // ---------- intenção ao longo do tempo (empilhado por origem)
        const firstDt = start || (intencao.length ? intencao[intencao.length - 1].dt.startOf("day") : end.startOf("day"));
        const spanDays = Math.max(1, Math.round(end.diff(firstDt, "days").days));
        const unit = spanDays <= 14 ? "day" : spanDays <= 180 ? "week" : "month";
        const buckets = [];
        let cur = firstDt.startOf(unit);
        while (cur <= end && buckets.length < 120) {
            buckets.push({ start: cur, end: cur.endOf(unit), byOrigem: {}, total: 0, pontos: 0 });
            cur = cur.plus({ [unit + "s"]: 1 });
        }
        for (const s of intencao) {
            const b = buckets.find((b) => s.dt >= b.start && s.dt <= b.end);
            if (b) {
                const o = s.x_origem || "false";
                b.byOrigem[o] = (b.byOrigem[o] || 0) + 1;
                b.total += 1;
                b.pontos += s.x_pontos || 0;
            }
        }
        const maxBucket = Math.max(1, ...buckets.map((b) => b.total));
        const labelFmt = unit === "month" ? "MMM/yy" : "dd/MM";
        const origemCount = new Map();
        for (const s of intencao) origemCount.set(s.x_origem || "false", (origemCount.get(s.x_origem || "false") || 0) + 1);
        const timeline = {
            unit: unit === "day" ? "por dia" : unit === "week" ? "por semana" : "por mês",
            max: maxBucket,
            origens: [...origemCount.entries()].sort((a, b) => b[1] - a[1]).map(([k, n]) => ({
                key: k, label: (ORIGENS[k] || ORIGENS.false).label, color: (ORIGENS[k] || ORIGENS.false).color, count: n,
            })),
            bars: buckets.map((b, i) => ({
                key: i,
                label: b.start.setLocale("pt-BR").toFormat(labelFmt),
                showLabel: buckets.length <= 8 || i % Math.ceil(buckets.length / 8) === 0,
                total: b.total,
                title: `${b.start.toFormat("dd/MM")}${unit !== "day" ? " – " + b.end.toFormat("dd/MM") : ""}: ${b.total} sinal(is), ${b.pontos} pts`,
                segs: Object.entries(b.byOrigem).map(([o, n]) => ({
                    key: o, height: (n * 100) / maxBucket, color: (ORIGENS[o] || ORIGENS.false).color,
                })),
            })),
        };

        // ---------- últimos sinais de intenção
        const feed = intencao.slice(0, 8).map((s) => ({
            ...s,
            quando: s.dt.setLocale("pt-BR").toFormat("dd/MM HH:mm"),
            tipoLabel: tipoLabel(s.tipoKey),
            pessoa: (s.x_name || "").split(/\s+[–-]\s+/).slice(1).join(" – "),
            origem: ORIGENS[s.x_origem || "false"] || ORIGENS.false,
        }));

        // ---------- jornada: funil, temperatura, prontidão
        const stageCount = new Map();
        for (const l of leads) {
            const id = l.stage_id && l.stage_id[0];
            stageCount.set(id, (stageCount.get(id) || 0) + 1);
        }
        const maxStage = Math.max(1, ...stageCount.values());
        const funil = raw.stages.map((s) => ({
            id: s.id, name: s.name, count: stageCount.get(s.id) || 0,
            width: pct(stageCount.get(s.id) || 0, maxStage),
            share: pct(stageCount.get(s.id) || 0, leads.length),
            zero: !stageCount.get(s.id),
            novas: novas.filter((l) => l.stage_id && l.stage_id[0] === s.id).length,
        }));
        const faixas = FAIXAS.map((f) => ({ ...f, count: leads.filter((l) => (l.x_abm_faixa || "fria") === f.key).length }));
        const cadencia = Object.entries(CADENCIA)
            .map(([k, v]) => ({ key: k, ...v, count: leads.filter((l) => String(l.x_abm_cadencia_status) === k).length }))
            .filter((c) => c.count);
        const ativas = leads.filter((l) => !ENCERRADAS.includes(stageName(l)));
        const prontidao = [
            {
                key: "decisor", label: "Comitê com decisor mapeado",
                n: ativas.filter((l) => l.x_abm_comite_decisores).length, de: ativas.length,
            },
            {
                key: "comite", label: "Comitê mapeado (alguma pessoa)",
                n: ativas.filter((l) => l.x_abm_comite_total).length, de: ativas.length,
            },
            {
                key: "cadencia", label: "Engajadas/quentes em cadência ativa",
                n: aquecidas.filter((l) => l.x_abm_cadencia_status === "ativa").length, de: aquecidas.length,
            },
        ].map((p) => ({ ...p, pct: pct(p.n, p.de) }));

        // ---------- tabela de contas
        const ultimoInt = new Map();
        const intPeriodo = new Map();
        for (const s of intAll) {
            const id = s.x_lead_id[0];
            if (!ultimoInt.has(id)) ultimoInt.set(id, s); // intAll vem em ordem decrescente de data
        }
        for (const s of intencao) {
            const r = intPeriodo.get(s.x_lead_id[0]) || { n: 0, pts: 0 };
            r.n += 1;
            r.pts += s.x_pontos || 0;
            intPeriodo.set(s.x_lead_id[0], r);
        }
        const linhas = leads.map((l) => {
            const ult = ultimoInt.get(l.id);
            const dias = ult ? Math.floor(today.diff(ult.dt.startOf("day"), "days").days) : null;
            const ip = intPeriodo.get(l.id) || { n: 0, pts: 0 };
            const faixa = FAIXAS.find((f) => f.key === (l.x_abm_faixa || "fria"));
            return {
                id: l.id,
                lead: l,
                nova: novasIds.has(l.id),
                stage: stageName(l),
                faixa,
                score: l.x_abm_score || 0,
                scorePct: Math.min(100, Math.round(((l.x_abm_score || 0) * 100) / SCORE_MAX)),
                intN: ip.n,
                intPts: ip.pts,
                ultimo: ult ? tipoLabel(ult.tipoKey) : null,
                ultimoQuando: dias === null ? "" : dias === 0 ? "hoje" : dias === 1 ? "ontem" : `há ${dias}d`,
                ultimoTitulo: ult ? `${ult.x_name || ""} · ${ult.dt.toFormat("dd/MM/yyyy")}` : "Nenhum sinal de intenção registrado",
                midia: midiaInfo(l),
                decisores: l.x_abm_comite_decisores || 0,
                comite: l.x_abm_comite_total || 0,
                cadencia: CADENCIA[l.x_abm_cadencia_status] || CADENCIA.false,
            };
        });
        const sorters = {
            score: (a, b) => b.score - a.score || b.intPts - a.intPts,
            intencao: (a, b) => b.intPts - a.intPts || b.intN - a.intN || b.score - a.score,
            midia: (a, b) => (b.midia.freq ?? -1) - (a.midia.freq ?? -1),
            nome: (a, b) => a.lead.name.localeCompare(b.lead.name),
        };
        const contas = linhas.sort(sorters[this.state.sort] || sorters.score);

        return {
            kpis, tipos, timeline, feed, funil, faixas, cadencia, prontidao, contas,
            novas: novas.length, scoreMedio,
            totalLeads: leads.length, totalIntencao: intencao.length,
            donutFaixas: this._donut(faixas),
            loadedAt: raw.loadedAt.toFormat("HH:mm"),
        };
    }

    _donut(items) {
        const total = items.reduce((t, i) => t + i.count, 0);
        let acc = 0;
        return {
            total,
            segs: items.filter((i) => i.count).map((i) => {
                const len = (i.count * 100) / (total || 1);
                const seg = { key: i.key, color: i.color, dash: `${len} ${100 - len}`, offset: 25 - acc };
                acc += len;
                return seg;
            }),
        };
    }

    // ---------------------------------------------------------- navegação
    _rangeDomain(field, isDate) {
        const { start, end } = this.period;
        const fmt = (d) => (isDate ? d.toISODate() : toUtcSql(d));
        const dom = [[field, "<=", fmt(end)]];
        if (start) dom.push([field, ">=", fmt(start)]);
        return dom;
    }

    _tierDomain(prefix = "") {
        return this.state.tier === "all" ? [] : [[`${prefix}x_abm_tier`, "=", this.state.tier]];
    }

    get _leadDomain() {
        return [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ...this._tierDomain()];
    }

    openLead(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "crm.lead",
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }

    openList(name, model, domain, views = [[false, "list"], [false, "form"]], context = {}) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name,
            res_model: model,
            domain,
            views,
            context,
            target: "current",
        });
    }

    openContas(name, domain) {
        this.openList(name, "crm.lead", [...this._leadDomain, ...domain], [[false, "list"], [false, "kanban"], [false, "form"]]);
    }

    openKpi(kind) {
        const sinalBase = [["x_lead_id.team_id", "=", TEAM_ID], ...this._tierDomain("x_lead_id."), ...this._rangeDomain("x_data")];
        const intencao = [...sinalBase, ["x_tipo", "!=", LI_RELATORIO]];
        if (kind === "contas") {
            this.openContas("Contas ABM", []);
        } else if (kind === "novas") {
            this.openContas(`Novas contas · ${this.periodLabel}`, this._rangeDomain("create_date"));
        } else if (kind === "cobertura") {
            this.openList(`Sinais que pontuaram · ${this.periodLabel}`, "x_abm_sinal", [...sinalBase, ["x_pontos", ">", 0]]);
        } else if (kind === "intencao") {
            this.openList(`Sinais de intenção · ${this.periodLabel}`, "x_abm_sinal", intencao);
        } else if (kind === "respostas") {
            this.openList(`Respostas · ${this.periodLabel}`, "x_abm_sinal", [...sinalBase, ["x_tipo", "in", [...TIPOS_RESPOSTA]]]);
        } else if (kind === "aquecidas") {
            this.openContas("Contas engajadas ou quentes", [["x_abm_faixa", "in", ["engajada", "quente"]]]);
        }
    }

    openTipo(t) {
        const dom = [["x_lead_id.team_id", "=", TEAM_ID], ...this._tierDomain("x_lead_id."), ...this._rangeDomain("x_data"),
            ["x_tipo", "=", t.tipo]];
        if (t.nome) dom.push(["x_name", "=like", `${t.nome}%`]);
        this.openList(`${t.label} · ${this.periodLabel}`, "x_abm_sinal", dom);
    }

    openStage(stageId) {
        this.openContas("Contas ABM", [["stage_id", "=", stageId]]);
    }

    openFaixa(faixa) {
        this.openContas(`Contas ${faixa}`, [["x_abm_faixa", "=", faixa]]);
    }
}

registry.category("actions").add("abm_setima_dashboard", AbmSetimaDashboard);
