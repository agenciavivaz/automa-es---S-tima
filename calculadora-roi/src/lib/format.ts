const brl = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  maximumFractionDigits: 0,
});

const brlPreciso = new Intl.NumberFormat('pt-BR', {
  style: 'currency',
  currency: 'BRL',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const inteiro = new Intl.NumberFormat('pt-BR', { maximumFractionDigits: 0 });

export const formatMoeda = (v: number) => brl.format(Number.isFinite(v) ? v : 0);
export const formatMoedaPrecisa = (v: number) => brlPreciso.format(Number.isFinite(v) ? v : 0);
export const formatNumero = (v: number) => inteiro.format(Number.isFinite(v) ? v : 0);

export const formatPercent = (v: number | null) =>
  v === null || !Number.isFinite(v) ? '—' : `${Math.round(v * 100)}%`;

/** Número grande em versão compacta para o hero do resultado: R$ 1,2 mi. */
export function formatMoedaCompacta(v: number): string {
  if (!Number.isFinite(v)) return 'R$ 0';
  const sinal = v < 0 ? '-' : '';
  const abs = Math.abs(v);
  const f = (n: number) =>
    n.toLocaleString('pt-BR', { minimumFractionDigits: 0, maximumFractionDigits: 1 });
  if (abs >= 1_000_000_000) return `${sinal}R$ ${f(abs / 1_000_000_000)} bi`;
  if (abs >= 1_000_000) return `${sinal}R$ ${f(abs / 1_000_000)} mi`;
  if (abs >= 1_000) return `${sinal}R$ ${f(abs / 1_000)} mil`;
  return `${sinal}R$ ${f(abs)}`;
}

export function formatMeses(v: number | null): string {
  if (v === null || !Number.isFinite(v) || v <= 0) return '—';
  if (v < 1) return 'menos de 1 mês';
  const meses = Math.round(v);
  return meses === 1 ? '1 mês' : `${meses} meses`;
}

export function formatDias(v: number): string {
  if (!Number.isFinite(v) || v <= 0) return '—';
  const dias = Math.round(v);
  return dias === 1 ? '1 dia' : `${dias} dias`;
}
