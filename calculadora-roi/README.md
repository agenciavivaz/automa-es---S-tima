# Calculadora de ROI NGI — Sétima (`ngi-roi`)

Ferramenta PLG gratuita e self-serve que transforma "economizamos milhões dos
nossos clientes" em **"você economizaria R$ X por ano"**, capturando e
qualificando leads por budget. Implementa a **Fase 1 (MVP)** do PRD, com as
peças da Fase 2 e 3 já estruturadas (narrativa por IA, relatório, scoring,
cenário compartilhável).

Stack: Next.js 15 (App Router) + TypeScript + Tailwind v4 + Supabase, deploy na
Vercel — o mesmo ecossistema que a Sétima já roda.

---

## ⚠️ Pendência bloqueante antes do launch

Os benchmarks de custo em `src/lib/benchmarks.ts` e em `supabase/schema.sql`
são **placeholders**. A ferramenta **não deve ir ao ar** com eles:

1. Coletar os custos reais com o time da Sétima.
2. Backtestar o modelo contra 2-3 projetos já entregues.
3. Definir a régua de complexidade do digital twin (simples / médio / complexo).
4. Carregar os valores finais na tabela `benchmarks` do Supabase — a partir daí
   são editáveis sem deploy, e o arquivo local vira só fallback.

Idem para os tokens de marca em `src/app/tokens.css`: as cores e a tipografia
são placeholders derivados do registro visual da LP (o CSS do site está
minificado). Trocar por manual de marca ou `getComputedStyle` do site.

---

## Rodando local

```bash
npm install
cp .env.example .env.local   # funciona mesmo sem preencher nada
npm run test                 # 57 testes do motor de cálculo e do scoring
npm run dev                  # http://localhost:3000
```

Sem Supabase configurado a calculadora funciona normalmente: benchmarks caem no
fallback local e a persistência vira no-op. Sem `ANTHROPIC_API_KEY`, o relatório
usa o texto estático por setor.

---

## Estrutura

```
src/lib/calc.ts          Motor de cálculo — puro, determinístico, sem I/O
src/lib/benchmarks.ts    Defaults locais + merge com a tabela do Supabase
src/lib/scoring.ts       Lead scoring (Tier A/B/C)
src/lib/report.ts        Narrativa via Claude API + fallback estático por setor
src/lib/url-state.ts     Cenário na URL (compartilhável)
src/lib/tracking.ts      Eventos para o GTM/sGTM
src/lib/rate-limit.ts    Rate limit por IP + verificação de origem
src/lib/__tests__/       Vitest cobrindo todas as fórmulas da seção 5.2 do PRD

src/app/page.tsx                   Landing (hero + prova social + CTA)
src/app/calculadora/page.tsx       Wizard de 4 passos + resultado
src/app/calculadora/[shareId]/     Cenário salvo/compartilhado
src/app/api/calculo                Persistência do cálculo (com ou sem lead)
src/app/api/lead                   Gate: valida, pontua, grava, alerta Tier A
src/app/api/report                 Narrativa personalizada
src/app/api/pdf                    Relatório com a marca (HTML → PDF)
src/app/tokens.css                 TODOS os tokens de marca, em um lugar só

supabase/schema.sql      Tabelas, índices, RLS, seed de benchmarks, rota LGPD
```

---

## Modelo de cálculo

Implementa a seção 5.2 do PRD, com 57 testes unitários (`npm run test`):

```
CUSTO_TRAD  = diarias × custo_diaria
            + (skus × variacoes_por_sku) × custo_reshoot_variacao
            + mercados_extras × custo_adaptacao_mercado
            + pecas_total × custo_pos_producao_peca

CUSTO_NGI_A1 = skus_digitalizados × custo_twin_por_sku
             + pecas_total × custo_desdobramento_peca

CUSTO_NGI_AN = pecas_total × custo_desdobramento_peca
             + skus_digitalizados × custo_manutencao_twin

ECONOMIA_A1        = CUSTO_TRAD − CUSTO_NGI_A1
ECONOMIA_ANUAL_A2+ = CUSTO_TRAD − CUSTO_NGI_AN
ECONOMIA_3_ANOS    = ECONOMIA_A1 + 2 × ECONOMIA_ANUAL_A2+
PAYBACK_MESES      = investimento_twins / (ECONOMIA_ANUAL_A2+ / 12)
TEMPO_ECONOMIZADO  = diarias × fator_dias_por_diaria
```

