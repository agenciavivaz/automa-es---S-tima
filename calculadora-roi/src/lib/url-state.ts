import { normalizeInputs } from './calc';
import { BENCHMARKS_FALLBACK } from './benchmarks';
import { COMPLEXIDADES, SETORES } from './types';
import type { Benchmarks, CalcInputs, Complexidade, Setor } from './types';

/**
 * Estado do cenário na URL — permite compartilhar o cálculo (vetor viral
 * secundário, PRD seção 6). Chaves curtas para manter o link legível.
 */

const CHAVES = {
  setor: 'setor',
  skus: 'skus',
  campanhas: 'camp',
  diarias: 'diarias',
  custoDiaria: 'custo',
  variacoesPorSku: 'var',
  mercados: 'merc',
  social: 'soc',
  ecommerce: 'ecom',
  ooh: 'ooh',
  video: 'vid',
  midiaPaga: 'paga',
  complexidadeTwin: 'cplx',
  skusDigitalizados: 'dig',
  ticketMedio: 'ticket',
  transacoesAno: 'trans',
  faturamentoDigital: 'fat',
} as const;

const asSetor = (v: string | null): Setor | undefined =>
  v && (SETORES as readonly string[]).includes(v) ? (v as Setor) : undefined;

const asComplexidade = (v: string | null): Complexidade | undefined =>
  v && (COMPLEXIDADES as readonly string[]).includes(v) ? (v as Complexidade) : undefined;

const asNum = (v: string | null): number | undefined => {
  if (v === null || v.trim() === '') return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
};

export function inputsToSearchParams(inputs: CalcInputs): URLSearchParams {
  const p = new URLSearchParams();
  p.set(CHAVES.setor, inputs.setor);
  p.set(CHAVES.skus, String(inputs.skus));
  p.set(CHAVES.campanhas, String(inputs.campanhas));
  p.set(CHAVES.diarias, String(inputs.diarias));
  p.set(CHAVES.custoDiaria, String(inputs.custoDiaria));
  p.set(CHAVES.variacoesPorSku, String(inputs.variacoesPorSku));
  p.set(CHAVES.mercados, String(inputs.mercados));
  p.set(CHAVES.social, String(inputs.pecas.social));
  p.set(CHAVES.ecommerce, String(inputs.pecas.ecommerce));
  p.set(CHAVES.ooh, String(inputs.pecas.ooh));
  p.set(CHAVES.video, String(inputs.pecas.video));
  p.set(CHAVES.midiaPaga, String(inputs.pecas.midiaPaga));
  p.set(CHAVES.complexidadeTwin, inputs.complexidadeTwin);
  p.set(CHAVES.skusDigitalizados, String(inputs.skusDigitalizados));
  if (inputs.ticketMedio) p.set(CHAVES.ticketMedio, String(inputs.ticketMedio));
  if (inputs.transacoesAno) p.set(CHAVES.transacoesAno, String(inputs.transacoesAno));
  if (inputs.faturamentoDigital) p.set(CHAVES.faturamentoDigital, String(inputs.faturamentoDigital));
  return p;
}

type ParamsLike = URLSearchParams | Record<string, string | string[] | undefined>;

function get(params: ParamsLike, chave: string): string | null {
  if (params instanceof URLSearchParams) return params.get(chave);
  const v = params[chave];
  if (Array.isArray(v)) return v[0] ?? null;
  return v ?? null;
}

/** Lê o cenário da URL; tudo que faltar cai no default do setor. */
export function searchParamsToInputs(
  params: ParamsLike,
  bm: Benchmarks = BENCHMARKS_FALLBACK,
): CalcInputs {
  const setor = asSetor(get(params, CHAVES.setor)) ?? 'automotivo';

  return normalizeInputs(
    {
      setor,
      skus: asNum(get(params, CHAVES.skus)),
      campanhas: asNum(get(params, CHAVES.campanhas)),
      diarias: asNum(get(params, CHAVES.diarias)),
      custoDiaria: asNum(get(params, CHAVES.custoDiaria)),
      variacoesPorSku: asNum(get(params, CHAVES.variacoesPorSku)),
      mercados: asNum(get(params, CHAVES.mercados)),
      pecas: {
        social: asNum(get(params, CHAVES.social)),
        ecommerce: asNum(get(params, CHAVES.ecommerce)),
        ooh: asNum(get(params, CHAVES.ooh)),
        video: asNum(get(params, CHAVES.video)),
        midiaPaga: asNum(get(params, CHAVES.midiaPaga)),
      },
      complexidadeTwin: asComplexidade(get(params, CHAVES.complexidadeTwin)),
      skusDigitalizados: asNum(get(params, CHAVES.skusDigitalizados)),
      ticketMedio: asNum(get(params, CHAVES.ticketMedio)),
      transacoesAno: asNum(get(params, CHAVES.transacoesAno)),
      faturamentoDigital: asNum(get(params, CHAVES.faturamentoDigital)),
    } as Partial<CalcInputs>,
    bm,
  );
}

/** UTMs preservadas do primeiro contato até o lead. */
export function extrairUtm(params: ParamsLike): Record<string, string> {
  const chaves = ['utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'];
  const out: Record<string, string> = {};
  for (const c of chaves) {
    const v = get(params, c);
    if (v) out[c] = v;
  }
  return out;
}
