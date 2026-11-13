// Calcula os números do Dashboard Inbound v2 fora do navegador, com o MESMO código do
// módulo (calc.js + data.js) e as mesmas consultas, via JSON-2 com a chave do .env.
//
//   NODE_USE_ENV_PROXY=1 node inbound_v2/scripts/valores_dashboard.mjs this_month prev_month year
//
// Saída: JSON { preset: { periodo, valores (_rec), leitura, textos } } em stdout.
// Credenciais só de ODOO_URL / ODOO_DB / ODOO_API_KEY; nunca impressas.

import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const aqui = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);
globalThis.luxon = require(path.join(aqui, "..", "node_modules", "luxon"));

const SRC = path.join(aqui, "..", "..", "odoo_modules", "vivaz_inbound", "static", "src");

/** Copia os módulos do Odoo para .mjs com imports relativos resolvíveis pelo Node. */
export async function importarModulo() {
    const tmp = fs.mkdtempSync(path.join(os.tmpdir(), "vivaz-inb-"));
    for (const f of ["calc", "data"]) {
        const txt = fs.readFileSync(path.join(SRC, `${f}.js`), "utf8").replace(/from "\.\/(\w+)"/g, 'from "./$1.mjs"');
        fs.writeFileSync(path.join(tmp, `${f}.mjs`), txt);
    }
    const calc = await import(pathToFileURL(path.join(tmp, "calc.mjs")).href);
    const data = await import(pathToFileURL(path.join(tmp, "data.mjs")).href);
    return { calc, data };
}

export function ormJson2() {
    const u = new URL(process.env.ODOO_URL);
    const base = `${u.protocol}//${u.host}`;
    const headers = {
        Authorization: `Bearer ${(process.env.ODOO_API_KEY || "").trim()}`,
        "X-Odoo-Database": (process.env.ODOO_DB || "").trim(),
        "Content-Type": "application/json",
    };
    async function call(model, method, body) {
        for (let t = 1; ; t++) {
            const r = await fetch(`${base}/json/2/${model}/${method}`, { method: "POST", headers, body: JSON.stringify(body) });
            if (r.ok) return r.json();
            if (t < 3 && [429, 500, 502, 503, 504].includes(r.status)) {
                await new Promise((ok) => setTimeout(ok, 1000 * t));
                continue;
            }
            const txt = (await r.text()).slice(0, 300).replaceAll(headers.Authorization, "***");
            throw new Error(`${model}.${method} HTTP ${r.status}: ${txt}`);
        }
    }
    return {
        search: (model, domain, kw = {}) => call(model, "search", { domain, ...kw }),
        searchRead: (model, domain, fields, kw = {}) => call(model, "search_read", { domain, fields, ...kw }),
        searchCount: (model, domain, kw = {}) => call(model, "search_count", { domain, ...kw }),
    };
}

export async function valores(presets, nowIso) {
    const { calc, data } = await importarModulo();
    const orm = ormJson2();
    const now = nowIso ? globalThis.luxon.DateTime.fromISO(nowIso, { zone: calc.TZ }) : globalThis.luxon.DateTime.now().setZone(calc.TZ);
    const saida = {};
    for (const p of presets) {
        const [preset, de, ate] = p.split(":");
        const per = calc.periodo(preset, de, ate, now);
        const t0 = Date.now();
        const raw = await data.carregar(orm, per);
        const r = calc.calcular(raw, per, { now });
        saida[p] = {
            periodo: { inicio: per.start && per.start.toISO(), fim: per.end.toISO(), label: per.label, comparado: per.prevLabel },
            ms: Date.now() - t0,
            valores: r._rec,
            leitura: r.leitura,
            textos: [
                ...r.kpis.flatMap((k) => [k.sub, k.delta && k.delta.texto, k.delta && k.delta.tooltip]),
                r.acumulado.apoio, r.acumulado.periodoTexto, r.operacao.tocadosTexto, r.operacao.cobertura,
                ...r.saude.map((s) => s.hint), r.funilNota,
            ].filter(Boolean),
            acumulado: r.acumulado,
        };
    }
    return saida;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    const args = process.argv.slice(2);
    const presets = args.length ? args : ["this_month", "prev_month", "year"];
    valores(presets, process.env.AGORA).then(
        (s) => process.stdout.write(JSON.stringify(s, null, 2) + "\n"),
        (e) => { console.error(String(e.message || e)); process.exit(1); }
    );
}
