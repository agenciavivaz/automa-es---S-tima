/** @odoo-module **/
// Relatório de resultados · Inbound Sétima (v2) — funções PURAS de cálculo.
//
// Nada aqui toca DOM, ORM ou serviços do Odoo: recebe os registros crus (data.js) e o
// período e devolve o "modelo de tela". O mesmo arquivo roda no navegador (Odoo) e no
// Node (inbound_v2/scripts/valores_dashboard.mjs), o que permite reconciliar cada número
// com consultas independentes ao CRM. Datas sempre em America/Sao_Paulo (RN6).
//
// Depende só do luxon global (o Odoo já carrega; no Node o script injeta).

export const TZ = "America/Sao_Paulo";
export const TEAM_ID = 16; // crm.team "Inbound Sétima" — RN1 (mesmo critério da v1)
const DT = () => globalThis.luxon.DateTime;

// ------------------------------------------------------------------ formatação pt-BR
const nbsp = / | /g;
export const fmtInt = (n) => Math.round(n || 0).toLocaleString("pt-BR");
export const fmtBrl = (v) =>
    "R$ " + Math.round(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
export function fmtBrlCurto(v) {
    const n = v || 0;
    if (Math.abs(n) >= 1e6) return `R$ ${(n / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
    if (Math.abs(n) >= 1e3) return `R$ ${(n / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mil`;
    return fmtBrl(n);
}
export const pct = (a, b) => (b ? (a * 100) / b : 0);
export const fmtPct = (v) => `${(Math.round((v || 0) * 10) / 10).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
export const fmtDate = (d) => (d ? d.setZone(TZ).toFormat("dd/MM/yyyy") : "—");
export function fmtHoras(h) {
    if (h === null || h === undefined) return "—";
    if (h < 1) return `${Math.max(1, Math.round(h * 60))} min`;
    if (h < 48) return `${fmtInt(h)} h`;
    return `${fmtInt(h / 24)} d`;
}
export function fmtIntervalo(a, b) {
    if (!a) return `todo o histórico até ${b.toFormat("dd/MM/yyyy")}`;
    if (a.hasSame(b, "day")) return a.toFormat("dd/MM/yyyy");
    if (a.hasSame(b, "month")) return `${a.toFormat("dd")}–${b.toFormat("dd/MM/yyyy")}`;
    if (a.hasSame(b, "year")) return `${a.toFormat("dd/MM")}–${b.toFormat("dd/MM/yyyy")}`;
    return `${a.toFormat("dd/MM/yyyy")}–${b.toFormat("dd/MM/yyyy")}`;
}
export function fmtIntervaloCurto(a, b) {
    if (!a) return "todo o histórico";
    if (a.hasSame(b, "day")) return a.toFormat("dd/MM");
    if (a.hasSame(b, "month")) return `${a.toFormat("dd")}–${b.toFormat("dd/MM")}`;
    return `${a.toFormat("dd/MM")}–${b.toFormat("dd/MM")}`;
}
// Template com placeholders {chave}: o texto nunca é concatenado à mão (causa do B1).
export function tpl(modelo, vals) {
    return modelo
        .replace(/\{(\w+)\}/g, (_, k) => (vals[k] === undefined || vals[k] === null ? "" : String(vals[k])))
        .replace(nbsp, " ")
        .replace(/ {2,}/g, " ")
        .trim();
}
const sinal = (n) => (n > 0 ? `+${fmtInt(n)}` : n < 0 ? `–${fmtInt(-n)}` : "0");

// ------------------------------------------------------------------ período (RN4, RN6)
export const PRESETS = [
    { key: "this_month", label: "Este mês" },
    { key: "prev_month", label: "Mês anterior" },
    { key: "7d", label: "7 dias" },
    { key: "30d", label: "30 dias" },
    { key: "90d", label: "90 dias" },
    { key: "quarter", label: "Trimestre" },
    { key: "year", label: "Este ano" },
    { key: "all", label: "Tudo" },
    { key: "custom", label: "Personalizado" },
];

/** Período e período de comparação (mesma duração, imediatamente anterior — RN4). */
export function periodo(preset, fromIso, toIso, now) {
    const hoje = (now || DT().now()).setZone(TZ).startOf("day");
    let start = null;
    let end = hoje;
    if (preset === "7d") start = hoje.minus({ days: 6 });
    else if (preset === "30d") start = hoje.minus({ days: 29 });
    else if (preset === "90d") start = hoje.minus({ days: 89 });
    else if (preset === "this_month") start = hoje.startOf("month");
    else if (preset === "quarter") start = hoje.startOf("quarter");
    else if (preset === "year") start = hoje.startOf("year");
    else if (preset === "prev_month") {
        start = hoje.minus({ months: 1 }).startOf("month");
        end = start.endOf("month").startOf("day");
    } else if (preset === "custom") {
        start = fromIso ? DT().fromISO(fromIso, { zone: TZ }).startOf("day") : hoje.startOf("month");
        end = toIso ? DT().fromISO(toIso, { zone: TZ }).startOf("day") : hoje;
        if (end < start) [start, end] = [end, start];
    }
    end = end.endOf("day");
    let prevStart = null;
    let prevEnd = null;
    if (start) {
        if (preset === "this_month" || preset === "prev_month" || preset === "quarter" || preset === "year") {
            // calendário: mesmos dias do mês/trimestre/ano anterior (01–15/10 → 01–15/09)
            const unit = preset === "year" ? { years: 1 } : preset === "quarter" ? { months: 3 } : { months: 1 };
            prevStart = start.minus(unit);
            prevEnd = preset === "prev_month" ? prevStart.endOf("month") : end.minus(unit).endOf("day");
        } else {
            const dias = Math.round(end.startOf("day").diff(start, "days").days) + 1;
            prevEnd = start.minus({ days: 1 }).endOf("day");
            prevStart = start.minus({ days: dias });
        }
    }
    return {
        preset, start, end, prevStart, prevEnd,
        label: fmtIntervalo(start, end),
        labelCurto: fmtIntervaloCurto(start, end),
        prevLabel: prevStart ? fmtIntervalo(prevStart, prevEnd) : null,
        prevLabelCurto: prevStart ? fmtIntervaloCurto(prevStart, prevEnd) : null,
        dias: start ? Math.round(end.diff(start, "days").days) : null,
        terminaHoje: end.hasSame(hoje, "day"),
    };
}
/** Data local → string UTC do banco ("yyyy-MM-dd HH:mm:ss"). */
export const toUtcSql = (d) => d.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
export const fromUtcSql = (s) => (s ? DT().fromSQL(s, { zone: "utc" }).setZone(TZ) : null);
const fromDateStr = (s) => (s ? DT().fromISO(s, { zone: TZ }) : null);

// ------------------------------------------------------------------ domínios (RN1)
export const BASE_DOMAIN = [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ["active", "in", [true, false]]];
/** Data de entrada do lead = criação no Pipedrive (migrados) senão criação no Odoo (v1). */
export function entradaDomain(a, b) {
    const rng = (f) => [...(a ? [[f, ">=", toUtcSql(a)]] : []), [f, "<=", toUtcSql(b)]];
    const pd = rng("x_pipedrive_add_time");
    const cd = rng("create_date");
    return [
        "|",
        ...Array(pd.length).fill("&"), ["x_pipedrive_add_time", "!=", false], ...pd,
        ...Array(cd.length).fill("&"), ["x_pipedrive_add_time", "=", false], ...cd,
    ];
}

// ------------------------------------------------------------------ texto / HTML
const ENTIDADES = { "&nbsp;": " ", "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": '"', "&#39;": "'", "&#x27;": "'" };
export function stripHtml(html) {
    return String(html || "")
        .replace(/<br\s*\/?>/gi, " ")
        .replace(/<\/(p|div|li)>/gi, " ")
        .replace(/<[^>]+>/g, "")
        .replace(/&[#\w]+;/g, (e) => ENTIDADES[e] ?? " ")
        .replace(/\s+/g, " ")
        .trim();
}
const RE_ESTRUTURADO = /cnpj|raz[ãa]o social|capital social|endere[çc]o|\bcep\b|\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}|natureza jur[íi]dica|inscri[çc][ãa]o estadual/i;
export const isBlocoEstruturado = (t) => t.length > 120 && RE_ESTRUTURADO.test(t);

// ------------------------------------------------------------------ classificação das ações (RN5)
// Palavra-chave só separa tipos de MENSAGEM e nunca gera "Reunião": reunião exige evento de
// agenda ou atividade do tipo Reunião (dado estruturado).
export const TIPOS_ACAO = [
    { key: "whatsapp", label: "WhatsApp / DataCrazy", icon: "fa-whatsapp", color: "#047857", contato: true },
    { key: "email", label: "E-mail", icon: "fa-envelope-o", color: "#b45309", contato: true },
    { key: "ligacao", label: "Ligação", icon: "fa-phone", color: "#0e7490", contato: true },
    { key: "convite", label: "Convite para agendar", icon: "fa-calendar-plus-o", color: "#6d28d9", contato: true },
    { key: "reuniao", label: "Reunião agendada/realizada", icon: "fa-handshake-o", color: "#1d4ed8", contato: true },
    { key: "pesquisa", label: "Pesquisa / qualificação", icon: "fa-search", color: "#57534e", contato: false },
    { key: "outro", label: "Outros", icon: "fa-sticky-note-o", color: "#94a3b8", contato: false },
];
export const TIPO = Object.fromEntries(TIPOS_ACAO.map((t) => [t.key, t]));
const REGRAS_TEXTO = [
    ["convite", /agenda\b|agendar|agendamento|marcar(mos)?\b|marcamos|reuni[ãa]o|disponibilidade|\bmeet\b|invite/],
    ["whatsapp", /datacrazy|datacray|whats|wpp|\bzap\b|mensagem/],
    ["email", /e-?mail/],
    ["ligacao", /liga[çc]|ligu|telefon|api4com|caixa postal/],
    ["pesquisa", /site|cnpj|linkedin|capital social|pesquis|qualific|\bicp\b|raz[ãa]o social/],
];
export function classificarTexto(texto) {
    const t = (texto || "").toLowerCase();
    for (const [k, re] of REGRAS_TEXTO) if (re.test(t)) return k;
    return "outro";
}
// "Sem sucesso": mesmo critério da v1 (tentativa registrada sem resposta).
export const RE_SEM_SUCESSO = /tentativa|sem contato|n[ãa]o atend|sem resposta|inv[áa]lid/;

// ------------------------------------------------------------------ campanhas (apelidos, L8)
export const PALETA = ["#1d4ed8", "#b45309", "#047857", "#be185d", "#6d28d9", "#0e7490", "#4d7c0f", "#9a3412"];
export const COR_SEM = "#78716c";
export function apelidoAutomatico(nome) {
    const limpo = String(nome || "")
        .replace(/\[[^\]]*\]/g, " ")
        .replace(/^[\s\-–—|:]+|[\s\-–—|:]+$/g, "")
        .replace(/\s*[-–—]\s*/g, " – ")
        .replace(/\s+/g, " ")
        .trim();
    return limpo || String(nome || "").trim();
}
export function mapaCampanhas(apelidos) {
    const m = new Map();
    for (const a of apelidos || []) {
        if (a.x_name) m.set(a.x_name.trim(), { apelido: (a.x_apelido || "").trim() || apelidoAutomatico(a.x_name), cor: a.x_cor || null });
    }
    return m;
}

// ------------------------------------------------------------------ etapas
const norm = (s) =>
    String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase()
        .replace(/\b(setima|brandspot|abm)\b/g, "").replace(/[^a-z ]/g, " ").replace(/\s+/g, " ").trim()
        .replace(/^leads$/, "lead");
/**
 * Etapa mais avançada alcançada = posição da etapa ATUAL no funil da equipe 16 (método da v1:
 * não usa histórico); ganho conta em todas. Etapas de outra equipe (ex.: "Oportunidade", de
 * leads migrados) são casadas pelo nome — na v1 elas caíam em "Lead" por engano.
 */
export function rankEtapas(stages) {
    const porId = new Map(stages.map((s, i) => [s.id, i]));
    const porNome = new Map(stages.map((s, i) => [norm(s.name), i]));
    return (stageTuple) => {
        if (!stageTuple) return 0;
        if (porId.has(stageTuple[0])) return porId.get(stageTuple[0]);
        return porNome.get(norm(stageTuple[1])) ?? 0;
    };
}
const idxNome = (stages, re, fb) => {
    const i = stages.findIndex((s) => re.test(norm(s.name)));
    return i >= 0 ? i : fb;
};

// ------------------------------------------------------------------ helpers
function rank(items, keyFn) {
    const m = new Map();
    for (const it of items) {
        const k = keyFn(it);
        m.set(k, (m.get(k) || 0) + 1);
    }
    return [...m.entries()].sort((a, b) => b[1] - a[1] || String(a[0]).localeCompare(String(b[0]), "pt-BR"));
}
export function mediana(arr) {
    if (!arr.length) return null;
    const s = [...arr].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
/** Delta com polaridade (§7.4): % só com base anterior ≥ 10; abaixo, absoluto e cor neutra. */
export function delta(cur, prev, { inverso = false, prevLabel = "" } = {}) {
    if (prev === null || prev === undefined) return null;
    const d = cur - prev;
    const usaPct = prev >= 10;
    const bom = inverso ? d < 0 : d > 0;
    return {
        valor: d,
        texto: usaPct && d !== 0 ? `${sinal(d)} (${d > 0 ? "+" : "–"}${fmtPct(Math.abs(pct(d, prev)))})` : sinal(d),
        seta: d > 0 ? "fa-arrow-up" : d < 0 ? "fa-arrow-down" : "fa-minus",
        classe: !usaPct || d === 0 ? "neutro" : bom ? "bom" : "ruim",
        tooltip: `${prevLabel}: ${typeof prev === "number" ? fmtInt(prev) : prev}`,
    };
}
const nomeLead = (l) => {
    if (!l) return "";
    const empresa = (l.partner_name || l.name || "").trim();
    const contato = (l.contact_name || "").trim();
    const partes = [empresa, contato].filter(Boolean);
    const unicas = partes.filter((p, i) => partes.findIndex((q) => q.toLowerCase() === p.toLowerCase()) === i);
    return unicas.join(" · ") || l.email_from || `#${l.id}`;
};
export { nomeLead };

// ------------------------------------------------------------------ cálculo principal
/**
 * @param raw  registros carregados por data.js
 * @param per  resultado de periodo()
 * @param opts { now, dim, logTipo, campSort }
 */
export function calcular(raw, per, opts = {}) {
    const now = (opts.now || DT().now()).setZone(TZ);
    const hoje = now.startOf("day");
    const { start, end, prevStart, prevEnd } = per;
    const inRange = (dt, a, b) => !!dt && (!a || dt >= a) && dt <= b;
    const stages = raw.stages;
    const nStages = stages.length;
    const rankOf = rankEtapas(stages);
    const iMql = idxNome(stages, /^mql/, 1);
    const iSql = idxNome(stages, /^sql/, Math.min(3, nStages - 1));
    const tagDC = new Set(raw.tagDataCrazy || []);
    const camp = mapaCampanhas(raw.apelidos);

    // ---------------- leads (coorte = entraram no período)
    const prep = (l) => {
        const entrada = fromUtcSql(l.x_pipedrive_add_time) || fromUtcSql(l.create_date);
        const won = l.won_status === "won";
        const lost = l.won_status === "lost";
        const campNome = l.campaign_id ? l.campaign_id[1] : "";
        const ap = campNome ? camp.get(campNome.trim()) : null;
        return {
            ...l, entrada, won, lost,
            aberto: !won && !lost && l.active !== false,
            reached: won ? nStages : rankOf(l.stage_id),
            campanha: campNome ? (ap ? ap.apelido : apelidoAutomatico(campNome)) : "Sem campanha",
            campanhaNome: campNome || "Sem campanha",
            campanhaCor: ap && ap.cor ? ap.cor : null,
            conjunto: l.x_meta_conjunto || "Sem conjunto",
            criativo: l.x_meta_anuncio || "Sem criativo",
            plataforma: l.source_id ? l.source_id[1] : "Sem origem",
            etapa: won ? "Ganho" : lost ? "Perdido" : (l.stage_id ? l.stage_id[1] : "Sem etapa"),
            datacrazy: (l.tag_ids || []).some((t) => tagDC.has(t)),
            titulo: nomeLead(l),
        };
    };
    const leadsById = new Map();
    for (const l of raw.leadsExtra || []) leadsById.set(l.id, prep(l));
    const leads = (raw.leads || []).map(prep).filter((l) => inRange(l.entrada, start, end));
    for (const l of leads) leadsById.set(l.id, l);
    const leadsPrev = prevStart ? (raw.leadsPrev || []).map(prep).filter((l) => inRange(l.entrada, prevStart, prevEnd)) : null;
    const cohortIds = new Set(leads.map((l) => l.id));
    const total = leads.length;
    const countReached = (arr, i) => arr.filter((l) => l.reached >= i).length;

    // ---------------- ações (notas/e-mails + atividades concluídas + eventos de agenda)
    const acoesAll = [];
    for (const m of raw.mensagens || []) {
        const texto = stripHtml(m.body) || (m.subject || "").trim();
        if (!texto) continue;
        const tipo = classificarTexto(texto);
        acoesAll.push({
            key: "m" + m.id, dt: fromUtcSql(m.date), leadId: m.res_id,
            autor: m.author_id ? m.author_id[1] : "—", tipo, texto,
            semSucesso: RE_SEM_SUCESSO.test(texto.toLowerCase()),
            origem: m.message_type === "email" ? "E-mail" : "Nota",
        });
    }
    const eventosDeAtividade = new Set();
    for (const a of raw.atividades || []) {
        if (a.calendar_event_id) eventosDeAtividade.add(a.calendar_event_id[0]);
        if (a.active || !a.date_done) continue;
        const texto = [a.activity_type_id && a.activity_type_id[1], a.summary, stripHtml(a.feedback), stripHtml(a.note)]
            .filter(Boolean).join(" · ");
        let tipo;
        if (a.activity_category === "meeting") tipo = "reuniao";
        else if (a.activity_category === "phonecall") tipo = "ligacao";
        else if (/mail/i.test(a.activity_type_id ? a.activity_type_id[1] : "")) tipo = "email";
        else tipo = classificarTexto(texto);
        acoesAll.push({
            key: "a" + a.id, dt: fromDateStr(a.date_done).set({ hour: 12 }), leadId: a.res_id,
            autor: a.user_id ? a.user_id[1] : "—", tipo, texto,
            semSucesso: RE_SEM_SUCESSO.test(texto.toLowerCase()), origem: "Atividade", atividade: true,
        });
    }
    for (const e of raw.eventos || []) {
        if (!e.opportunity_id) continue;
        acoesAll.push({
            key: "e" + e.id, dt: fromUtcSql(e.create_date), leadId: e.opportunity_id[0],
            autor: e.user_id ? e.user_id[1] : "—", tipo: "reuniao",
            texto: tpl("Reunião na agenda: {nome} · {quando}", { nome: e.name, quando: fromUtcSql(e.start).toFormat("dd/MM HH:mm") }),
            semSucesso: false, origem: "Agenda",
        });
    }
    acoesAll.sort((a, b) => b.dt - a.dt || (a.key < b.key ? 1 : -1));
    const acoes = acoesAll.filter((a) => inRange(a.dt, start, end));
    const acoesPrev = prevStart ? acoesAll.filter((a) => inRange(a.dt, prevStart, prevEnd)) : null;

    // ---------------- 1º contato (B8): primeiro toque de saída por pessoa ou automação de contato
    const ehContato = (a) => TIPO[a.tipo].contato || (a.atividade && a.tipo !== "pesquisa");
    const primeiro = new Map();
    for (const a of acoesAll) {
        if (!cohortIds.has(a.leadId) || !ehContato(a)) continue;
        const l = leadsById.get(a.leadId);
        if (!l.entrada || a.dt < l.entrada) continue;
        if (!primeiro.has(a.leadId) || a.dt < primeiro.get(a.leadId)) primeiro.set(a.leadId, a.dt);
    }
    const horas = leads.filter((l) => primeiro.has(l.id)).map((l) => primeiro.get(l.id).diff(l.entrada, "hours").hours);
    const medianaH = mediana(horas);
    const ate1 = horas.filter((h) => h <= 1).length;
    const ate24 = horas.filter((h) => h <= 24).length;
    const semContato = leads.filter((l) => !primeiro.has(l.id));
    const tocouAlgumaVez = new Set(acoesAll.filter((a) => ehContato(a)).map((a) => a.leadId));
    const semContatoNunca = leads.filter((l) => !tocouAlgumaVez.has(l.id));

    // ---------------- reuniões (RN5: só dado estruturado)
    const reunioesAgendadas = (a, b) => {
        let n = 0;
        for (const e of raw.eventos || []) if (inRange(fromUtcSql(e.create_date), a, b)) n++;
        for (const at of raw.atividades || []) {
            if (at.activity_category !== "meeting") continue;
            if (at.calendar_event_id) continue; // já contado pelo evento
            if (inRange(fromUtcSql(at.create_date), a, b)) n++;
        }
        return n;
    };
    const reunioesRealizadas = (a, b) => {
        let n = 0;
        for (const e of raw.eventos || []) {
            const s = fromUtcSql(e.start);
            if (e.active !== false && s <= now && inRange(s, a, b)) n++;
        }
        for (const at of raw.atividades || []) {
            if (at.activity_category !== "meeting" || at.active || !at.date_done) continue;
            if (at.calendar_event_id && (raw.eventos || []).some((e) => e.id === at.calendar_event_id[0])) continue;
            if (inRange(fromDateStr(at.date_done), a, b)) n++;
        }
        return n;
    };
    const reun = reunioesAgendadas(start, end);
    const reunReal = reunioesRealizadas(start, end);
    const reunPrev = prevStart ? reunioesAgendadas(prevStart, prevEnd) : null;

    // ---------------- funil (coorte)
    const funnelOf = (arr) => {
        const steps = stages.map((s, i) => ({ key: s.id, name: s.name, idx: i, count: countReached(arr, i) }));
        steps.push({ key: "won", name: "Ganho", idx: nStages, count: arr.filter((l) => l.won).length });
        return steps;
    };
    const metas = new Map((raw.metas || []).filter((m) => m.x_taxa_alvo).map((m) => [norm(m.x_etapa), m.x_taxa_alvo]));
    const fSteps = funnelOf(leads);
    const funil = fSteps.map((s, i) => {
        const anterior = i ? fSteps[i - 1].count : null;
        const conv = anterior ? pct(s.count, anterior) : null;
        const meta = metas.get(norm(s.name));
        return {
            ...s,
            width: total ? Math.max(s.count ? 2 : 0, pct(s.count, total)) : 0,
            pctTotal: fmtPct(pct(s.count, total)),
            conv: i === 0 || !anterior ? null : fmtPct(conv),
            convClasse: meta === undefined || conv === null ? "neutro" : conv >= meta ? "bom" : "ruim",
            convTitulo: meta === undefined ? "Conversão da etapa anterior (sem meta configurada)" : `Meta: ${fmtPct(meta)}`,
            zero: s.count === 0,
            perdidosAqui: s.key === "won" ? 0 : leads.filter((l) => l.lost && l.reached === i).length,
        };
    });
    const funilNota = total && (per.dias === null ? false : per.dias < 29 || per.terminaHoje)
        ? "Leads recentes ainda em maturação; parte deles pode avançar nas próximas semanas."
        : "";

    // ---------------- saúde da base (leads do período, situação de hoje)
    const temProximaAtividade = new Set(
        (raw.atividades || []).filter((a) => a.active && fromDateStr(a.date_deadline) >= hoje).map((a) => a.res_id)
    );
    const abertos = leads.filter((l) => l.aberto);
    const parados = abertos.filter((l) => {
        const u = fromUtcSql(l.date_last_stage_update) || l.entrada;
        return u && now.diff(u, "days").days > 7 && !temProximaAtividade.has(l.id);
    });
    const semProxima = abertos.filter((l) => !temProximaAtividade.has(l.id));
    const perdidos = leads.filter((l) => l.lost);
    const motivos = rank(perdidos.filter((l) => l.lost_reason_id), (l) => l.lost_reason_id[1]);
    const situacao = rank(leads, (l) => l.etapa).map(([k, n]) => ({
        key: k, label: k, count: n,
        color: k === "Perdido" ? "#b91c1c" : k === "Ganho" ? "#047857"
            : ["#bfdbfe", "#60a5fa", "#2563eb", "#1e40af", "#172554"][Math.min(4, Math.max(0, stages.findIndex((s) => s.name === k)))],
    }));
    const amostra = (arr) => arr.slice(0, 5).map((l) => l.titulo).join(", ") + (arr.length > 5 ? "…" : "");
    const saude = [
        { key: "parados", label: "Parados há mais de 7 dias", hint: "abertos, sem mudar de etapa há 7+ dias e sem atividade futura", count: parados.length, ids: parados.map((l) => l.id), nomes: amostra(parados), classe: parados.length ? "atencao" : "" },
        { key: "sem_proxima", label: "Sem próxima atividade agendada", hint: "abertos sem atividade com prazo a partir de hoje", count: semProxima.length, ids: semProxima.map((l) => l.id), nomes: amostra(semProxima), classe: semProxima.length ? "atencao" : "" },
        { key: "sem_contato", label: "Sem nenhum contato registrado", hint: "nenhum WhatsApp, e-mail, ligação, convite, reunião ou atividade concluída", count: semContatoNunca.length, ids: semContatoNunca.map((l) => l.id), nomes: amostra(semContatoNunca), classe: semContatoNunca.length ? "atencao" : "" },
        { key: "perdidos", label: "Perdidos", hint: motivos.length ? tpl("motivo mais frequente: {m} ({n})", { m: motivos[0][0], n: motivos[0][1] }) : perdidos.length ? "motivo de perda não informado" : "", count: perdidos.length, ids: perdidos.map((l) => l.id), nomes: amostra(perdidos), classe: "" },
    ];

    // ---------------- KPIs (todos respeitam o filtro)
    const mql = countReached(leads, iMql);
    const sql = countReached(leads, iSql);
    const dl = (cur, prev, o = {}) => delta(cur, prev, { prevLabel: per.prevLabel, ...o });
    const kpis = [
        { key: "leads", icon: "fa-user-plus", label: "Leads", value: fmtInt(total), raw: total,
          sub: "novos no período", delta: dl(total, leadsPrev && leadsPrev.length),
          info: "Leads inbound (equipe Inbound Sétima, ativos e perdidos) com data de entrada no período. Entrada = criação no Pipedrive para migrados, senão criação no Odoo." },
        { key: "mql", icon: "fa-check", label: "MQL", value: fmtInt(mql), raw: mql,
          sub: tpl("{p} dos leads", { p: fmtPct(pct(mql, total)) }), delta: dl(mql, leadsPrev && countReached(leadsPrev, iMql)),
          info: "Leads do período cuja etapa atual é MQL ou posterior (ou ganhos). Critério de negócio: empresa que investe mais de R$ 100 mil/mês em marketing." },
        { key: "sql", icon: "fa-star", label: "SQL+", value: fmtInt(sql), raw: sql,
          sub: tpl("{p} dos MQLs", { p: fmtPct(pct(sql, mql)) }), delta: dl(sql, leadsPrev && countReached(leadsPrev, iSql)),
          info: "Leads do período cuja etapa atual é SQL, Oportunidade Sétima ou ganho." },
        { key: "reunioes", icon: "fa-handshake-o", label: "Reuniões", value: fmtInt(reun), raw: reun,
          sub: tpl("{n} realizadas", { n: fmtInt(reunReal) }), delta: dl(reun, reunPrev),
          info: "Só dado estruturado (RN5): eventos de agenda ligados a leads inbound ou atividades do tipo Reunião criados no período. Realizadas: evento já passado e não cancelado, ou atividade Reunião concluída. Mensagens pedindo agenda contam como “Convite para agendar”, não como reunião." },
        { key: "contato", icon: "fa-clock-o", label: "Tempo até 1º contato", value: fmtHoras(medianaH), raw: medianaH,
          sub: horas.length ? tpl("{p} em até 24 h", { p: fmtPct(pct(ate24, horas.length)) }) : "nenhum lead do período contatado",
          delta: null,
          info: "Mediana, em horas corridas (D1), entre a entrada do lead e o primeiro toque de saída: WhatsApp/DataCrazy, e-mail, ligação, convite, reunião ou atividade concluída. Notas de pesquisa/enriquecimento não contam." },
    ];
    if (prevStart) {
        const horasPrev = (() => {
            const pm = new Map();
            const prevIds = new Map((leadsPrev || []).map((l) => [l.id, l]));
            for (const a of acoesAll) {
                const l = prevIds.get(a.leadId);
                if (!l || !ehContato(a) || a.dt < l.entrada) continue;
                if (!pm.has(l.id) || a.dt < pm.get(l.id)) pm.set(l.id, a.dt);
            }
            return [...pm.entries()].map(([id, dt]) => dt.diff(prevIds.get(id).entrada, "hours").hours);
        })();
        const mp = mediana(horasPrev);
        if (mp !== null && medianaH !== null) {
            // polaridade inversa (menos horas = melhor); cor só com base anterior ≥ 10 contatados
            const d = Math.round(medianaH) - Math.round(mp);
            kpis[4].delta = {
                valor: d,
                texto: d === 0 ? "0 h" : `${d > 0 ? "+" : "–"}${fmtInt(Math.abs(d))} h`,
                seta: d > 0 ? "fa-arrow-up" : d < 0 ? "fa-arrow-down" : "fa-minus",
                classe: horasPrev.length < 10 || d === 0 ? "neutro" : d < 0 ? "bom" : "ruim",
                tooltip: `${per.prevLabel}: ${fmtHoras(mp)}`,
            };
        }
    }
    if (!prevStart) for (const k of kpis) k.delta = null;

    // ---------------- acumulado do processo (fixo — A5) + linha do período
    const contratos = (raw.contratos || [])
        .map((r) => ({ ...r, fechado: fromDateStr(r.x_studio_data_de_ganho) || fromUtcSql(r.date_closed), valor: r.expected_revenue || 0 }))
        .filter((c) => c.fechado);
    const desdeCfg = (raw.ajustes || {}).acumulado_desde;
    const desde = desdeCfg ? fromDateStr(desdeCfg) : contratos.length ? contratos.reduce((m, c) => (c.fechado < m ? c.fechado : m), contratos[0].fechado) : null;
    const validos = contratos.filter((c) => !desde || c.fechado >= desde.startOf("day")).sort((a, b) => b.fechado - a.fechado);
    const noPeriodo = validos.filter((c) => inRange(c.fechado, start, end));
    const receitaTotal = validos.reduce((t, c) => t + c.valor, 0);
    const receitaPeriodo = noPeriodo.reduce((t, c) => t + c.valor, 0);
    const conta = (d) => {
        const m = /^\s*\d+\/\d+\s*-\s*([^-]+?)\s*-/.exec(d.name || "");
        return (m ? m[1] : d.partner_id ? d.partner_id[1] : "").trim();
    };
    const acumulado = {
        desde: desde ? fmtDate(desde) : null,
        valor: fmtBrl(receitaTotal), valorRaw: receitaTotal,
        nContratos: validos.length,
        apoio: validos.length
            ? tpl("{n} {c} · ticket médio {t}", { n: fmtInt(validos.length), c: validos.length === 1 ? "contrato" : "contratos", t: fmtBrlCurto(receitaTotal / validos.length) })
            : "nenhum contrato marcado como “Originado no Inbound”",
        lista: validos.slice(0, 3).map((c) => ({
            id: c.id, nome: c.name, conta: conta(c), data: fmtDate(c.fechado), valor: fmtBrl(c.valor),
            novo: noPeriodo.some((x) => x.id === c.id),
        })),
        todosIds: validos.map((c) => c.id),
        periodoTexto: tpl("No período ({p}): {v} · {n} {c}", {
            p: per.labelCurto, v: fmtBrl(receitaPeriodo), n: fmtInt(noPeriodo.length), c: noPeriodo.length === 1 ? "contrato" : "contratos",
        }),
        periodoValorRaw: receitaPeriodo, periodoN: noPeriodo.length,
    };

    // ---------------- aquisição: entrada por dia/semana/mês e campanha
    const fonte = opts.serie === "mql" ? leads.filter((l) => l.reached >= iMql) : leads;
    const campRank = rank(leads, (l) => l.campanha);
    const coresUsadas = new Set();
    const campColor = new Map();
    for (const [k] of campRank) {
        const l = leads.find((x) => x.campanha === k);
        if (k === "Sem campanha") campColor.set(k, COR_SEM);
        else if (l.campanhaCor) { campColor.set(k, l.campanhaCor); coresUsadas.add(l.campanhaCor); }
    }
    let pi = 0;
    for (const [k] of campRank) {
        if (campColor.has(k)) continue;
        while (coresUsadas.has(PALETA[pi % PALETA.length]) && pi < PALETA.length * 2) pi++;
        campColor.set(k, PALETA[pi % PALETA.length]);
        coresUsadas.add(PALETA[pi % PALETA.length]);
        pi++;
    }
    const firstDt = start || (leads.length ? leads.reduce((m, l) => (l.entrada < m ? l.entrada : m), end) : end);
    const spanDias = Math.max(1, Math.round(end.diff(firstDt, "days").days));
    const unit = spanDias <= 45 ? "day" : spanDias <= 200 ? "week" : "month";
    const timeline = serie(fonte, (l) => l.entrada, (l) => l.campanha, campColor, firstDt, end, unit);
    const legendaCamp = rank(fonte, (l) => l.campanha).map(([k, n]) => ({
        key: k, label: k, count: n, color: campColor.get(k),
        nomeCompleto: [...new Set(leads.filter((l) => l.campanha === k).map((l) => l.campanhaNome))].join(" | "),
    }));

    // ---------------- resultado por dimensão (§7.6)
    const dimKey = opts.dim || "campanha";
    let linhas = rank(leads, (l) => l[dimKey]).map(([k, n]) => {
        const arr = leads.filter((l) => l[dimKey] === k);
        const m = countReached(arr, iMql);
        return {
            key: k, leads: n, share: fmtPct(pct(n, total)),
            mql: m, pctMql: fmtPct(pct(m, n)), pctMqlRaw: pct(m, n),
            sql: countReached(arr, iSql),
            ganhos: arr.filter((l) => l.won).length,
            perdidos: arr.filter((l) => l.lost).length,
            cor: dimKey === "campanha" ? campColor.get(k) : null,
            titulo: dimKey === "campanha" ? [...new Set(arr.map((l) => l.campanhaNome))].join(" | ") : k,
            ids: arr.map((l) => l.id),
        };
    });
    const sortKey = opts.sort || "leads";
    const sortDir = opts.sortDir === "asc" ? 1 : -1;
    const sortVal = (r) => (sortKey === "key" ? r.key : sortKey === "pctMql" ? r.pctMqlRaw : r[sortKey]);
    linhas.sort((a, b) => {
        const va = sortVal(a);
        const vb = sortVal(b);
        if (typeof va === "string") return sortDir * va.localeCompare(vb, "pt-BR");
        return sortDir * (va - vb) || b.leads - a.leads;
    });
    const maxL = Math.max(1, ...linhas.map((r) => r.leads));
    linhas.forEach((r) => (r.width = (r.leads * 100) / maxL));
    const totalLinha = {
        leads: total, mql, pctMql: fmtPct(pct(mql, total)), sql,
        ganhos: leads.filter((l) => l.won).length, perdidos: perdidos.length,
    };

    // ---------------- operação (B7, B9)
    const tocados = new Set(acoes.map((a) => a.leadId));
    const tocadosNovos = [...tocados].filter((id) => cohortIds.has(id)).length;
    const porTipo = TIPOS_ACAO.map((t) => ({
        ...t,
        total: acoes.filter((a) => a.tipo === t.key).length,
        semSucesso: acoes.filter((a) => a.tipo === t.key && a.semSucesso).length,
    }));
    const tipoColor = new Map(TIPOS_ACAO.map((t) => [t.key, t.color]));
    const timelineAcoes = serie(acoes, (a) => a.dt, (a) => a.tipo, tipoColor, firstDt, end, unit);
    const porPessoa = rank(acoes, (a) => a.autor).map(([k, n]) => ({ key: k, count: n, width: pct(n, Math.max(1, acoes.length)) }));
    const dcN = leads.filter((l) => l.datacrazy).length;
    const operacao = {
        tocados: tocados.size, tocadosNovos, tocadosAnteriores: tocados.size - tocadosNovos,
        tocadosTexto: tpl("{t} ({n} novos + {a} anteriores)", { t: fmtInt(tocados.size), n: fmtInt(tocadosNovos), a: fmtInt(tocados.size - tocadosNovos) }),
        toquesPorLead: tocados.size ? (acoes.length / tocados.size).toLocaleString("pt-BR", { maximumFractionDigits: 1 }) : "—",
        cobertura: tpl("{n}/{t} enviados ao DataCrazy ({p})", { n: fmtInt(dcN), t: fmtInt(total), p: fmtPct(pct(dcN, total)) }),
        coberturaN: dcN,
        dist: { ate1: ate1, de1a24: ate24 - ate1, mais24: horas.length - ate24, semContato: semContato.length },
        totalAcoes: acoes.length,
        deltaAcoes: prevStart ? dl(acoes.length, acoesPrev.length) : null,
    };

    // ---------------- registro de atividades (A1): até 100 no período, paginação no cliente
    const LIMITE = 100;
    const filtroTipo = opts.logTipo || "all";
    const logFiltrado = acoes.filter((a) => filtroTipo === "all" || a.tipo === filtroTipo);
    const ontem = hoje.minus({ days: 1 });
    const log = logFiltrado.slice(0, LIMITE).map((a) => {
        const l = leadsById.get(a.leadId);
        const estruturado = isBlocoEstruturado(a.texto);
        const dia = a.dt.startOf("day");
        return {
            key: a.key, leadId: a.leadId, tipo: TIPO[a.tipo], semSucesso: a.semSucesso,
            titulo: l ? l.titulo : `Lead #${a.leadId}`, etapa: l ? l.etapa : "",
            resumo: estruturado ? "Dados da empresa registrados" : a.texto,
            completo: a.texto, longo: estruturado || a.texto.length > 160, estruturado,
            quando: a.dt.toFormat("dd/MM/yyyy HH:mm"), autor: a.autor, origem: a.origem,
            dia: dia.hasSame(hoje, "day") ? "Hoje" : dia.hasSame(ontem, "day") ? "Ontem" : dia.toFormat("dd/MM"),
        };
    });

    // ---------------- leitura do período (A3) — regras determinísticas, templates
    const leitura = leituraDoPeriodo({
        per, total, leadsPrev, leads, mql, sql, iMql, stages, fSteps, horas, medianaH, ate24, parados,
        kpiPrev: leadsPrev ? { leads: leadsPrev.length, mql: countReached(leadsPrev, iMql), sql: countReached(leadsPrev, iSql) } : null,
        countReached,
    });

    return {
        periodo: per, total, kpis, leitura, acumulado, funil, funilNota, saude, situacao,
        donut: donut(situacao), timeline, legendaCamp, linhas, totalLinha, dimKey,
        operacao, porTipo, timelineAcoes, porPessoa, log, logTotal: logFiltrado.length, logLimite: LIMITE,
        // valores crus para reconciliação
        _rec: {
            leads: total, mql, sql, reunioes: reun, reunioesRealizadas: reunReal,
            perdidos: perdidos.length, ganhos: leads.filter((l) => l.won).length,
            mediana1oContatoHoras: medianaH, contatados: horas.length,
            datacrazy: dcN, acoes: acoes.length, leadsTocados: tocados.size,
            receitaAcumulada: receitaTotal, contratosAcumulados: validos.length,
            receitaPeriodo, contratosPeriodo: noPeriodo.length,
            funil: Object.fromEntries(fSteps.map((s) => [s.name, s.count])),
            leadsAnterior: leadsPrev ? leadsPrev.length : null,
            parados: parados.length, semProxima: semProxima.length, semContato: semContatoNunca.length,
        },
    };
}

function serie(items, dtFn, keyFn, colorMap, from, end, unit) {
    const buckets = [];
    let cur = from.startOf(unit === "week" ? "week" : unit);
    while (cur <= end && buckets.length < 400) {
        buckets.push({ start: cur, end: cur.endOf(unit), by: {}, total: 0 });
        cur = cur.plus({ [unit + "s"]: 1 });
    }
    for (const it of items) {
        const dt = dtFn(it);
        const b = dt && buckets.find((x) => dt >= x.start && dt <= x.end);
        if (b) {
            const k = keyFn(it);
            b.by[k] = (b.by[k] || 0) + 1;
            b.total += 1;
        }
    }
    const max = Math.max(1, ...buckets.map((b) => b.total));
    const fmt = unit === "month" ? "MM/yy" : "dd/MM";
    const passo = Math.ceil(buckets.length / 10);
    return {
        unit: unit === "day" ? "por dia" : unit === "week" ? "por semana" : "por mês",
        max, hasData: buckets.some((b) => b.total),
        bars: buckets.map((b, i) => ({
            key: i, label: b.start.toFormat(fmt), showLabel: buckets.length <= 10 || i % passo === 0,
            total: b.total,
            title: `${b.start.toFormat("dd/MM")}${unit !== "day" ? "–" + b.end.toFormat("dd/MM") : ""}: ${b.total}` +
                Object.entries(b.by).map(([k, n]) => ` · ${k}: ${n}`).join(""),
            segs: Object.entries(b.by).map(([k, n]) => ({ key: k, height: (n * 100) / max, color: colorMap.get(k) || COR_SEM })),
        })),
    };
}

function donut(items) {
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

function leituraDoPeriodo(c) {
    const { per, total, leads, mql, iMql, stages, fSteps, horas, medianaH, ate24, parados, kpiPrev } = c;
    const destaques = [];
    const atencao = [];
    const vs = per.prevLabel;
    // D1 — volume
    if (total) {
        destaques.push(kpiPrev
            ? tpl("{n} leads no período ({d} vs. {p}).", { n: fmtInt(total), d: sinal(total - kpiPrev.leads), p: vs })
            : tpl("{n} leads no período.", { n: fmtInt(total) }));
    } else {
        destaques.push("Nenhum lead entrou no período.");
    }
    const porDim = (dim) => {
        const m = new Map();
        for (const l of leads) {
            if (String(l[dim]).startsWith("Sem ")) continue;
            const r = m.get(l[dim]) || { k: l[dim], n: 0, mql: 0 };
            r.n += 1;
            if (l.reached >= iMql) r.mql += 1;
            m.set(l[dim], r);
        }
        return [...m.values()];
    };
    // D2 — campanha por volume e por taxa de MQL (base ≥ 3)
    const camps = porDim("campanha");
    if (total && camps.length) {
        const vol = [...camps].sort((a, b) => b.n - a.n)[0];
        const taxa = camps.filter((r) => r.n >= 3 && r.mql > 0).sort((a, b) => b.mql / b.n - a.mql / a.n || b.n - a.n)[0];
        if (taxa && taxa.k === vol.k) {
            destaques.push(tpl("{c} trouxe {n} leads ({p}) e teve a melhor taxa de MQL ({t}).", { c: vol.k, n: fmtInt(vol.n), p: fmtPct(pct(vol.n, total)), t: fmtPct(pct(taxa.mql, taxa.n)) }));
        } else if (taxa) {
            destaques.push(tpl("{c} trouxe {n} leads ({p}); {c2} teve a melhor taxa de MQL ({t}).", { c: vol.k, n: fmtInt(vol.n), p: fmtPct(pct(vol.n, total)), c2: taxa.k, t: fmtPct(pct(taxa.mql, taxa.n)) }));
        } else if (vol.n >= 3) {
            destaques.push(tpl("{c} trouxe {n} leads ({p}).", { c: vol.k, n: fmtInt(vol.n), p: fmtPct(pct(vol.n, total)) }));
        }
    }
    // D3 — melhor criativo / conjunto em MQL (base ≥ 3)
    const melhor = (dim) => porDim(dim).filter((r) => r.n >= 3 && r.mql > 0).sort((a, b) => b.mql / b.n - a.mql / a.n || b.n - a.n)[0];
    const cri = melhor("criativo");
    const con = melhor("conjunto");
    if (cri || con) {
        const partes = [];
        if (cri) partes.push(tpl("criativo {k} ({m} de {n}, {p})", { k: cri.k, m: fmtInt(cri.mql), n: fmtInt(cri.n), p: fmtPct(pct(cri.mql, cri.n)) }));
        if (con) partes.push(tpl("conjunto {k} ({m} de {n}, {p})", { k: con.k, m: fmtInt(con.mql), n: fmtInt(con.n), p: fmtPct(pct(con.mql, con.n)) }));
        destaques.push(tpl("Melhor em MQL: {x}.", { x: partes.join("; ") }));
    }
    // A1 — gargalo do funil (etapa anterior com ≥ 3 leads)
    let gargalo = null;
    for (let i = 1; i < fSteps.length; i++) {
        const ant = fSteps[i - 1];
        if (ant.count < 3) continue;
        const conv = fSteps[i].count / ant.count;
        if (!gargalo || conv < gargalo.conv) gargalo = { conv, ant, at: fSteps[i] };
    }
    if (gargalo && gargalo.conv < 0.5) {
        // siglas no plural ("MQLs"); demais etapas: "leads em Discovery"
        const nomeAnt = gargalo.ant.idx === 0 ? "leads" : /^[A-Z]{2,4}$/.test(gargalo.ant.name) ? gargalo.ant.name + "s" : `leads em ${gargalo.ant.name}`;
        atencao.push(gargalo.at.count === 0
            ? tpl("Nenhum dos {n} {e} avançou para {p}.", { n: fmtInt(gargalo.ant.count), e: nomeAnt, p: gargalo.at.name })
            : tpl("Só {m} de {n} {e} avançaram para {p} ({c}).", { m: fmtInt(gargalo.at.count), n: fmtInt(gargalo.ant.count), e: nomeAnt, p: gargalo.at.name, c: fmtPct(gargalo.conv * 100) }));
    }
    // A2 — SLA do 1º contato (D1: horas corridas)
    if (horas.length) {
        const fora = 100 - pct(ate24, horas.length);
        if (medianaH > 1 || pct(ate24, horas.length) < 80) {
            atencao.push(tpl("1º contato levou {h} (mediana); {p} passaram de 24 h.", { h: fmtHoras(medianaH), p: fmtPct(fora) }));
        }
    } else if (total) {
        atencao.push(tpl("Nenhum dos {n} leads do período tem contato registrado.", { n: fmtInt(total) }));
    }
    // A3 — queda relevante vs. período anterior (Δ absoluto ≥ 3 e ≥ 20%)
    if (kpiPrev) {
        for (const [k, nome, cur] of [["leads", "Leads", total], ["mql", "MQLs", mql], ["sql", "SQL+", c.sql]]) {
            const prev = kpiPrev[k];
            if (prev - cur >= 3 && pct(prev - cur, prev) >= 20) {
                atencao.push(tpl("{x} caíram de {a} para {b} (–{p}) vs. {v}.", { x: nome, a: fmtInt(prev), b: fmtInt(cur), p: fmtPct(pct(prev - cur, prev)), v: vs }));
            }
        }
    }
    // A4 — leads parados
    if (parados.length) {
        atencao.push(tpl("{n} {l} sem próxima ação há mais de 7 dias.", { n: fmtInt(parados.length), l: parados.length === 1 ? "lead parado" : "leads parados" }));
    }
    return {
        destaques: destaques.slice(0, 3),
        atencao: atencao.length ? atencao.slice(0, 3) : ["Sem pontos de atenção neste período."],
        _stages: stages.length,
    };
}
