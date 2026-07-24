'use client';

import { BarrasComparativas } from './BarrasComparativas';
import {
  formatDias,
  formatMeses,
  formatMoeda,
  formatMoedaCompacta,
  formatNumero,
  formatPercent,
} from '@/lib/format';
import { CANAL_LABEL } from '@/lib/types';
import type { CalcInputs, CalcResultados } from '@/lib/types';
import type { Narrativa } from '@/lib/report';

export function Resultado({
  inputs,
  r,
  desbloqueado,
  narrativa,
  carregandoNarrativa,
}: {
  inputs: CalcInputs;
  r: CalcResultados;
  desbloqueado: boolean;
  narrativa: Narrativa | null;
  carregandoNarrativa?: boolean;
}) {
  const economiaPositiva = r.economiaAnualRecorrente > 0;

  return (
    <div>
      {/* O resultado é o título da tela — mesma hierarquia da LP. */}
      <p className="eyebrow mb-3">
        {economiaPositiva ? 'Sua economia anual estimada' : 'Diferença anual estimada'}
      </p>
      <p className="numero-dominante mb-4" style={!economiaPositiva ? { color: 'var(--setima-negativo)' } : undefined}>
        {formatMoedaCompacta(r.economiaAnualRecorrente)}
      </p>
      <p className="mb-10 max-w-2xl text-lg" style={{ color: 'var(--setima-muted)' }}>
        {economiaPositiva ? (
          <>
            É o que sua operação deixaria de gastar por ano, a partir do ano 2, trocando produção
            tradicional por digital twins — uma redução de {formatPercent(r.percentualEconomia)}{' '}
            sobre {formatMoeda(r.custoTradicional)} ao ano.
          </>
        ) : (
          <>
            Neste cenário o modelo NGI ainda não se paga: o volume de peças não dilui o
            investimento nos twins. Vale revisar o volume anual de desdobramentos.
          </>
        )}
      </p>

      <div className="mb-8 grid gap-6 md:grid-cols-2">
        <div className="card">
          <p className="eyebrow mb-5">Custo anual: tradicional × NGI</p>
          <BarrasComparativas
            tradicional={r.custoTradicional}
            ngi={r.custoNgiRecorrente}
          />
          <p className="text-xs" style={{ color: 'var(--setima-muted)' }}>
            No ano 1 o custo NGI é {formatMoeda(r.custoNgiAno1)}, porque inclui a criação dos
            digital twins ({formatMoeda(r.investimentoTwins)}).
          </p>
        </div>

        <div className="grid gap-6">
          <Metrica
            rotulo="Payback do digital twin"
            valor={formatMeses(r.paybackMeses)}
            nota="Tempo para o investimento nos twins se pagar com a economia recorrente."
          />
          <Metrica
            rotulo="Tempo de produção liberado"
            valor={formatDias(r.tempoEconomizadoDias)}
            nota={`${formatNumero(inputs.diarias)} diárias/ano em setup, logística e aprovação.`}
          />
        </div>
      </div>

      {/* Cards com gate: liberados só depois do e-mail. */}
      <div className="grid gap-6 md:grid-cols-2">
        <CardTravado titulo="Breakdown por canal" desbloqueado={desbloqueado}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: 'var(--setima-muted)' }}>
                <th className="pb-2 text-left font-normal">Canal</th>
                <th className="pb-2 text-right font-normal">Peças/ano</th>
                <th className="pb-2 text-right font-normal">Economia</th>
              </tr>
            </thead>
            <tbody>
              {r.breakdownPorCanal.map((b) => (
                <tr key={b.canal} style={{ borderTop: '1px solid var(--setima-border)' }}>
                  <td className="py-2">{CANAL_LABEL[b.canal]}</td>
                  <td className="py-2 text-right tabular-nums">{formatNumero(b.pecas)}</td>
                  <td className="py-2 text-right tabular-nums">{formatMoeda(b.economia)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardTravado>

        <CardTravado titulo="Projeção de 3 anos" desbloqueado={desbloqueado}>
          <table className="w-full text-sm">
            <thead>
              <tr style={{ color: 'var(--setima-muted)' }}>
                <th className="pb-2 text-left font-normal">Ano</th>
                <th className="pb-2 text-right font-normal">Custo NGI</th>
                <th className="pb-2 text-right font-normal">Acumulado</th>
              </tr>
            </thead>
            <tbody>
              {r.projecao3Anos.map((p) => (
                <tr key={p.ano} style={{ borderTop: '1px solid var(--setima-border)' }}>
                  <td className="py-2">Ano {p.ano}</td>
                  <td className="py-2 text-right tabular-nums">{formatMoeda(p.custoNgi)}</td>
                  <td className="py-2 text-right tabular-nums">
                    {formatMoeda(p.economiaAcumulada)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </CardTravado>

        <CardTravado
          titulo="Uplift de receita (estimativa)"
          desbloqueado={desbloqueado}
          className="md:col-span-2"
        >
          {r.upliftReceita === null ? (
            <p className="text-sm" style={{ color: 'var(--setima-muted)' }}>
              Informe ticket médio e volume de transações no passo 4 para ver esta estimativa.
            </p>
          ) : (
            <>
              <p className="font-display text-3xl" style={{ color: 'var(--setima-accent)' }}>
                {formatMoeda(r.upliftReceita)}
              </p>
              <p className="mt-3 text-sm" style={{ color: 'var(--setima-muted)' }}>
                Estimativa de receita adicional aplicando o benchmark de +9% em vendas com
                experiências 3D interativas sobre{' '}
                {formatMoeda(r.faturamentoDigitalConsiderado ?? 0)} de faturamento digital.{' '}
                <strong style={{ color: 'var(--setima-fg)' }}>
                  Este valor não está somado à economia acima
                </strong>{' '}
                — economia é cálculo, uplift é estimativa.
              </p>
            </>
          )}
        </CardTravado>
      </div>

      {desbloqueado && (
        <div className="card mt-6">
          <p className="eyebrow mb-4">Leitura estratégica</p>
          {carregandoNarrativa && !narrativa ? (
            <p style={{ color: 'var(--setima-muted)' }}>Gerando a análise do seu cenário…</p>
          ) : narrativa ? (
            <>
              <h3 className="display mb-4 text-2xl">{narrativa.titulo}</h3>
              {narrativa.paragrafos.map((p, i) => (
                <p key={i} className="mb-4 leading-relaxed" style={{ color: 'var(--setima-muted)' }}>
                  {p}
                </p>
              ))}
              <ul className="mt-6 grid gap-2">
                {narrativa.destaques.map((d, i) => (
                  <li key={i} className="text-sm font-semibold">
                    → {d}
                  </li>
                ))}
              </ul>
            </>
          ) : null}
        </div>
      )}

      <p className="mt-10 text-xs leading-relaxed" style={{ color: 'var(--setima-muted)' }}>
        Os resultados são estimativas baseadas em benchmarks de mercado e na base de projetos da
        Sétima. Não constituem proposta comercial nem orçamento. Os valores finais dependem da
        complexidade dos produtos, do volume real de peças e do escopo acordado.
      </p>
    </div>
  );
}

function Metrica({ rotulo, valor, nota }: { rotulo: string; valor: string; nota: string }) {
  return (
    <div className="card">
      <p className="eyebrow mb-3">{rotulo}</p>
      <p className="font-display text-4xl" style={{ color: 'var(--setima-accent)' }}>
        {valor}
      </p>
      <p className="mt-3 text-xs" style={{ color: 'var(--setima-muted)' }}>
        {nota}
      </p>
    </div>
  );
}

function CardTravado({
  titulo,
  desbloqueado,
  children,
  className = '',
}: {
  titulo: string;
  desbloqueado: boolean;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`card ${desbloqueado ? '' : 'bloqueado'} ${className}`}>
      <p className="eyebrow mb-4">{titulo}</p>
      <div className={desbloqueado ? '' : 'conteudo-bloqueado'} aria-hidden={!desbloqueado}>
        {children}
      </div>
      {!desbloqueado && (
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-sm font-semibold uppercase tracking-wider">
            Liberado no relatório completo
          </span>
        </div>
      )}
    </div>
  );
}
