/** @odoo-module **/
// Dashboard do Inbound Sétima (CRM / Inbound Sétima / Dashboard).
// Resultado (funil, campanhas, conjuntos, criativos) e trabalho do time (notas e atividades)
// lidos ao vivo de crm.lead, mail.message e mail.activity, com a sessão do usuário.

import { Component, markup, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

const TEAM_ID = 16; // crm.team "Inbound Sétima"

// Resultado comercial atribuído ao inbound, independente do pipeline onde o negócio está.
// Só os contratos listados aqui somam receita; a data é a do fechamento do contrato.
const CONTRATOS = [
    { id: 15317, fechado: "2026-03-16" }, // 25/0172 - Hyundai - Experiência Interativa 3D (Pipeline Sétima)
];
// Oportunidades em aberto relacionadas às empresas desses contratos.
const EMPRESAS_RELACIONADAS = ["hyundai"];

const PRESETS = [
    { key: "month", label: "Este mês" },
    { key: "prev_month", label: "Mês anterior" },
    { key: "7d", label: "7 dias" },
    { key: "30d", label: "30 dias" },
    { key: "90d", label: "90 dias" },
    { key: "quarter", label: "Trimestre" },
    { key: "year", label: "Este ano" },
    { key: "all", label: "Tudo" },
    { key: "custom", label: "Personalizado" },
];

const DIMENSOES = [
    { key: "campanha", label: "Campanha", icon: "fa-bullhorn" },
    { key: "conjunto", label: "Conjunto de anúncios", icon: "fa-users" },
    { key: "criativo", label: "Criativo", icon: "fa-picture-o" },
    { key: "plataforma", label: "Plataforma", icon: "fa-instagram" },
    { key: "etapa", label: "Etapa atual", icon: "fa-filter" },
];

// Ordem importa: a primeira regra que casar define o tipo da ação registrada.
const TIPOS_ACAO = [
    { key: "reuniao", label: "Reunião / agendamento", color: "#8b5cf6", icon: "fa-handshake-o", re: /reuni|agend|marcar|marcarmos|marcamos|invite|meet\b/ },
    { key: "email", label: "E-mail", color: "#f59e0b", icon: "fa-envelope-o", re: /e-?mail/ },
    { key: "whatsapp", label: "WhatsApp / DataCrazy", color: "#22c55e", icon: "fa-whatsapp", re: /datacrazy|whats|wpp|zap|mensagem/ },
    { key: "ligacao", label: "Ligação", color: "#0ea5e9", icon: "fa-phone", re: /liga[çc]|ligu|telefon|atend/ },
    { key: "pesquisa", label: "Pesquisa / qualificação", color: "#6366f1", icon: "fa-search", re: /site|cnpj|linkedin|capital social|pesquis|qualific|icp/ },
    { key: "outro", label: "Outros registros", color: "#94a3b8", icon: "fa-sticky-note-o", re: /.*/ },
];
const TIPO_POR_CATEGORIA = { phonecall: "ligacao", meeting: "reuniao", email: "email" };
const TENTATIVA = /tentativa|sem contato|n[ãa]o atend|sem resposta|inv[áa]lid/;

const STAGE_COLORS = ["#93c5fd", "#60a5fa", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7", "#14b8a6"];
const CAMPAIGN_COLORS = ["#0a66c2", "#f59e0b", "#10b981", "#ec4899", "#8b5cf6", "#14b8a6", "#ef4444", "#64748b"];

const LEAD_FIELDS = [
    "name", "partner_name", "contact_name", "stage_id", "won_status", "active", "create_date",
    "x_pipedrive_add_time", "date_closed", "lost_reason_id", "campaign_id", "source_id",
    "x_meta_conjunto", "x_meta_anuncio", "user_id", "tag_ids",
];

const fromUtcSql = (s) => (s ? DateTime.fromSQL(s, { zone: "utc" }).toLocal() : null);
const fromDate = (s) => (s ? DateTime.fromISO(s) : null);
const pct = (a, b) => (b ? Math.round((a * 1000) / b) / 10 : 0);
const fmtPct = (v) => `${v.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
const esc = (s) => String(s ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const strip = (html) => {
    const div = document.createElement("div");
    div.innerHTML = html || "";
    return (div.textContent || "").replace(/\s+/g, " ").trim();
};

export class InboundSetimaDashboard extends Component {
    static template = "inbound_setima.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.presets = PRESETS;
        this.dimensoes = DIMENSOES;
        this.tiposAcao = TIPOS_ACAO;
        this.markup = markup;
        this.state = useState({
            preset: "month",
            from: "",
            to: "",
            dim: "campanha",
            logTipo: "all",
            logLimit: 40,
            loading: true,
            error: null,
            raw: null,
        });
        this._setPresetDates("month");
        onWillStart(() => this.load());
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
        else if (key === "quarter") from = today.startOf("quarter");
        else if (key === "year") from = today.startOf("year");
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
            if (this.state.preset === "month" || this.state.preset === "prev_month") {
                prevStart = start.minus({ months: 1 });
                prevEnd = start.minus({ milliseconds: 1 });
            } else {
                const days = Math.round(end.diff(start, "days").days);
                prevEnd = start.minus({ milliseconds: 1 });
                prevStart = start.minus({ days });
            }
        }
        return { start, end, prevStart, prevEnd };
    }

    get periodLabel() {
        const { start, end } = this.period;
        const f = (d) => d.toFormat("dd/MM/yyyy");
        return start ? `${f(start)} – ${f(end)}` : `Todo o histórico até ${f(end)}`;
    }

    onPreset(key) {
        this.state.preset = key;
        this.state.logLimit = 40;
        if (key !== "custom") {
            this._setPresetDates(key);
        }
    }

    onCustomDate(field, ev) {
        this.state[field] = ev.target.value;
        this.state.preset = "custom";
    }

    onDim(key) {
        this.state.dim = key;
    }

    onLogTipo(key) {
        this.state.logTipo = key;
        this.state.logLimit = 40;
    }

    printReport() {
        window.print();
    }

    // -------------------------------------------------------------- dados
    async load() {
        this.state.loading = true;
        this.state.error = null;
        try {
            const [leads, stages, tags] = await Promise.all([
                this.orm.searchRead(
                    "crm.lead",
                    [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ["active", "in", [true, false]]],
                    LEAD_FIELDS,
                    { context: { active_test: false } }
                ),
                this.orm.searchRead("crm.stage", [["team_ids", "in", [TEAM_ID]]], ["name", "sequence"], {
                    order: "sequence, id",
                }),
                this.orm.searchRead("crm.tag", [["name", "ilike", "datacrazy"]], ["name"]),
            ]);
            const ids = leads.map((l) => l.id);
            const [mensagens, atividades] = await Promise.all([
                this.orm.searchRead(
                    "mail.message",
                    [["model", "=", "crm.lead"], ["res_id", "in", ids], ["message_type", "in", ["comment", "email"]]],
                    ["body", "date", "author_id", "res_id", "message_type", "subject"],
                    { order: "date desc" }
                ),
                this.orm.searchRead(
                    "mail.activity",
                    [["res_model", "=", "crm.lead"], ["res_id", "in", ids], ["active", "in", [true, false]]],
                    ["activity_type_id", "activity_category", "summary", "note", "date_deadline", "date_done", "user_id", "res_id", "active", "feedback"],
                    { context: { active_test: false } }
                ),
            ]);
            const relDomain = ["&", ["active", "=", true], ["probability", "<", 100]];
            // várias empresas: OR entre os blocos de cada uma
            for (let i = 1; i < EMPRESAS_RELACIONADAS.length; i++) relDomain.push("|");
            const relOr = EMPRESAS_RELACIONADAS.flatMap((n) => [
                "|", "|", ["name", "ilike", n], ["partner_name", "ilike", n],
                ["partner_id.commercial_partner_id.name", "ilike", n],
            ]);
            const DEAL_FIELDS = ["name", "partner_id", "team_id", "stage_id", "expected_revenue", "company_currency", "user_id", "probability", "won_status"];
            const [contratos, relacionadas] = await Promise.all([
                this.orm.searchRead("crm.lead", [["id", "in", CONTRATOS.map((c) => c.id)]], DEAL_FIELDS, { context: { active_test: false } }),
                this.orm.searchRead("crm.lead", [...relDomain, ...relOr], DEAL_FIELDS, { order: "expected_revenue desc" }),
            ]);
            this.state.raw = {
                leads, stages, mensagens, atividades, contratos, relacionadas,
                tagDataCrazy: new Set(tags.map((t) => t.id)),
                loadedAt: DateTime.local(),
            };
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
        const inRange = (dt, a, b) => dt && (!a || dt >= a) && dt <= b;
        const stages = raw.stages;
        const stageIdx = new Map(stages.map((s, i) => [s.id, i]));
        const nStages = stages.length;

        // ---------- leads: data de entrada = criação no Pipedrive (migrados) ou no Odoo
        const leadsAll = raw.leads.map((l) => {
            const entrada = fromUtcSql(l.x_pipedrive_add_time) || fromUtcSql(l.create_date);
            const won = l.won_status === "won";
            const lost = l.won_status === "lost";
            let idx = l.stage_id ? stageIdx.get(l.stage_id[0]) : undefined;
            if (idx === undefined) idx = 0;
            return {
                ...l, entrada, won, lost,
                reached: won ? nStages : idx, // ganho percorreu todo o funil
                campanha: l.campaign_id ? l.campaign_id[1] : "Sem campanha",
                conjunto: l.x_meta_conjunto || "Sem conjunto",
                criativo: l.x_meta_anuncio || "Sem criativo",
                plataforma: l.source_id ? l.source_id[1] : "Sem origem",
                etapa: won ? "Ganho" : lost ? "Perdido" : (l.stage_id ? l.stage_id[1] : "Sem etapa"),
                datacrazy: (l.tag_ids || []).some((t) => raw.tagDataCrazy.has(t)),
            };
        });
        const byId = new Map(leadsAll.map((l) => [l.id, l]));
        const leads = leadsAll.filter((l) => inRange(l.entrada, start, end));
        const leadsPrev = prevStart ? leadsAll.filter((l) => inRange(l.entrada, prevStart, prevEnd)) : null;

        // ---------- resultado comercial (contratos atribuídos ao inbound)
        const brl = (v) => (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
        const contratos = CONTRATOS.map((c) => {
            const r = (raw.contratos || []).find((x) => x.id === c.id);
            return r && { ...r, fechado: fromDate(c.fechado), valor: r.expected_revenue || 0 };
        }).filter(Boolean);
        const contratosNoPeriodo = contratos.filter((c) => inRange(c.fechado, start, end));
        const receitaTotal = contratos.reduce((t, c) => t + c.valor, 0);
        const receitaPeriodo = contratosNoPeriodo.reduce((t, c) => t + c.valor, 0);
        const relacionadas = (raw.relacionadas || []).filter((r) => !CONTRATOS.some((c) => c.id === r.id));
        const comercial = {
            receitaTotal: brl(receitaTotal),
            receitaPeriodo: brl(receitaPeriodo),
            noPeriodo: contratosNoPeriodo.length,
            contratos: contratos.map((c) => ({
                id: c.id, name: c.name, valor: brl(c.valor),
                fechado: c.fechado.toFormat("dd/MM/yyyy"),
                pipeline: c.team_id ? c.team_id[1] : "",
                empresa: c.partner_id ? c.partner_id[1] : "",
            })),
            abertas: relacionadas.map((r) => ({
                id: r.id, name: r.name, etapa: r.stage_id ? r.stage_id[1] : "",
                pipeline: r.team_id ? r.team_id[1] : "",
                valor: r.expected_revenue ? brl(r.expected_revenue) : "sem valor estimado",
            })),
            abertasValor: brl(relacionadas.reduce((t, r) => t + (r.expected_revenue || 0), 0)),
        };
        // ---------- funil: quantos chegaram a cada etapa (≥) + ganho
        const funnelOf = (arr, extraGanhos = 0) => {
            const steps = stages.map((s, i) => ({
                key: s.id, name: s.name, count: arr.filter((l) => l.reached >= i).length,
            }));
            steps.push({ key: "won", name: "Ganho", count: arr.filter((l) => l.won).length + extraGanhos });
            return steps;
        };
        // contratos fechados no período contam como ganho, mesmo fora deste pipeline
        const fSteps = funnelOf(leads, contratosNoPeriodo.length);
        const total = leads.length;
        const funil = fSteps.map((s, i) => {
            const prev = i ? fSteps[i - 1].count : null;
            return {
                ...s,
                color: s.key === "won" ? "#10b981" : STAGE_COLORS[i % STAGE_COLORS.length],
                width: total ? Math.max(1.5, (s.count * 100) / total) : 0,
                pctTotal: pct(s.count, total),
                pctStep: prev === null ? null : pct(s.count, prev),
                lostHere: s.key === "won" ? 0 : leads.filter((l) => l.lost && l.reached === i).length,
            };
        });
        const idxNamed = (re, fallback) => {
            const i = stages.findIndex((s) => re.test(s.name.toLowerCase()));
            return i >= 0 ? i : fallback;
        };
        const iMql = idxNamed(/mql/, 1);
        const iSql = idxNamed(/^sql/, Math.min(3, nStages - 1));
        const iOpp = idxNamed(/oportunidade/, nStages - 1);
        const countReached = (arr, i) => arr.filter((l) => l.reached >= i).length;

        // ---------- trabalho: notas/e-mails + atividades concluídas
        const classify = (texto) => {
            const t = (texto || "").toLowerCase();
            return TIPOS_ACAO.find((tp) => tp.re.test(t));
        };
        const acoesAll = [];
        for (const m of raw.mensagens) {
            const texto = strip(m.body) || m.subject || "";
            if (!texto) continue;
            const tipo = classify(texto);
            acoesAll.push({
                key: "m" + m.id, dt: fromUtcSql(m.date), leadId: m.res_id, autor: m.author_id ? m.author_id[1] : "—",
                tipo, texto, tentativa: TENTATIVA.test(texto.toLowerCase()), origem: m.message_type === "email" ? "E-mail" : "Nota",
            });
        }
        for (const a of raw.atividades.filter((a) => !a.active && a.date_done)) {
            const tipoKey = TIPO_POR_CATEGORIA[a.activity_category];
            const texto = [a.activity_type_id && a.activity_type_id[1], a.summary, strip(a.feedback)].filter(Boolean).join(" · ");
            acoesAll.push({
                key: "a" + a.id, dt: fromDate(a.date_done), leadId: a.res_id, autor: a.user_id ? a.user_id[1] : "—",
                tipo: TIPOS_ACAO.find((t) => t.key === tipoKey) || classify(texto), texto,
                tentativa: TENTATIVA.test(texto.toLowerCase()), origem: "Atividade",
            });
        }
        acoesAll.sort((a, b) => b.dt - a.dt);
        const acoes = acoesAll.filter((a) => inRange(a.dt, start, end));
        const acoesPrev = prevStart ? acoesAll.filter((a) => inRange(a.dt, prevStart, prevEnd)) : null;
        const leadsTrabalhados = new Set(acoes.map((a) => a.leadId));

        // tempo até o 1º registro (leads do período)
        const primeiro = new Map();
        for (const a of acoesAll) {
            const l = byId.get(a.leadId);
            if (!l || !l.entrada || a.dt < l.entrada) continue;
            if (!primeiro.has(a.leadId) || a.dt < primeiro.get(a.leadId)) primeiro.set(a.leadId, a.dt);
        }
        const horas = leads.filter((l) => primeiro.has(l.id)).map((l) => primeiro.get(l.id).diff(l.entrada, "hours").hours).sort((a, b) => a - b);
        const mediana = horas.length ? horas[Math.floor(horas.length / 2)] : null;
        const em24h = horas.filter((h) => h <= 24).length;
        const fmtHoras = (h) => (h === null ? "—" : h < 1 ? "< 1 h" : h < 48 ? `${Math.round(h)} h` : `${Math.round(h / 24)} d`);

        // ---------- KPIs
        const delta = (cur, prev) => (prev === null || prev === undefined ? null : cur - prev);
        const perdidos = leads.filter((l) => l.lost).length;
        const mql = countReached(leads, iMql);
        const sql = countReached(leads, iSql);
        const opp = countReached(leads, iOpp);
        const ganhos = leads.filter((l) => l.won).length + contratosNoPeriodo.length;
        const kpis = [
            { key: "leads", icon: "fa-user-plus", label: "Leads gerados", value: total,
              sub: `${leads.filter((l) => l.datacrazy).length} enviados ao WhatsApp (DataCrazy)`,
              delta: delta(total, leadsPrev && leadsPrev.length), color: "#0a66c2", click: "leads" },
            { key: "mql", icon: "fa-check", label: `${stages[iMql]?.name || "MQL"}+`, value: mql,
              sub: `${fmtPct(pct(mql, total))} dos leads`, delta: delta(mql, leadsPrev && countReached(leadsPrev, iMql)),
              color: "#3b82f6", click: "mql" },
            { key: "sql", icon: "fa-star", label: `${stages[iSql]?.name || "SQL"}+`, value: sql,
              sub: `${fmtPct(pct(sql, total))} dos leads · ${fmtPct(pct(sql, mql))} dos MQL`,
              delta: delta(sql, leadsPrev && countReached(leadsPrev, iSql)), color: "#6366f1", click: "sql" },
            { key: "opp", icon: "fa-briefcase", label: "Oportunidades", value: opp,
              sub: `${ganhos} ganho(s)${contratosNoPeriodo.length ? ` · ${brl(receitaPeriodo)}` : ""} · ${fmtPct(pct(opp, total))} dos leads`,
              delta: delta(opp, leadsPrev && countReached(leadsPrev, iOpp)), color: "#8b5cf6", click: "opp" },
            { key: "perdidos", icon: "fa-times-circle", label: "Perdidos", value: perdidos,
              sub: `${fmtPct(pct(perdidos, total))} dos leads`, color: "#ef4444", click: "perdidos" },
            { key: "acoes", icon: "fa-bolt", label: "Ações registradas", value: acoes.length,
              sub: `em ${leadsTrabalhados.size} lead(s)`, delta: delta(acoes.length, acoesPrev && acoesPrev.length),
              color: "#10b981", click: "acoes" },
            { key: "sla", icon: "fa-clock-o", label: "Tempo até 1º registro", value: fmtHoras(mediana), raw: true,
              sub: horas.length ? `mediana · ${fmtPct(pct(em24h, horas.length))} em até 24 h` : "sem registros nos leads do período",
              color: "#f59e0b" },
        ];

        // ---------- linha do tempo de leads (empilhada por campanha)
        const firstDt = start || (leadsAll.length ? leadsAll.reduce((m, l) => (l.entrada && l.entrada < m ? l.entrada : m), end) : end);
        const spanDays = Math.max(1, Math.round(end.diff(firstDt, "days").days));
        const unit = spanDays <= 35 ? "day" : spanDays <= 200 ? "week" : "month";
        const campRank = this._rank(leads, (l) => l.campanha);
        const campColor = new Map(campRank.map(([k], i) => [k, i < CAMPAIGN_COLORS.length - 1 ? CAMPAIGN_COLORS[i] : CAMPAIGN_COLORS.at(-1)]));
        const timeline = this._timeline(leads, (l) => l.entrada, (l) => l.campanha, campColor, firstDt, end, unit);
        const legendCamp = campRank.map(([k, n]) => ({ key: k, label: k, count: n, color: campColor.get(k) }));

        // ---------- quebra por dimensão
        const dimKey = this.state.dim;
        const breakdown = this._rank(leads, (l) => l[dimKey]).map(([k, n]) => {
            const arr = leads.filter((l) => l[dimKey] === k);
            return {
                key: k, leads: n, share: pct(n, total),
                steps: fSteps.slice(1).map((s, j) => {
                    const c = s.key === "won" ? arr.filter((l) => l.won).length : countReached(arr, j + 1);
                    return { key: s.key, count: c, pct: pct(c, n) };
                }),
                perdidos: arr.filter((l) => l.lost).length,
                pctPerdidos: pct(arr.filter((l) => l.lost).length, n),
                datacrazy: arr.filter((l) => l.datacrazy).length,
            };
        });
        const maxBreak = Math.max(1, ...breakdown.map((b) => b.leads));
        breakdown.forEach((b) => (b.width = (b.leads * 100) / maxBreak));

        // ---------- situação atual dos leads do período
        const situacao = this._rank(leads, (l) => l.etapa).map(([k, n], i) => ({
            key: k, label: k, count: n,
            color: k === "Perdido" ? "#ef4444" : k === "Ganho" ? "#10b981" : STAGE_COLORS[(stages.findIndex((s) => s.name === k) + STAGE_COLORS.length) % STAGE_COLORS.length],
        }));
        const motivos = this._rank(leads.filter((l) => l.lost), (l) => (l.lost_reason_id ? l.lost_reason_id[1] : "Sem motivo informado"));
        const maxMotivo = Math.max(1, ...motivos.map(([, n]) => n));

        // ---------- trabalho por tipo / pessoa / tempo
        const porTipo = TIPOS_ACAO.map((t) => ({
            ...t, count: acoes.filter((a) => a.tipo.key === t.key).length,
            tentativas: acoes.filter((a) => a.tipo.key === t.key && a.tentativa).length,
        })).filter((t) => t.count);
        const tipoColor = new Map(TIPOS_ACAO.map((t) => [t.key, t.color]));
        const timelineAcoes = this._timeline(acoes, (a) => a.dt, (a) => a.tipo.key, tipoColor, firstDt, end, unit);
        const porPessoa = this._rank(acoes, (a) => a.autor).map(([k, n]) => ({ key: k, count: n, width: (n * 100) / Math.max(1, acoes.length) }));
        const logFiltrado = acoes.filter((a) => this.state.logTipo === "all" || a.tipo.key === this.state.logTipo);
        const log = logFiltrado.slice(0, this.state.logLimit).map((a) => {
            const l = byId.get(a.leadId);
            return {
                ...a, lead: l ? l.name : `#${a.leadId}`, etapa: l ? l.etapa : "",
                quando: a.dt.setLocale("pt-BR").toFormat("dd/MM HH:mm"),
                resumo: a.texto.length > 220 ? a.texto.slice(0, 220) + "…" : a.texto,
            };
        });

        // ---------- resumo executivo (para o relatório do cliente)
        const melhor = (dim) => {
            const rows = this._rank(leads, (l) => l[dim])
                .map(([k, n]) => ({ k, n, mql: countReached(leads.filter((l) => l[dim] === k), iMql) }))
                .filter((r) => r.n >= 3 && !r.k.startsWith("Sem "));
            rows.sort((a, b) => b.mql / b.n - a.mql / a.n || b.n - a.n);
            return rows[0];
        };
        const topCamp = campRank.find(([k]) => k !== "Sem campanha");
        const bestCriativo = melhor("criativo");
        const bestConjunto = melhor("conjunto");
        const resumo = [];
        if (total) {
            const d = delta(total, leadsPrev && leadsPrev.length);
            resumo.push(`Entraram <b>${total} leads</b>${d === null ? "" : ` (${d >= 0 ? "+" : ""}${d} vs. período anterior)`}; <b>${mql}</b> avançaram para ${stages[iMql]?.name || "MQL"} (${fmtPct(pct(mql, total))}) e <b>${sql}</b> chegaram a ${stages[iSql]?.name || "SQL"} (${fmtPct(pct(sql, total))}).`);
            if (topCamp) resumo.push(`A campanha com mais leads foi <b>${esc(topCamp[0])}</b> (${topCamp[1]} leads, ${fmtPct(pct(topCamp[1], total))} do total).`);
            if (bestCriativo) resumo.push(`Melhor criativo em qualificação: <b>${esc(bestCriativo.k)}</b>, com ${fmtPct(pct(bestCriativo.mql, bestCriativo.n))} dos leads virando ${stages[iMql]?.name || "MQL"} (${bestCriativo.n} leads).`);
            if (bestConjunto) resumo.push(`Melhor conjunto de anúncios: <b>${esc(bestConjunto.k)}</b> (${fmtPct(pct(bestConjunto.mql, bestConjunto.n))} de ${stages[iMql]?.name || "MQL"} em ${bestConjunto.n} leads).`);
        } else {
            resumo.push("Nenhum lead entrou no período selecionado.");
        }
        if (acoes.length) {
            const partes = porTipo.filter((t) => t.key !== "outro").map((t) => `${t.count} ${t.label.toLowerCase()}`);
            resumo.push(`O time registrou <b>${acoes.length} ações</b> em ${leadsTrabalhados.size} leads${partes.length ? ` (${partes.join(", ")})` : ""}${mediana !== null ? `; o primeiro contato saiu em ${fmtHoras(mediana)} (mediana)` : ""}.`);
        }
        if (contratos.length) {
            const c = contratos[0];
            resumo.unshift(`Receita gerada pelo inbound: <b>${brl(receitaTotal)}</b> (${contratos.map((x) => `${esc(x.name)}, fechado em ${x.fechado.toFormat("dd/MM/yyyy")}`).join("; ")})${relacionadas.length ? `; ${relacionadas.length} oportunidade(s) em aberto com a mesma empresa` : ""}.`);
        }

        if (perdidos && motivos.length) {
            resumo.push(`${perdidos} lead(s) perdidos; principal motivo: <b>${esc(motivos[0][0])}</b> (${motivos[0][1]}).`);
        }

        return {
            kpis, funil, timeline, legendCamp, breakdown, situacao, total, resumo, comercial,
            stepHeads: fSteps.slice(1).map((s) => s.name),
            donutSituacao: this._donut(situacao),
            motivos: motivos.map(([k, n]) => ({ key: k, count: n, width: (n * 100) / maxMotivo })),
            porTipo, timelineAcoes, porPessoa, log, logTotal: logFiltrado.length, totalAcoes: acoes.length,
            dimLabel: DIMENSOES.find((d) => d.key === dimKey).label,
        };
    }

    _rank(items, keyFn) {
        const m = new Map();
        for (const it of items) {
            const k = keyFn(it);
            m.set(k, (m.get(k) || 0) + 1);
        }
        return [...m.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0])));
    }

    _timeline(items, dtFn, keyFn, colorMap, from, end, unit) {
        const buckets = [];
        let cur = from.startOf(unit);
        while (cur <= end && buckets.length < 120) {
            buckets.push({ start: cur, end: cur.endOf(unit), by: {}, total: 0 });
            cur = cur.plus({ [unit + "s"]: 1 });
        }
        for (const it of items) {
            const dt = dtFn(it);
            const b = dt && buckets.find((b) => dt >= b.start && dt <= b.end);
            if (b) {
                const k = keyFn(it);
                b.by[k] = (b.by[k] || 0) + 1;
                b.total += 1;
            }
        }
        const max = Math.max(1, ...buckets.map((b) => b.total));
        const fmt = unit === "month" ? "MMM/yy" : "dd/MM";
        return {
            unit: unit === "day" ? "por dia" : unit === "week" ? "por semana" : "por mês",
            max,
            hasData: buckets.some((b) => b.total),
            bars: buckets.map((b, i) => ({
                key: i,
                label: b.start.setLocale("pt-BR").toFormat(fmt),
                showLabel: buckets.length <= 7 || i % Math.ceil(buckets.length / 7) === 0,
                total: b.total,
                title: `${b.start.toFormat("dd/MM")}${unit !== "day" ? " – " + b.end.toFormat("dd/MM") : ""}: ${b.total}`,
                segs: Object.entries(b.by).map(([k, n]) => ({ key: k, height: (n * 100) / max, color: colorMap.get(k) || "#94a3b8" })),
            })),
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
    openLeadIds(title, ids) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: "crm.lead",
            domain: [["id", "in", ids]],
            views: [[false, "list"], [false, "kanban"], [false, "form"]],
            context: { active_test: false },
            target: "current",
        });
    }

    openLead(id) {
        this.actionService.doAction({
            type: "ir.actions.act_window", res_model: "crm.lead", res_id: id,
            views: [[false, "form"]], target: "current", context: { active_test: false },
        });
    }

    _leadsOfPeriod(filterFn) {
        const { start, end } = this.period;
        const stageIdx = new Map(this.state.raw.stages.map((s, i) => [s.id, i]));
        return this.state.raw.leads.filter((l) => {
            const e = fromUtcSql(l.x_pipedrive_add_time) || fromUtcSql(l.create_date);
            return e && (!start || e >= start) && e <= end && filterFn(l, stageIdx);
        }).map((l) => l.id);
    }

    openKpi(kind) {
        const stages = this.state.raw.stages;
        const reachedAtLeast = (re, fb) => {
            let i = stages.findIndex((s) => re.test(s.name.toLowerCase()));
            if (i < 0) i = fb;
            return (l, idx) => l.won_status === "won" || (idx.get(l.stage_id && l.stage_id[0]) ?? 0) >= i;
        };
        if (kind === "leads") this.openLeadIds(`Leads · ${this.periodLabel}`, this._leadsOfPeriod(() => true));
        else if (kind === "mql") this.openLeadIds(`MQL+ · ${this.periodLabel}`, this._leadsOfPeriod(reachedAtLeast(/mql/, 1)));
        else if (kind === "sql") this.openLeadIds(`SQL+ · ${this.periodLabel}`, this._leadsOfPeriod(reachedAtLeast(/^sql/, 3)));
        else if (kind === "opp") this.openLeadIds(`Oportunidades · ${this.periodLabel}`, this._leadsOfPeriod(reachedAtLeast(/oportunidade/, stages.length - 1)));
        else if (kind === "perdidos") this.openLeadIds(`Perdidos · ${this.periodLabel}`, this._leadsOfPeriod((l) => l.won_status === "lost"));
        else if (kind === "acoes") this.state.logTipo = "all";
    }

    openStep(i) {
        const stages = this.state.raw.stages;
        const isWon = i >= stages.length;
        this.openLeadIds(
            `${isWon ? "Ganhos" : stages[i].name + "+"} · ${this.periodLabel}`,
            this._leadsOfPeriod((l, idx) => l.won_status === "won" || (!isWon && (idx.get(l.stage_id && l.stage_id[0]) ?? 0) >= i))
        );
    }

    openDim(value) {
        const dim = this.state.dim;
        const { start, end } = this.period;
        const ids = this.state.raw.leads.filter((l) => {
            const e = fromUtcSql(l.x_pipedrive_add_time) || fromUtcSql(l.create_date);
            if (!e || (start && e < start) || e > end) return false;
            const v = {
                campanha: l.campaign_id ? l.campaign_id[1] : "Sem campanha",
                conjunto: l.x_meta_conjunto || "Sem conjunto",
                criativo: l.x_meta_anuncio || "Sem criativo",
                plataforma: l.source_id ? l.source_id[1] : "Sem origem",
                etapa: l.won_status === "won" ? "Ganho" : l.won_status === "lost" ? "Perdido" : (l.stage_id ? l.stage_id[1] : "Sem etapa"),
            }[dim];
            return v === value;
        }).map((l) => l.id);
        this.openLeadIds(`${value} · ${this.periodLabel}`, ids);
    }
}

registry.category("actions").add("inbound_setima_dashboard", InboundSetimaDashboard);
