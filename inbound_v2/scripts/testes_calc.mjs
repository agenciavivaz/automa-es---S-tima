// Testes das funções puras do calc.js (sem rede): RN4, RN5, B1, formatação pt-BR.
//   node inbound_v2/scripts/testes_calc.mjs
import assert from "node:assert/strict";
import { importarModulo } from "./valores_dashboard.mjs";

const { calc } = await importarModulo();
const { DateTime } = globalThis.luxon;
const agora = DateTime.fromISO("2026-10-15T11:43:00", { zone: calc.TZ });
let ok = 0;
const t = (nome, fn) => { fn(); ok++; console.log("ok -", nome); };

t("RN4 este mês parcial compara com os mesmos dias do mês anterior", () => {
    const p = calc.periodo("this_month", null, null, agora);
    assert.equal(p.label, "01–15/10/2026");
    assert.equal(p.prevLabel, "01–15/09/2026");
});
t("RN4 mês anterior compara com o mês antes dele", () => {
    const p = calc.periodo("prev_month", null, null, agora);
    assert.equal(p.label, "01–30/09/2026");
    assert.equal(p.prevLabel, "01–31/08/2026");
});
t("RN4 7 dias compara com os 7 dias anteriores", () => {
    const p = calc.periodo("7d", null, null, agora);
    assert.equal(p.label, "09–15/10/2026");
    assert.equal(p.prevLabel, "02–08/10/2026");
});
t("RN4 personalizado compara com intervalo de mesmo tamanho; Tudo sem comparação", () => {
    const p = calc.periodo("custom", "2026-09-10", "2026-09-19", agora);
    assert.equal(p.prevLabel, "31/08–09/09/2026");
    assert.equal(calc.periodo("all", null, null, agora).prevStart, null);
});
t("RN6 limites em America/Sao_Paulo (01/10 00:00 local = 03:00 UTC)", () => {
    const p = calc.periodo("this_month", null, null, agora);
    assert.equal(calc.toUtcSql(p.start), "2026-10-01 03:00:00");
});
t("RN5 palavra-chave nunca gera Reunião", () => {
    assert.equal(calc.classificarTexto("Enviei nova mensagem pelo Datacrazy: Queria ver como está sua agenda para marcarmos essa semana?"), "convite");
    assert.equal(calc.classificarTexto("Isack pediu reunião para o dia 24/09"), "convite");
    for (const s of ["reunião agendada", "meeting", "call marcada", "agenda"]) assert.notEqual(calc.classificarTexto(s), "reuniao");
    assert.equal(calc.classificarTexto("Enviado mensagem pelo Datacrazy!"), "whatsapp");
    assert.equal(calc.classificarTexto("Tentativa de ligação no API4COM - Não atende"), "ligacao");
    assert.equal(calc.classificarTexto("Pesquisa: CNPJ 08.299.803/0001-09 Razão Social"), "pesquisa");
});
t("formatação pt-BR", () => {
    assert.equal(calc.fmtBrl(962800), "R$ 962.800");
    assert.equal(calc.fmtBrlCurto(481400), "R$ 481,4 mil");
    assert.equal(calc.fmtPct(18.518), "18,5%");
    assert.equal(calc.fmtHoras(15.67), "16 h");
    assert.equal(calc.mediana([1, 2, 3, 10]), 2.5);
});
t("delta: % só com base anterior ≥ 10; abaixo, absoluto e neutro", () => {
    assert.equal(calc.delta(27, 1).classe, "neutro");
    assert.equal(calc.delta(27, 1).texto, "+26");
    const d = calc.delta(20, 28);
    assert.equal(d.classe, "ruim");
    assert.equal(d.texto, "–8 (–28,6%)");
});
t("apelido automático de campanha", () => {
    assert.equal(calc.apelidoAutomatico("[M][Lead][Nátivo][Sétima] - Contínua"), "Contínua");
    assert.equal(calc.apelidoAutomatico(""), "");
});

/** B1: nenhum texto gerado pode ter "x(" sem espaço nem vírgula seguida de não-espaço/não-dígito. */
export function checarB1(textos) {
    const ruins = textos.filter((s) => /[a-zA-Z0-9)][(]/.test(s) || /,[^ \d]/.test(s));
    return ruins;
}
t("B1 no template", () => {
    assert.deepEqual(checarB1([calc.tpl("{n} leads no período ({d} vs. {p}).", { n: "27", d: "–1", p: "01–15/09" })]), []);
    assert.deepEqual(checarB1(["27 leads(-1vs.)", "3D,R$ 650.000,fechado"]).length, 2);
});
console.log(`${ok} testes ok`);
