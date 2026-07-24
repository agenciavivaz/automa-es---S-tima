import { describe, expect, it } from 'vitest';
import { calcular, defaultInputs, faturamentoDigital, normalizeInputs, pecasPorCampanha } from '../calc';
import { BENCHMARKS_FALLBACK, mergeBenchmarks } from '../benchmarks';
import type { Benchmarks, CalcInputs } from '../types';

/**
 * Benchmarks sintéticos com números redondos: cada asserção abaixo pode ser
 * conferida na mão contra as fórmulas da seção 5.2 do PRD.
 */
const BM: Benchmarks = {
  custoDiaria: {
    automotivo: 10_000,
    maquinas_agro: 10_000,
    bens_consumo: 10_000,
    moda: 10_000,
    eletronicos: 10_000,
    outro: 10_000,
  },
  custoTwinPorSku: { simples: 1_000, medio: 2_000, complexo: 5_000 },
  custoDesdobramentoPeca: 100,
  custoReshootVariacao: 2_000,
  custoAdaptacaoMercado: 20_000,
  custoPosProducaoPeca: 500,
  custoManutencaoTwin: 200,
  fatorDiasPorDiaria: 3,
  upliftConversao: 0.09,
  upliftEngajamento: 0.66,
};

/**
 * Cenário-base:
 *   diárias 10 × 10.000                          = 100.000
 *   variações 10 SKUs × 4 = 40 × 2.000           =  80.000
 *   mercados extras 1 × 20.000                   =  20.000
 *   peças 100/campanha × 2 campanhas = 200 × 500 = 100.000
 *   CUSTO_TRAD                                   = 300.000
 *
 *   twins 10 × 5.000                             =  50.000
 *   desdobramento 200 × 100                      =  20.000
 *   CUSTO_NGI_A1                                 =  70.000
 *   manutenção 10 × 200                          =   2.000
 *   CUSTO_NGI_AN                                 =  22.000
 */
const CENARIO: CalcInputs = {
  setor: 'automotivo',
  skus: 10,
  campanhas: 2,
  diarias: 10,
  custoDiaria: 10_000,
  variacoesPorSku: 4,
  mercados: 2,
  pecas: { social: 40, ecommerce: 30, ooh: 10, video: 5, midiaPaga: 15 },
  complexidadeTwin: 'complexo',
  skusDigitalizados: 10,
};

describe('pecasPorCampanha', () => {
  it('soma todos os canais', () => {
    expect(pecasPorCampanha(CENARIO.pecas)).toBe(100);
  });

  it('retorna 0 quando nenhum canal tem peça', () => {
    expect(
      pecasPorCampanha({ social: 0, ecommerce: 0, ooh: 0, video: 0, midiaPaga: 0 }),
    ).toBe(0);
  });
});

describe('volumes derivados', () => {
  const r = calcular(CENARIO, BM);

  it('peças totais = peças por campanha × campanhas', () => {
    expect(r.pecasTotal).toBe(200);
  });

  it('variações totais = skus × variações por sku', () => {
    expect(r.variacoesTotal).toBe(40);
  });

  it('mercados extras desconta o mercado de origem', () => {
    expect(r.mercadosExtras).toBe(1);
    expect(calcular({ ...CENARIO, mercados: 1 }, BM).mercadosExtras).toBe(0);
    expect(calcular({ ...CENARIO, mercados: 5 }, BM).mercadosExtras).toBe(4);
  });
});

describe('CUSTO_TRAD', () => {
  it('soma diárias, reshoot de variações, adaptação de mercado e pós-produção', () => {
    expect(calcular(CENARIO, BM).custoTradicional).toBe(300_000);
  });

  it('cresce linearmente com as diárias', () => {
    const dobro = calcular({ ...CENARIO, diarias: 20 }, BM).custoTradicional;
    expect(dobro).toBe(400_000); // +100.000 de diárias
  });

  it('não cobra adaptação quando há um único mercado', () => {
    expect(calcular({ ...CENARIO, mercados: 1 }, BM).custoTradicional).toBe(280_000);
  });
});

