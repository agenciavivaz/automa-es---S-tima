'use client';

import { useState } from 'react';

export interface DadosLead {
  nome: string;
  email: string;
  empresa: string;
  cargo: string;
  consentimento: boolean;
  /** Honeypot — preenchido só por bot. */
  website: string;
}

const POLITICA_URL =
  process.env.NEXT_PUBLIC_POLITICA_PRIVACIDADE_URL ??
  'https://setima.cc/PT/politica-de-privacidade';

export function GateEmail({
  onSubmit,
  enviando,
  erro,
}: {
  onSubmit: (dados: DadosLead) => void;
  enviando: boolean;
  erro?: string | null;
}) {
  const [dados, setDados] = useState<DadosLead>({
    nome: '',
    email: '',
    empresa: '',
    cargo: '',
    consentimento: false,
    website: '',
  });

  const emailValido = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(dados.email);
  const podeEnviar = dados.nome.trim().length > 1 && emailValido && dados.consentimento && !enviando;

  return (
    <form
      className="card"
      onSubmit={(e) => {
        e.preventDefault();
        if (podeEnviar) onSubmit(dados);
      }}
    >
      <p className="eyebrow mb-3">Relatório completo</p>
      <h2 className="display mb-3 text-3xl">Receba o detalhamento em PDF</h2>
      <p className="mb-8 text-sm" style={{ color: 'var(--setima-muted)' }}>
        Breakdown por canal, projeção de 3 anos, uplift de receita e a leitura estratégica do seu
        cenário — num PDF que você leva para a reunião de budget.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <Campo
          id="lead-nome"
          label="Nome"
          value={dados.nome}
          onChange={(v) => setDados({ ...dados, nome: v })}
          required
        />
        <Campo
          id="lead-email"
          label="E-mail corporativo"
          type="email"
          value={dados.email}
          onChange={(v) => setDados({ ...dados, email: v })}
          required
        />
        <Campo
          id="lead-empresa"
          label="Empresa"
          value={dados.empresa}
          onChange={(v) => setDados({ ...dados, empresa: v })}
        />
        <Campo
          id="lead-cargo"
          label="Cargo"
          value={dados.cargo}
          onChange={(v) => setDados({ ...dados, cargo: v })}
        />
      </div>

      {/* Honeypot: invisível para humanos, irresistível para bot. */}
      <div aria-hidden className="absolute h-0 w-0 overflow-hidden opacity-0">
        <label htmlFor="lead-website">Não preencha este campo</label>
        <input
          id="lead-website"
          type="text"
          tabIndex={-1}
          autoComplete="off"
          value={dados.website}
          onChange={(e) => setDados({ ...dados, website: e.target.value })}
        />
      </div>

      <label className="mt-6 flex items-start gap-3 text-xs" style={{ color: 'var(--setima-muted)' }}>
        <input
          type="checkbox"
          className="mt-0.5 h-4 w-4 shrink-0"
          checked={dados.consentimento}
          onChange={(e) => setDados({ ...dados, consentimento: e.target.checked })}
          required
        />
        <span>
          Autorizo a Sétima a usar meus dados para enviar este relatório e comunicações sobre a
          solução, conforme a{' '}
          <a href={POLITICA_URL} target="_blank" rel="noopener noreferrer" className="underline">
            política de privacidade
          </a>
          . Posso solicitar a exclusão a qualquer momento.
        </span>
      </label>

      {erro && (
        <p className="mt-4 text-sm" style={{ color: 'var(--setima-negativo)' }} role="alert">
          {erro}
        </p>
      )}

      <button type="submit" className="cta mt-8" disabled={!podeEnviar}>
        {enviando ? 'Liberando…' : 'Ver relatório completo'}
        <span aria-hidden>→</span>
      </button>
    </form>
  );
}

function Campo({
  id,
  label,
  value,
  onChange,
  type = 'text',
  required,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <div>
      <label htmlFor={id} className="mb-2 block text-sm font-semibold">
        {label}
        {required && <span aria-hidden> *</span>}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        required={required}
        autoComplete={type === 'email' ? 'email' : 'off'}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}
