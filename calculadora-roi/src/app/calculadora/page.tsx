import Link from 'next/link';
import { Wizard } from '@/components/Wizard';
import { carregarBenchmarks } from '@/lib/supabase';
import { extrairUtm, searchParamsToInputs } from '@/lib/url-state';

export const dynamic = 'force-dynamic';

export default async function CalculadoraPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  // Benchmarks vêm do Supabase (editáveis sem deploy) com fallback local.
  const benchmarks = await carregarBenchmarks();
  const inputs = searchParamsToInputs(params, benchmarks);

  return (
    <main className="mx-auto px-6 py-10 md:py-16" style={{ maxWidth: 'var(--max-width)' }}>
      <header className="mb-12 flex items-center justify-between gap-6">
        <Link href="/" className="eyebrow no-underline">
          Sétima · Calculadora de ROI NGI
        </Link>
      </header>

      <Wizard benchmarks={benchmarks} inputsIniciais={inputs} utm={extrairUtm(params)} />
    </main>
  );
}
