import { NextResponse } from 'next/server';
import { calcular } from '@/lib/calc';
import { checarRateLimit, ipDoRequest, origemValida } from '@/lib/rate-limit';
import { carregarBenchmarks, getSupabaseAdmin } from '@/lib/supabase';
import { calculoSchema } from '@/lib/validation';

export const runtime = 'nodejs';

/** Identificador curto e legível para compartilhar o cenário. */
function novoShareId(): string {
  return crypto.randomUUID().replace(/-/g, '').slice(0, 12);
}

/**
 * Persiste cada execução da calculadora — inclusive as que nunca viram lead.
 * É o que permite medir drop-off por passo desde o dia 1 (PRD seção 10).
 */
export async function POST(req: Request) {
  if (!origemValida(req)) {
    return NextResponse.json({ erro: 'Origem não permitida.' }, { status: 403 });
  }

  const { permitido } = checarRateLimit(`calculo:${ipDoRequest(req)}`, 30, 60_000);
  if (!permitido) {
    return NextResponse.json({ erro: 'Muitas requisições. Tente em instantes.' }, { status: 429 });
  }

  const corpo = await req.json().catch(() => null);
  const parsed = calculoSchema.safeParse(corpo);
  if (!parsed.success) {
    return NextResponse.json({ erro: 'Dados inválidos.' }, { status: 400 });
  }

  const { sessionId, inputs } = parsed.data;
  const shareId = parsed.data.shareId ?? novoShareId();

  const benchmarks = await carregarBenchmarks();
  const resultados = calcular(inputs, benchmarks);

  const supabase = getSupabaseAdmin();
  if (!supabase) {
    // Sem Supabase, o cenário continua compartilhável pela própria URL.
    return NextResponse.json({ shareId, persistido: false });
  }

  const { data, error } = await supabase
    .from('calculos')
    .upsert(
      {
        share_id: shareId,
        session_id: sessionId,
        inputs,
        resultados,
        setor: inputs.setor,
        concluido: true,
      },
      { onConflict: 'share_id' },
    )
    .select('id')
    .single();

  if (error || !data) {
    return NextResponse.json({ shareId, persistido: false });
  }

  await supabase.from('eventos').insert({
    calculo_id: data.id,
    tipo: 'roi_calc_result_viewed',
    payload: { setor: inputs.setor, economia_anual: resultados.economiaAnualRecorrente },
  });

  return NextResponse.json({ id: data.id, shareId, persistido: true });
}
