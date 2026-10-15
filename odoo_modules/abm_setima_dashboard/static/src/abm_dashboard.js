/** @odoo-module **/
// Dashboard estratégico do ABM Sétima (CRM / ABM Setima / Dashboard).
// Lê ao vivo crm.lead (equipe ABM Setima), x_abm_sinal e mail.activity (tipos "ABM · …")
// com a sessão do próprio usuário: nada é copiado nem gravado.

import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

const TEAM_ID = 20; // crm.team "ABM Setima" (ir.config_parameter abm.team_id)
const ACTIVITY_DOMAIN = [["activity_type_id.name", "=like", "ABM · %"]];
const SCORE_MAX = 90; // mesma régua do campo x_abm_score_pct

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
    { key: "fria", label: "Fria", hint: "score < 30", color: "#3b82f6" },
    { key: "engajada", label: "Engajada", hint: "score 30–59", color: "#f59e0b" },
    { key: "quente", label: "Quente", hint: "score ≥ 60", color: "#ef4444" },
];

const ORIGENS = {
    linkedin_ads: { label: "LinkedIn Ads", color: "#0a66c2" },
    linkedin_manual: { label: "LinkedIn (manual)", color: "#60a5fa" },
    apollo_manual: { label: "Apollo", color: "#8b5cf6" },
    site: { label: "Site", color: "#10b981" },
    email: { label: "E-mail", color: "#f59e0b" },
    whatsapp: { label: "WhatsApp", color: "#22c55e" },
    formulario: { label: "Formulário", color: "#ec4899" },
    ligacao: { label: "Ligação", color: "#14b8a6" },
    false: { label: "Sem origem", color: "#94a3b8" },
};

const TIPOS = {
    li_ads_relatorio: "LinkedIn Ads · relatório 30d",
    li_impressoes_semana: "LinkedIn · 50+ impressões",
    li_cliques: "LinkedIn · cliques",
    li_reacao_post: "Reagiu a post do especialista",
    li_conexao_aceita: "Conexão aceita",
    li_seguiu_pagina: "Seguiu a página",
    li_dm_resposta: "Respondeu DM",
    visita_dominio: "Visita ao site",
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
    "resposta_a_classificar", "resposta_automatica", "resposta_negativa",
    "resposta_neutra", "resposta_positiva", "email_resposta", "li_dm_resposta",
]);

const CADENCIA = {
    nao_iniciada: { label: "Não iniciada", color: "#94a3b8" },
    ativa: { label: "Ativa", color: "#10b981" },
    pausada: { label: "Pausada", color: "#f59e0b" },
    concluida: { label: "Concluída", color: "#6366f1" },
    false: { label: "Sem status", color: "#cbd5e1" },
};

const STATUS_ATIV = [
    { key: "done", label: "Concluídas", color: "#10b981" },
    { key: "planned", label: "No prazo", color: "#3b82f6" },
    { key: "today", label: "Hoje", color: "#f59e0b" },
    { key: "overdue", label: "Atrasadas", color: "#ef4444" },
];

const STAGE_COLORS = [
    "#cbd5e1", "#93c5fd", "#60a5fa", "#3b82f6", "#6366f1",
    "#8b5cf6", "#a855f7", "#14b8a6", "#94a3b8", "#10b981", "#64748b",
];

const LEAD_FIELDS = [
    "name", "stage_id", "user_id", "create_date", "x_abm_score", "x_abm_tier", "x_abm_faixa",
    "x_abm_cadencia_status", "x_abm_preparacao", "x_abm_trilha", "x_abm_ultimo_sinal_data",
    "x_abm_comite_total", "x_abm_comite_decisores", "x_abm_comite_conectados",
    "x_abm_comite_emails_ok", "x_abm_exposicao", "x_abm_onda",
];

const SQL = "yyyy-MM-dd HH:mm:ss";
const toUtcSql = (dt) => dt.toUTC().toFormat(SQL);
const fromUtcSql = (s) => (s ? DateTime.fromSQL(s, { zone: "utc" }).toLocal() : null);
const fromDate = (s) => (s ? DateTime.fromISO(s) : null);
const fmtInt = (n) => (n || 0).toLocaleString("pt-BR");
const pct = (a, b) => (b ? Math.round((a * 100) / b) : 0);

