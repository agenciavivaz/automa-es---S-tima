// Calcula os números do Dashboard Sétima fora do navegador, com o MESMO código do módulo
// (calc.js + data.js) e as mesmas consultas, via JSON-2 com a chave do ambiente.
//
//   NODE_USE_ENV_PROXY=1 node setima_resultados/scripts/valores_dashboard.mjs year this_month all
//
// Saída: JSON { preset: { periodo, kpis, acumulado, leitura, ... } } em stdout.
// Credenciais só de ODOO_URL / ODOO_DB / ODOO_API_KEY; nunca impressas.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
globalThis.luxon = require(path.join(aqui, "..", "node_modules", "luxon"));

const SRC = path.join(aqui, "..", "..", "odoo_modules", "vivaz_setima", "static", "src");

/** Copia os módulos do Odoo para .mjs com imports relativos resolvíveis pelo Node. */
export async function importarModulo() {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vivaz-setima-"));
    for (const f of ["calc", "data"]) {
        const txt = fs.readFileSync(path.join(SRC, `${f}.js`), "utf8").replace(/from "\.\/(\w+)"/g, 'from "./$1.mjs"');
        fs.writeFileSync(path.join(tmp, `${f}.mjs`), txt);
    }
    return {
        calc: await import(pathToFileURL(path.join(tmp, "calc.mjs")).href),
        data: await import(pathToFileURL(path.join(tmp, "data.mjs")).href),
    };
}

export function ormJson2() {
    const u = new URL(process.env.ODOO_URL);
    const base = `${u.protocol}//${u.host}`;
    const headers = {
        Authorization: `Bearer ${(process.env.ODOO_API_KEY || "").trim()}`,
        "X-Odoo-Database": (process.env.ODOO_DB || "").trim(),
        "Content-Type": "application/json",
    };
    return {
        async searchRead(model, domain, fields, opts = {}) {
            const r = await fetch(`${base}/json/2/${model}/search_read`, {
                method: "POST", headers,
                body: JSON.stringify({ domain, fields, order: opts.order, context: opts.context || {} }),
            });
            if (!r.ok) throw new Error(`${model}.search_read: HTTP ${r.status} ${(await r.text()).slice(0, 300)}`);
            return r.json();
        },
    };
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
    const { calc, data } = await importarModulo();
    const raw = await data.carregar(ormJson2());
    const presets = process.argv.slice(2).length ? process.argv.slice(2) : [calc.PRESET_PADRAO];
    const saida = {};
    for (const p of presets) {
        const per = calc.periodo(p);
        const r = calc.calcular(raw, per);
        saida[p] = {
            periodo: per.label, comparacao: per.prevLabel,
            kpis: r.kpis.map((k) => ({ [k.label]: k.titulo || k.value, sub: k.sub, delta: k.delta && k.delta.texto })),
            resumo: r.resumo, acumulado: { ...r.acumulado, todosIds: r.acumulado.todosIds.length },
            leitura: r.leitura, concentracao: r.concentracao,
            clientes: r.clientes.slice(0, 5).map((c) => [c.key, c.receita, c.n, c.share]),
            tipos: r.tipos.map((t) => [t.label, t.receita, t.n, t.conv, t.aberto]),
            vendedores: r.mostrarVendedores ? r.vendedores.map((v) => [v.key, v.receita, v.n, v.conv, v.gerado]) : "oculto",
            pipeline: { ...r.pipeline, funil: r.pipeline.funil.map((f) => [f.nome, f.n, f.valor]), saude: r.pipeline.saude.map((s) => [s.label, s.count]), motivos: r.pipeline.motivos.slice(0, 3).map((m) => [m.key, m.n]), idsAbertos: undefined, idsGeradoAno: undefined, idsGeradoPeriodo: undefined },
            historico: r.historico.map((h) => [h.ano, h.receita, h.n, h.delta && h.delta.texto]),
        };
    }
    console.log(JSON.stringify(saida, null, 1));
}
