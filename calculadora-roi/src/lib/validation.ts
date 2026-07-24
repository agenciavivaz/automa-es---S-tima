import { z } from 'zod';
import { COMPLEXIDADES, SETORES } from './types';

const numeroOpcional = z.coerce.number().finite().nonnegative().optional();

export const inputsSchema = z.object({
  setor: z.enum(SETORES),
  skus: z.coerce.number().finite().nonnegative().max(1_000_000),
  campanhas: z.coerce.number().finite().nonnegative().max(1_000),
  diarias: z.coerce.number().finite().nonnegative().max(10_000),
  custoDiaria: z.coerce.number().finite().nonnegative().max(100_000_000),
  variacoesPorSku: z.coerce.number().finite().nonnegative().max(1_000),
  mercados: z.coerce.number().finite().nonnegative().max(500),
  pecas: z.object({
    social: z.coerce.number().finite().nonnegative().max(100_000),
    ecommerce: z.coerce.number().finite().nonnegative().max(100_000),
    ooh: z.coerce.number().finite().nonnegative().max(100_000),
    video: z.coerce.number().finite().nonnegative().max(100_000),
    midiaPaga: z.coerce.number().finite().nonnegative().max(100_000),
  }),
  complexidadeTwin: z.enum(COMPLEXIDADES),
  skusDigitalizados: z.coerce.number().finite().nonnegative().max(1_000_000),
  ticketMedio: numeroOpcional,
  transacoesAno: numeroOpcional,
  faturamentoDigital: numeroOpcional,
});

export const calculoSchema = z.object({
  sessionId: z.string().min(1).max(100),
  inputs: inputsSchema,
  shareId: z.string().min(1).max(40).optional(),
});

export const leadSchema = z.object({
  nome: z.string().trim().min(2).max(120),
  email: z.string().trim().email().max(200),
  empresa: z.string().trim().max(160).optional().default(''),
  cargo: z.string().trim().max(160).optional().default(''),
  consentimento: z.literal(true),
  /** Honeypot: se veio preenchido, é bot. */
  website: z.string().max(200).optional().default(''),
  sessionId: z.string().min(1).max(100),
  calculoId: z.string().uuid().nullable().optional(),
  shareId: z.string().min(1).max(40).optional(),
  inputs: inputsSchema,
  utm: z.record(z.string().max(400)).optional().default({}),
});

export const reportSchema = z.object({
  inputs: inputsSchema,
});

export type LeadPayload = z.infer<typeof leadSchema>;
