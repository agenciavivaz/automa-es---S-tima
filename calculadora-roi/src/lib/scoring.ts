import type { Setor } from './types';

/** Lead scoring — PRD seção 8.3. */

export type Tier = 'A' | 'B' | 'C';
export type EmailTipo = 'corporativo' | 'gratuito';

const DOMINIOS_GRATUITOS = new Set([
  'gmail.com',
  'googlemail.com',
  'hotmail.com',
  'hotmail.com.br',
  'outlook.com',
  'outlook.com.br',
  'live.com',
  'msn.com',
  'yahoo.com',
  'yahoo.com.br',
  'ymail.com',
  'icloud.com',
  'me.com',
  'aol.com',
  'proton.me',
  'protonmail.com',
  'bol.com.br',
  'uol.com.br',
  'terra.com.br',
  'ig.com.br',
  'zipmail.com.br',
]);

const CARGOS_DECISORES = ['diretor', 'diretora', 'head', 'gerente', 'cmo', 'vp', 'c-level', 'cco'];

export function dominioDoEmail(email: string): string {
  return email.trim().toLowerCase().split('@')[1] ?? '';
}

export function classificarEmail(email: string): EmailTipo {
  const dominio = dominioDoEmail(email);
  if (!dominio) return 'gratuito';
  return DOMINIOS_GRATUITOS.has(dominio) ? 'gratuito' : 'corporativo';
}

export interface ScoringInput {
  skusAno: number;
  economiaCalculada: number;
  setor: Setor;
  email: string;
  cargo?: string | null;
  /** Passo 4 (receita) preenchido. */
  informouReceita: boolean;
}

export interface ScoringResult {
  score: number;
  tier: Tier;
  emailTipo: EmailTipo;
  /** Componentes da nota — útil para o time comercial entender o porquê. */
  detalhe: Array<{ criterio: string; pontos: number }>;
}

export function calcularScore(input: ScoringInput): ScoringResult {
  const detalhe: Array<{ criterio: string; pontos: number }> = [];
  const add = (criterio: string, pontos: number) => {
    if (pontos > 0) detalhe.push({ criterio, pontos });
  };

  if (input.skusAno >= 50) add('SKUs/ano ≥ 50', 30);
  else if (input.skusAno >= 20) add('SKUs/ano entre 20 e 49', 20);

  if (input.economiaCalculada >= 500_000) add('Economia ≥ R$ 500k', 25);
  else if (input.economiaCalculada >= 150_000) add('Economia entre R$ 150k e R$ 499k', 15);

  if (input.setor === 'automotivo' || input.setor === 'maquinas_agro') {
    add('Setor prioritário (automotivo / máquinas-agro)', 20);
  }

  const emailTipo = classificarEmail(input.email);
  if (emailTipo === 'corporativo') add('E-mail corporativo', 15);

  const cargo = (input.cargo ?? '').toLowerCase();
  if (cargo && CARGOS_DECISORES.some((c) => cargo.includes(c))) add('Cargo decisor', 10);

  if (input.informouReceita) add('Completou o passo de receita', 10);

  const score = detalhe.reduce((acc, d) => acc + d.pontos, 0);
  const tier: Tier = score >= 70 ? 'A' : score >= 40 ? 'B' : 'C';

  return { score, tier, emailTipo, detalhe };
}

/** Tier A vai para o time comercial; B entra em nutrição; C nunca toca o BDR. */
export function exigeToqueComercial(tier: Tier): boolean {
  return tier === 'A';
}
