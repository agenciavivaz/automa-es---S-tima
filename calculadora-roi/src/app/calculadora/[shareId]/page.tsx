import Link from 'next/link';
import { notFound } from 'next/navigation';
import { Wizard } from '@/components/Wizard';
import { normalizeInputs } from '@/lib/calc';
import { carregarBenchmarks, getSupabaseAdmin } from '@/lib/supabase';
import { extrairUtm, searchParamsToInputs } from '@/lib/url-state';
import type { CalcInputs } from '@/lib/types';

export const dynamic = 'force-dynamic';

/**
 * Cenário salvo e compartilhável.
 * Sem Supabase configurado, a página cai no cenário da própria query string —
 * o link continua funcionando porque o estado também vive na URL.
 */
export default async function CenarioPage({
  params,
  searchParams,
}: {
  params: Promise<{ shareId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { shareId } = await params;
  const query = await searchParams;
  const benchmarks = await carregarBenchmarks();

  let inputs: CalcInputs | null = null;
  const supabase = getSupabaseAdmin();

  if (supabase) {
    const { data } = await supabase
      .from('calculos')
      .select('inputs')
      .eq('share_id', shareId)
      .maybeSingle();

    if (data?.inputs) {
      inputs = normalizeInputs(data.inputs as Partial<CalcInputs>, benchmarks);
    }
  }

  if (!inputs) {
    const temCenarioNaUrl = Object.keys(query).length > 0;
    if (!temCenarioNaUrl && supabase) notFound();
    inputs = searchParamsToInputs(query, benchmarks);
  }

  return (
    <main className="mx-auto px-6 py-10 md:py-16" style={{ maxWidth: 'var(--max-width)' }}>
      <header className="mb-12">
        <Link href="/" className="eyebrow no-underline">
          Sétima · Calculadora de ROI NGI
        </Link>
        <p className="mt-3 text-sm" style={{ color: 'var(--setima-muted)' }}>
          Cenário compartilhado. Ajuste os números para simular o seu.
        </p>
      </header>

      <Wizard
        benchmarks={benchmarks}
        inputsIniciais={inputs}
        utm={extrairUtm(query)}
        shareIdInicial={shareId}
      />
    </main>
  );
}
