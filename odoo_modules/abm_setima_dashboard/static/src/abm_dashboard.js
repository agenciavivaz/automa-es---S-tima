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
    { key: "midia", label: "Mídia" },
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
    ["Mídia · frente", "Comitê · Sétima = campanhas de comitê das contas do ABM Sétima (Contas - Montadora, Comitê - 93 montadoras, Lista + Comitê, Comitê + Lista). Educação · BrandSpot = [Comite] Educação, que mira contas do ABM BrandSpot."],
    ["Investimento", "Custo do LinkedIn Ads no período (soma diária por campanha, coletada pelo Make)."],
    ["CPM médio", "Investimento ÷ impressões × 1.000. Quanto custa aparecer mil vezes para o público da campanha."],
    ["CTR médio", "Cliques ÷ impressões. Para anúncio de awareness em ABM, a referência do LinkedIn fica em 0,4–0,6%."],
    ["CPC médio", "Investimento ÷ cliques."],
    ["Frequência média (contas)", "Soma das impressões nas contas ABM medidas ÷ soma do público estimado na segmentação dessas contas (impressões por pessoa). Usa a medição x_abm_midia_* (não muda com o filtro de período). Faixas: < 2× baixa, 2–4× construindo, 4–8× ideal, > 8× saturando."],
    ["Retenção de vídeo", "Vídeos assistidos até o fim ÷ views de 2 segundos ou mais. View rate = views ÷ impressões."],
    ["Público (cargo, senioridade, função)", "Impressões por característica de quem viu o anúncio (pivôs demográficos do LinkedIn). Coleta pontual de 21/09 a 26/11; não segue o filtro de período. Uma pessoa pode ter mais de uma função, então a soma das funções passa de 100%."],
    ["Próxima ação de mídia", "Regra por conta: sem entrega → incluir na lista; < 2× → ampliar; 2–4× → manter; 4–8× → ideal (acionar cadência se a conta ainda não está em cadência ativa); > 8× → saturando (trocar criativo ou reduzir verba)."],
];

const FRENTES_MIDIA = [
    { key: "comite", label: "Comitê · Sétima", color: "#1d4ed8" },
    { key: "educacao", label: "Educação · BrandSpot", color: "#0e7490" },
    { key: "todas", label: "Todas as campanhas", color: "#64748b" },
];
const EM_CONTATO = ["Conversa", "Reunião agendada", "Reunião realizada", "Nutrição"];
const ENSINO = /educa|escola|universi|faculdade|ensino|col[eé]gio|senai|senac|sesi|sesc|sebrae|firjan|fiep|fiesc|ciee|fgv|getulio|puc|usp|uerj|ufmg|ibmec|espm|fia |alura|arco |marista|positivo|ftd|seb |salta|inspira|ebac|uniube|g4|cesar|cruzeiro|fluency|lumiar|paula souza|dom cabral|belas artes|direito|arbitr|moot|ciarb|icca|oab|jurimetria|legal|inber|brasilcon|abrarec|cgu|societ|fundep|inovabra|toon boom/i;
const COR_FRENTE = { comite: "#1d4ed8", educacao: "#0e7490", outra: "#94a3b8" };
const GRUPOS_SENIORIDADE = [
    { key: "decisor", label: "Decisores (diretor, VP, C-level, sócio)", ids: ["6", "7", "8", "9", "10"], color: "#1d4ed8" },
    { key: "gestao", label: "Gerência", ids: ["5"], color: "#60a5fa" },
    { key: "execucao", label: "Execução (sênior, júnior, estágio)", ids: ["1", "2", "3", "4"], color: "#cbd5e1" },
];
const MIDIA_STATUS = [
    { key: "saturando", label: "Saturando > 8×", color: "#6d28d9" },
    { key: "ideal", label: "Ideal 4–8×", color: "#047857" },
    { key: "construindo", label: "Construindo 2–4×", color: "#b45309" },
    { key: "baixa", label: "Baixa < 2×", color: "#b91c1c" },
    { key: "nao_medida", label: "Com entrega, sem medição", color: "#94a3b8" },
    { key: "sem_entrega", label: "Sem entrega", color: "#e3e6ea" },
];
const DIA_FIELDS = [
    "x_data", "x_campanha_id", "x_campanha", "x_frente", "x_impressoes", "x_cliques", "x_custo", "x_cliques_lp",
    "x_aberturas_form", "x_leads_form", "x_engajamentos", "x_video_views", "x_video_completos", "x_coletado_em",
];
const fmtBRL = (n, dec) => (n === null || n === undefined || !isFinite(n)) ? "—"
    : "R$ " + n.toLocaleString("pt-BR", { minimumFractionDigits: dec ?? (n >= 100 ? 0 : 2), maximumFractionDigits: dec ?? (n >= 100 ? 0 : 2) });
