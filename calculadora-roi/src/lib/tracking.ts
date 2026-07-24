'use client';

/**
 * Eventos do funil — PRD seção 8.6.
 * Empurrados para o dataLayer do GTM já existente (GTM-TSGKH6D2), que
 * encaminha para o sGTM e faz a deduplicação com a Meta CAPI.
 */

export type EventoRoi =
  | 'roi_calc_started'
  | 'roi_calc_step_completed'
  | 'roi_calc_result_viewed'
  | 'roi_calc_lead_submitted'
  | 'roi_calc_pdf_downloaded'
  | 'roi_calc_meeting_clicked'
  | 'roi_calc_shared';

declare global {
  interface Window {
    dataLayer?: Array<Record<string, unknown>>;
  }
}

export function track(evento: EventoRoi, payload: Record<string, unknown> = {}): void {
  if (typeof window === 'undefined') return;
  window.dataLayer = window.dataLayer || [];
  window.dataLayer.push({ event: evento, ...payload });
}

/** Dispara o evento uma única vez por sessão de navegação. */
const jaDisparados = new Set<string>();
export function trackUmaVez(
  evento: EventoRoi,
  payload: Record<string, unknown> = {},
  chave = evento,
): void {
  if (jaDisparados.has(chave)) return;
  jaDisparados.add(chave);
  track(evento, payload);
}

/** Identificador anônimo de sessão, usado para amarrar cálculo → lead. */
export function getSessionId(): string {
  if (typeof window === 'undefined') return 'server';
  const CHAVE = 'ngi_roi_session_id';
  try {
    const existente = window.sessionStorage.getItem(CHAVE);
    if (existente) return existente;
    const novo = crypto.randomUUID();
    window.sessionStorage.setItem(CHAVE, novo);
    return novo;
  } catch {
    return 'anon';
  }
}
