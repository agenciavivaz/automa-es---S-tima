import { BENCHMARKS_FALLBACK, COMPLEXIDADE_PADRAO_POR_SETOR } from './benchmarks';
import { CANAIS } from './types';
import type {
  Benchmarks,
  BreakdownCanal,
  CalcInputs,
  CalcResultados,
  Canal,
  PecasPorCanal,
  Setor,
} from './types';

/**
 * Motor de cálculo — determinístico e puro.
 * Referência: PRD seção 5.2. A IA nunca calcula: ela só lê o resultado daqui.
 */

const round2 = (n: number) => Math.round((n + Number.EPSILON) * 100) / 100;

/** Normaliza um número de entrada: finito, não negativo. */
const num = (v: unknown, fallback = 0): number => {
  const n = typeof v === 'string' ? Number(v) : (v as number);
  if (typeof n !== 'number' || !Number.isFinite(n)) return fallback;
  return n < 0 ? 0 : n;
};

/** Números inteiros de contagem (SKUs, diárias, peças). */
const int = (v: unknown, fallback = 0): number => Math.floor(num(v, fallback));

const PECAS_ZERO: PecasPorCanal = {
  social: 0,
  ecommerce: 0,
  ooh: 0,
  video: 0,
  midiaPaga: 0,
};

/** Defaults por setor — nenhum campo do wizard começa vazio (PRD seção 6). */
export function defaultInputs(setor: Setor = 'automotivo', bm: Benchmarks = BENCHMARKS_FALLBACK): CalcInputs {
  const porSetor: Record<Setor, Omit<CalcInputs, 'setor' | 'custoDiaria' | 'complexidadeTwin'>> = {
    automotivo: {
      skus: 40,
      campanhas: 6,
      diarias: 12,
      variacoesPorSku: 6,
      mercados: 2,
      pecas: { social: 40, ecommerce: 25, ooh: 6, video: 4, midiaPaga: 20 },
      skusDigitalizados: 40,
    },
    maquinas_agro: {
      skus: 30,
      campanhas: 4,
      diarias: 8,
      variacoesPorSku: 4,
      mercados: 2,
      pecas: { social: 30, ecommerce: 20, ooh: 4, video: 3, midiaPaga: 15 },
      skusDigitalizados: 30,
    },
    bens_consumo: {
      skus: 120,
      campanhas: 8,
      diarias: 16,
      variacoesPorSku: 3,
      mercados: 1,
      pecas: { social: 50, ecommerce: 40, ooh: 3, video: 4, midiaPaga: 25 },
      skusDigitalizados: 120,
    },
    moda: {
      skus: 200,
      campanhas: 6,
      diarias: 20,
      variacoesPorSku: 4,
      mercados: 1,
      pecas: { social: 60, ecommerce: 50, ooh: 2, video: 3, midiaPaga: 30 },
      skusDigitalizados: 200,
    },
    eletronicos: {
      skus: 60,
      campanhas: 6,
      diarias: 10,
      variacoesPorSku: 3,
      mercados: 2,
      pecas: { social: 40, ecommerce: 35, ooh: 3, video: 4, midiaPaga: 22 },
      skusDigitalizados: 60,
    },
    outro: {
      skus: 50,
      campanhas: 5,
      diarias: 10,
      variacoesPorSku: 3,
      mercados: 1,
      pecas: { social: 35, ecommerce: 25, ooh: 3, video: 3, midiaPaga: 18 },
      skusDigitalizados: 50,
    },
  };

  return {
    setor,
    custoDiaria: bm.custoDiaria[setor],
    complexidadeTwin: COMPLEXIDADE_PADRAO_POR_SETOR[setor],
    ...porSetor[setor],
  };
}

/** Sanitiza inputs vindos da URL, do formulário ou da API. */
export function normalizeInputs(raw: Partial<CalcInputs> & { setor?: Setor }, bm: Benchmarks = BENCHMARKS_FALLBACK): CalcInputs {
  const setor = (raw.setor ?? 'automotivo') as Setor;
  const base = defaultInputs(setor, bm);
  const skus = int(raw.skus, base.skus);

  const pecas = { ...PECAS_ZERO };
  for (const canal of CANAIS) {
    pecas[canal] = int(raw.pecas?.[canal], base.pecas[canal]);
  }

  return {
    setor,
    skus,
    campanhas: int(raw.campanhas, base.campanhas),
    diarias: int(raw.diarias, base.diarias),
    custoDiaria: num(raw.custoDiaria, base.custoDiaria),
    variacoesPorSku: num(raw.variacoesPorSku, base.variacoesPorSku),
    // Sem adaptação de mercado, o mínimo é 1 (o mercado de origem).
    mercados: Math.max(1, int(raw.mercados, base.mercados)),
    pecas,
    complexidadeTwin: raw.complexidadeTwin ?? base.complexidadeTwin,
    // Não faz sentido digitalizar mais SKUs do que os que recebem conteúdo.
    skusDigitalizados: Math.min(skus, int(raw.skusDigitalizados, skus)),
    ticketMedio: raw.ticketMedio === undefined ? undefined : num(raw.ticketMedio),
    transacoesAno: raw.transacoesAno === undefined ? undefined : num(raw.transacoesAno),
    faturamentoDigital:
      raw.faturamentoDigital === undefined ? undefined : num(raw.faturamentoDigital),
  };
}

/** Peças por campanha somadas em todos os canais. */
export function pecasPorCampanha(pecas: PecasPorCanal): number {
  return CANAIS.reduce((acc, canal) => acc + num(pecas[canal]), 0);
}