const fmtPct = (x, dec = 1) => (x === null || x === undefined || !isFinite(x)) ? "—"
    : (x * 100).toLocaleString("pt-BR", { minimumFractionDigits: dec, maximumFractionDigits: dec }) + "%";
const fmtX = (x) => (x === null || x === undefined) ? "—" : x.toLocaleString("pt-BR", { maximumFractionDigits: 1 }) + "×";

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
        this.fmt = { brl: fmtBRL, pct: fmtPct };
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
            frente: "comite",
            midiaContasTodas: false,
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
            const [leads, relatorios, intencao, midiaDia, midiaEmpresa, midiaSegmento] = await Promise.all([
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
                this.orm.searchRead("x_abm_midia_dia", [], DIA_FIELDS, { order: "x_data asc" }),
                this.orm.searchRead("x_abm_midia_empresa", [],
                    ["x_periodo_inicio", "x_periodo_fim", "x_empresa", "x_impressoes", "x_cliques", "x_lead_id"],
                    { order: "x_periodo_inicio desc, x_impressoes desc" }),
                this.orm.searchRead("x_abm_midia_segmento", [],
                    ["x_periodo_inicio", "x_periodo_fim", "x_frente", "x_dimensao", "x_valor_id", "x_valor",
                        "x_impressoes", "x_cliques", "x_custo"],
                    { order: "x_impressoes desc" }),
            ]);
            const stageIds = [...new Set(leads.map((l) => l.stage_id && l.stage_id[0]).filter(Boolean))];
            const stages = await this.orm.searchRead(
                "crm.stage",
                ["|", ["team_ids", "in", [TEAM_ID]], ["id", "in", stageIds]],
                ["name", "sequence"],
                { order: "sequence, id" }
            );
            this.state.raw = {
                leads, relatorios, intencao, stages, midiaDia, midiaEmpresa, midiaSegmento, loadedAt: DateTime.local(),
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

        const midia = this._midia(raw, leads, { start, end, prevStart, prevEnd, inRange, stageName });

        return {
            midia,
            kpis, tipos, timeline, feed, funil, faixas, cadencia, prontidao, contas,
            novas: novas.length, scoreMedio,
            totalLeads: leads.length, totalIntencao: intencao.length,
            donutFaixas: this._donut(faixas),
            loadedAt: raw.loadedAt.toFormat("HH:mm"),
        };
    }

    // ------------------------------------------------------------- mídia
    // LinkedIn Ads (x_abm_midia_*): planilha do Make carregada no Odoo por atualizar_midia_abm.py.
    _midia(raw, leadsTier, { start, end, prevStart, prevEnd, inRange, stageName }) {
        const fr = this.state.frente;
        const daFrente = (r) => fr === "todas" || r.x_frente === fr;
        const todasDias = raw.midiaDia.map((r) => ({ ...r, d: fromDate(r.x_data) }));
        const dias = todasDias.filter(daFrente);
        const cur = dias.filter((r) => inRange(r.d, start, end));
        const prev = prevStart ? dias.filter((r) => inRange(r.d, prevStart, prevEnd)) : null;
        const soma = (rows) => {
            const t = { imp: 0, cli: 0, custo: 0, lp: 0, form: 0, leads: 0, eng: 0, vv: 0, vc: 0 };
            for (const r of rows) {
                t.imp += r.x_impressoes || 0; t.cli += r.x_cliques || 0; t.custo += r.x_custo || 0;
                t.lp += r.x_cliques_lp || 0; t.form += r.x_aberturas_form || 0; t.leads += r.x_leads_form || 0;
                t.eng += r.x_engajamentos || 0; t.vv += r.x_video_views || 0; t.vc += r.x_video_completos || 0;
            }
            t.cpm = t.imp ? (t.custo * 1000) / t.imp : null;
            t.ctr = t.imp ? t.cli / t.imp : null;
            t.cpc = t.cli ? t.custo / t.cli : null;
            t.ret = t.vv ? t.vc / t.vv : null;
            t.viewRate = t.imp ? t.vv / t.imp : null;
            t.engRate = t.imp ? t.eng / t.imp : null;
            return t;
        };
        const T = soma(cur);
        const P = prev && prev.length ? soma(prev) : null;
        const prevLabel = this.prevLabel;
        // variação relativa; "menor" = cair é bom (custos)
        const varia = (a, b, { menor = false, neutro = false, fmt = (x) => x } = {}) => {
            if (a === null || b === null || b === undefined || !b) return null;
            const d = (a - b) / b;
            if (Math.abs(d) < 0.005) return { texto: "0%", seta: "fa-minus", classe: "neutro", tooltip: `${prevLabel}: ${fmt(b)}` };
            const bom = menor ? d < 0 : d > 0;
            return {
                texto: `${d > 0 ? "+" : "–"}${Math.abs(Math.round(d * 100))}%`,
                seta: d > 0 ? "fa-arrow-up" : "fa-arrow-down",
                classe: neutro ? "neutro" : bom ? "bom" : "ruim",
                tooltip: `${prevLabel}: ${fmt(b)}`,
            };
        };

        // ---------- contas ABM e frequência (x_abm_midia_*; medição própria, não segue o período)
        const ativas = leadsTier.filter((l) => !ENCERRADAS.includes(stageName(l)));
        const medidas = ativas.filter((l) => (l.x_abm_midia_publico || 0) > 0);
        const impMed = medidas.reduce((t, l) => t + (l.x_abm_midia_impressoes || 0), 0);
        const pubMed = medidas.reduce((t, l) => t + (l.x_abm_midia_publico || 0), 0);
        const freqMedia = pubMed ? impMed / pubMed : null;
        const periodoMedicao = (medidas.find((l) => l.x_abm_midia_periodo) || {}).x_abm_midia_periodo || "";
        const periodoMedCurto = (periodoMedicao.match(/\d{2}[–-]\d{2}\/\d{2}\/\d{4}|\d{2}\/\d{2}[^·]*/) || [""])[0].trim();

        // semana mais recente do relatório por empresa dentro do período
        const semanas = [...new Set(raw.midiaEmpresa.map((e) => e.x_periodo_inicio))]
            .filter((s) => { const d = fromDate(s); return d <= end && (!start || d >= start.minus({ days: 6 })); })
            .sort();
        const semana = semanas[semanas.length - 1] || null;
        const empSemana = semana ? raw.midiaEmpresa.filter((e) => e.x_periodo_inicio === semana) : [];
        const semanaFim = empSemana.length ? empSemana[0].x_periodo_fim : null;
        const semanaLabel = semana ? `${fromDate(semana).toFormat("dd/MM")}–${fromDate(semanaFim).toFormat("dd/MM")}` : null;
        const porLead = new Map();
        for (const e of empSemana) {
            if (!e.x_lead_id) continue;
            const r = porLead.get(e.x_lead_id[0]) || { imp: 0, cli: 0 };
            r.imp += e.x_impressoes || 0;
            r.cli += e.x_cliques || 0;
            porLead.set(e.x_lead_id[0], r);
        }
        // na frente Comitê, tira instituições de ensino (são alvo da campanha de Educação / ABM BrandSpot)
        const foraDaLista = empSemana
            .filter((e) => !e.x_lead_id && (fr !== "comite" || !ENSINO.test(e.x_empresa || "")))
            .slice(0, 8);

        const contasMidia = ativas.map((l) => {
            const info = midiaInfo(l);
            const sem = porLead.get(l.id) || { imp: 0, cli: 0 };
            let status = info.faixa ? info.faixa.key : (sem.imp || l.x_abm_midia_impressoes) ? "nao_medida" : "sem_entrega";
            const cadAtiva = l.x_abm_cadencia_status === "ativa";
            // já em contato 1:1 (cadência ativa ou etapa depois de "Em cadência"): mídia só sustenta presença
            const emContato = cadAtiva || EM_CONTATO.includes(stageName(l));
            const acoes = {
                saturando: emContato ? "Saturando: trocar criativo ou reduzir verba" : "Saturando: acionar cadência e reduzir verba",
                ideal: emContato ? "Exposição ideal: manter presença" : "Exposição ideal: acionar cadência",
                construindo: "Construindo: manter verba",
                baixa: "Subexposta: ampliar público ou lance",
                nao_medida: "Medir público (Apollo) para ler a frequência",
                sem_entrega: "Sem entrega: incluir na lista da campanha",
            };
            return {
                id: l.id, lead: l, stage: stageName(l), info, status, acao: acoes[status],
                semImp: sem.imp, semCli: sem.cli, cadAtiva, emContato,
                statusInfo: MIDIA_STATUS.find((s) => s.key === status),
                faixa: FAIXAS.find((f) => f.key === (l.x_abm_faixa || "fria")),
                score: l.x_abm_score || 0,
            };
        });
        const ordemStatus = Object.fromEntries(MIDIA_STATUS.map((s, i) => [s.key, i]));
        contasMidia.sort((a, b) => (b.lead.x_abm_midia_impressoes || 0) - (a.lead.x_abm_midia_impressoes || 0)
            || b.semImp - a.semImp || ordemStatus[a.status] - ordemStatus[b.status] || a.lead.name.localeCompare(b.lead.name));
        const distrib = MIDIA_STATUS.map((s) => ({ ...s, count: contasMidia.filter((c) => c.status === s.key).length }));
        const comEntrega = contasMidia.filter((c) => c.status !== "sem_entrega").length;

        // ---------- KPIs
        const kpis = [
            {
                key: "investimento", icon: "fa-money", label: "Valor investido", value: fmtBRL(T.custo, 0),
                sub: `${fmtInt(T.imp)} impressões`, delta: P && varia(T.custo, P.custo, { neutro: true, fmt: (x) => fmtBRL(x, 0) }),
                info: "Custo do LinkedIn Ads no período, na frente selecionada.",
            },
            {
                key: "cpm", icon: "fa-eye", label: "CPM médio", value: fmtBRL(T.cpm, 2),
                sub: "custo por mil impressões", delta: P && varia(T.cpm, P.cpm, { menor: true, fmt: (x) => fmtBRL(x, 2) }),
                info: "Investimento ÷ impressões × 1.000.",
            },
            {
                key: "ctr", icon: "fa-mouse-pointer", label: "CTR médio", value: fmtPct(T.ctr, 2),
                sub: `${fmtInt(T.cli)} cliques`, delta: P && varia(T.ctr, P.ctr, { fmt: (x) => fmtPct(x, 2) }),
                info: "Cliques ÷ impressões.",
            },
            {
                key: "cpc", icon: "fa-hand-pointer-o", label: "CPC médio", value: fmtBRL(T.cpc, 2),
                sub: `${fmtInt(T.lp)} cliques na landing page`, delta: P && varia(T.cpc, P.cpc, { menor: true, fmt: (x) => fmtBRL(x, 2) }),
                info: "Investimento ÷ cliques.",
            },
            {
                key: "freq", icon: "fa-repeat", label: "Frequência média",
                value: fr === "educacao" ? "—" : fmtX(freqMedia),
                sub: fr === "educacao" ? "contas da Educação não estão no ABM Sétima"
                    : `${medidas.length} contas medidas${periodoMedCurto ? " · " + periodoMedCurto : ""}`,
                delta: null,
                info: "Impressões ÷ público estimado na segmentação, nas contas ABM medidas. Ideal entre 4× e 8×.",
            },
            {
                key: "retencao", icon: "fa-play-circle", label: "Retenção de vídeo", value: fmtPct(T.ret, 1),
                sub: `view rate ${fmtPct(T.viewRate, 0)} · ${fmtInt(T.vc)} até o fim`,
                delta: P && varia(T.ret, P.ret, { fmt: (x) => fmtPct(x, 1) }),
                info: "Assistiram até o fim ÷ views de 2s ou mais.",
            },
        ];

        // ---------- investimento por semana (ou dia), com CPM
        const firstDt = start || (dias.length ? dias[0].d : end.startOf("day"));
        const spanDays = Math.max(1, Math.round(end.diff(firstDt, "days").days));
        const unit = spanDays <= 14 ? "day" : "week";
        const buckets = [];
        let c0 = firstDt.startOf(unit);
        while (c0 <= end && buckets.length < 60) {
            buckets.push({ start: c0, end: c0.endOf(unit), rows: [] });
            c0 = c0.plus({ [unit + "s"]: 1 });
        }
        for (const r of cur) {
            const b = buckets.find((b) => r.d >= b.start && r.d <= b.end);
            if (b) b.rows.push(r);
        }
        const maxCusto = Math.max(1, ...buckets.map((b) => b.rows.reduce((t, r) => t + (r.x_custo || 0), 0)));
        const serie = {
            unit: unit === "day" ? "por dia" : "por semana",
            max: maxCusto,
            bars: buckets.map((b, i) => {
                const t = soma(b.rows);
                const porFrente = {};
                for (const r of b.rows) porFrente[r.x_frente] = (porFrente[r.x_frente] || 0) + (r.x_custo || 0);
                return {
                    key: i,
                    label: b.start.setLocale("pt-BR").toFormat("dd/MM"),
                    showLabel: buckets.length <= 10 || i % Math.ceil(buckets.length / 10) === 0,
                    valor: t.custo ? fmtBRL(t.custo, 0).replace("R$ ", "") : "",
                    cpm: t.cpm ? fmtBRL(t.cpm, 0) : "",
                    title: `${b.start.toFormat("dd/MM")}${unit !== "day" ? " – " + b.end.toFormat("dd/MM") : ""}: ${fmtBRL(t.custo, 0)} · ${fmtInt(t.imp)} impr. · CPM ${fmtBRL(t.cpm, 2)} · CTR ${fmtPct(t.ctr, 2)}`,
                    segs: Object.entries(porFrente).map(([k, v]) => ({ key: k, height: (v * 100) / maxCusto, color: COR_FRENTE[k] || COR_FRENTE.outra })),
                };
            }),
        };

        // ---------- campanhas
        const camp = new Map();
        for (const r of cur) {
            const c = camp.get(r.x_campanha_id) || { id: r.x_campanha_id, nome: r.x_campanha, frente: r.x_frente, rows: [] };
            c.nome = r.x_campanha || c.nome;
            c.rows.push(r);
            camp.set(r.x_campanha_id, c);
        }
        const campanhas = [...camp.values()].map((c) => {
            const t = soma(c.rows);
            return {
                ...c, t, share: T.custo ? Math.round((t.custo * 100) / T.custo) : 0,
                cor: COR_FRENTE[c.frente] || COR_FRENTE.outra,
                frenteLabel: (FRENTES_MIDIA.find((f) => f.key === c.frente) || { label: "Outra" }).label,
                dias: new Set(c.rows.map((r) => r.x_data)).size,
            };
        }).sort((a, b) => b.t.custo - a.t.custo);

        // ---------- funil de vídeo
        const funilVideo = [
            { key: "imp", label: "Impressões", n: T.imp, pct: 100, txt: "" },
            { key: "vv", label: "Views de 2s+", n: T.vv, pct: T.imp ? (T.vv * 100) / T.imp : 0, txt: fmtPct(T.viewRate, 0) + " das impressões" },
            { key: "vc", label: "Assistiram até o fim", n: T.vc, pct: T.imp ? (T.vc * 100) / T.imp : 0, txt: fmtPct(T.ret, 1) + " de quem assistiu" },
        ];
        const acao = [
            { key: "eng", label: "Engajamentos", n: T.eng, txt: fmtPct(T.engRate, 2) },
            { key: "cli", label: "Cliques", n: T.cli, txt: fmtPct(T.ctr, 2) },
            { key: "lp", label: "Cliques na landing page", n: T.lp, txt: "" },
            { key: "form", label: "Aberturas de formulário", n: T.form, txt: "" },
            { key: "leads", label: "Leads de formulário", n: T.leads, txt: "" },
        ];

        // ---------- público (cargo, senioridade, função)
        const segs = raw.midiaSegmento.filter((s) => fr === "todas" || s.x_frente === fr);
        const segPeriodo = segs.length
            ? `${fromDate(segs[0].x_periodo_inicio).toFormat("dd/MM")}–${fromDate(segs[0].x_periodo_fim).toFormat("dd/MM/yyyy")}` : null;
        const agrupa = (dim) => {
            const m = new Map();
            for (const s of segs.filter((x) => x.x_dimensao === dim)) {
                const r = m.get(s.x_valor_id) || { id: s.x_valor_id, nome: s.x_valor, imp: 0, cli: 0 };
                r.imp += s.x_impressoes || 0;
                r.cli += s.x_cliques || 0;
                m.set(s.x_valor_id, r);
            }
            return [...m.values()].sort((a, b) => b.imp - a.imp);
        };
        const sen = agrupa("senioridade");
        const totSen = sen.reduce((t, s) => t + s.imp, 0);
        const grupos = GRUPOS_SENIORIDADE.map((g) => {
            const itens = sen.filter((s) => g.ids.includes(s.id));
            const imp = itens.reduce((t, s) => t + s.imp, 0);
            const cli = itens.reduce((t, s) => t + s.cli, 0);
            return { ...g, imp, pct: totSen ? Math.round((imp * 100) / totSen) : 0, ctr: imp ? cli / imp : null,
                detalhe: itens.map((s) => `${s.nome} ${totSen ? Math.round((s.imp * 100) / totSen) : 0}%`).join(" · ") };
        });
        const funcoes = agrupa("funcao").slice(0, 8);
        const maxFun = Math.max(1, ...funcoes.map((f) => f.imp));
        const cargos = agrupa("cargo").slice(0, 12);
        const maxCargo = Math.max(1, ...cargos.map((c) => c.imp));
        const publico = {
            periodo: segPeriodo, totSen, grupos,
            funcoes: funcoes.map((f) => ({ ...f, pct: totSen ? Math.round((f.imp * 100) / totSen) : 0, width: Math.round((f.imp * 100) / maxFun) })),
            cargos: cargos.map((c) => ({ ...c, pct: totSen ? ((c.imp * 100) / totSen) : 0, width: Math.round((c.imp * 100) / maxCargo), ctr: c.imp ? c.cli / c.imp : null })),
        };

        // ---------- leitura para decisão (regras simples, em linguagem de board)
        const leitura = [];
        if (T.imp) {
            const decisor = grupos.find((g) => g.key === "decisor");
            const gestao = grupos.find((g) => g.key === "gestao");
            if (decisor && totSen) {
                leitura.push(decisor.pct < 20 ? {
                    tipo: "alerta", titulo: `Só ${decisor.pct}% das impressões chegam a decisores`,
                    texto: `Diretores, VPs e C-level somam ${decisor.pct}% (gerência ${gestao.pct}%). O restante é execução: especialistas, analistas e estagiários. Para ABM, restringir a senioridade a gerente+ ou usar a lista do comitê (Matched Audiences) concentra a verba em quem decide.`,
                } : {
                    tipo: "ok", titulo: `${decisor.pct}% das impressões em decisores`,
                    texto: `Com gerência, ${decisor.pct + gestao.pct}% da mídia está em quem influencia ou decide a compra.`,
                });
            }
            if (campanhas.length > 1) {
                const comImp = campanhas.filter((c) => c.t.imp >= 500);
                const barata = comImp.reduce((a, b) => (a && a.t.cpm <= b.t.cpm ? a : b), null);
                const cara = comImp.reduce((a, b) => (a && a.t.cpm >= b.t.cpm ? a : b), null);
                if (barata && cara && barata !== cara && cara.t.cpm > barata.t.cpm * 1.5) {
                    leitura.push({
                        tipo: "oportunidade", titulo: `CPM varia ${Math.round(cara.t.cpm / barata.t.cpm)}× entre campanhas`,
                        texto: `${cara.nome}: ${fmtBRL(cara.t.cpm, 0)} por mil impressões; ${barata.nome}: ${fmtBRL(barata.t.cpm, 0)}. Público pequeno e muito segmentado encarece o leilão: vale comparar o custo por conta impactada antes de remanejar verba.`,
                    });
                }
            }
            if (T.vv) {
                leitura.push(T.ret < 0.05 ? {
                    tipo: "alerta", titulo: `O vídeo prende no início e perde no meio: ${fmtPct(T.ret, 1)} chegam ao fim`,
                    texto: `${fmtPct(T.viewRate, 0)} das impressões viram view de 2s, mas só ${fmtInt(T.vc)} pessoas assistiram até o fim. Testar cortes de 6–15s com a mensagem e a marca nos 3 primeiros segundos.`,
                } : {
                    tipo: "ok", titulo: `Retenção de vídeo de ${fmtPct(T.ret, 1)}`,
                    texto: `${fmtPct(T.viewRate, 0)} das impressões viram view de 2s e ${fmtInt(T.vc)} pessoas assistiram até o fim.`,
                });
            }
            if (fr !== "educacao" && ativas.length) {
                const sat = distrib.find((d) => d.key === "saturando").count;
                const ideal = distrib.find((d) => d.key === "ideal").count;
                const baixa = distrib.find((d) => d.key === "baixa").count;
                const sem = distrib.find((d) => d.key === "sem_entrega").count;
                leitura.push({
                    tipo: sem > ativas.length / 2 ? "alerta" : "oportunidade",
                    titulo: `${comEntrega} de ${ativas.length} contas recebem mídia`,
                    texto: `${ideal} em frequência ideal, ${sat} saturando (> 8×), ${baixa} abaixo de 2× e ${sem} sem entrega mensurável. Contas novas sem entrega precisam entrar na lista da campanha; as saturadas pedem criativo novo ou cadência.`,
                });
                const prontas = contasMidia.filter((c) => ["ideal", "saturando"].includes(c.status) && !c.emContato);
                if (prontas.length) {
                    leitura.push({
                        tipo: "oportunidade", titulo: `${prontas.length} contas já aquecidas pela mídia sem cadência ativa`,
                        texto: `${prontas.slice(0, 5).map((c) => c.lead.name).join(", ")}${prontas.length > 5 ? "…" : ""}: a mídia já fez a parte de exposição. Próximo passo é o contato 1:1 com o comitê.`,
                    });
                }
            }
            if (T.cli && !T.leads) {
                leitura.push({
                    tipo: "alerta", titulo: "Mídia gera atenção, ainda não gera ação",
                    texto: `${fmtInt(T.cli)} cliques, ${fmtInt(T.lp)} na landing page, ${fmtInt(T.form)} aberturas de formulário e nenhum lead no período. Para a mídia gerar sinal de intenção, testar oferta com valor para o comitê (diagnóstico, benchmark) no formulário nativo.`,
                });
            }
            const foraSetima = foraDaLista.filter((e) => /volks|vw|mercedes|renault|hyundai|fiat|chevrolet|peugeot|citro|scania|volvo|iveco|daf|man |tractor|maquin|implement/i.test(e.x_empresa || ""));
            if (fr !== "educacao" && foraSetima.length) {
                leitura.push({
                    tipo: "oportunidade", titulo: "Empresas do setor impactadas fora do ABM",
                    texto: `${foraSetima.map((e) => `${e.x_empresa} (${fmtInt(e.x_impressoes)} impr.${e.x_cliques ? ", " + e.x_cliques + " cliques" : ""})`).join(", ")} na semana ${semanaLabel}. Avaliar se entram como conta do programa.`,
                });
            }
        }

        const datas = todasDias.map((r) => r.x_data).sort();
        const coleta = todasDias.map((r) => r.x_coletado_em).filter(Boolean).sort().pop();
        return {
            vazio: !raw.midiaDia.length,
            semDadosPeriodo: !cur.length,
            frentes: FRENTES_MIDIA,
            fonte: datas.length ? `dados de ${fromDate(datas[0]).toFormat("dd/MM")} a ${fromDate(datas[datas.length - 1]).toFormat("dd/MM/yyyy")}${coleta ? " · coletado em " + coleta.slice(8, 10) + "/" + coleta.slice(5, 7) + " " + coleta.slice(11, 16) : ""}` : "",
            kpis, serie, campanhas, total: T, funilVideo, acao, publico, leitura,
            contas: contasMidia, distrib, comEntrega, totalAtivas: ativas.length, semanaLabel, foraDaLista,
            mostraContas: fr !== "educacao",
        };
    }

    onFrente(key) {
        this.state.frente = key;
    }

    openCampanha(c) {
        const dom = [["x_campanha_id", "=", c.id], ...this._rangeDomain("x_data", true)];
        this.openList(`${c.nome} · ${this.periodLabel}`, "x_abm_midia_dia", dom);
    }

    openMidiaDia() {
        const dom = [...this._rangeDomain("x_data", true)];
        if (this.state.frente !== "todas") dom.push(["x_frente", "=", this.state.frente]);
        this.openList(`LinkedIn Ads por dia · ${this.periodLabel}`, "x_abm_midia_dia", dom);
    }

    openSegmento(dim) {
        const dom = [["x_dimensao", "=", dim]];
        if (this.state.frente !== "todas") dom.push(["x_frente", "=", this.state.frente]);
        this.openList("Público do LinkedIn Ads", "x_abm_midia_segmento", dom);
    }

    openMidiaStatus(key, contas) {
        this.openList(`Mídia · ${(MIDIA_STATUS.find((s) => s.key === key) || {}).label}`, "crm.lead",
            [["id", "in", contas.filter((c) => c.status === key).map((c) => c.id)]],
            [[false, "list"], [false, "kanban"], [false, "form"]]);
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
