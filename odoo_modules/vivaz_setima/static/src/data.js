/** @odoo-module **/
// Leitura dos dados do Resultado comercial · Sétima. Só leitura, com a sessão de quem vê.
// Recebe um objeto com a interface do serviço "orm" do Odoo (searchRead), para o mesmo
// código rodar no navegador e no script de conferência (Node + JSON-2).
// O pipeline inteiro (~1,5 mil negócios desde 2020) cabe numa leitura: todos os cortes de
// período, o acumulado do ano e o histórico anual saem dela, sem nova consulta ao filtrar.

import { BASE_DOMAIN, TEAM_ID, prepararNegocios } from "./calc";

const CTX = { context: { active_test: false } };
export const NEGOCIO_FIELDS = [
    "name", "partner_id", "stage_id", "won_status", "active", "expected_revenue", "probability",
    "create_date", "x_pipedrive_add_time", "date_closed", "x_studio_data_de_ganho",
    "x_pipedrive_won_time", "x_pipedrive_lost_time", "date_last_stage_update", "date_deadline",
    "user_id", "tag_ids", "lost_reason_id",
];

export async function carregar(orm) {
    const [stages, negocios] = await Promise.all([
        orm.searchRead("crm.stage", [["team_ids", "in", [TEAM_ID]]], ["name", "sequence", "is_won"], { order: "sequence, id" }),
        orm.searchRead("crm.lead", BASE_DOMAIN, NEGOCIO_FIELDS, CTX),
    ]);
    const partnerIds = [...new Set(negocios.map((n) => n.partner_id && n.partner_id[0]).filter(Boolean))];
    const tagIds = [...new Set(negocios.flatMap((n) => n.tag_ids || []))];
    const [parceiros, tags] = await Promise.all([
        partnerIds.length
            ? orm.searchRead("res.partner", [["id", "in", partnerIds]], ["commercial_partner_id", "industry_id"], CTX)
            : [],
        tagIds.length ? orm.searchRead("crm.tag", [["id", "in", tagIds]], ["name"]) : [],
    ]);
    const raw = { stages, negocios, parceiros, tags };
    raw._negocios = prepararNegocios(raw);
    return raw;
}
