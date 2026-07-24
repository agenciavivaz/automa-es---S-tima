'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CampoNumero, CampoSelect, CampoSlider } from './campos';
import { GateEmail, type DadosLead } from './GateEmail';
import { Resultado } from './Resultado';
import { calcular, defaultInputs, pecasPorCampanha } from '@/lib/calc';
import { formatMoedaCompacta, formatNumero } from '@/lib/format';
import { getSessionId, track, trackUmaVez } from '@/lib/tracking';
import { inputsToSearchParams } from '@/lib/url-state';
import {
  CANAIS,
  CANAL_LABEL,
  COMPLEXIDADES,
  COMPLEXIDADE_LABEL,
  SETORES,
  SETOR_LABEL,
} from '@/lib/types';
import type { Benchmarks, CalcInputs, Complexidade, Setor } from '@/lib/types';
import type { Narrativa } from '@/lib/report';

const TOTAL_PASSOS = 4;

export function Wizard({
  benchmarks,
  inputsIniciais,
  utm,
  shareIdInicial,
}: {
  benchmarks: Benchmarks;
  inputsIniciais: CalcInputs;
  utm: Record<string, string>;
  shareIdInicial?: string;
}) {
  const [inputs, setInputs] = useState<CalcInputs>(inputsIniciais);
  const [passo, setPasso] = useState(1);
  const [desbloqueado, setDesbloqueado] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [erroLead, setErroLead] = useState<string | null>(null);
  const [narrativa, setNarrativa] = useState<Narrativa | null>(null);
  const [carregandoNarrativa, setCarregandoNarrativa] = useState(false);
  const [shareId, setShareId] = useState<string | undefined>(shareIdInicial);
  const [linkCopiado, setLinkCopiado] = useState(false);
  const calculoIdRef = useRef<string | null>(null);

  // Cálculo em tempo real — puro, síncrono, sem I/O.
  const resultados = useMemo(() => calcular(inputs, benchmarks), [inputs, benchmarks]);

  // Estado persistido na URL: permite compartilhar o cenário.
  useEffect(() => {
    const params = inputsToSearchParams(inputs);
    for (const [chave, valor] of Object.entries(utm)) params.set(chave, valor);
    window.history.replaceState(null, '', `?${params.toString()}`);
  }, [inputs, utm]);

  const atualizar = useCallback(
    (patch: Partial<CalcInputs>) => {
      trackUmaVez('roi_calc_started', { setor: inputs.setor });
      setInputs((atual) => ({ ...atual, ...patch }));
    },
    [inputs.setor],
  );

  /** Trocar de setor recarrega os defaults do setor — o usuário só ajusta o que quiser. */
  const trocarSetor = useCallback(
    (setor: Setor) => {
      trackUmaVez('roi_calc_started', { setor });
      setInputs(defaultInputs(setor, benchmarks));
    },
    [benchmarks],
  );

  const irPara = useCallback(
    (novoPasso: number) => {
      if (novoPasso > passo) {
        track('roi_calc_step_completed', { step_number: passo, setor: inputs.setor });
      }
      setPasso(novoPasso);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    },
    [passo, inputs.setor],
  );

  // Ao chegar no resultado, registra o cálculo (sem lead) e dispara o evento.
  const noResultado = passo > TOTAL_PASSOS;
  useEffect(() => {
    if (!noResultado) return;
    track('roi_calc_result_viewed', {
      setor: inputs.setor,
      economia_anual: resultados.economiaAnualRecorrente,
    });

    let cancelado = false;
    (async () => {
      try {
        const res = await fetch('/api/calculo', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            sessionId: getSessionId(),
            inputs,
            shareId,
          }),
        });
        if (!res.ok || cancelado) return;
        const data = (await res.json()) as { id?: string; shareId?: string };
        if (data.id) calculoIdRef.current = data.id;
        if (data.shareId) setShareId(data.shareId);
      } catch {
        // Persistência é best-effort: nunca bloqueia o resultado na tela.
      }
    })();

    return () => {
      cancelado = true;
    };
    // Registra uma vez por entrada no resultado; ajustes de slider não repersistem.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noResultado]);

  const enviarLead = useCallback(
    async (dados: DadosLead) => {
      setEnviando(true);
      setErroLead(null);
      try {
        const res = await fetch('/api/lead', {
          method: 'POST',
          headers: { 'content-type': 'application/json' },
          body: JSON.stringify({
            ...dados,
            sessionId: getSessionId(),
            calculoId: calculoIdRef.current,
            shareId,
            inputs,
            utm,
          }),
        });

        if (!res.ok) {
          const corpo = (await res.json().catch(() => ({}))) as { erro?: string };
          throw new Error(corpo.erro ?? 'Não foi possível liberar o relatório agora.');
        }

        const data = (await res.json()) as { tier?: string; score?: number };
        setDesbloqueado(true);
        // Evento de MQL — otimizado nas campanhas de Meta Ads via sGTM/CAPI.
        track('roi_calc_lead_submitted', {
          setor: inputs.setor,
          economia_anual: resultados.economiaAnualRecorrente,
          tier: data.tier,
          score: data.score,
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
        void carregarNarrativa();
      } catch (e) {
        setErroLead(e instanceof Error ? e.message : 'Erro inesperado.');
      } finally {
        setEnviando(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [inputs, shareId, utm, resultados.economiaAnualRecorrente],
  );

  const carregarNarrativa = useCallback(async () => {
    setCarregandoNarrativa(true);
    try {
      const res = await fetch('/api/report', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ inputs }),
      });
      if (res.ok) setNarrativa((await res.json()) as Narrativa);
    } catch {
      // O relatório continua utilizável sem a narrativa.
    } finally {
      setCarregandoNarrativa(false);
    }
  }, [inputs]);

  const compartilhar = useCallback(async () => {
    const url = window.location.href;
    try {
      await navigator.clipboard.writeText(url);
      setLinkCopiado(true);
      setTimeout(() => setLinkCopiado(false), 2500);
    } catch {
      // Clipboard bloqueado: a URL já está na barra de endereços.
    }
    track('roi_calc_shared', { setor: inputs.setor });
  }, [inputs.setor]);

  if (noResultado) {
    return (
      <div>
        <Resultado
          inputs={inputs}
          r={resultados}
          desbloqueado={desbloqueado}
          narrativa={narrativa}
          carregandoNarrativa={carregandoNarrativa}
        />

        <div className="mt-10">
          {!desbloqueado ? (
            <GateEmail onSubmit={enviarLead} enviando={enviando} erro={erroLead} />
          ) : (
            <div className="card">
              <p className="eyebrow mb-4">Próximo passo</p>
              <div className="flex flex-wrap gap-4">
                <a
                  className="cta"
                  href={`/api/pdf?${inputsToSearchParams(inputs).toString()}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => track('roi_calc_pdf_downloaded', { setor: inputs.setor })}
                >
                  Baixar relatório em PDF <span aria-hidden>→</span>
                </a>
                <a
                  className="cta cta-secundario"
                  href={process.env.NEXT_PUBLIC_AGENDAMENTO_URL ?? 'https://setima.cc/PT#contato'}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={() => track('roi_calc_meeting_clicked', { setor: inputs.setor })}
                >
                  Agendar conversa <span aria-hidden>→</span>
                </a>
                <a
                  className="cta cta-secundario"
                  href="https://setima.cc/PT#cases"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Ver cases do meu setor <span aria-hidden>→</span>
                </a>
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <button type="button" className="cta cta-secundario" onClick={() => irPara(1)}>
            Ajustar meus números
          </button>
          <button type="button" className="cta cta-secundario" onClick={compartilhar}>
            {linkCopiado ? 'Link copiado' : 'Copiar link do cenário'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Progresso passo={passo} />

      <div className="grid gap-10 lg:grid-cols-[1fr_320px]">
        <div>
          {passo === 1 && <PassoContexto inputs={inputs} atualizar={atualizar} trocarSetor={trocarSetor} />}
          {passo === 2 && <PassoProducao inputs={inputs} atualizar={atualizar} />}
          {passo === 3 && <PassoPecas inputs={inputs} atualizar={atualizar} />}
          {passo === 4 && <PassoReceita inputs={inputs} atualizar={atualizar} />}

          <div className="mt-8 flex flex-wrap items-center gap-4">
            {passo > 1 && (
              <button type="button" className="cta cta-secundario" onClick={() => irPara(passo - 1)}>
                Voltar
              </button>
            )}
            <button type="button" className="cta" onClick={() => irPara(passo + 1)}>
              {passo === TOTAL_PASSOS ? 'Ver minha economia' : 'Continuar'}{' '}
              <span aria-hidden>→</span>
            </button>
            {passo === TOTAL_PASSOS && (
              <button
                type="button"
                className="text-sm underline"
                style={{ color: 'var(--setima-muted)' }}
                onClick={() => irPara(passo + 1)}
              >
                Pular este passo
              </button>
            )}
          </div>
        </div>

        {/* Prévia em tempo real: o número atualiza a cada ajuste. */}
        <aside className="card h-fit lg:sticky lg:top-8">
          <p className="eyebrow mb-3">Economia anual estimada</p>
          <p
            className="font-display text-4xl"
            style={{
              color:
                resultados.economiaAnualRecorrente >= 0
                  ? 'var(--setima-accent)'
                  : 'var(--setima-negativo)',
            }}
          >
            {formatMoedaCompacta(resultados.economiaAnualRecorrente)}
          </p>
          <dl className="mt-6 grid gap-3 text-sm">
            <Linha rotulo="Peças por ano" valor={formatNumero(resultados.pecasTotal)} />
            <Linha rotulo="Variações/ano" valor={formatNumero(resultados.variacoesTotal)} />
            <Linha
              rotulo="Custo tradicional"
              valor={formatMoedaCompacta(resultados.custoTradicional)}
            />
            <Linha rotulo="Custo NGI (ano 2+)" valor={formatMoedaCompacta(resultados.custoNgiRecorrente)} />
          </dl>
          <p className="mt-6 text-xs" style={{ color: 'var(--setima-muted)' }}>
            Estimativa baseada em benchmarks. Não é proposta comercial.
          </p>
        </aside>
      </div>
    </div>
  );
}

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <dt style={{ color: 'var(--setima-muted)' }}>{rotulo}</dt>
      <dd className="tabular-nums font-semibold">{valor}</dd>
    </div>
  );
}

function Progresso({ passo }: { passo: number }) {
  return (
    <div className="mb-10">
      <p className="eyebrow mb-3">
        Passo {passo} de {TOTAL_PASSOS}
      </p>
      <div className="flex gap-2" role="progressbar" aria-valuenow={passo} aria-valuemin={1} aria-valuemax={TOTAL_PASSOS}>
        {Array.from({ length: TOTAL_PASSOS }, (_, i) => (
          <span
            key={i}
            className="h-1 flex-1 rounded-sm"
            style={{
              background: i < passo ? 'var(--setima-accent)' : 'var(--setima-border)',
            }}
          />
        ))}
      </div>
    </div>
  );
}

type PassoProps = {
  inputs: CalcInputs;
  atualizar: (patch: Partial<CalcInputs>) => void;
};

function PassoContexto({
  inputs,
  atualizar,
  trocarSetor,
}: PassoProps & { trocarSetor: (s: Setor) => void }) {
  return (
    <section>
      <h2 className="display mb-2 text-3xl">Contexto</h2>
      <p className="mb-8 text-sm" style={{ color: 'var(--setima-muted)' }}>
        Tudo já vem preenchido com a média do seu setor. Ajuste só o que quiser.
      </p>
      <CampoSelect
        id="setor"
        label="Setor"
        valor={inputs.setor}
        opcoes={SETORES.map((s) => ({ valor: s, rotulo: SETOR_LABEL[s] }))}
        onChange={trocarSetor}
        ajuda="Trocar de setor recarrega os valores médios de referência."
      />
      <CampoSlider
        id="skus"
        label="SKUs que recebem produção de conteúdo por ano"
        valor={inputs.skus}
        min={1}
        max={500}
        onChange={(skus) => atualizar({ skus, skusDigitalizados: Math.min(skus, inputs.skusDigitalizados) })}
      />
      <CampoSlider
        id="campanhas"
        label="Campanhas ou lançamentos por ano"
        valor={inputs.campanhas}
        min={1}
        max={24}
        onChange={(campanhas) => atualizar({ campanhas })}
      />
    </section>
  );
}

function PassoProducao({ inputs, atualizar }: PassoProps) {
  return (
    <section>
      <h2 className="display mb-2 text-3xl">Produção atual</h2>
      <p className="mb-8 text-sm" style={{ color: 'var(--setima-muted)' }}>
        Como o conteúdo é produzido hoje: ensaio fotográfico, filmagem e refação.
      </p>
      <CampoSlider
        id="diarias"
        label="Diárias de produção por ano"
        valor={inputs.diarias}
        min={0}
        max={120}
        onChange={(diarias) => atualizar({ diarias })}
        ajuda="Ensaio fotográfico e filmagem somados."
      />
      <CampoSlider
        id="custo-diaria"
        label="Custo médio por diária"
        valor={inputs.custoDiaria}
        min={0}
        max={150000}
        step={1000}
        formato="moeda"
        onChange={(custoDiaria) => atualizar({ custoDiaria })}
        ajuda="Equipe, estúdio ou locação, equipamento e logística."
      />
      <CampoSlider
        id="variacoes"
        label="Variações por produto (cores, versões, acabamentos)"
        valor={inputs.variacoesPorSku}
        min={0}
        max={30}
        onChange={(variacoesPorSku) => atualizar({ variacoesPorSku })}
      />
      <CampoSlider
        id="mercados"
        label="Mercados ou idiomas que exigem adaptação"
        valor={inputs.mercados}
        min={1}
        max={20}
        onChange={(mercados) => atualizar({ mercados })}
        ajuda="Contando o mercado de origem."
      />
      <CampoSelect
        id="complexidade"
        label="Complexidade do produto para o digital twin"
        valor={inputs.complexidadeTwin}
        opcoes={COMPLEXIDADES.map((c) => ({ valor: c, rotulo: COMPLEXIDADE_LABEL[c] }))}
        onChange={(complexidadeTwin: Complexidade) => atualizar({ complexidadeTwin })}
      />
      <CampoSlider
        id="skus-digitalizados"
        label="SKUs que entrariam no digital twin"
        valor={inputs.skusDigitalizados}
        min={0}
        max={Math.max(1, inputs.skus)}
        onChange={(skusDigitalizados) => atualizar({ skusDigitalizados })}
        ajuda="Dá para começar por uma parte do catálogo."
      />
    </section>
  );
}

function PassoPecas({ inputs, atualizar }: PassoProps) {
  const total = pecasPorCampanha(inputs.pecas);
  return (
    <section>
      <h2 className="display mb-2 text-3xl">Volume de peças</h2>
      <p className="mb-8 text-sm" style={{ color: 'var(--setima-muted)' }}>
        Quantas peças cada campanha gera por canal. Hoje: {formatNumero(total)} peças por campanha,{' '}
        {formatNumero(total * inputs.campanhas)} por ano.
      </p>
      {CANAIS.map((canal) => (
        <CampoSlider
          key={canal}
          id={`pecas-${canal}`}
          label={`${CANAL_LABEL[canal]} — peças por campanha`}
          valor={inputs.pecas[canal]}
          min={0}
          max={200}
          onChange={(v) => atualizar({ pecas: { ...inputs.pecas, [canal]: v } })}
        />
      ))}
    </section>
  );
}

function PassoReceita({ inputs, atualizar }: PassoProps) {
  return (
    <section>
      <h2 className="display mb-2 text-3xl">Receita (opcional)</h2>
      <p className="mb-8 text-sm" style={{ color: 'var(--setima-muted)' }}>
        Só para estimar o impacto em vendas. Este bloco aparece separado e nunca é somado à
        economia de custo. Pode pular.
      </p>
      <CampoNumero
        id="ticket"
        label="Ticket médio (R$)"
        valor={inputs.ticketMedio}
        onChange={(ticketMedio) => atualizar({ ticketMedio })}
        placeholder="Ex.: 250"
      />
      <CampoNumero
        id="transacoes"
        label="Transações por ano"
        valor={inputs.transacoesAno}
        onChange={(transacoesAno) => atualizar({ transacoesAno })}
        placeholder="Ex.: 40000"
      />
      <CampoNumero
        id="faturamento"
        label="Ou: faturamento anual do canal digital (R$)"
        valor={inputs.faturamentoDigital}
        onChange={(faturamentoDigital) => atualizar({ faturamentoDigital })}
        ajuda="Se preenchido, usamos este valor no lugar de ticket × transações."
        placeholder="Ex.: 10000000"
      />
    </section>
  );
}