describe('CUSTO_NGI', () => {
  const r = calcular(CENARIO, BM);

  it('ano 1 inclui a criação dos digital twins', () => {
    expect(r.investimentoTwins).toBe(50_000);
    expect(r.custoNgiAno1).toBe(70_000);
  });

  it('ano 2+ troca a criação do twin pela manutenção', () => {
    expect(r.custoNgiRecorrente).toBe(22_000);
  });

  it('usa a régua de complexidade do twin', () => {
    expect(calcular({ ...CENARIO, complexidadeTwin: 'simples' }, BM).custoNgiAno1).toBe(30_000);
    expect(calcular({ ...CENARIO, complexidadeTwin: 'medio' }, BM).custoNgiAno1).toBe(40_000);
  });

  it('digitalizar menos SKUs reduz o investimento do ano 1', () => {
    const r5 = calcular({ ...CENARIO, skusDigitalizados: 5 }, BM);
    expect(r5.investimentoTwins).toBe(25_000);
    expect(r5.custoNgiAno1).toBe(45_000);
    expect(r5.custoNgiRecorrente).toBe(21_000); // 20.000 + 5 × 200
  });
});

describe('economias', () => {
  const r = calcular(CENARIO, BM);

  it('ECONOMIA_A1 = CUSTO_TRAD − CUSTO_NGI_A1', () => {
    expect(r.economiaAno1).toBe(230_000);
  });

  it('ECONOMIA_ANUAL_A2+ = CUSTO_TRAD − CUSTO_NGI_AN', () => {
    expect(r.economiaAnualRecorrente).toBe(278_000);
  });

  it('ECONOMIA_3_ANOS = ECONOMIA_A1 + 2 × ECONOMIA_ANUAL_A2+', () => {
    expect(r.economia3Anos).toBe(230_000 + 2 * 278_000);
  });

  it('percentual de economia é a economia recorrente sobre o custo tradicional', () => {
    expect(r.percentualEconomia).toBeCloseTo(278_000 / 300_000, 10);
  });

  it('economia pode ser negativa quando o NGI custa mais — e o número é exibido como é', () => {
    // Volume alto de peças com produção tradicional barata: NGI perde.
    const caro = calcular(
      {
        ...CENARIO,
        diarias: 0,
        variacoesPorSku: 0,
        mercados: 1,
        skus: 100,
        skusDigitalizados: 100,
      },
      { ...BM, custoPosProducaoPeca: 50 },
    );
    expect(caro.custoTradicional).toBe(10_000);
    expect(caro.economiaAno1).toBeLessThan(0);
  });
});

describe('PAYBACK_MESES', () => {
  it('= investimento em twins / (economia recorrente / 12)', () => {
    const r = calcular(CENARIO, BM);
    expect(r.paybackMeses).toBeCloseTo(50_000 / (278_000 / 12), 2);
  });

  it('é null quando não há economia recorrente positiva', () => {
    const r = calcular(
      { ...CENARIO, diarias: 0, variacoesPorSku: 0, mercados: 1 },
      BM,
    );
    // TRAD = 200 × 500 = 100.000 ; NGI_AN = 20.000 + 2.000 = 22.000 → ainda positivo
    expect(r.economiaAnualRecorrente).toBe(78_000);

    const semEconomia = calcular(
      { ...CENARIO, diarias: 0, variacoesPorSku: 0, mercados: 1 },
      { ...BM, custoPosProducaoPeca: 0 },
    );
    expect(semEconomia.economiaAnualRecorrente).toBeLessThanOrEqual(0);
    expect(semEconomia.paybackMeses).toBeNull();
  });
});

describe('TEMPO_ECONOMIZADO', () => {
  it('= diárias × fator de dias por diária', () => {
    expect(calcular(CENARIO, BM).tempoEconomizadoDias).toBe(30);
  });
});

