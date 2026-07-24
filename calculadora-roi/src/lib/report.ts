import Anthropic from '@anthropic-ai/sdk';
import { formatMoeda, formatMeses, formatNumero, formatPercent } from './format';
import { SETOR_LABEL } from './types';
import type { CalcInputs, CalcResultados, Setor } from './types';

/**
 * Narrativa do relatório — PRD seção 8.4.
 *
 * Guardrails inegociáveis:
 *   1. O cálculo é 100% determinístico em TypeScript. A IA NUNCA calcula.
 *   2. O prompt recebe apenas números já prontos e um resumo de cases do setor.
 *   3. Resposta em JSON estruturado.
 *   4. Timeout de 8s; se estourar (ou faltar chave), entrega o texto estático do setor.
 */

export interface Narrativa {
  titulo: string;
  paragrafos: string[];
  destaques: string[];
  origem: 'ia' | 'estatico';
}

/** Cases reais da Sétima por setor — contexto para a leitura estratégica. */
const CASES_POR_SETOR: Record<Setor, string> = {
  automotivo:
    'Volkswagen e VWCO: digital twin de veículo permitindo gerar todas as versões, cores e acessórios sem novo ensaio fotográfico.',
  maquinas_agro:
    'Projetos de maquinário pesado em que o transporte do equipamento para estúdio era o maior custo do ensaio.',
  bens_consumo:
    'Nestlé e Mercado Livre: catálogo amplo desdobrado a partir de um único asset 3D.',
  moda: 'Catálogos com alta rotatividade de coleção, em que o custo por peça derruba a margem da campanha.',
  eletronicos: 'iFood e Nubank: peças de produto e interface em escala para performance e social.',
  outro: 'Mais de 60 projetos em 2025 usando digital twin no lugar de produção tradicional.',
};

/** Texto estático por setor — fallback e base de comparação para a IA. */
export function narrativaEstatica(
  inputs: CalcInputs,
  r: CalcResultados,
): Narrativa {
  const setor = SETOR_LABEL[inputs.setor];
  const paragrafos = [
    `Com ${formatNumero(inputs.skus)} SKUs e ${formatNumero(inputs.campanhas)} campanhas por ano, sua operação de conteúdo em ${setor.toLowerCase()} custa hoje cerca de ${formatMoeda(r.custoTradicional)} por ano no modelo de produção tradicional — diárias, refação de ensaio por variação, adaptação de mercado e pós-produção das ${formatNumero(r.pecasTotal)} peças.`,
    `No modelo NGI, o investimento se concentra no ano 1, na criação dos digital twins (${formatMoeda(r.investimentoTwins)}). A partir daí cada nova peça é um desdobramento do mesmo asset: o custo anual recorrente cai para ${formatMoeda(r.custoNgiRecorrente)}, uma economia de ${formatPercent(r.percentualEconomia)} sobre o modelo atual.`,
    r.paybackMeses !== null
      ? `O investimento nos twins se paga em ${formatMeses(r.paybackMeses)}. Em três anos, a diferença acumulada é de ${formatMoeda(r.economia3Anos)}.`
      : `Nesse cenário específico, o volume de peças ainda não é suficiente para o modelo NGI se pagar — vale revisar o volume anual de desdobramentos com o time.`,
    `Além do custo, há o calendário: as ${formatNumero(inputs.diarias)} diárias de produção consomem cerca de ${formatNumero(r.tempoEconomizadoDias)} dias de setup, logística e aprovação por ano. Com o twin pronto, uma nova peça não depende de agenda de estúdio.`,
  ];

  return {
    titulo: `Sua economia anual estimada com NGI`,
    paragrafos,
    destaques: [
      `Economia recorrente de ${formatMoeda(r.economiaAnualRecorrente)} por ano`,
      r.paybackMeses !== null ? `Payback do digital twin em ${formatMeses(r.paybackMeses)}` : 'Payback fora do horizonte de 12 meses neste cenário',
      `${formatNumero(r.pecasTotal)} peças/ano geradas a partir do mesmo asset`,
    ],
    origem: 'estatico',
  };
}