Regras que os testes travam:

- **Uplift de receita nunca entra no número principal.** Economia é cálculo,
  uplift é estimativa — há um teste garantindo que informar faturamento não
  altera nenhuma das economias.
- **A soma do breakdown por canal reconcilia com o custo anual total.**
- **Nenhum input produz `NaN`** (zeros, negativos, texto vindo da URL).
- **Payback é `null`** quando não há economia recorrente positiva — nada de
  dividir por zero e exibir "Infinity meses".
- Economia negativa é exibida como é, sem maquiagem.

---

## Lead scoring (PRD 8.3)

```
+30 SKUs/ano ≥ 50            +20 SKUs/ano 20-49
+25 economia ≥ R$ 500k       +15 economia R$ 150k-499k
+20 setor automotivo/agro    +15 e-mail corporativo
+10 cargo decisor            +10 completou o passo de receita

Tier A ≥ 70  → alerta imediato no Slack (+ tarefa no CRM, Fase 2)
Tier B 40-69 → nutrição por e-mail
Tier C < 40  → nutrição, sem toque comercial
```

O `score` vem com `detalhe` — o BDR vê *por que* o lead pontuou.

---

## Eventos (GTM `GTM-TSGKH6D2`)

`roi_calc_started`, `roi_calc_step_completed` (com `step_number`),
`roi_calc_result_viewed`, `roi_calc_lead_submitted` (**evento de MQL**),
`roi_calc_pdf_downloaded`, `roi_calc_meeting_clicked`, `roi_calc_shared`.

`roi_calc_lead_submitted` é o evento a otimizar no Meta Ads, com deduplicação
via CAPI pelo sGTM já implantado. Os mesmos eventos são gravados na tabela
`eventos` para análise de drop-off por passo.

---

## Segurança e LGPD

- Rate limit por IP em todos os route handlers (`src/lib/rate-limit.ts`).
  Em memória — trocar por Vercel KV/Upstash antes de escalar mídia paga; a
  assinatura já está pronta para isso.
- Honeypot + verificação de origem no formulário do gate.
- Service role do Supabase e chave da Claude API só server-side.
- Checkbox de consentimento explícito com link para a política de privacidade.
- `excluir_dados_do_lead(email)` no Supabase para pedidos de exclusão.
- Disclaimer visível na tela e no PDF: estimativa, não proposta comercial.

---

## O que falta (Fases 2 e 3)

- [ ] PDF binário via `@react-pdf/renderer` + Supabase Storage + envio (Resend)
      — hoje a rota `/api/pdf` entrega HTML pronto para "Salvar como PDF"
- [ ] Integração com o CRM (Pipedrive) e tarefa automática para Tier A
- [ ] Meta CAPI via sGTM (evento já disparado, falta o mapeamento no sGTM)
- [ ] Versão EN
- [ ] Variações de copy e cases por setor para a cadência ABM
- [ ] Widget embutível para apresentações comerciais ao vivo

## Perguntas em aberto do PRD que afetam o código

1. **Payback em meses fica exposto?** Está exibido; esconder é remover um card
   em `src/components/Resultado.tsx`.
2. **Subdomínio ou rota?** O código assume rota (`/calculadora`). Para
   `roi.setima.cc`, nada muda; para servir sob outro path, há um `basePath`
   comentado em `next.config.ts`.
3. **CRM de destino** — a gravação do lead já isola o ponto de integração no
   route handler `/api/lead`.
