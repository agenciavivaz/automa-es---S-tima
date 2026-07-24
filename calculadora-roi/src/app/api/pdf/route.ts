import { calcular } from '@/lib/calc';
import { formatDias, formatMeses, formatMoeda, formatNumero, formatPercent } from '@/lib/format';
import { checarRateLimit, ipDoRequest } from '@/lib/rate-limit';
import { narrativaEstatica } from '@/lib/report';
import { carregarBenchmarks } from '@/lib/supabase';
import { CANAL_LABEL, SETOR_LABEL } from '@/lib/types';
import { searchParamsToInputs } from '@/lib/url-state';

export const runtime = 'nodejs';

/**
 * Relatório com a marca Sétima — o vetor viral do PRD (seção 4): ele circula
 * internamente na empresa do prospect, no contexto de uma decisão de budget.
 *
 * Entrega HTML paginado com `@page` e impressão automática (Salvar como PDF).
 * Fase 2 troca esta rota por @react-pdf/renderer + Supabase Storage + envio por
 * e-mail; o template e os dados abaixo continuam valendo.
 */
export async function GET(req: Request) {
  const { permitido } = checarRateLimit(`pdf:${ipDoRequest(req)}`, 20, 60_000);
  if (!permitido) {
    return new Response('Muitas requisições.', { status: 429 });
  }

  const url = new URL(req.url);
  const benchmarks = await carregarBenchmarks();
  const inputs = searchParamsToInputs(url.searchParams, benchmarks);
  const r = calcular(inputs, benchmarks);
  const narrativa = narrativaEstatica(inputs, r);

  const html = `<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Calculadora de ROI NGI — Sétima</title>
<style>
  @page { size: A4; margin: 16mm; }
  * { box-sizing: border-box; }
  body { font-family: Helvetica, Arial, sans-serif; color: #111; margin: 0; }
  .eyebrow { text-transform: uppercase; letter-spacing: .16em; font-size: 10px; color: #666; font-weight: 700; }
  h1 { text-transform: uppercase; font-size: 26px; letter-spacing: -.02em; margin: 6px 0 20px; }
  h2 { text-transform: uppercase; font-size: 14px; letter-spacing: .04em; margin: 28px 0 10px; }
  .destaque { font-size: 46px; font-weight: 800; letter-spacing: -.03em; margin: 4px 0; }
  .grid { display: flex; gap: 12px; flex-wrap: wrap; }
  .card { border: 1px solid #ddd; border-radius: 6px; padding: 12px 14px; flex: 1 1 150px; }
  .card .rotulo { font-size: 10px; text-transform: uppercase; letter-spacing: .1em; color: #666; }
  .card .valor { font-size: 20px; font-weight: 700; margin-top: 4px; }
  table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 6px; }
  th, td { text-align: left; padding: 7px 4px; border-bottom: 1px solid #e6e6e6; }
  td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
  p { font-size: 12px; line-height: 1.55; }
  .rodape { margin-top: 28px; padding-top: 12px; border-top: 1px solid #ddd; font-size: 10px; color: #666; }
  .clientes { font-size: 11px; color: #666; letter-spacing: .06em; text-transform: uppercase; }
  .barra { height: 12px; background: #eee; border-radius: 2px; overflow: hidden; margin: 4px 0 10px; }
  .barra > span { display: block; height: 100%; }
  .sem-impressao { margin-bottom: 16px; }
  @media print { .sem-impressao { display: none; } }
</style>
</head>
<body>
  <div class="sem-impressao">
    <button onclick="window.print()">Salvar como PDF</button>
  </div>

  <p class="eyebrow">Sétima · NGI — Next-Gen Imagery</p>
  <h1>Estimativa de economia com digital twin</h1>
  <p class="clientes">Volkswagen · VWCO · Embraer · iFood · Nubank · Mercado Livre</p>

  <h2>Resultado</h2>
  <p class="eyebrow">Economia anual estimada (ano 2 em diante)</p>
  <p class="destaque">${formatMoeda(r.economiaAnualRecorrente)}</p>

  <div class="grid">
    <div class="card"><div class="rotulo">Economia no ano 1</div><div class="valor">${formatMoeda(r.economiaAno1)}</div></div>
    <div class="card"><div class="rotulo">Economia em 3 anos</div><div class="valor">${formatMoeda(r.economia3Anos)}</div></div>
    <div class="card"><div class="rotulo">Payback do twin</div><div class="valor">${formatMeses(r.paybackMeses)}</div></div>
    <div class="card"><div class="rotulo">Tempo liberado/ano</div><div class="valor">${formatDias(r.tempoEconomizadoDias)}</div></div>
  </div>

  <h2>Custo anual: tradicional × NGI</h2>
  <p style="margin:0"><strong>Produção tradicional:</strong> ${formatMoeda(r.custoTradicional)}</p>
  <div class="barra"><span style="width:100%;background:#c0392b"></span></div>
  <p style="margin:0"><strong>NGI (ano 2 em diante):</strong> ${formatMoeda(r.custoNgiRecorrente)} — redução de ${formatPercent(r.percentualEconomia)}</p>
  <div class="barra"><span style="width:${pct(r.custoNgiRecorrente, r.custoTradicional)}%;background:#2d7a3e"></span></div>
  <p>No ano 1 o custo NGI é ${formatMoeda(r.custoNgiAno1)}, porque inclui a criação dos digital twins (${formatMoeda(r.investimentoTwins)}).</p>

  <h2>Cenário informado</h2>
  <table>
    <tbody>
      <tr><td>Setor</td><td class="num">${SETOR_LABEL[inputs.setor]}</td></tr>
      <tr><td>SKUs com produção de conteúdo</td><td class="num">${formatNumero(inputs.skus)}</td></tr>
      <tr><td>SKUs no digital twin</td><td class="num">${formatNumero(inputs.skusDigitalizados)}</td></tr>
      <tr><td>Campanhas por ano</td><td class="num">${formatNumero(inputs.campanhas)}</td></tr>
      <tr><td>Diárias de produção por ano</td><td class="num">${formatNumero(inputs.diarias)}</td></tr>
      <tr><td>Variações por produto</td><td class="num">${formatNumero(inputs.variacoesPorSku)}</td></tr>
      <tr><td>Mercados com adaptação</td><td class="num">${formatNumero(inputs.mercados)}</td></tr>
      <tr><td>Peças produzidas por ano</td><td class="num">${formatNumero(r.pecasTotal)}</td></tr>
    </tbody>
  </table>

  <h2>Breakdown por canal</h2>
  <table>
    <thead><tr><th>Canal</th><th class="num">Peças/ano</th><th class="num">Tradicional</th><th class="num">NGI</th><th class="num">Economia</th></tr></thead>
    <tbody>
      ${r.breakdownPorCanal
        .map(
          (b) =>
            `<tr><td>${CANAL_LABEL[b.canal]}</td><td class="num">${formatNumero(b.pecas)}</td><td class="num">${formatMoeda(b.custoTradicional)}</td><td class="num">${formatMoeda(b.custoNgi)}</td><td class="num">${formatMoeda(b.economia)}</td></tr>`,
        )
        .join('')}
    </tbody>
  </table>

  <h2>Projeção de 3 anos</h2>
  <table>
    <thead><tr><th>Ano</th><th class="num">Tradicional</th><th class="num">NGI</th><th class="num">Economia</th><th class="num">Acumulado</th></tr></thead>
    <tbody>
      ${r.projecao3Anos
        .map(
          (p) =>
            `<tr><td>Ano ${p.ano}</td><td class="num">${formatMoeda(p.custoTradicional)}</td><td class="num">${formatMoeda(p.custoNgi)}</td><td class="num">${formatMoeda(p.economia)}</td><td class="num">${formatMoeda(p.economiaAcumulada)}</td></tr>`,
        )
        .join('')}
    </tbody>
  </table>

  ${
    r.upliftReceita !== null
      ? `<h2>Uplift de receita (estimativa)</h2>
  <p><strong>${formatMoeda(r.upliftReceita)}</strong> — receita adicional estimada aplicando o benchmark de +9% em vendas com experiências 3D interativas sobre ${formatMoeda(r.faturamentoDigitalConsiderado ?? 0)} de faturamento digital. Este valor <strong>não</strong> está somado à economia de custo: economia é cálculo, uplift é estimativa.</p>`
      : ''
  }

  <h2>Leitura estratégica</h2>
  ${narrativa.paragrafos.map((p) => `<p>${escapar(p)}</p>`).join('')}

  <div class="rodape">
    Os resultados são estimativas baseadas em benchmarks de mercado e na base de projetos da Sétima.
    Não constituem proposta comercial nem orçamento. Os valores finais dependem da complexidade dos
    produtos, do volume real de peças e do escopo acordado.
    Gerado em ${new Date().toLocaleDateString('pt-BR')}.
  </div>
</body>
</html>`;

  return new Response(html, {
    headers: {
      'content-type': 'text/html; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}

const pct = (parte: number, total: number) =>
  total > 0 ? Math.max(1, Math.round((parte / total) * 100)) : 0;

const escapar = (texto: string) =>
  texto.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
