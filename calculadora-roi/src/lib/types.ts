/**
 * Tipos do domínio da Calculadora de ROI NGI.
 * Referência: PRD seção 5 (modelo de cálculo).
 */

export const SETORES = [
  'automotivo',
  'maquinas_agro',
  'bens_consumo',
  'moda',
  'eletronicos',
  'outro',
] as const;

export type Setor = (typeof SETORES)[number];

export const SETOR_LABEL: Record<Setor, string> = {
  automotivo: 'Automotivo',
  maquinas_agro: 'Máquinas / Agro',
  bens_consumo: 'Bens de consumo',
  moda: 'Moda / Vestuário',
  eletronicos: 'Eletrônicos',
  outro: 'Outro',
};

export const COMPLEXIDADES = ['simples', 'medio', 'complexo'] as const;
export type Complexidade = (typeof COMPLEXIDADES)[number];

export const COMPLEXIDADE_LABEL: Record<Complexidade, string> = {
  simples: 'Simples (embalagem, produto sem mecanismo)',
  medio: 'Médio (eletrodoméstico, calçado, produto com partes)',
  complexo: 'Complexo (veículo, máquina agrícola, linha completa)',
};

export const CANAIS = ['social', 'ecommerce', 'ooh', 'video', 'midiaPaga'] as const;
export type Canal = (typeof CANAIS)[number];

export const CANAL_LABEL: Record<Canal, string> = {
  social: 'Social',
  ecommerce: 'E-commerce / PDP',
  ooh: 'OOH',
  video: 'Vídeo',
  midiaPaga: 'Mídia paga',
};

/** Peças produzidas por campanha, por canal. */
export type PecasPorCanal = Record<Canal, number>;

/** Inputs coletados no wizard (passos 1 a 4). */
export interface CalcInputs {
  // Passo 1 — contexto
  setor: Setor;
  skus: number;
  campanhas: number;

  // Passo 2 — produção atual
  diarias: number;
  custoDiaria: number;
  variacoesPorSku: number;
  mercados: number;

  // Passo 3 — volume de peças (por campanha, por canal)
  pecas: PecasPorCanal;

  // Régua de digitalização
  complexidadeTwin: Complexidade;
  /** Quantos SKUs entram no digital twin. Default: todos. */
  skusDigitalizados: number;

  // Passo 4 — receita (opcional)
  ticketMedio?: number;
  transacoesAno?: number;
  faturamentoDigital?: number;
}

/** Benchmarks editáveis (Supabase `benchmarks`, com fallback local). */
export interface Benchmarks {
  /** Custo médio de diária de produção, por setor. */
  custoDiaria: Record<Setor, number>;
  /** Custo de modelagem do digital twin, por complexidade de SKU. */
  custoTwinPorSku: Record<Complexidade, number>;
  /** Custo de gerar 1 peça a partir do twin. */
  custoDesdobramentoPeca: number;
  /** Custo de refazer ensaio por variação (cor, versão, acabamento). */
  custoReshootVariacao: number;
  /** Custo de adaptar a produção para 1 mercado/idioma adicional. */
  custoAdaptacaoMercado: number;
  /** Pós-produção (tratamento, recorte, adaptação de formato) por peça no fluxo tradicional. */
  custoPosProducaoPeca: number;
  /** Manutenção anual do twin a partir do ano 2. */
  custoManutencaoTwin: number;
  /** Dias de calendário consumidos por diária (setup, logística, aprovação). */
  fatorDiasPorDiaria: number;
  /** Benchmark público da Sétima: +9% em vendas. */
  upliftConversao: number;
  /** Benchmark público da Sétima: +66% de engajamento. */
  upliftEngajamento: number;
}

export interface BreakdownCanal {
  canal: Canal;
  pecas: number;
  custoTradicional: number;
  custoNgi: number;
  economia: number;
}

export interface CalcResultados {
  // Volumes derivados
  pecasTotal: number;
  variacoesTotal: number;
  mercadosExtras: number;

  // Custos
  custoTradicional: number;
  custoNgiAno1: number;
  custoNgiRecorrente: number;

  // Resultados principais
  economiaAno1: number;
  economiaAnualRecorrente: number;
  economia3Anos: number;
  /** Percentual de economia recorrente sobre o custo tradicional (0..1). Null se custo tradicional = 0. */
  percentualEconomia: number | null;
  /** Meses para o investimento nos twins se pagar. Null quando não há economia recorrente positiva. */
  paybackMeses: number | null;
  /** Dias de calendário liberados por ano. */
  tempoEconomizadoDias: number;

  // Blocos secundários (nunca somados à economia)
  faturamentoDigitalConsiderado: number | null;
  upliftReceita: number | null;

  // Detalhamento
  breakdownPorCanal: BreakdownCanal[];
  projecao3Anos: Array<{
    ano: number;
    custoTradicional: number;
    custoNgi: number;
    economia: number;
    economiaAcumulada: number;
  }>;
  investimentoTwins: number;
}
