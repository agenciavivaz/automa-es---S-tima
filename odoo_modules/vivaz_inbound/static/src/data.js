/** @odoo-module **/
// Leitura dos dados do Relatório Inbound v2. Só leitura, com a sessão de quem vê o painel.
// Recebe um objeto com a interface do serviço "orm" do Odoo (search, searchRead), para o
// mesmo código rodar no navegador e no script de reconciliação (Node + JSON-2).
// Todas as consultas ficam limitadas ao período + período de comparação (§10.3), exceto o
// card fixo do acumulado (A5), que por definição não tem período.

import { BASE_DOMAIN, TEAM_ID, entradaDomain, toUtcSql } from "./calc";

const CTX = { context: { active_test: false } };
export const LEAD_FIELDS = [
    "name", "partner_name", "contact_name", "email_from", "stage_id", "won_status", "active",
    "create_date", "x_pipedrive_add_time", "date_last_stage_update", "lost_reason_id",
    "campaign_id", "source_id", "x_meta_conjunto", "x_meta_anuncio", "user_id", "tag_ids",
];
const MSG_FIELDS = ["body", "date", "author_id", "res_id", "message_type", "subject"];
const ACT_FIELDS = [
    "activity_type_id", "activity_category", "summary", "note", "date_deadline", "date_done",
    "user_id", "res_id", "active", "feedback", "create_date", "calendar_event_id",
];
const DEAL_FIELDS = ["name", "partner_id", "team_id", "expected_revenue", "won_status", "date_closed", "x_studio_data_de_ganho"];

export const MODELO = {
    comentario: "x_vivaz_inb_comentario",
    campanha: "x_vivaz_inb_campanha",
    meta: "x_vivaz_inb_meta",
    ajuste: "x_vivaz_inb_ajuste",
};

async function opcional(promise, fallback) {
    try {
        return await promise;
    } catch {
        return fallback; // modelo de configuração ausente não derruba o relatório
    }
}

export async function carregar(orm, per) {
    const { start, end, prevStart, prevEnd } = per;
    const ini = prevStart || start; // janela total: comparação + período
    const janela = (f) => [...(ini ? [[f, ">=", toUtcSql(ini)]] : []), [f, "<=", toUtcSql(end)]];

    const [stages, leads, leadsPrev, todosIds, tags, contratos, apelidos, metas, ajustes] = await Promise.all([
        orm.searchRead("crm.stage", [["team_ids", "in", [TEAM_ID]]], ["name", "sequence", "is_won"], { order: "sequence, id" }),
        orm.searchRead("crm.lead", [...BASE_DOMAIN, ...entradaDomain(start, end)], LEAD_FIELDS, CTX),
        prevStart ? orm.searchRead("crm.lead", [...BASE_DOMAIN, ...entradaDomain(prevStart, prevEnd)], LEAD_FIELDS, CTX) : [],
        orm.search("crm.lead", BASE_DOMAIN, CTX),
        orm.searchRead("crm.tag", [["name", "=ilike", "datacrazy"]], ["name"]),
        // RN2/RN3: receita = ganhos marcados "Originado no Inbound", qualquer pipeline.
        orm.searchRead("crm.lead", [["x_origem_inbound", "=", true], ["won_status", "=", "won"], ["active", "in", [true, false]]], DEAL_FIELDS, CTX),
        opcional(orm.searchRead(MODELO.campanha, [], ["x_name", "x_apelido", "x_cor"]), []),
        opcional(orm.searchRead(MODELO.meta, [], ["x_etapa", "x_taxa_alvo"]), []),
        opcional(orm.searchRead(MODELO.ajuste, [], ["x_name", "x_valor"]), []),
    ]);
    const cohortIds = leads.map((l) => l.id);
    const resIn = (ids) => ["res_id", "in", ids];
    const [msgJanela, msgCoorte, atividades, eventos] = await Promise.all([
        orm.searchRead("mail.message",
            [["model", "=", "crm.lead"], resIn(todosIds), ["message_type", "in", ["comment", "email"]], ...janela("date")],
            MSG_FIELDS, { order: "date desc" }),
        // mensagens dos leads do período em qualquer data: 1º contato e "sem contato"
        cohortIds.length
            ? orm.searchRead("mail.message",
                [["model", "=", "crm.lead"], resIn(cohortIds), ["message_type", "in", ["comment", "email"]]],
                MSG_FIELDS, { order: "date desc" })
            : [],
        orm.searchRead("mail.activity",
            [["res_model", "=", "crm.lead"], resIn(todosIds), ["active", "in", [true, false]],
             "|", "|", resIn(cohortIds),
             ...(ini ? ["&", ["date_done", ">=", ini.toISODate()]] : []), ["date_done", "<=", end.toISODate()],
             ...(ini ? ["&", ["create_date", ">=", toUtcSql(ini)]] : []), ["create_date", "<=", toUtcSql(end)]],
            ACT_FIELDS, CTX),
        orm.searchRead("calendar.event",
            [["opportunity_id", "in", todosIds], ["active", "in", [true, false]],
             "|", ...(ini ? ["&", ["create_date", ">=", toUtcSql(ini)]] : []), ["create_date", "<=", toUtcSql(end)],
             ...(ini ? ["&", ["start", ">=", toUtcSql(ini)]] : []), ["start", "<=", toUtcSql(end)]],
            ["name", "start", "stop", "create_date", "opportunity_id", "active", "user_id"], CTX),
    ]);
    const vistos = new Set();
    const mensagens = [...msgJanela, ...msgCoorte].filter((m) => (vistos.has(m.id) ? false : vistos.add(m.id)));
    // leads tocados no período que entraram antes dele (B7): só para nome/etapa
    const conhecidos = new Set([...cohortIds, ...leadsPrev.map((l) => l.id)]);
    const extraIds = [...new Set([...mensagens.map((m) => m.res_id), ...atividades.map((a) => a.res_id),
        ...eventos.map((e) => e.opportunity_id && e.opportunity_id[0])])].filter((id) => id && !conhecidos.has(id));
    const leadsExtra = extraIds.length ? await orm.searchRead("crm.lead", [["id", "in", extraIds], ["active", "in", [true, false]]], LEAD_FIELDS, CTX) : [];
    return {
        stages, leads, leadsPrev, leadsExtra, mensagens, atividades, eventos, contratos,
        tagDataCrazy: tags.map((t) => t.id), apelidos, metas,
        ajustes: Object.fromEntries(ajustes.map((a) => [a.x_name, a.x_valor])),
        todosIds,
    };
}

/** Comentário do analista que vale para o período: mesmo intervalo, senão o mais recente que o cobre. */
export async function carregarComentario(orm, per) {
    if (!per.start) return null;
    const ini = per.start.toISODate();
    const fim = per.end.toISODate();
    const regs = await opcional(orm.searchRead(MODELO.comentario,
        [["x_data_inicio", "<=", ini], ["x_data_fim", ">=", fim]],
        ["x_data_inicio", "x_data_fim", "x_texto", "write_uid", "write_date"], { order: "write_date desc" }), []);
    const exato = regs.find((r) => r.x_data_inicio === ini && r.x_data_fim === fim);
    return exato || regs[0] || null;
}
