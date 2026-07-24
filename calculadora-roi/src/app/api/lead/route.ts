import { NextResponse } from 'next/server';
import { calcular } from '@/lib/calc';
import { checarRateLimit, ipDoRequest, origemValida } from '@/lib/rate-limit';
import { calcularScore, exigeToqueComercial } from '@/lib/scoring';
import { carregarBenchmarks, getSupabaseAdmin } from '@/lib/supabase';
import { leadSchema } from '@/lib/validation';
import type { CalcResultados, CalcInputs } from '@/lib/types';
import type { ScoringResult } from '@/lib/scoring';

export const runtime = 'nodejs';

/**
 * Captura do lead no gate: persiste, pontua e — só para Tier A — avisa o time.
 * O scoring é o que impede curioso e concorrente de chegarem à mesa do BDR.
 */
export async function POST(req: Request) {
  if (!origemValida(req)) {
    return NextResponse.json({ erro: 'Origem não permitida.' }, { status: 403 });
  }

  const { permitido } = checarRateLimit(`lead:${ipDoRequest(req)}`, 5, 60_000);
  if (!permitido) {
    return NextResponse.json(
      { erro: 'Muitas tentativas. Aguarde um minuto e tente de novo.' },
      { status: 429 },
    );
  }

  const corpo = await req.json().catch(() => null);
  const parsed = leadSchema.safeParse(corpo);
  if (!parsed.success) {
    return NextResponse.json({ erro: 'Confira os campos e tente novamente.' }, { status: 400 });
  }

  const dados = parsed.data;

  // Honeypot: responde 200 para não ensinar o bot, mas não grava nada.
  if (dados.website.trim() !== '') {
    return NextResponse.json({ ok: true, tier: 'C', score: 0 });
  }

  const benchmarks = await carregarBenchmarks();
  const resultados = calcular(dados.inputs, benchmarks);

  const scoring = calcularScore({
    skusAno: dados.inputs.skus,
    economiaCalculada: resultados.economiaAnualRecorrente,
    setor: dados.inputs.setor,
    email: dados.email,
    cargo: dados.cargo,
    informouReceita: resultados.faturamentoDigitalConsiderado !== null,
  });

  const supabase = getSupabaseAdmin();
  if (supabase) {
    let calculoId = dados.calculoId ?? null;

    // Se o cálculo não foi persistido antes (falha de rede, por exemplo), grava agora.
    if (!calculoId && dados.shareId) {
      const { data } = await supabase
        .from('calculos')
        .select('id')
        .eq('share_id', dados.shareId)
        .maybeSingle();
      calculoId = data?.id ?? null;
    }

    const { data: lead } = await supabase
      .from('leads')
      .insert({
        calculo_id: calculoId,
        nome: dados.nome,
        email: dados.email.toLowerCase(),
        empresa: dados.empresa || null,
        cargo: dados.cargo || null,
        email_tipo: scoring.emailTipo,
        score: scoring.score,
        tier: scoring.tier,
        utm: dados.utm,
      })
      .select('id')
      .single();

    await supabase.from('eventos').insert({
      calculo_id: calculoId,
      tipo: 'roi_calc_lead_submitted',
      payload: {
        lead_id: lead?.id ?? null,
        tier: scoring.tier,
        score: scoring.score,
        setor: dados.inputs.setor,
        economia_anual: resultados.economiaAnualRecorrente,
      },
    });
  }

  if (exigeToqueComercial(scoring.tier)) {
    await notificarSlack(dados, resultados, scoring);
  }

  return NextResponse.json({ ok: true, tier: scoring.tier, score: scoring.score });
}

/** Alerta imediato de Tier A. Falha silenciosa: nunca bloqueia o lead. */
async function notificarSlack(
  dados: { nome: string; email: string; empresa: string; cargo: string; inputs: CalcInputs },
  resultados: CalcResultados,
  scoring: ScoringResult,
): Promise<void> {
  const webhook = process.env.SLACK_WEBHOOK_URL;
  if (!webhook) return;

  const economia = new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
    maximumFractionDigits: 0,
  }).format(resultados.economiaAnualRecorrente);

  const texto = [
    `*Lead Tier A na Calculadora de ROI* (score ${scoring.score})`,
    `${dados.nome}${dados.cargo ? ` — ${dados.cargo}` : ''}${dados.empresa ? ` @ ${dados.empresa}` : ''}`,
    `${dados.email} (${scoring.emailTipo})`,
    `Setor: ${dados.inputs.setor} · ${dados.inputs.skus} SKUs · ${resultados.pecasTotal} peças/ano`,
    `Economia calculada: ${economia}/ano`,
    `Critérios: ${scoring.detalhe.map((d) => `${d.criterio} (+${d.pontos})`).join(', ')}`,
  ].join('\n');

  try {
    await fetch(webhook, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ text: texto }),
      signal: AbortSignal.timeout(4000),
    });
  } catch {
    // Sem alerta o lead continua gravado e visível no Supabase.
  }
}