describe('uplift de receita', () => {
  it('é null quando o passo 4 não foi preenchido', () => {
    const r = calcular(CENARIO, BM);
    expect(r.faturamentoDigitalConsiderado).toBeNull();
    expect(r.upliftReceita).toBeNull();
  });

  it('usa o faturamento informado × benchmark de +9%', () => {
    const r = calcular({ ...CENARIO, faturamentoDigital: 10_000_000 }, BM);
    expect(r.upliftReceita).toBe(900_000);
  });

  it('deriva o faturamento de ticket médio × transações quando não informado', () => {
    const r = calcular({ ...CENARIO, ticketMedio: 250, transacoesAno: 40_000 }, BM);
    expect(r.faturamentoDigitalConsiderado).toBe(10_000_000);
    expect(r.upliftReceita).toBe(900_000);
  });

  it('NUNCA é somado à economia de custo', () => {
    const semReceita = calcular(CENARIO, BM);
    const comReceita = calcular({ ...CENARIO, faturamentoDigital: 50_000_000 }, BM);
    expect(comReceita.economiaAno1).toBe(semReceita.economiaAno1);
    expect(comReceita.economiaAnualRecorrente).toBe(semReceita.economiaAnualRecorrente);
    expect(comReceita.economia3Anos).toBe(semReceita.economia3Anos);
  });

  it('ignora faturamento inválido ou zerado', () => {
    expect(faturamentoDigital({ ...CENARIO, faturamentoDigital: 0 })).toBeNull();
    expect(faturamentoDigital({ ...CENARIO, ticketMedio: 100, transacoesAno: 0 })).toBeNull();
  });
});

describe('breakdown por canal', () => {
  const r = calcular(CENARIO, BM);

  it('cobre todos os canais', () => {
    expect(r.breakdownPorCanal.map((b) => b.canal)).toEqual([
      'social',
      'ecommerce',
      'ooh',
      'video',
      'midiaPaga',
    ]);
  });

  it('reconcilia com o total: a soma dos canais reproduz os custos anuais', () => {
    const somaTrad = r.breakdownPorCanal.reduce((a, b) => a + b.custoTradicional, 0);
    const somaNgi = r.breakdownPorCanal.reduce((a, b) => a + b.custoNgi, 0);
    expect(somaTrad).toBeCloseTo(r.custoTradicional, 2);
    expect(somaNgi).toBeCloseTo(r.custoNgiRecorrente, 2);
  });

  it('rateia proporcionalmente ao volume de peças do canal', () => {
    const social = r.breakdownPorCanal.find((b) => b.canal === 'social')!;
    expect(social.pecas).toBe(80); // 40 por campanha × 2
    // Custo não atribuído a canal: diárias (100.000) + variações (80.000) + mercado (20.000)
    // 40% das peças → 40% desses 200.000 + a pós-produção das próprias peças
    expect(social.custoTradicional).toBeCloseTo(80 * 500 + 0.4 * 200_000, 2);
  });

  it('não divide por zero quando não há peças', () => {
    const semPecas = calcular(
      { ...CENARIO, pecas: { social: 0, ecommerce: 0, ooh: 0, video: 0, midiaPaga: 0 } },
      BM,
    );
    expect(semPecas.pecasTotal).toBe(0);
    for (const b of semPecas.breakdownPorCanal) {
      expect(Number.isFinite(b.custoTradicional)).toBe(true);
      expect(b.custoTradicional).toBe(0);
    }
  });
});

describe('projeção de 3 anos', () => {
  const r = calcular(CENARIO, BM);

  it('ano 1 carrega o investimento no twin; anos 2 e 3 não', () => {
    expect(r.projecao3Anos[0].custoNgi).toBe(70_000);
    expect(r.projecao3Anos[1].custoNgi).toBe(22_000);
    expect(r.projecao3Anos[2].custoNgi).toBe(22_000);
  });

  it('economia acumulada do ano 3 = ECONOMIA_3_ANOS', () => {
    expect(r.projecao3Anos[2].economiaAcumulada).toBe(r.economia3Anos);
  });
});

