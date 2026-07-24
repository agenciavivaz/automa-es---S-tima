import { createClient, type SupabaseClient } from '@supabase/supabase-js';
import { BENCHMARKS_FALLBACK, mergeBenchmarks, type LinhaBenchmark } from './benchmarks';
import type { Benchmarks } from './types';

/**
 * Acesso ao Supabase.
 *
 * - `benchmarks` é público (anon, somente leitura via RLS).
 * - `calculos`, `leads` e `eventos` só são gravados pelo service role, dentro
 *   dos route handlers. A chave de service role nunca chega ao client.
 *
 * Sem env configurada a aplicação continua funcionando: benchmarks caem no
 * fallback local e as gravações viram no-op (útil em dev e em preview).
 */

const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const serviceKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

export const supabaseConfigurado = Boolean(url && serviceKey);

export function getSupabaseAnon(): SupabaseClient | null {
  if (!url || !anonKey) return null;
  return createClient(url, anonKey, { auth: { persistSession: false } });
}

/** Client privilegiado — usar SOMENTE em route handlers / server components. */
export function getSupabaseAdmin(): SupabaseClient | null {
  if (!url || !serviceKey) return null;
  return createClient(url, serviceKey, { auth: { persistSession: false } });
}

let cache: { valor: Benchmarks; expiraEm: number } | null = null;
const TTL_MS = 5 * 60 * 1000;

/**
 * Carrega os benchmarks do Supabase com cache curto em memória.
 * Qualquer falha (env ausente, rede, tabela vazia) cai no fallback local —
 * a calculadora nunca deixa de responder por causa disso.
 */
export async function carregarBenchmarks(): Promise<Benchmarks> {
  if (cache && cache.expiraEm > Date.now()) return cache.valor;

  const client = getSupabaseAdmin() ?? getSupabaseAnon();
  if (!client) return BENCHMARKS_FALLBACK;

  try {
    const { data, error } = await client.from('benchmarks').select('setor, chave, valor');
    if (error || !data) return BENCHMARKS_FALLBACK;
    const valor = mergeBenchmarks(data as LinhaBenchmark[]);
    cache = { valor, expiraEm: Date.now() + TTL_MS };
    return valor;
  } catch {
    return BENCHMARKS_FALLBACK;
  }
}
