import type { Benchmarks, Complexidade, Setor } from './types';
import { COMPLEXIDADES, SETORES } from './types';

/**
 * ============================================================================
 * ATENÇÃO — PENDÊNCIA BLOQUEANTE DE LAUNCH (PRD seção 5.3 / Fase 0)
 * ============================================================================
 * Os valores abaixo são PLACEHOLDERS conservadores, colocados apenas para
 * destravar o desenvolvimento. Eles NÃO foram validados pelo time da Sétima e
 * NÃO devem ir ao ar.
 *
 * Antes do launch:
 *   1. Substituir cada valor por um benchmark que a Sétima consiga defender
 *      numa call com um gerente de marketing de montadora.
 *   2. Backtestar contra 2-3 projetos reais já entregues.
 *   3. Carregar os valores finais na tabela `benchmarks` do Supabase — a partir
 *      daí eles são editáveis sem deploy e esta tabela vira só o fallback.
 *
 * Um número inflado que não sobrevive ao escrutínio do prospect custa mais caro
 * do que não ter a ferramenta.
 */
export const BENCHMARKS_FALLBACK: Benchmarks = {
  // Diária de produção (equipe, estúdio/locação, equipamento, logística).
  custoDiaria: {
    automotivo: 45000,
    maquinas_agro: 38000,
    bens_consumo: 18000,
    moda: 22000,
    eletronicos: 20000,
    outro: 20000,
  },
  // Modelagem do digital twin, por complexidade do SKU.
  custoTwinPorSku: {
    simples: 4500,
    medio: 12000,
    complexo: 28000,
  },
  custoDesdobramentoPeca: 180,
  custoReshootVariacao: 2800,
  custoAdaptacaoMercado: 15000,
  custoPosProducaoPeca: 450,
  custoManutencaoTwin: 900,
  fatorDiasPorDiaria: 3.5,
  // Fontes públicas (LP da Sétima).
  upliftConversao: 0.09,
  upliftEngajamento: 0.66,
};

/** Chaves aceitas na tabela `benchmarks` do Supabase. */
export type ChaveBenchmark =
  | 'custo_diaria'
  | 'custo_twin_por_sku'
  | 'custo_desdobramento_peca'
  | 'custo_reshoot_variacao'
  | 'custo_adaptacao_mercado'
  | 'custo_pos_producao_peca'
  | 'custo_manutencao_twin'
  | 'fator_dias_por_diaria'
  | 'uplift_conversao'
  | 'uplift_engajamento';

export interface LinhaBenchmark {
  /** Setor da linha, ou `null`/`'*'` quando o valor vale para todos os setores. */
  setor: string | null;
  chave: string;
  valor: number | string;
}

const isSetor = (v: string): v is Setor => (SETORES as readonly string[]).includes(v);
const isComplexidade = (v: string): v is Complexidade =>
  (COMPLEXIDADES as readonly string[]).includes(v);

/**
 * Converte as linhas da tabela `benchmarks` num objeto `Benchmarks`,
 * mantendo o fallback local para toda chave ausente ou inválida.
 *
 * Convenções de chave aceitas:
 *   - `custo_diaria` com `setor` preenchido (ex.: setor=automotivo)
 *   - `custo_diaria_automotivo` (setor embutido na chave, setor='*')
 *   - `custo_twin_por_sku` com setor `simples|medio|complexo` (régua de complexidade)
 *   - `custo_twin_por_sku_complexo`
 *   - demais chaves globais, com qualquer setor
 */
export function mergeBenchmarks(
  linhas: LinhaBenchmark[] | null | undefined,
  base: Benchmarks = BENCHMARKS_FALLBACK,
): Benchmarks {
  const out: Benchmarks = {
    ...base,
    custoDiaria: { ...base.custoDiaria },
    custoTwinPorSku: { ...base.custoTwinPorSku },
  };
  if (!linhas?.length) return out;

  for (const linha of linhas) {
    const valor = typeof linha.valor === 'string' ? Number(linha.valor) : linha.valor;
    if (!Number.isFinite(valor)) continue;

    const chaveBruta = String(linha.chave ?? '').trim().toLowerCase();
    const setorBruto = String(linha.setor ?? '').trim().toLowerCase();

    if (chaveBruta.startsWith('custo_diaria')) {
      const sufixo = chaveBruta.slice('custo_diaria'.length).replace(/^_/, '');
      const alvo = sufixo || setorBruto;
      if (isSetor(alvo)) out.custoDiaria[alvo] = valor;
      continue;
    }

    if (chaveBruta.startsWith('custo_twin_por_sku')) {
      const sufixo = chaveBruta.slice('custo_twin_por_sku'.length).replace(/^_/, '');
      const alvo = sufixo || setorBruto;
      if (isComplexidade(alvo)) out.custoTwinPorSku[alvo] = valor;
      continue;
    }

    switch (chaveBruta) {
      case 'custo_desdobramento_peca':
        out.custoDesdobramentoPeca = valor;
        break;
      case 'custo_reshoot_variacao':
        out.custoReshootVariacao = valor;
        break;
      case 'custo_adaptacao_mercado':
        out.custoAdaptacaoMercado = valor;
        break;
      case 'custo_pos_producao_peca':
        out.custoPosProducaoPeca = valor;
        break;
      case 'custo_manutencao_twin':
        out.custoManutencaoTwin = valor;
        break;
      case 'fator_dias_por_diaria':
        out.fatorDiasPorDiaria = valor;
        break;
      case 'uplift_conversao':
        out.upliftConversao = valor;
        break;
      case 'uplift_engajamento':
        out.upliftEngajamento = valor;
        break;
      default:
        break;
    }
  }

  return out;
}

/** Complexidade de twin sugerida por setor (usada como default do wizard). */
export const COMPLEXIDADE_PADRAO_POR_SETOR: Record<Setor, Complexidade> = {
  automotivo: 'complexo',
  maquinas_agro: 'complexo',
  bens_consumo: 'simples',
  moda: 'medio',
  eletronicos: 'medio',
  outro: 'medio',
};
