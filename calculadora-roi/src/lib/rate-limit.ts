/**
 * Rate limit por IP nos route handlers (PRD seção 8.7).
 *
 * Implementação em memória: suficiente para MVP em uma instância, mas em
 * ambiente serverless cada instância tem seu próprio contador. Antes de
 * escalar campanha paga, trocar por Vercel KV ou Upstash mantendo esta
 * assinatura — nenhum route handler precisa mudar.
 */

interface Janela {
  contador: number;
  expiraEm: number;
}

const janelas = new Map<string, Janela>();

export interface ResultadoRateLimit {
  permitido: boolean;
  restante: number;
  resetEm: number;
}

export function checarRateLimit(
  chave: string,
  limite = 10,
  janelaMs = 60_000,
): ResultadoRateLimit {
  const agora = Date.now();
  const atual = janelas.get(chave);

  if (!atual || atual.expiraEm <= agora) {
    janelas.set(chave, { contador: 1, expiraEm: agora + janelaMs });
    return { permitido: true, restante: limite - 1, resetEm: agora + janelaMs };
  }

  atual.contador += 1;
  const restante = Math.max(0, limite - atual.contador);
  return { permitido: atual.contador <= limite, restante, resetEm: atual.expiraEm };
}

/** IP do request atrás do proxy da Vercel. */
export function ipDoRequest(req: Request): string {
  const forwarded = req.headers.get('x-forwarded-for');
  if (forwarded) return forwarded.split(',')[0].trim();
  return req.headers.get('x-real-ip') ?? 'desconhecido';
}

/**
 * Verificação de origem: rejeita POST vindo de outro site.
 * Em dev (sem host confiável configurado) aceita mesma origem do próprio request.
 */
export function origemValida(req: Request): boolean {
  const origin = req.headers.get('origin');
  if (!origin) return true; // navegação direta / curl em dev

  const permitidos = (process.env.ORIGENS_PERMITIDAS ?? '')
    .split(',')
    .map((o) => o.trim())
    .filter(Boolean);

  if (permitidos.length === 0) {
    try {
      return new URL(origin).host === new URL(req.url).host;
    } catch {
      return false;
    }
  }

  return permitidos.includes(origin);
}

/** Limpa janelas expiradas — evita crescimento indefinido em processo longo. */
export function limparJanelasExpiradas(): void {
  const agora = Date.now();
  for (const [chave, janela] of janelas) {
    if (janela.expiraEm <= agora) janelas.delete(chave);
  }
}
