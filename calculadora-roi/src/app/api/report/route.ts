import { NextResponse } from 'next/server';
import { calcular } from '@/lib/calc';
import { checarRateLimit, ipDoRequest, origemValida } from '@/lib/rate-limit';
import { gerarNarrativa, narrativaEstatica } from '@/lib/report';
import { carregarBenchmarks } from '@/lib/supabase';
import { reportSchema } from '@/lib/validation';

export const runtime = 'nodejs';
export const maxDuration = 15;

/**
 * Narrativa do relatório. O cálculo continua determinístico aqui no servidor —
 * a IA recebe os resultados prontos e só escreve a leitura estratégica.
 */
export async function POST(req: Request) {
  if (!origemValida(req)) {
    return NextResponse.json({ erro: 'Origem não permitida.' }, { status: 403 });
  }

  const { permitido } = checarRateLimit(`report:${ipDoRequest(req)}`, 10, 60_000);
  if (!permitido) {
    return NextResponse.json({ erro: 'Muitas requisições.' }, { status: 429 });
  }

  const corpo = await req.json().catch(() => null);
  const parsed = reportSchema.safeParse(corpo);
  if (!parsed.success) {
    return NextResponse.json({ erro: 'Dados inválidos.' }, { status: 400 });
  }

  const benchmarks = await carregarBenchmarks();
  const inputs = parsed.data.inputs;
  const resultados = calcular(inputs, benchmarks);

  try {
    const narrativa = await gerarNarrativa(inputs, resultados);
    return NextResponse.json(narrativa);
  } catch {
    return NextResponse.json(narrativaEstatica(inputs, resultados));
  }
}
