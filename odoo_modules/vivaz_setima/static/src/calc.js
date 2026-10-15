/** @odoo-module **/
// Resultado comercial · Pipeline Sétima — funções PURAS de cálculo.
//
// Nada aqui toca DOM, ORM ou serviços do Odoo: recebe os registros crus (data.js) e o
// período e devolve o "modelo de tela". O mesmo arquivo roda no navegador (Odoo) e no
// Node (setima_resultados/scripts/valores_dashboard.mjs), o que permite conferir cada
// número com consultas independentes ao CRM. Datas sempre em America/Sao_Paulo.
//
// Depende só do luxon global (o Odoo já carrega; no Node o script injeta).

export const TZ = "America/Sao_Paulo";
export const TEAM_ID = 4; // crm.team "Pipeline Sétima" — resultado bruto da Sétima
const DT = () => globalThis.luxon.DateTime;

// ------------------------------------------------------------------ formatação pt-BR
export const fmtInt = (n) => Math.round(n || 0).toLocaleString("pt-BR");
export const fmtBrl = (v) => "R$ " + Math.round(v || 0).toLocaleString("pt-BR", { maximumFractionDigits: 0 });
export function fmtBrlCurto(v) {
    const n = v || 0;
    const f = (x) => x.toLocaleString("pt-BR", { maximumFractionDigits: 1 });
    if (Math.abs(n) >= 1e6) return `R$ ${f(n / 1e6)} mi`;
    if (Math.abs(n) >= 1e3) return `R$ ${f(n / 1e3)} mil`;
    return fmtBrl(n);
}
export const pct = (a, b) => (b ? (a * 100) / b : 0);
export const fmtPct = (v) => `${(Math.round((v || 0) * 10) / 10).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
export const fmtData = (d) => (d ? d.toFormat("dd/MM/yyyy") : "—");
export function fmtIntervalo(a, b) {
    if (!a) return `todo o histórico até ${b.toFormat("dd/MM/yyyy")}`;
    if (a.hasSame(b, "day")) return a.toFormat("dd/MM/yyyy");
    if (a.hasSame(b, "month")) return `${a.toFormat("dd")}–${b.toFormat("dd/MM/yyyy")}`;
    if (a.hasSame(b, "year")) return `${a.toFormat("dd/MM")}–${b.toFormat("dd/MM/yyyy")}`;
    return `${a.toFormat("dd/MM/yyyy")}–${b.toFormat("dd/MM/yyyy")}`;
}
const MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

// ------------------------------------------------------------------ período
export const PRESETS = [
    { key: "this_month", label: "Este mês" },
    { key: "prev_month", label: "Mês anterior" },
    { key: "quarter", label: "Trimestre" },
    { key: "year", label: "Este ano" },
    { key: "prev_year", label: "Ano anterior" },
    { key: "12m", label: "12 meses" },
    { key: "all", label: "Tudo" },
    { key: "custom", label: "Personalizado" },
];
export const PRESET_PADRAO = "year";

/** Período e período de comparação. Mês/trimestre/ano comparam com os mesmos dias do anterior. */
export function periodo(preset, fromIso, toIso, now) {
    const hoje = (now || DT().now()).setZone(TZ).startOf("day");
    let start = null;
    let end = hoje;
    if (preset === "this_month") start = hoje.startOf("month");
    else if (preset === "quarter") start = hoje.startOf("quarter");
    else if (preset === "year") start = hoje.startOf("year");
    else if (preset === "12m") start = hoje.minus({ months: 12 }).plus({ days: 1 });
    else if (preset === "prev_month") {
        start = hoje.minus({ months: 1 }).startOf("month");
        end = start.endOf("month").startOf("day");
    } else if (preset === "prev_year") {
        start = hoje.minus({ years: 1 }).startOf("year");
        end = start.endOf("year").startOf("day");
    } else if (preset === "custom") {
        start = fromIso ? DT().fromISO(fromIso, { zone: TZ }).startOf("day") : hoje.startOf("year");
        end = toIso ? DT().fromISO(toIso, { zone: TZ }).startOf("day") : hoje;
        if (end < start) [start, end] = [end, start];
    }
    end = end.endOf("day");
    let prevStart = null;
    let prevEnd = null;
    if (start) {
        const cal = { this_month: { months: 1 }, prev_month: { months: 1 }, quarter: { months: 3 }, year: { years: 1 }, prev_year: { years: 1 }, "12m": { years: 1 } }[preset];
        if (cal) {
            prevStart = start.minus(cal);
            prevEnd = preset === "prev_month" ? prevStart.endOf("month") : end.minus(cal).endOf("day");
        } else {
            const dias = Math.round(end.startOf("day").diff(start, "days").days) + 1;
            prevEnd = start.minus({ days: 1 }).endOf("day");
            prevStart = start.minus({ days: dias });
        }
    }
    return {
        preset, start, end, prevStart, prevEnd, hoje,
        label: fmtIntervalo(start, end),
        prevLabel: prevStart ? fmtIntervalo(prevStart, prevEnd) : null,
    };
}
export const toUtcSql = (d) => d.toUTC().toFormat("yyyy-MM-dd HH:mm:ss");
/** Campo date ("yyyy-MM-dd") ou datetime UTC ("yyyy-MM-dd HH:mm:ss") → DateTime local. */
export function dataLocal(s) {
    if (!s) return null;
    return s.length <= 10 ? DT().fromISO(s, { zone: TZ }) : DT().fromSQL(s, { zone: "utc" }).setZone(TZ);
}
const dentro = (d, a, b) => !!d && (!a || d >= a) && d <= b;

// ------------------------------------------------------------------ domínio
export const BASE_DOMAIN = [["team_id", "=", TEAM_ID], ["type", "=", "opportunity"], ["active", "in", [true, false]]];
const RE_TESTE = /^\s*teste\b/i; // negócios de teste ("Teste Flávia") não entram em nenhum número

// ------------------------------------------------------------------ clientes
// Mesmo cliente cadastrado com nomes diferentes no CRM (empresa comercial do contato).
export const ALIAS_CLIENTE = {
    "vw": "Volkswagen do Brasil",
    "volkswagen": "Volkswagen do Brasil",
    "espaçolaser": "Espaço Laser",
};
export const SEM_CLIENTE = "(sem cliente)";

// ------------------------------------------------------------------ tipo de projeto
// O CRM não tem campo de tipo/segmento: o tipo vem de uma etiqueta "Tipo: …" no negócio
// (prevalece) ou, sem ela, do nome do projeto (palavra-chave, primeira regra que casa).
export const TIPOS = [
    { key: "fee", label: "Fee / escopo recorrente", color: "#4d7c0f", re: /\bfee\b|escopo geral|retainer/ },
    { key: "lives", label: "Lives e transmissões", color: "#be185d", re: /\blives?\b|transmiss|webinar|streaming/ },
    { key: "3d", label: "3D, CGI e interativos", color: "#1d4ed8", re: /\b[23]d\b|cgi|render|anima[çc]|motion|beauty ?shot|pac?k ?shot|ddx|manual cognitivo|interativ|interactive|configurador|realidade (virtual|aumentada)/ },
    { key: "evento", label: "Eventos e experiências", color: "#b45309", re: /cobertura|after ?movie|making ?of|evento|conven[çc][ãa]o|congresso|estande|feira|roadshow|cerim[ôo]nia|ativa[çc][ãa]o|a[çc][ãa]o social|experi[êe]nc|festival|oktoberfest|happy hour|lan[çc]amento|brand day|encontro|caravana|fenatran|pitch day/ },
    { key: "foto", label: "Foto e still", color: "#0e7490", re: /\bfotos?\b|still|photo|banco de imagens|imagens|footage/ },
    { key: "estrategia", label: "Estratégia, marca e design", color: "#6d28d9", re: /planejamento|branding|\bmarca\b|naming|design|\blogo|\bkv'?s?\b|identidade|embalage|livro|apresenta|\bppt\b|interface|estudo|consultoria|treinamento|\bgtm\b|estrat|differentiation/ },
    { key: "midia", label: "Conteúdo, social e mídia", color: "#047857", re: /m[íi]dia|redes sociais|social|tiktok|creator|conte[úu]do|influenc|pe[çc]as|podcast|vinheta/ },
    { key: "producao", label: "Brindes e produção gráfica", color: "#9a3412", re: /brinde|camiseta|garrafa|adesiv|\bkit\b|selo|sinaliza|impress|badge|pixel map/ },
    { key: "video", label: "Vídeo e filme", color: "#334155", re: /v[íi]deo|filme|s[ée]rie|depoimento|\bdep\b|document|walk ?around|edi[çc][ãa]o|institucional|release|legenda|capta[çc]|\bclip|manifesto|grava[çc]|tutorial|reels|locu[çc]|teaser|onboarding/ },
    { key: "campanha", label: "Campanhas e concorrências", color: "#a16207", re: /campanha|concorr[êe]ncia|\bbid\b|\brfp\b|\bpack\b/ },
];
export const TIPO_OUTROS = { key: "outros", label: "Outros / não classificado", color: "#94a3b8" };
const TIPO_POR_KEY = Object.fromEntries([...TIPOS, TIPO_OUTROS].map((t) => [t.key, t]));
const normTxt = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().trim();

export function classificarTipo(nome, tagsNomes = []) {
    for (const tg of tagsNomes) {
        const m = /^tipo\s*:\s*(.+)$/i.exec(tg || "");
        if (!m) continue;
        const alvo = normTxt(m[1]);
        const t = [...TIPOS, TIPO_OUTROS].find((x) => normTxt(x.label) === alvo || normTxt(x.label).startsWith(alvo) || x.key === alvo);
        return t || { key: `tag:${alvo}`, label: m[1].trim(), color: "#64748b" };
    }
    const t = String(nome || "").toLowerCase();
    return TIPOS.find((x) => x.re.test(t)) || TIPO_OUTROS;
}

// ------------------------------------------------------------------ helpers
export function mediana(arr) {
    if (!arr.length) return null;
    const s = [...arr].sort((a, b) => a - b);
    const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}
const soma = (arr, f = (x) => x.valor) => arr.reduce((t, x) => t + (f(x) || 0), 0);
/** Variação % com polaridade. Sem base anterior não há %; abaixo de min, cor neutra. */
export function variacao(cur, prev, { fmt = fmtInt, prevLabel = "", inverso = false, pp = false } = {}) {
    if (prev === null || prev === undefined) return null;
    const d = cur - prev;
    const seta = d > 0 ? "fa-arrow-up" : d < 0 ? "fa-arrow-down" : "fa-minus";
    const tooltip = `${prevLabel}: ${fmt(prev)}`;
    if (pp) { // variação em pontos percentuais (taxas)
        const v = Math.round(d * 10) / 10;
        return { valor: d, seta, tooltip, texto: `${v > 0 ? "+" : v < 0 ? "–" : ""}${fmtPct(Math.abs(v)).replace("%", "")} p.p.`, classe: v === 0 ? "neutro" : (inverso ? v < 0 : v > 0) ? "bom" : "ruim" };
    }
    if (!prev) return { valor: d, seta, tooltip, texto: cur ? "sem base" : "0", classe: "neutro" };
    const p = pct(d, prev);
    return { valor: d, seta, tooltip, texto: `${p > 0 ? "+" : p < 0 ? "–" : ""}${fmtPct(Math.abs(p))}`, classe: Math.abs(p) < 0.05 ? "neutro" : (inverso ? d < 0 : d > 0) ? "bom" : "ruim" };
}

// ------------------------------------------------------------------ preparação
/** Registros crus → negócios normalizados (cliente, tipo, datas locais). Sem negócios de teste. */
export function prepararNegocios(raw) {
    const parceiros = new Map((raw.parceiros || []).map((p) => [p.id, p]));
    const tags = new Map((raw.tags || []).map((t) => [t.id, t.name]));
    const etapas = new Map((raw.stages || []).map((s) => [s.id, s]));
    const out = [];
    for (const l of raw.negocios || []) {
        if (RE_TESTE.test(l.name || "")) continue;
        const p = l.partner_id ? parceiros.get(l.partner_id[0]) : null;
        const com = p && p.commercial_partner_id ? p.commercial_partner_id : l.partner_id;
        let cliente = com ? com[1] : SEM_CLIENTE;
        cliente = ALIAS_CLIENTE[cliente.trim().toLowerCase()] || cliente.trim();
        const tipo = classificarTipo(l.name, (l.tag_ids || []).map((id) => tags.get(id)).filter(Boolean));
        const ganho = l.won_status === "won"
            ? dataLocal(l.x_studio_data_de_ganho) || dataLocal(l.x_pipedrive_won_time) || dataLocal(l.date_closed) : null;
        const perda = l.won_status === "lost" ? dataLocal(l.date_closed) || dataLocal(l.x_pipedrive_lost_time) : null;
        const etapa = l.stage_id ? etapas.get(l.stage_id[0]) : null;
        out.push({
            id: l.id,
            nome: (l.name || "").trim(),
            valor: l.expected_revenue || 0,
            prob: l.probability || 0,
            status: l.won_status,
            entrada: dataLocal(l.x_pipedrive_add_time) || dataLocal(l.create_date),
            ganho,
            perda,
            mudouEtapa: dataLocal(l.date_last_stage_update),
            previsao: dataLocal(l.date_deadline),
            etapaId: l.stage_id ? l.stage_id[0] : null,
            etapaNome: l.stage_id ? l.stage_id[1] : "—",
            etapaSeq: etapa ? etapa.sequence : 999,
            vendedor: l.user_id ? l.user_id[1] : "Sem vendedor",
            cliente,
            setor: p && p.industry_id ? p.industry_id[1] : null,
            tipo,
            motivo: l.lost_reason_id ? l.lost_reason_id[1] : "Motivo não informado",
        });
    }
    return out;
}

// ------------------------------------------------------------------ cálculo principal
/**
 * @param raw   registros de data.js
 * @param per   resultado de periodo()
 * @param opts  { serie: "receita"|"pipeline", clientesTodos: bool, ordem: {chave, dir} }
 */
export function calcular(raw, per, opts = {}) {
    const ns = raw._negocios || prepararNegocios(raw);
    const { start, end, prevStart, prevEnd, hoje } = per;
    const fimHoje = hoje.endOf("day");

    const ganhos = (a, b) => ns.filter((n) => n.status === "won" && dentro(n.ganho, a, b));
    const perdidos = (a, b) => ns.filter((n) => n.status === "lost" && dentro(n.perda, a, b));
    const gerados = (a, b) => ns.filter((n) => dentro(n.entrada, a, b));
    const temPrev = !!prevStart;

    const gP = ganhos(start, end);
    const pP = perdidos(start, end);
    const geP = gerados(start, end);
    const gA = temPrev ? ganhos(prevStart, prevEnd) : null;
    const pA = temPrev ? perdidos(prevStart, prevEnd) : null;
    const geA = temPrev ? gerados(prevStart, prevEnd) : null;
    const abertos = ns.filter((n) => n.status === "pending");

    const resumo = (g, p, ge) => {
        const comValor = g.filter((n) => n.valor > 0);
        const receita = soma(g);
        return {
            receita, n: g.length, nComValor: comValor.length,
            ticket: comValor.length ? receita / comValor.length : 0,
            clientes: new Set(g.map((n) => n.cliente)).size,
            conv: g.length + p.length ? pct(g.length, g.length + p.length) : null,
            convValor: soma(g) + soma(p) ? pct(soma(g), soma(g) + soma(p)) : null,
            fechados: g.length + p.length,
            gerado: soma(ge), nGerado: ge.length, geradoSemValor: ge.filter((n) => !n.valor).length,
            ciclo: mediana(g.filter((n) => n.entrada && n.ganho >= n.entrada).map((n) => n.ganho.diff(n.entrada, "days").days)),
        };
    };
    const R = resumo(gP, pP, geP);
    const A = temPrev ? resumo(gA, pA, geA) : null;
    const pl = per.prevLabel;
    const v = (k, o = {}) => (A ? variacao(R[k] ?? 0, A[k] ?? 0, { prevLabel: pl, ...o }) : null);

    // primeira vitória de cada cliente (para "cliente novo")
    const primeiraVitoria = new Map();
    for (const n of ns) {
        if (n.status !== "won" || !n.ganho) continue;
        const f = primeiraVitoria.get(n.cliente);
        if (!f || n.ganho < f) primeiraVitoria.set(n.cliente, n.ganho);
    }
    const ehNovo = (c) => dentro(primeiraVitoria.get(c), start, end);

    // ---------------- KPIs (respeitam o filtro)
    const kpis = [
        { key: "receita", icon: "fa-money", label: "Receita no período", value: fmtBrlCurto(R.receita), titulo: fmtBrl(R.receita),
          sub: `${fmtInt(R.n)} projeto(s) ganho(s)`, delta: v("receita", { fmt: fmtBrl }), ids: gP.map((n) => n.id),
          info: "Soma do valor dos negócios ganhos no Pipeline Sétima com data de ganho no período. Data de ganho = campo “Data de Ganho”, senão a data do Pipedrive (migrados), senão a data de fechamento do CRM." },
        { key: "ganhos", icon: "fa-trophy", label: "Negócios ganhos", value: fmtInt(R.n),
          sub: R.n - R.nComValor ? `${fmtInt(R.n - R.nComValor)} sem valor no CRM` : "projetos fechados", delta: v("n"), ids: gP.map((n) => n.id),
          info: "Quantidade de negócios ganhos (projetos) com data de ganho no período." },
        { key: "ticket", icon: "fa-tag", label: "Ticket médio por projeto", value: fmtBrlCurto(R.ticket), titulo: fmtBrl(R.ticket),
          sub: R.n ? `mediana ${fmtBrlCurto(mediana(gP.filter((n) => n.valor > 0).map((n) => n.valor)) || 0)}` : "sem projetos ganhos", delta: v("ticket", { fmt: fmtBrl }), ids: gP.map((n) => n.id),
          info: "Receita do período ÷ projetos ganhos com valor (negócios ganhos com valor zero não entram na média). A mediana mostra o projeto “típico”, sem a distorção dos grandes contratos." },
        { key: "clientes", icon: "fa-building-o", label: "Clientes atendidos", value: fmtInt(R.clientes),
          sub: (() => { const novos = [...new Set(gP.map((n) => n.cliente))].filter(ehNovo).length; return novos ? `${fmtInt(novos)} novo(s) na base` : "todos recorrentes"; })(),
          delta: v("clientes"), ids: gP.map((n) => n.id),
          info: "Clientes distintos (empresa do contato) com pelo menos um projeto ganho no período. Novo = primeira vitória do cliente no histórico do CRM cai dentro do período." },
        { key: "conv", icon: "fa-percent", label: "Taxa de conversão", value: R.conv === null ? "—" : fmtPct(R.conv),
          sub: R.fechados ? `${fmtInt(R.n)} ganhos de ${fmtInt(R.fechados)} decididos` : "nenhum negócio decidido",
          delta: A && R.conv !== null && A.conv !== null ? variacao(R.conv, A.conv, { prevLabel: pl, fmt: fmtPct, pp: true }) : null,
          ids: [...gP, ...pP].map((n) => n.id),
          info: "Ganhos ÷ (ganhos + perdidos) decididos no período, em quantidade. Em valor: " + (R.convValor === null ? "—" : fmtPct(R.convValor)) + "." },
        { key: "gerado", icon: "fa-filter", label: "Pipeline gerado", value: fmtBrlCurto(R.gerado), titulo: fmtBrl(R.gerado),
          sub: `${fmtInt(R.nGerado)} oportunidade(s)${R.geradoSemValor ? ` · ${fmtInt(R.geradoSemValor)} sem valor` : ""}`,
          delta: v("gerado", { fmt: fmtBrl }), ids: geP.map((n) => n.id),
          info: "Valor das oportunidades que entraram no pipeline no período (qualquer situação atual). Entrada = criação no Pipedrive para migrados, senão criação no Odoo." },
    ];
    if (!temPrev) for (const k of kpis) k.delta = null;

    // ---------------- acumulado do ano (fixo, não muda com o filtro)
    const iniAno = hoje.startOf("year");
    const gAno = ganhos(iniAno, fimHoje);
    const gAnoAnt = ganhos(iniAno.minus({ years: 1 }), fimHoje.minus({ years: 1 }));
    const geAno = gerados(iniAno, fimHoje);
    const recAno = soma(gAno);
    const recAnoAnt = soma(gAnoAnt);
    const comValorAno = gAno.filter((n) => n.valor > 0);
    const recPeriodoNoAno = soma(gP.filter((n) => n.ganho >= iniAno));
    const acumulado = {
        ano: hoje.year,
        ate: hoje.toFormat("dd/MM"),
        valor: fmtBrl(recAno),
        delta: variacao(recAno, recAnoAnt, { fmt: fmtBrl, prevLabel: `01/01–${hoje.toFormat("dd/MM")}/${hoje.year - 1}` }),
        apoio: `${fmtInt(gAno.length)} projetos · ${fmtInt(new Set(gAno.map((n) => n.cliente)).size)} clientes · ticket ${fmtBrlCurto(comValorAno.length ? recAno / comValorAno.length : 0)}`,
        gerado: `${fmtBrlCurto(soma(geAno))} em ${fmtInt(geAno.length)} oportunidades geradas no ano`,
        lista: [...gAno].sort((a, b) => b.valor - a.valor).slice(0, 3).map((n) => ({
            id: n.id, nome: n.nome, conta: n.cliente, data: n.ganho.toFormat("dd/MM"), valor: fmtBrlCurto(n.valor),
        })),
        todosIds: gAno.map((n) => n.id),
        nProjetos: gAno.length,
        periodoTexto: per.preset === "year" ? "o filtro atual é o próprio ano"
            : recPeriodoNoAno ? `${fmtBrlCurto(recPeriodoNoAno)} do ano estão no período filtrado (${fmtPct(pct(recPeriodoNoAno, recAno))})`
            : "nenhuma receita do ano no período filtrado",
        periodoTem: recPeriodoNoAno > 0,
    };

    // ---------------- evolução mensal (ano do fim do período × ano anterior)
    const anoRef = end.year;
    const mensal = (ano, serie) => MESES.map((_, i) => {
        const a = DT().fromObject({ year: ano, month: i + 1, day: 1 }, { zone: TZ });
        const b = a.endOf("month");
        return serie === "pipeline" ? soma(gerados(a, b)) : soma(ganhos(a, b));
    });
    const serie = opts.serie === "pipeline" ? "pipeline" : "receita";
    const atual = mensal(anoRef, serie);
    const anterior = mensal(anoRef - 1, serie);
    const maxM = Math.max(1, ...atual, ...anterior);
    const mesAtual = hoje.year === anoRef ? hoje.month : 13;
    const evolucao = {
        anoRef, serie,
        totalAtual: fmtBrlCurto(soma(atual, (x) => x)),
        totalAnterior: fmtBrlCurto(soma(anterior.slice(0, Math.min(12, mesAtual)), (x) => x)),
        meses: MESES.map((m, i) => ({
            key: m, label: m,
            atual: atual[i], anterior: anterior[i],
            hAtual: Math.round((atual[i] * 100) / maxM), hAnterior: Math.round((anterior[i] * 100) / maxM),
            rotulo: atual[i] ? fmtBrlCurto(atual[i]).replace("R$ ", "") : "",
            futuro: i + 1 > mesAtual,
            noPeriodo: (() => { const a = DT().fromObject({ year: anoRef, month: i + 1, day: 1 }, { zone: TZ }); return (!start || a.endOf("month") >= start) && a <= end; })(),
            title: `${m}/${anoRef}: ${fmtBrl(atual[i])} · ${m}/${anoRef - 1}: ${fmtBrl(anterior[i])}`,
        })),
        max: fmtBrlCurto(maxM),
        hasData: atual.some(Boolean) || anterior.some(Boolean),
    };

    // ---------------- histórico anual
    const anosGanho = ns.filter((n) => n.status === "won" && n.ganho).map((n) => n.ganho.year);
    const anoMin = anosGanho.length ? Math.min(...anosGanho) : hoje.year;
    const historico = [];
    for (let ano = hoje.year; ano >= anoMin; ano--) {
        const a = DT().fromObject({ year: ano, month: 1, day: 1 }, { zone: TZ });
        const corrente = ano === hoje.year;
        const b = corrente ? fimHoje : a.endOf("year");
        const g = ganhos(a, b);
        const cv = g.filter((n) => n.valor > 0);
        const rec = soma(g);
        // ano corrente compara com o mesmo período do ano anterior (YTD × YTD)
        const recAntComp = soma(ganhos(a.minus({ years: 1 }), b.minus({ years: 1 })));
        historico.push({
            key: ano, ano: corrente ? `${ano} (até ${hoje.toFormat("dd/MM")})` : String(ano),
            receita: fmtBrl(rec), receitaRaw: rec, n: g.length,
            ticket: fmtBrlCurto(cv.length ? rec / cv.length : 0),
            clientes: new Set(g.map((n) => n.cliente)).size,
            gerado: fmtBrlCurto(soma(gerados(a, b))),
            delta: ano > anoMin ? variacao(rec, recAntComp, { fmt: fmtBrl, prevLabel: corrente ? `mesmo período de ${ano - 1}` : String(ano - 1) }) : null,
            ids: g.map((n) => n.id),
        });
    }
    const maxHist = Math.max(1, ...historico.map((h) => h.receitaRaw));
    for (const h of historico) h.width = Math.round((h.receitaRaw * 100) / maxHist);

    // ---------------- clientes do período
    const porCliente = new Map();
    for (const n of gP) {
        const c = porCliente.get(n.cliente) || { key: n.cliente, receita: 0, n: 0, ids: [], ultimo: null, tipos: new Map() };
        c.receita += n.valor; c.n += 1; c.ids.push(n.id);
        if (!c.ultimo || n.ganho > c.ultimo) c.ultimo = n.ganho;
        c.tipos.set(n.tipo.label, (c.tipos.get(n.tipo.label) || 0) + n.valor);
        porCliente.set(n.cliente, c);
    }
    const clientesOrd = [...porCliente.values()].sort((a, b) => b.receita - a.receita || b.n - a.n);
    const maxCli = Math.max(1, ...clientesOrd.map((c) => c.receita));
    const clientes = clientesOrd.map((c, i) => ({
        key: c.key, pos: i + 1, receita: fmtBrl(c.receita), receitaRaw: c.receita, n: c.n,
        share: fmtPct(pct(c.receita, R.receita)), width: Math.round((c.receita * 100) / maxCli),
        ticket: fmtBrlCurto(c.n ? c.receita / c.n : 0), ultimo: c.ultimo ? c.ultimo.toFormat("dd/MM/yy") : "—",
        tipoPrincipal: [...c.tipos.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] || "—",
        novo: ehNovo(c.key), ids: c.ids,
    }));
    const top = (k) => pct(soma(clientesOrd.slice(0, k), (c) => c.receita), R.receita);
    const novosCli = clientes.filter((c) => c.novo);
    const concentracao = {
        top1: clientesOrd.length ? fmtPct(top(1)) : "—", top1Nome: clientesOrd[0]?.key || "",
        top1Raw: clientesOrd.length ? top(1) : 0,
        top5: clientesOrd.length ? fmtPct(top(5)) : "—",
        novos: novosCli.length, novosReceita: fmtBrlCurto(soma(novosCli, (c) => c.receitaRaw)),
    };

    // ---------------- projetos do período
    const projetos = [...gP].sort((a, b) => b.valor - a.valor).slice(0, 10).map((n) => ({
        id: n.id, nome: n.nome, cliente: n.cliente, tipo: n.tipo.label, cor: n.tipo.color,
        vendedor: n.vendedor, data: n.ganho.toFormat("dd/MM/yy"), valor: fmtBrl(n.valor),
        share: fmtPct(pct(n.valor, R.receita)),
    }));

    // ---------------- tipo de projeto
    const tiposMap = new Map();
    const tipoDe = (t) => {
        if (!tiposMap.has(t.key)) tiposMap.set(t.key, { tipo: t, g: [], p: [], ab: [] });
        return tiposMap.get(t.key);
    };
    for (const n of gP) tipoDe(n.tipo).g.push(n);
    for (const n of pP) tipoDe(n.tipo).p.push(n);
    for (const n of abertos) tipoDe(n.tipo).ab.push(n);
    const tiposOrd = [...tiposMap.values()].sort((a, b) => soma(b.g) - soma(a.g) || soma(b.ab) - soma(a.ab));
    const maxTipo = Math.max(1, ...tiposOrd.map((t) => soma(t.g)));
    const tipos = tiposOrd.map((t) => {
        const rec = soma(t.g);
        const cv = t.g.filter((n) => n.valor > 0);
        return {
            key: t.tipo.key, label: t.tipo.label, cor: t.tipo.color,
            receita: fmtBrl(rec), receitaRaw: rec, share: fmtPct(pct(rec, R.receita)), width: Math.round((rec * 100) / maxTipo),
            n: t.g.length, ticket: cv.length ? fmtBrlCurto(rec / cv.length) : "—",
            conv: t.g.length + t.p.length ? fmtPct(pct(t.g.length, t.g.length + t.p.length)) : "—",
            aberto: soma(t.ab) ? fmtBrlCurto(soma(t.ab)) : "—", nAberto: t.ab.length,
            ids: [...t.g, ...t.p].map((n) => n.id), idsAbertos: t.ab.map((n) => n.id),
        };
    });
    const donutTipos = (() => {
        const C = 100; // circunferência normalizada (r = 15.915)
        let acc = 0;
        const segs = tipos.filter((t) => t.receitaRaw > 0).map((t) => {
            const frac = (t.receitaRaw * C) / (R.receita || 1);
            const seg = { key: t.key, color: t.cor, dash: `${frac} ${C - frac}`, offset: String(25 - acc) };
            acc += frac;
            return seg;
        });
        return { segs, total: fmtBrlCurto(R.receita) };
    })();

    // ---------------- vendedores (só aparece com 2+ vendedores no período)
    const vendMap = new Map();
    const vendDe = (nome) => {
        if (!vendMap.has(nome)) vendMap.set(nome, { key: nome, g: [], p: [], ge: [], ab: [] });
        return vendMap.get(nome);
    };
    for (const n of gP) vendDe(n.vendedor).g.push(n);
    for (const n of pP) vendDe(n.vendedor).p.push(n);
    for (const n of geP) vendDe(n.vendedor).ge.push(n);
    for (const n of abertos) if (vendMap.has(n.vendedor)) vendMap.get(n.vendedor).ab.push(n);
    const vendOrd = [...vendMap.values()].filter((x) => x.g.length || x.ge.length)
        .sort((a, b) => soma(b.g) - soma(a.g) || soma(b.ge) - soma(a.ge));
    const maxVend = Math.max(1, ...vendOrd.map((x) => soma(x.g)));
    const vendedores = vendOrd.map((x) => {
        const rec = soma(x.g);
        const cv = x.g.filter((n) => n.valor > 0);
        return {
            key: x.key, receita: fmtBrl(rec), receitaRaw: rec, share: fmtPct(pct(rec, R.receita)), width: Math.round((rec * 100) / maxVend),
            n: x.g.length, ticket: cv.length ? fmtBrlCurto(rec / cv.length) : "—",
            conv: x.g.length + x.p.length ? fmtPct(pct(x.g.length, x.g.length + x.p.length)) : "—",
            gerado: soma(x.ge) ? fmtBrlCurto(soma(x.ge)) : "—", nGerado: x.ge.length,
            aberto: soma(x.ab) ? fmtBrlCurto(soma(x.ab)) : "—", nAberto: x.ab.length,
            ids: [...x.g, ...x.p, ...x.ge].map((n) => n.id),
        };
    });

    // ---------------- pipeline aberto (hoje) e saúde
    const etapasAbertas = (raw.stages || []).filter((s) => !s.is_won).sort((a, b) => a.sequence - b.sequence || a.id - b.id);
    const valorAberto = soma(abertos);
    const maxEtapa = Math.max(1, ...etapasAbertas.map((s) => soma(abertos.filter((n) => n.etapaId === s.id))));
    const funil = etapasAbertas.map((s) => {
        const it = abertos.filter((n) => n.etapaId === s.id);
        const val = soma(it);
        return {
            key: s.id, nome: s.name, n: it.length, valor: fmtBrlCurto(val), valorRaw: val,
            ponderado: fmtBrlCurto(soma(it, (n) => (n.valor * n.prob) / 100)),
            semValor: it.filter((n) => !n.valor).length,
            width: Math.round((val * 100) / maxEtapa), ids: it.map((n) => n.id),
        };
    });
    const forasDoFunil = abertos.filter((n) => !etapasAbertas.some((s) => s.id === n.etapaId));
    if (forasDoFunil.length) {
        funil.push({ key: "outras", nome: "Outras etapas", n: forasDoFunil.length, valor: fmtBrlCurto(soma(forasDoFunil)), valorRaw: soma(forasDoFunil),
            ponderado: fmtBrlCurto(soma(forasDoFunil, (n) => (n.valor * n.prob) / 100)), semValor: forasDoFunil.filter((n) => !n.valor).length,
            width: Math.round((soma(forasDoFunil) * 100) / maxEtapa), ids: forasDoFunil.map((n) => n.id) });
    }
    const semValor = abertos.filter((n) => !n.valor);
    const parados = abertos.filter((n) => n.mudouEtapa && hoje.diff(n.mudouEtapa.startOf("day"), "days").days > 30);
    const vencidos = abertos.filter((n) => n.previsao && n.previsao < hoje);
    const amostra = (arr) => arr.slice(0, 5).map((n) => n.nome).join(", ") + (arr.length > 5 ? "…" : "");
    // receita média mensal dos últimos 12 meses fechados → quantos meses o pipeline aberto cobre
    const ini12 = hoje.startOf("month").minus({ months: 12 });
    const media12 = soma(ganhos(ini12, hoje.startOf("month").minus({ days: 1 }).endOf("day"))) / 12;
    const cobertura = media12 ? valorAberto / media12 : null;
    const saude = [
        { key: "sem_valor", label: "Abertas sem valor", hint: "sem valor esperado, não entram na soma do pipeline", count: semValor.length, ids: semValor.map((n) => n.id), nomes: amostra(semValor), classe: semValor.length ? "atencao" : "" },
        { key: "parados", label: "Paradas há mais de 30 dias", hint: "abertas sem mudar de etapa há 30+ dias", count: parados.length, ids: parados.map((n) => n.id), nomes: amostra(parados), classe: parados.length ? "atencao" : "" },
        { key: "vencidos", label: "Previsão de fechamento vencida", hint: "data prevista já passou e o negócio segue aberto", count: vencidos.length, ids: vencidos.map((n) => n.id), nomes: amostra(vencidos), classe: vencidos.length ? "atencao" : "" },
    ];
    const motivosMap = new Map();
    for (const n of pP) {
        const m = motivosMap.get(n.motivo) || { key: n.motivo, n: 0, valor: 0, ids: [] };
        m.n += 1; m.valor += n.valor; m.ids.push(n.id);
        motivosMap.set(n.motivo, m);
    }
    const motivos = [...motivosMap.values()].sort((a, b) => b.n - a.n || b.valor - a.valor).map((m) => ({
        ...m, valorTxt: m.valor ? fmtBrlCurto(m.valor) : "—", share: fmtPct(pct(m.n, pP.length)), width: Math.round(pct(m.n, pP.length)),
    }));
    const pipeline = {
        geradoPeriodo: fmtBrl(R.gerado), nGeradoPeriodo: R.nGerado, geradoSemValor: R.geradoSemValor, idsGeradoPeriodo: geP.map((n) => n.id),
        geradoAno: fmtBrl(soma(geAno)), nGeradoAno: geAno.length, idsGeradoAno: geAno.map((n) => n.id),
        aberto: fmtBrl(valorAberto), nAberto: abertos.length, idsAbertos: abertos.map((n) => n.id),
        ponderado: fmtBrlCurto(soma(abertos, (n) => (n.valor * n.prob) / 100)),
        cobertura: cobertura === null ? "—" : `${cobertura.toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mês(es)`,
        media12: fmtBrlCurto(media12),
        ciclo: R.ciclo === null ? "—" : `${fmtInt(R.ciclo)} dias`,
        funil, saude, motivos, nPerdidos: pP.length, valorPerdido: fmtBrlCurto(soma(pP)),
    };

    // ---------------- leitura do período (regras; sempre a partir do CRM)
    const destaques = [];
    const atencao = [];
    const nomePer = per.preset === "year" ? "no ano" : "no período";
    if (R.n) {
        destaques.push(`${fmtBrl(R.receita)} em ${fmtInt(R.n)} projeto(s) ganho(s) ${nomePer}` +
            (A && A.receita ? `, ${R.receita >= A.receita ? "+" : "–"}${fmtPct(Math.abs(pct(R.receita - A.receita, A.receita)))} contra ${pl}.` : "."));
        const maior = [...gP].sort((a, b) => b.valor - a.valor)[0];
        if (maior && maior.valor) destaques.push(`Maior projeto: ${maior.nome} (${fmtBrlCurto(maior.valor)}, ${fmtPct(pct(maior.valor, R.receita))} da receita).`);
        const tipoLider = tipos.find((t) => t.key !== TIPO_OUTROS.key && t.receitaRaw > 0);
        if (tipoLider) destaques.push(`${tipoLider.label} é o tipo de projeto que mais fatura: ${fmtBrlCurto(tipoLider.receitaRaw)} (${tipoLider.share}).`);
        if (novosCli.length) destaques.push(`${fmtInt(novosCli.length)} cliente(s) novo(s) na base: ${novosCli.slice(0, 3).map((c) => c.key).join(", ")}${novosCli.length > 3 ? "…" : ""}.`);
    } else {
        atencao.push(`Nenhum projeto ganho ${nomePer}.`);
    }
    if (A && A.receita && R.receita < A.receita) atencao.push(`Receita ${fmtPct(Math.abs(pct(R.receita - A.receita, A.receita)))} abaixo de ${pl} (${fmtBrlCurto(A.receita)}).`);
    // completude: meses já encerrados do ano sem nenhum ganho, quando o ano anterior teve
    const mesesSemGanho = MESES.map((m, i) => ({ m, i })).filter(({ i }) => {
        const a = DT().fromObject({ year: hoje.year, month: i + 1, day: 1 }, { zone: TZ });
        return a.endOf("month") < hoje && !ganhos(a, a.endOf("month")).length && ganhos(a.minus({ years: 1 }), a.minus({ years: 1 }).endOf("month")).length;
    }).map(({ m }) => m);
    if (mesesSemGanho.length >= 2 && (!start || start.year <= hoje.year) && end.year === hoje.year) {
        atencao.push(`Nenhum ganho registrado no CRM em ${mesesSemGanho.join(", ")}/${hoje.year} (o ano anterior teve): confira se esses projetos estão lançados — o acumulado do ano pode estar incompleto.`);
    }
    if (concentracao.top1Raw >= 40) atencao.push(`Concentração: ${concentracao.top1Nome} responde por ${concentracao.top1} da receita; top 5 somam ${concentracao.top5}.`);
    if (R.conv !== null && A && A.conv !== null && R.conv < A.conv - 5) atencao.push(`Conversão caiu para ${fmtPct(R.conv)} (era ${fmtPct(A.conv)}).`);
    else if (R.conv !== null && R.fechados >= 5) destaques.push(`Conversão de ${fmtPct(R.conv)} (${fmtInt(R.n)} de ${fmtInt(R.fechados)} decididos).`);
    const semMotivo = pP.filter((n) => !n.motivo || n.motivo === "Motivo não informado").length;
    const motivoReal = motivos.find((m) => m.key !== "Motivo não informado");
    if (pP.length >= 3 && semMotivo > pP.length / 2) atencao.push(`${fmtInt(semMotivo)} de ${fmtInt(pP.length)} perdas sem motivo informado: sem isso não dá para saber por que perdemos.`);
    else if (motivoReal && pP.length >= 3) atencao.push(`Principal motivo de perda: ${motivoReal.key} (${fmtInt(motivoReal.n)} de ${fmtInt(pP.length)}).`);
    if (semValor.length) atencao.push(`${fmtInt(semValor.length)} de ${fmtInt(abertos.length)} oportunidades abertas estão sem valor no CRM: o pipeline aberto está subestimado.`);
    if (cobertura !== null) (cobertura >= 3 ? destaques : atencao).push(`Pipeline aberto de ${fmtBrlCurto(valorAberto)} cobre ${pipeline.cobertura} da receita média mensal (${fmtBrlCurto(media12)}).`);
    if (!destaques.length) destaques.push("Sem destaques positivos no período.");
    if (!atencao.length) atencao.push("Nenhum ponto de atenção no período.");

    return {
        kpis, acumulado, evolucao, historico, clientes: opts.clientesTodos ? clientes : clientes.slice(0, 10),
        nClientes: clientes.length, concentracao, projetos, tipos, donutTipos, vendedores,
        mostrarVendedores: vendedores.length >= 2, pipeline,
        leitura: { destaques: destaques.slice(0, 5), atencao: atencao.slice(0, 5) },
        resumo: R, anterior: A,
    };
}
