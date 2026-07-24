'use client';

import { formatMoeda } from '@/lib/format';

/**
 * Gráfico comparativo: duas barras, sem ornamento (PRD seção 7).
 * Tradicional × NGI, na mesma escala.
 */
export function BarrasComparativas({
  tradicional,
  ngi,
  rotuloNgi = 'NGI (recorrente)',
}: {
  tradicional: number;
  ngi: number;
  rotuloNgi?: string;
}) {
  const maior = Math.max(tradicional, ngi, 1);
  const pctTrad = Math.max(2, (tradicional / maior) * 100);
  const pctNgi = Math.max(2, (ngi / maior) * 100);

  return (
    <div>
      <Barra
        rotulo="Produção tradicional"
        valor={tradicional}
        percentual={pctTrad}
        cor="var(--setima-negativo)"
      />
      <Barra rotulo={rotuloNgi} valor={ngi} percentual={pctNgi} cor="var(--setima-accent)" />
    </div>
  );
}

function Barra({
  rotulo,
  valor,
  percentual,
  cor,
}: {
  rotulo: string;
  valor: number;
  percentual: number;
  cor: string;
}) {
  return (
    <div className="mb-5">
      <div className="mb-2 flex items-baseline justify-between gap-4">
        <span className="text-sm" style={{ color: 'var(--setima-muted)' }}>
          {rotulo}
        </span>
        <span className="font-display text-base tabular-nums">{formatMoeda(valor)}</span>
      </div>
      <div
        className="h-4 w-full overflow-hidden rounded-sm"
        style={{ background: 'var(--setima-bg)' }}
        role="img"
        aria-label={`${rotulo}: ${formatMoeda(valor)}`}
      >
        <div
          className="h-full rounded-sm transition-[width] duration-300"
          style={{ width: `${percentual}%`, background: cor }}
        />
      </div>
    </div>
  );
}