export class AbmSetimaDashboard extends Component {
    static template = "abm_setima_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.presets = PRESETS;
        this.faixas = FAIXAS;
        this.statusAtiv = STATUS_ATIV;
        this.state = useState({
            preset: "30d",
            from: "",
            to: "",
            tier: "all",
            sort: "score",
            loading: true,
            error: null,
            raw: null,
        });
        this._setPresetDates("30d");
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

    async onPreset(key) {
        this.state.preset = key;
        if (key !== "custom") {
            this._setPresetDates(key);
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

    onTier(ev) {
        this.state.tier = ev.target.value;
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
            const sinalDomain = [["x_lead_id.team_id", "=", TEAM_ID], ["x_data", "<=", toUtcSql(end)]];
            const doneDomain = [
                ...ACTIVITY_DOMAIN, ["active", "=", false], ["date_done", "<=", end.toISODate()],
            ];
            if (lower) {
                sinalDomain.push(["x_data", ">=", toUtcSql(lower)]);
                doneDomain.push(["date_done", ">=", lower.toISODate()]);
            }
            const [leads, sinais, abertas, concluidas] = await Promise.all([
                this.orm.searchRead(
                    "crm.lead",
                    [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"]],
                    LEAD_FIELDS,
                    { order: "x_abm_score desc, name" }
                ),
                this.orm.searchRead(
                    "x_abm_sinal",
                    sinalDomain,
                    ["x_name", "x_data", "x_lead_id", "x_origem", "x_tipo", "x_pontos", "x_ativo", "x_partner_id"],
                    { order: "x_data desc" }
                ),
                this.orm.searchRead(
                    "mail.activity",
                    ACTIVITY_DOMAIN,
                    ["activity_type_id", "res_model", "res_id", "res_name", "date_deadline", "user_id", "summary"],
                    { order: "date_deadline asc" }
                ),
                this.orm.searchRead(
                    "mail.activity",
                    doneDomain,
                    ["activity_type_id", "res_model", "res_id", "res_name", "date_deadline", "date_done", "user_id"],
                    { context: { active_test: false } }
                ),
            ]);
            const stageIds = [...new Set(leads.map((l) => l.stage_id && l.stage_id[0]).filter(Boolean))];
            const stages = await this.orm.searchRead(
                "crm.stage",
                ["|", ["team_ids", "in", [TEAM_ID]], ["id", "in", stageIds]],
                ["name", "sequence"],
                { order: "sequence, id" }
            );
            this.state.raw = { leads, sinais, abertas, concluidas, stages, loadedAt: DateTime.local() };
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
        const leads = raw.leads.filter((l) => tier === "all" || l.x_abm_tier === tier);
        const leadIds = new Set(leads.map((l) => l.id));
        const inRange = (dt, a, b) => dt && (!a || dt >= a) && dt <= b;

        const sinaisAll = raw.sinais
            .filter((s) => s.x_lead_id && leadIds.has(s.x_lead_id[0]))
            .map((s) => ({ ...s, dt: fromUtcSql(s.x_data) }));
        const sinais = sinaisAll.filter((s) => inRange(s.dt, start, end));
        const sinaisPrev = prevStart ? sinaisAll.filter((s) => inRange(s.dt, prevStart, prevEnd)) : null;

        const isAbmRecord = (a) => (a.res_model === "crm.lead" ? leadIds.has(a.res_id) : tier === "all");
        const today = DateTime.local().startOf("day");
        const abertas = raw.abertas.filter(isAbmRecord).map((a) => {
            const dl = fromDate(a.date_deadline);
            const status = dl < today ? "overdue" : dl.equals(today) ? "today" : "planned";
            return { ...a, dl, status };
        });
        const concluidasAll = raw.concluidas.filter(isAbmRecord).map((a) => ({ ...a, dd: fromDate(a.date_done) }));
        const concluidas = concluidasAll.filter((a) => inRange(a.dd, start && start.startOf("day"), end));
        const concluidasPrev = prevStart
            ? concluidasAll.filter((a) => inRange(a.dd, prevStart.startOf("day"), prevEnd))
            : null;
        const onTime = concluidas.filter((a) => a.date_done <= a.date_deadline).length;

        // ---------- por conta
        const byLead = new Map(leads.map((l) => [l.id, {
            lead: l, sinais: 0, pontos: 0, abertas: 0, atrasadas: 0, concluidas: 0, proxima: null,
        }]));
        for (const s of sinais) {
            const r = byLead.get(s.x_lead_id[0]);
            r.sinais += 1;
            r.pontos += s.x_pontos || 0;
        }
        for (const a of abertas) {
            const r = a.res_model === "crm.lead" && byLead.get(a.res_id);
            if (r) {
                r.abertas += 1;
                if (a.status === "overdue") r.atrasadas += 1;
                if (!r.proxima || a.dl < r.proxima.dl) r.proxima = a;
            }
        }
        for (const a of concluidas) {
            const r = a.res_model === "crm.lead" && byLead.get(a.res_id);
            if (r) r.concluidas += 1;
        }

        // ---------- KPIs
        const score = leads.map((l) => l.x_abm_score || 0);
        const contasComSinal = new Set(sinais.map((s) => s.x_lead_id[0])).size;
        const pontos = sinais.reduce((t, s) => t + (s.x_pontos || 0), 0);
        const respostas = sinais.filter((s) => TIPOS_RESPOSTA.has(s.x_tipo)).length;
        const bracos = sinais.filter((s) => s.x_tipo === "resposta_positiva").length;
        const delta = (cur, prev) => (prev === null || prev === undefined ? null : cur - prev);
        const kpis = [
            {
                key: "contas", icon: "fa-building", label: "Contas no programa", value: leads.length,
                sub: `${leads.filter((l) => l.x_abm_cadencia_status === "ativa").length} em cadência ativa`,
                color: "#6366f1", click: "contas",
            },
            {
                key: "ativadas", icon: "fa-bolt", label: "Contas com sinal", value: contasComSinal,
                sub: `${pct(contasComSinal, leads.length)}% da base no período`,
                delta: delta(contasComSinal, sinaisPrev && new Set(sinaisPrev.map((s) => s.x_lead_id[0])).size),
                color: "#0a66c2", click: "sinais",
            },
            {
                key: "sinais", icon: "fa-signal", label: "Sinais captados", value: sinais.length,
                sub: `${fmtInt(pontos)} pontos gerados`,
                delta: delta(sinais.length, sinaisPrev && sinaisPrev.length),
                color: "#0ea5e9", click: "sinais",
            },
            {
                key: "respostas", icon: "fa-reply", label: "Respostas", value: respostas,
                sub: `${bracos} braço(s) erguido(s)`,
                delta: delta(respostas, sinaisPrev && sinaisPrev.filter((s) => TIPOS_RESPOSTA.has(s.x_tipo)).length),
                color: "#f59e0b", click: "respostas",
            },
            {
                key: "score", icon: "fa-thermometer-half", label: "Score médio",
                value: score.length ? Math.round(score.reduce((a, b) => a + b, 0) / score.length) : 0,
                sub: `${leads.filter((l) => l.x_abm_faixa === "engajada").length} engajadas · ${leads.filter((l) => l.x_abm_faixa === "quente").length} quentes`,
                color: "#ef4444", click: "contas",
            },
            {
                key: "feitas", icon: "fa-check-circle", label: "Atividades concluídas", value: concluidas.length,
                sub: concluidas.length ? `${pct(onTime, concluidas.length)}% no prazo` : "nenhuma no período",
                delta: delta(concluidas.length, concluidasPrev && concluidasPrev.length),
                color: "#10b981", click: "concluidas",
            },
            {
                key: "atrasadas", icon: "fa-exclamation-triangle", label: "Atividades atrasadas",
                value: abertas.filter((a) => a.status === "overdue").length,
                sub: `${abertas.length} abertas · ${abertas.filter((a) => a.status === "today").length} para hoje`,
                color: "#dc2626", click: "atrasadas", danger: true,
            },
        ];

        // ---------- funil por estágio
        const stageCount = new Map();
        for (const l of leads) {
            const id = l.stage_id && l.stage_id[0];
            stageCount.set(id, (stageCount.get(id) || 0) + 1);
        }
        const maxStage = Math.max(1, ...stageCount.values());
        const funil = raw.stages.map((s, i) => ({
            id: s.id, name: s.name, count: stageCount.get(s.id) || 0,
            width: Math.max(2, pct(stageCount.get(s.id) || 0, maxStage)),
            share: pct(stageCount.get(s.id) || 0, leads.length),
            color: STAGE_COLORS[i % STAGE_COLORS.length],
        }));

        // ---------- linha do tempo de sinais (empilhado por origem)
        const firstDt = start || (sinais.length ? sinais[sinais.length - 1].dt.startOf("day") : end.startOf("day"));
        const spanDays = Math.max(1, Math.round(end.diff(firstDt, "days").days));
        const unit = spanDays <= 35 ? "day" : spanDays <= 180 ? "week" : "month";
        const buckets = [];
        let cur = firstDt.startOf(unit);
        while (cur <= end && buckets.length < 120) {
            buckets.push({ start: cur, end: cur.endOf(unit), byOrigem: {}, total: 0, pontos: 0 });
            cur = cur.plus({ [unit + "s"]: 1 });
        }
        for (const s of sinais) {
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
        const timeline = {
            unit: unit === "day" ? "por dia" : unit === "week" ? "por semana" : "por mês",
            max: maxBucket,
            bars: buckets.map((b, i) => ({
                key: i,
                label: b.start.setLocale("pt-BR").toFormat(labelFmt),
                showLabel: buckets.length <= 7 || i % Math.ceil(buckets.length / 7) === 0,
                total: b.total,
                title: `${b.start.toFormat("dd/MM")}${unit !== "day" ? " – " + b.end.toFormat("dd/MM") : ""}: ${b.total} sinal(is), ${b.pontos} pts`,
                segs: Object.entries(b.byOrigem).map(([o, n]) => ({
                    key: o, height: (n * 100) / maxBucket, color: (ORIGENS[o] || ORIGENS.false).color,
                })),
            })),
        };

        // ---------- composição dos sinais
        const groupCount = (items, keyFn) => {
            const m = new Map();
            for (const it of items) {
                const k = keyFn(it);
                const r = m.get(k) || { count: 0, pontos: 0 };
                r.count += 1;
                r.pontos += it.x_pontos || 0;
                m.set(k, r);
            }
            return [...m.entries()].sort((a, b) => b[1].count - a[1].count);
        };
        const origens = groupCount(sinais, (s) => s.x_origem || "false").map(([k, v]) => ({
            key: k, label: (ORIGENS[k] || ORIGENS.false).label, color: (ORIGENS[k] || ORIGENS.false).color, ...v,
        }));
        const maxTipo = Math.max(1, ...groupCount(sinais, (s) => s.x_tipo).map(([, v]) => v.count));
        const tipos = groupCount(sinais, (s) => s.x_tipo).map(([k, v]) => ({
            key: k, label: TIPOS[k] || k || "—", ...v, width: pct(v.count, maxTipo),
            resposta: TIPOS_RESPOSTA.has(k),
        }));

        // ---------- temperatura e cadência
        const faixas = FAIXAS.map((f) => ({ ...f, count: leads.filter((l) => (l.x_abm_faixa || "fria") === f.key).length }));
        const cadencia = Object.entries(CADENCIA)
            .map(([k, v]) => ({ key: k, ...v, count: leads.filter((l) => String(l.x_abm_cadencia_status) === k).length }))
            .filter((c) => c.count);
        const tiers = ["1", "2", "3", false].map((t) => ({
            key: String(t), label: t ? `Tier ${t}` : "Sem tier",
            count: leads.filter((l) => (l.x_abm_tier || false) === t).length,
        })).filter((t) => t.count);

        // ---------- atividades por tipo
        const tipoAtiv = new Map();
        const addAtiv = (a, status) => {
            const name = (a.activity_type_id && a.activity_type_id[1] || "—").replace(/^ABM · /, "");
            const r = tipoAtiv.get(name) || { name, done: 0, planned: 0, today: 0, overdue: 0, total: 0 };
            r[status] += 1;
            r.total += 1;
            tipoAtiv.set(name, r);
        };
        concluidas.forEach((a) => addAtiv(a, "done"));
        abertas.forEach((a) => addAtiv(a, a.status));
        const maxAtiv = Math.max(1, ...[...tipoAtiv.values()].map((r) => r.total));
        const atividadesTipo = [...tipoAtiv.values()]
            .sort((a, b) => b.total - a.total)
            .map((r) => ({
                ...r,
                segs: STATUS_ATIV.filter((s) => r[s.key]).map((s) => ({
                    key: s.key, color: s.color, width: (r[s.key] * 100) / maxAtiv, n: r[s.key],
                })),
            }));
        const statusTotals = STATUS_ATIV.map((s) => ({
            ...s, count: s.key === "done" ? concluidas.length : abertas.filter((a) => a.status === s.key).length,
        }));

        // ---------- agenda: próximos 7 dias úteis
        const agendaEnd = today.plus({ days: 7 });
        const agenda = abertas
            .filter((a) => a.dl <= agendaEnd)
            .slice(0, 12)
            .map((a) => ({
                ...a,
                tipo: (a.activity_type_id && a.activity_type_id[1] || "").replace(/^ABM · /, ""),
                quando: a.status === "overdue"
                    ? `atrasada ${Math.round(today.diff(a.dl, "days").days)}d`
                    : a.status === "today" ? "hoje" : a.dl.setLocale("pt-BR").toFormat("ccc dd/MM"),
            }));

        // ---------- alertas estratégicos
        const semSinalDias = (l) => {
            const u = fromUtcSql(l.x_abm_ultimo_sinal_data);
            return u ? Math.floor(today.diff(u.startOf("day"), "days").days) : null;
        };
        const stageName = (l) => (l.stage_id ? l.stage_id[1] : "");
        const alertas = [
            {
                key: "quente_sem_cadencia", icon: "fa-fire", color: "#ef4444",
                title: "Engajadas/quentes sem cadência ativa",
                hint: "Prioridade: transformar atenção em conversa.",
                items: leads.filter((l) => ["engajada", "quente"].includes(l.x_abm_faixa) && l.x_abm_cadencia_status !== "ativa"
                    && !["Descartada", "Cliente – expansão"].includes(stageName(l))),
            },
            {
                key: "esfriando", icon: "fa-snowflake-o", color: "#3b82f6",
                title: "Sem sinal há 21+ dias",
                hint: "Contas em aquecimento/cadência que pararam de reagir.",
                items: leads.filter((l) => {
                    const n = semSinalDias(l);
                    return ["Aquecendo", "Engajada", "Em cadência"].includes(stageName(l)) && (n === null || n >= 21);
                }),
            },
            {
                key: "sem_decisor", icon: "fa-user-times", color: "#f59e0b",
                title: "Comitê sem decisor mapeado",
                hint: "Sem decisor a cadência não chega a quem assina.",
                items: leads.filter((l) => !l.x_abm_comite_decisores && !["Descartada", "Cliente – expansão"].includes(stageName(l))),
            },
            {
                key: "atrasadas", icon: "fa-clock-o", color: "#dc2626",
                title: "Contas com atividade atrasada",
                hint: "Execução da cadência travada.",
                items: [...byLead.values()].filter((r) => r.atrasadas).map((r) => r.lead),
            },
        ].map((a) => ({ ...a, count: a.items.length, top: a.items.slice(0, 5) }));

        // ---------- tabela de contas
        const sorters = {
            score: (a, b) => (b.lead.x_abm_score || 0) - (a.lead.x_abm_score || 0) || b.pontos - a.pontos,
            sinais: (a, b) => b.pontos - a.pontos || b.sinais - a.sinais,
            exposicao: (a, b) => (b.lead.x_abm_exposicao || 0) - (a.lead.x_abm_exposicao || 0),
            atividades: (a, b) => b.atrasadas - a.atrasadas || b.abertas - a.abertas,
            nome: (a, b) => a.lead.name.localeCompare(b.lead.name),
        };
        const contas = [...byLead.values()].sort(sorters[this.state.sort] || sorters.score).map((r) => {
            const l = r.lead;
            const faixa = FAIXAS.find((f) => f.key === (l.x_abm_faixa || "fria"));
            const dias = semSinalDias(l);
            return {
                ...r,
                id: l.id,
                scorePct: Math.min(100, Math.round(((l.x_abm_score || 0) * 100) / SCORE_MAX)),
                faixa,
                stage: stageName(l),
                ultimoSinal: dias === null ? "—" : dias === 0 ? "hoje" : `há ${dias}d`,
                cadencia: (CADENCIA[l.x_abm_cadencia_status] || CADENCIA.false),
                comite: `${l.x_abm_comite_decisores || 0}/${l.x_abm_comite_total || 0}`,
                exposicao: (l.x_abm_exposicao || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 }),
            };
        });

        // ---------- últimos sinais
        const feed = sinais.slice(0, 10).map((s) => ({
            ...s,
            quando: s.dt.setLocale("pt-BR").toFormat("dd/MM HH:mm"),
            tipoLabel: TIPOS[s.x_tipo] || s.x_tipo,
            origem: ORIGENS[s.x_origem || "false"] || ORIGENS.false,
        }));

        return {
            kpis, funil, timeline, origens, tipos, faixas, cadencia, tiers, atividadesTipo, statusTotals,
            agenda, alertas, contas, feed, totalLeads: leads.length, totalSinais: sinais.length,
            totalAtiv: concluidas.length + abertas.length,
            donutFaixas: this._donut(faixas),
            donutOrigens: this._donut(origens),
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

    openKpi(kind) {
        const leadDom = [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ...this._tierDomain()];
        const sinalBase = [["x_lead_id.team_id", "=", TEAM_ID], ...this._tierDomain("x_lead_id."), ...this._rangeDomain("x_data")];
        if (kind === "contas") {
            this.openList("Contas ABM", "crm.lead", leadDom, [[false, "list"], [false, "kanban"], [false, "form"]]);
        } else if (kind === "sinais") {
            this.openList(`Sinais · ${this.periodLabel}`, "x_abm_sinal", sinalBase);
        } else if (kind === "respostas") {
            this.openList(`Respostas · ${this.periodLabel}`, "x_abm_sinal", [...sinalBase, ["x_tipo", "in", [...TIPOS_RESPOSTA]]]);
        } else if (kind === "concluidas") {
            this.openList(
                `Atividades concluídas · ${this.periodLabel}`, "mail.activity",
                [...ACTIVITY_DOMAIN, ["active", "=", false], ...this._rangeDomain("date_done", true)],
                [[false, "list"], [false, "form"]], { active_test: false }
            );
        } else if (kind === "atrasadas") {
            this.openList("Atividades ABM atrasadas", "mail.activity",
                [...ACTIVITY_DOMAIN, ["date_deadline", "<", DateTime.local().toISODate()]]);
        }
    }

    openStage(stageId) {
        this.openList("Contas ABM", "crm.lead",
            [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ["stage_id", "=", stageId], ...this._tierDomain()],
            [[false, "list"], [false, "kanban"], [false, "form"]]);
    }

    openFaixa(faixa) {
        this.openList(`Contas ${faixa}`, "crm.lead",
            [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ["x_abm_faixa", "=", faixa], ...this._tierDomain()],
            [[false, "list"], [false, "kanban"], [false, "form"]]);
    }

    openAlert(alerta) {
        this.openList(alerta.title, "crm.lead", [["id", "in", alerta.items.map((l) => l.id)]],
            [[false, "list"], [false, "kanban"], [false, "form"]]);
    }

    openActivity(a) {
        if (a.res_model === "crm.lead") {
            this.openLead(a.res_id);
        } else {
            this.openList("Atividade", "mail.activity", [["id", "=", a.id]]);
        }
    }
}

registry.category("actions").add("abm_setima_dashboard", AbmSetimaDashboard);