describe('normalização de inputs', () => {
  it('rejeita negativos e usa defaults do setor para campos ausentes', () => {
    const n = normalizeInputs({ setor: 'moda', skus: -50 }, BM);
    const padrao = defaultInputs('moda', BM);
    expect(n.skus).toBe(0);
    expect(n.campanhas).toBe(padrao.campanhas);
    expect(n.custoDiaria).toBe(BM.custoDiaria.moda);
  });

  it('não digitaliza mais SKUs do que existem', () => {
    const n = normalizeInputs({ setor: 'automotivo', skus: 10, skusDigitalizados: 999 }, BM);
    expect(n.skusDigitalizados).toBe(10);
  });

  it('garante ao menos um mercado', () => {
    expect(normalizeInputs({ setor: 'automotivo', mercados: 0 }, BM).mercados).toBe(1);
  });

  it('ignora valores não numéricos vindos da URL', () => {
    const n = normalizeInputs({ setor: 'automotivo', skus: 'abc' as unknown as number }, BM);
    expect(n.skus).toBe(defaultInputs('automotivo', BM).skus);
  });

  it('cálculo com inputs zerados não produz NaN', () => {
    const r = calcular(
      {
        setor: 'outro',
        skus: 0,
        campanhas: 0,
        diarias: 0,
        custoDiaria: 0,
        variacoesPorSku: 0,
        mercados: 1,
        pecas: { social: 0, ecommerce: 0, ooh: 0, video: 0, midiaPaga: 0 },
        complexidadeTwin: 'simples',
        skusDigitalizados: 0,
      },
      BM,
    );
    expect(r.custoTradicional).toBe(0);
    expect(r.economiaAno1).toBe(0);
    expect(r.percentualEconomia).toBeNull();
    expect(r.paybackMeses).toBeNull();
  });
});

describe('defaults por setor', () => {
  it('todo setor tem default preenchido e calculável', () => {
    for (const setor of ['automotivo', 'maquinas_agro', 'bens_consumo', 'moda', 'eletronicos', 'outro'] as const) {
      const inputs = defaultInputs(setor);
      const r = calcular(inputs);
      expect(inputs.custoDiaria).toBe(BENCHMARKS_FALLBACK.custoDiaria[setor]);
      expect(Number.isFinite(r.economiaAnualRecorrente)).toBe(true);
    }
  });
});

describe('merge de benchmarks do Supabase', () => {
  it('mantém o fallback quando não há linhas', () => {
    expect(mergeBenchmarks([])).toEqual(BENCHMARKS_FALLBACK);
    expect(mergeBenchmarks(null)).toEqual(BENCHMARKS_FALLBACK);
  });

  it('sobrescreve custo de diária por setor (chave + coluna setor)', () => {
    const bm = mergeBenchmarks([{ setor: 'automotivo', chave: 'custo_diaria', valor: 99_000 }]);
    expect(bm.custoDiaria.automotivo).toBe(99_000);
    expect(bm.custoDiaria.moda).toBe(BENCHMARKS_FALLBACK.custoDiaria.moda);
  });

  it('aceita setor embutido na chave (custo_diaria_moda)', () => {
    const bm = mergeBenchmarks([{ setor: '*', chave: 'custo_diaria_moda', valor: 31_000 }]);
    expect(bm.custoDiaria.moda).toBe(31_000);
  });

  it('sobrescreve a régua de complexidade do twin', () => {
    const bm = mergeBenchmarks([
      { setor: null, chave: 'custo_twin_por_sku_complexo', valor: 33_000 },
      { setor: 'medio', chave: 'custo_twin_por_sku', valor: 15_000 },
    ]);
    expect(bm.custoTwinPorSku.complexo).toBe(33_000);
    expect(bm.custoTwinPorSku.medio).toBe(15_000);
    expect(bm.custoTwinPorSku.simples).toBe(BENCHMARKS_FALLBACK.custoTwinPorSku.simples);
  });

  it('sobrescreve chaves globais e converte string numérica', () => {
    const bm = mergeBenchmarks([
      { setor: null, chave: 'custo_desdobramento_peca', valor: '250' },
      { setor: null, chave: 'uplift_conversao', valor: 0.12 },
    ]);
    expect(bm.custoDesdobramentoPeca).toBe(250);
    expect(bm.upliftConversao).toBe(0.12);
  });

  it('ignora linhas inválidas sem quebrar o restante', () => {
    const bm = mergeBenchmarks([
      { setor: null, chave: 'chave_inexistente', valor: 1 },
      { setor: null, chave: 'custo_manutencao_twin', valor: 'não é número' },
    ]);
    expect(bm.custoManutencaoTwin).toBe(BENCHMARKS_FALLBACK.custoManutencaoTwin);
  });

  it('não muta o objeto de fallback', () => {
    mergeBenchmarks([{ setor: 'automotivo', chave: 'custo_diaria', valor: 1 }]);
    expect(BENCHMARKS_FALLBACK.custoDiaria.automotivo).toBe(45_000);
  });
});