/**
 * Faturamento digital considerado no bloco de uplift.
 * Preferimos o valor informado direto; se ausente, derivamos de ticket × transações.
 */
export function faturamentoDigital(inputs: CalcInputs): number | null {
  if (inputs.faturamentoDigital && inputs.faturamentoDigital > 0) {
    return num(inputs.faturamentoDigital);
  }
  const ticket = num(inputs.ticketMedio);
  const transacoes = num(inputs.transacoesAno);
  if (ticket > 0 && transacoes > 0) return round2(ticket * transacoes);
  return null;
}

/**
 * Núcleo do produto: transforma inputs + benchmarks em resultados.
 * Puro, síncrono e sem I/O — é o que os testes cobrem.
 */
export function calcular(rawInputs: CalcInputs, bm: Benchmarks = BENCHMARKS_FALLBACK): CalcResultados {
  const inputs = normalizeInputs(rawInputs, bm);

  const custoTwinPorSku = bm.custoTwinPorSku[inputs.complexidadeTwin] ?? 0;

  const pecasCampanha = pecasPorCampanha(inputs.pecas);
  const pecasTotal = pecasCampanha * inputs.campanhas;
  const variacoesTotal = inputs.skus * inputs.variacoesPorSku;
  const mercadosExtras = Math.max(0, inputs.mercados - 1);

  // --- Custo da produção tradicional (anual) ---
  const custoTradicional = round2(
    inputs.diarias * inputs.custoDiaria +
      variacoesTotal * bm.custoReshootVariacao +
      mercadosExtras * bm.custoAdaptacaoMercado +
      pecasTotal * bm.custoPosProducaoPeca,
  );

  // --- Custo NGI ---
  const investimentoTwins = round2(inputs.skusDigitalizados * custoTwinPorSku);
  const custoDesdobramento = round2(pecasTotal * bm.custoDesdobramentoPeca);

  const custoNgiAno1 = round2(investimentoTwins + custoDesdobramento);
  const custoNgiRecorrente = round2(
    custoDesdobramento + inputs.skusDigitalizados * bm.custoManutencaoTwin,
  );

  // --- Resultados ---
  const economiaAno1 = round2(custoTradicional - custoNgiAno1);
  const economiaAnualRecorrente = round2(custoTradicional - custoNgiRecorrente);
  const economia3Anos = round2(economiaAno1 + 2 * economiaAnualRecorrente);

  const percentualEconomia =
    custoTradicional > 0 ? economiaAnualRecorrente / custoTradicional : null;

  // Payback só existe se a operação recorrente de fato economiza.
  const paybackMeses =
    economiaAnualRecorrente > 0
      ? round2(investimentoTwins / (economiaAnualRecorrente / 12))
      : null;

  const tempoEconomizadoDias = round2(inputs.diarias * bm.fatorDiasPorDiaria);

  // --- Bloco de uplift de receita: estimativa, NUNCA somada à economia ---
  const faturamento = faturamentoDigital(inputs);
  const upliftReceita = faturamento === null ? null : round2(faturamento * bm.upliftConversao);

  // --- Detalhamento por canal (card com gate) ---
  // O custo de diária, reshoot e adaptação de mercado é rateado pela participação
  // do canal no volume total de peças — é o que permite ler "quanto cada canal custa".
  const custoNaoAtribuidoTrad =
    inputs.diarias * inputs.custoDiaria +
    variacoesTotal * bm.custoReshootVariacao +
    mercadosExtras * bm.custoAdaptacaoMercado;

  const breakdownPorCanal: BreakdownCanal[] = CANAIS.map((canal: Canal) => {
    const pecasCanal = num(inputs.pecas[canal]) * inputs.campanhas;
    const participacao = pecasTotal > 0 ? pecasCanal / pecasTotal : 0;
    const custoTradCanal = round2(
      pecasCanal * bm.custoPosProducaoPeca + custoNaoAtribuidoTrad * participacao,
    );
    const custoNgiCanal = round2(
      pecasCanal * bm.custoDesdobramentoPeca +
        inputs.skusDigitalizados * bm.custoManutencaoTwin * participacao,
    );
    return {
      canal,
      pecas: pecasCanal,
      custoTradicional: custoTradCanal,
      custoNgi: custoNgiCanal,
      economia: round2(custoTradCanal - custoNgiCanal),
    };
  });

  // --- Projeção de 3 anos (card com gate) ---
  const projecao3Anos = [1, 2, 3].map((ano) => {
    const custoNgi = ano === 1 ? custoNgiAno1 : custoNgiRecorrente;
    const economia = ano === 1 ? economiaAno1 : economiaAnualRecorrente;
    const economiaAcumulada =
      ano === 1 ? economiaAno1 : round2(economiaAno1 + (ano - 1) * economiaAnualRecorrente);
    return { ano, custoTradicional, custoNgi, economia, economiaAcumulada };
  });

  return {
    pecasTotal,
    variacoesTotal,
    mercadosExtras,
    custoTradicional,
    custoNgiAno1,
    custoNgiRecorrente,
    economiaAno1,
    economiaAnualRecorrente,
    economia3Anos,
    percentualEconomia,
    paybackMeses,
    tempoEconomizadoDias,
    faturamentoDigitalConsiderado: faturamento,
    upliftReceita,
    breakdownPorCanal,
    projecao3Anos,
    investimentoTwins,
  };
}