const SCHEMA_NARRATIVA = {
  type: 'object',
  properties: {
    titulo: { type: 'string' },
    paragrafos: {
      type: 'array',
      items: { type: 'string' },
    },
    destaques: {
      type: 'array',
      items: { type: 'string' },
    },
  },
  required: ['titulo', 'paragrafos', 'destaques'],
  additionalProperties: false,
} as const;

const TIMEOUT_MS = 8_000;

/**
 * Gera a leitura estratégica com a Claude API.
 * Qualquer falha, timeout ou resposta fora do formato cai no texto estático.
 */
export async function gerarNarrativa(
  inputs: CalcInputs,
  r: CalcResultados,
): Promise<Narrativa> {
  const estatica = narrativaEstatica(inputs, r);
  if (!process.env.ANTHROPIC_API_KEY) return estatica;

  const client = new Anthropic({ timeout: TIMEOUT_MS, maxRetries: 0 });

  // A IA recebe SOMENTE resultados já calculados. Nenhum input bruto para cálculo.
  const dados = {
    setor: SETOR_LABEL[inputs.setor],
    skus: inputs.skus,
    campanhas_ano: inputs.campanhas,
    diarias_ano: inputs.diarias,
    pecas_ano: r.pecasTotal,
    custo_tradicional_ano: r.custoTradicional,
    custo_ngi_ano1: r.custoNgiAno1,
    custo_ngi_recorrente: r.custoNgiRecorrente,
    economia_ano1: r.economiaAno1,
    economia_anual_recorrente: r.economiaAnualRecorrente,
    economia_3_anos: r.economia3Anos,
    percentual_economia: r.percentualEconomia,
    payback_meses: r.paybackMeses,
    dias_liberados_ano: r.tempoEconomizadoDias,
    uplift_receita_estimado: r.upliftReceita,
  };

  const system = [
    'Você escreve a leitura estratégica de um relatório de ROI da Sétima, uma content-tech brasileira de NGI (Next-Gen Imagery: 3D + IA + automação).',
    'Regras inegociáveis:',
    '1. NUNCA calcule, recalcule, arredonde ou invente números. Use exatamente os valores fornecidos.',
    '2. Não cite preços unitários nem a tabela de custos da Sétima.',
    '3. A economia de custo e o uplift de receita são leituras distintas — jamais some as duas.',
    '4. Escreva em português do Brasil, tom direto e afirmativo, sem adjetivo de venda.',
    '5. 3 a 4 parágrafos curtos e 3 destaques de uma linha.',
    'O relatório é lido por um gerente de marketing que precisa defender essa troca numa reunião interna de budget.',
  ].join('\n');

  const prompt = [
    `Resultados calculados (já finais, apenas interprete):\n${JSON.stringify(dados, null, 2)}`,
    `Cases relevantes da Sétima neste setor: ${CASES_POR_SETOR[inputs.setor]}`,
    'Benchmarks públicos da Sétima: +66% de engajamento e +9% em vendas com experiências 3D interativas.',
    'Escreva a leitura estratégica desses números.',
  ].join('\n\n');

  try {
    const response = await client.messages.create({
      model: 'claude-opus-5',
      max_tokens: 2000,
      system,
      output_config: {
        effort: 'low',
        format: { type: 'json_schema', schema: SCHEMA_NARRATIVA },
      },
      messages: [{ role: 'user', content: prompt }],
    });

    if (response.stop_reason === 'refusal') return estatica;

    const texto = response.content
      .filter((b): b is Anthropic.TextBlock => b.type === 'text')
      .map((b) => b.text)
      .join('');

    const parsed = JSON.parse(texto) as Partial<Narrativa>;
    if (
      typeof parsed.titulo !== 'string' ||
      !Array.isArray(parsed.paragrafos) ||
      parsed.paragrafos.length === 0
    ) {
      return estatica;
    }

    return {
      titulo: parsed.titulo,
      paragrafos: parsed.paragrafos.filter((p) => typeof p === 'string'),
      destaques: (parsed.destaques ?? estatica.destaques).filter(
        (d) => typeof d === 'string',
      ),
      origem: 'ia',
    };
  } catch {
    // Timeout, rede, cota, JSON inválido — o relatório sai igual, com o texto do setor.
    return estatica;
  }
}
