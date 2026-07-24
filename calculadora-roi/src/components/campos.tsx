'use client';

import { formatMoeda, formatNumero } from '@/lib/format';

interface BaseProps {
  id: string;
  label: string;
  ajuda?: string;
}

export function CampoSlider({
  id,
  label,
  ajuda,
  valor,
  min,
  max,
  step = 1,
  onChange,
  formato = 'numero',
}: BaseProps & {
  valor: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  formato?: 'numero' | 'moeda';
}) {
  const exibicao = formato === 'moeda' ? formatMoeda(valor) : formatNumero(valor);

  return (
    <div className="mb-6">
      <div className="flex items-baseline justify-between gap-4">
        <label htmlFor={id} className="text-sm font-semibold">
          {label}
        </label>
        <output
          htmlFor={id}
          className="font-display text-lg tabular-nums"
          style={{ color: 'var(--setima-accent)' }}
        >
          {exibicao}
        </output>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={Math.min(Math.max(valor, min), max)}
        onChange={(e) => onChange(Number(e.target.value))}
        aria-describedby={ajuda ? `${id}-ajuda` : undefined}
      />
      {/* O slider cobre a faixa usual; o campo numérico aceita qualquer valor. */}
      <div className="flex items-center gap-3">
        <input
          type="number"
          inputMode="numeric"
          min={0}
          value={valor}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label={`${label} (valor exato)`}
          className="max-w-40"
        />
        {ajuda && (
          <p id={`${id}-ajuda`} className="text-xs" style={{ color: 'var(--setima-muted)' }}>
            {ajuda}
          </p>
        )}
      </div>
    </div>
  );
}

export function CampoNumero({
  id,
  label,
  ajuda,
  valor,
  onChange,
  placeholder,
}: BaseProps & {
  valor: number | undefined;
  onChange: (v: number | undefined) => void;
  placeholder?: string;
}) {
  return (
    <div className="mb-6">
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        {label}
      </label>
      <input
        id={id}
        type="number"
        inputMode="numeric"
        min={0}
        placeholder={placeholder}
        value={valor ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
        aria-describedby={ajuda ? `${id}-ajuda` : undefined}
      />
      {ajuda && (
        <p id={`${id}-ajuda`} className="mt-2 text-xs" style={{ color: 'var(--setima-muted)' }}>
          {ajuda}
        </p>
      )}
    </div>
  );
}

export function CampoSelect<T extends string>({
  id,
  label,
  ajuda,
  valor,
  opcoes,
  onChange,
}: BaseProps & {
  valor: T;
  opcoes: Array<{ valor: T; rotulo: string }>;
  onChange: (v: T) => void;
}) {
  return (
    <div className="mb-6">
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        {label}
      </label>
      <select
        id={id}
        value={valor}
        onChange={(e) => onChange(e.target.value as T)}
        aria-describedby={ajuda ? `${id}-ajuda` : undefined}
      >
        {opcoes.map((o) => (
          <option key={o.valor} value={o.valor}>
            {o.rotulo}
          </option>
        ))}
      </select>
      {ajuda && (
        <p id={`${id}-ajuda`} className="mt-2 text-xs" style={{ color: 'var(--setima-muted)' }}>
          {ajuda}
        </p>
      )}
    </div>
  );
}
