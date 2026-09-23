# Cadência ABM guiada por score — equipe ABM Sétima (Odoo)

Diagnóstico do acesso via API e proposta de cadência para a equipe **ABM Setima
(`crm.team` 20)**. Levantamento feito em 2026-09-23 direto na base
`grupo-setima` (Odoo 19.0 Enterprise). **Nada foi criado em produção ainda.**
Os únicos registros criados foram 5 registros de teste, apagados em seguida.

---

## 1. O que a API consegue fazer

A chave em `ODOO_API_KEY` pertence ao usuário `contato@vivazagencia.com.br`
(id 22) e tem **direitos de administrador**. Testei criar e apagar de verdade
um registro de cada tipo abaixo, e todos funcionaram.

| Recurso no Odoo | Modelo | Ler | Criar/editar | Para que serve na cadência |
|---|---|:-:|:-:|---|
| Contas/oportunidades | `crm.lead` | ✅ | ✅ | conta ABM, estágio, score da conta |
| Contatos (comitê de compra) | `res.partner` | ✅ | ✅ | papel, senioridade, score do contato |
| Estágios do funil | `crm.stage` | ✅ | ✅ | ABM · Conta-alvo … Ganho |
| Tipos de atividade | `mail.activity.type` | ✅ | ✅ | LinkedIn, e-mail, ligação, WhatsApp… com **encadeamento** |
| Planos de atividade | `mail.activity.plan` | ✅ | ✅ | a cadência "Dia 1, Dia 3…" como sequência |
| Atividades (tarefas) | `mail.activity` | ✅ | ✅ | tarefa na agenda do vendedor |
| Regras de automação | `base.automation` | ✅ | ✅ | gatilhos: mudança de estágio, campo, data, e-mail recebido |
| Ações de servidor (Python) | `ir.actions.server` | ✅ | ✅ | cálculo de score, criar tarefas por contato |
| Campos customizados | `ir.model.fields` | ✅ | ✅ | campos `x_abm_*` |
| Modelos de e-mail | `mail.template` | ✅ | ✅ | e-mails da cadência com variáveis |
| Telas (views/Studio) | `ir.ui.view` | ✅ | ✅ | colunas novas na lista do comitê |
| Tarefas agendadas | `ir.cron` | ✅ | ✅ | recálculo diário / decaimento do score |
| Templates de WhatsApp | `whatsapp.template` | ✅ | ❌ | só leitura (aprovação da Meta é pela tela) |
| Social Marketing | `social.account` | ❌ | ❌ | sem acesso |
| Lead scoring nativo | `crm.lead.scoring.frequency` | ✅ | ❌ | calculado pelo Odoo, não dá para editar |

Módulos instalados que importam: CRM, Automation Rules, Studio, Email Marketing
(+ `mass_mailing_crm`), WhatsApp, SMS, Calendar, Appointments, Surveys, Link
Tracker, Social LinkedIn, **AI** (`ai_crm`, `ai_server_actions`, `ai_fields`).
**Marketing Automation não está instalado.** Por isso a cadência é feita com
planos de atividade + regras de automação, que é o mecanismo nativo do CRM.

### O que dá para automatizar e o que continua manual

- **Automatizável no Odoo:** criar as tarefas da cadência com prazo, dono e
  roteiro; encadear a tarefa seguinte quando a anterior é concluída; calcular
  o score de contato e de conta; mover a conta de estágio pelo score; mandar
  e-mail por template (se vocês quiserem que o 1º e-mail saia sozinho);
  detectar e-mail recebido de um contato da conta e subir o score;
  alertar o vendedor; devolver conta fria para nutrição e reativar depois de X
  dias.
- **Manual (o vendedor executa):** tudo que acontece dentro do LinkedIn
  (conectar, comentar, mandar mensagem). O LinkedIn não tem API para isso e
  proíbe automação de perfil pessoal. O Odoo cria a tarefa com link do perfil
  (`x_linkedin_url`) e roteiro, e o vendedor executa e registra o resultado.
  Ligações também são manuais, porque não há VoIP instalado.

### Problema encontrado e corrigido

`ODOO_URL` está configurada como `https://grupo-setima.odoo.com/odoo`. Com o
sufixo `/odoo`, toda chamada JSON-2 volta `400 Session expired`, e a camada
`odoo/` não funcionava. O cliente agora remove esse sufixo (`odoo/client.py`,
com teste).

---

## 2. Situação atual da equipe ABM Setima

- **28 contas**, todas em `ABM · Conta-alvo` (estágio 80) e todas com o
  vendedor Diego Rodrigues (user 22).
- Estágios compartilhados com ABM BrandSpot (team 22): Conta-alvo (80) →
  Engajando (81) → MQL (82) → SQL (83) → Oportunidade (84) → Proposta (85) →
  Ganho (86).
- **1.115 contatos** vinculados às empresas das contas (~40 por conta, 917 com
  e-mail). Eles aparecem no formulário pelo campo Studio `x_studio_comite`
  (`partner_id.child_ids`), que é a lista da tela do print.
- Campos ABM que já existem no contato (`res.partner`):
  `x_abm_papel`, `x_abm_senioridade`, `x_abm_area`, `x_abm_score` (todos com
  score 0) e `x_abm_notas`. Também já existem `x_linkedin` e `x_linkedin_url`.
- Distribuição do comitê: Decisor 46 · Influenciador-chave 18 · Influenciador
  280 · Usuário/Técnico 25 · Ponto de entrada 364 · **sem papel 382**.
- Nenhum tipo de atividade, plano ou automação de ABM existe ainda. A única
  automação de CRM é "Alterar vendedor - Amanda" (team 16).
- O lead scoring nativo do Odoo (`automated_probability`) está em 0% nessas
  contas. Ele aprende com o histórico de ganhos e perdas por país, origem e
  tags, e não serve para ABM. O score precisa ser **nosso**.

---

## 3. O que a pesquisa diz (base do desenho)

1. **Trate a conta, não o lead.** A qualificação ABM é por conta: um MQA
   (Marketing Qualified Account) junta **fit + intenção + engajamento**
   somados entre todos os contatos da conta
   ([Demandbase](https://www.demandbase.com/blog/account-scoring/),
   [Only B2B](https://www.only-b2b.com/blog/marketing-qualified-account-mqa/)).
   Referência de saúde: 60–80% dos MQAs aceitos por vendas.
2. **O comitê é grande.** A Gartner fala em 5 a 16 pessoas de até 4 áreas, e
   ~11 em enterprise. Em 74% dos comitês há conflito interno, e conteúdo que
   ajuda o *grupo* a chegar em consenso rende mais do que conteúdo pensado só
   para um indivíduo
   ([Gartner](https://www.gartner.com/en/newsroom/press-releases/2025-05-07-gartner-sales-survey-finds-74-percent-of-b2b-buyer-teams-demonstrate-unhealthy-conflict-during-the-decision-process)).
3. **Multi-threading ganha.** Negócios ganhos têm cerca de 2× mais contatos
   envolvidos do que os perdidos
   ([Gong](https://www.gong.io/resources/guides/the-data-backed-guide-to-multi-threading-and-team-selling)).
   A cadência abre várias frentes em paralelo, não uma pessoa por vez.
4. **Multicanal, 8 a 12 toques.** Com 3 ou mais canais a resposta chega a 3×
   a do e-mail puro. LinkedIn funciona antes e entre os e-mails, como
   credibilidade, e a ligação é o canal que mais marca reunião. Depois de ~12
   toques o retorno cai
   ([Apollo](https://www.apollo.io/insights/whats-the-ideal-cadence-for-a-multi-channel-outbound-sequence),
   [Outreach](https://www.outreach.ai/resources/blog/timeless-tips-for-sales-sequences),
   [Ploomes](https://blog.ploomes.com/prospeccao-multicanal/)).
5. **Tiers definem a intensidade.** 1:1 para 10–40 contas estratégicas, com
   material sob medida; 1:few para clusters de 5–15 contas parecidas; 1:many
   para as demais, em escala
   ([ITSMA via Only B2B](https://www.only-b2b.com/blog/abm-tiers/)).
   Com 28 contas, a Sétima cabe em Tier 1 + Tier 2.
6. **95% não está comprando agora.** Só ~5% das contas estão no mercado num
   trimestre
   ([LinkedIn B2B Institute / Ehrenberg-Bass](https://business.linkedin.com/marketing-solutions/b2b-institute/b2b-research/trends/95-5-rule)).
   Conta que não reage não é descartada: vai para nutrição e volta a ser
   trabalhada depois.
7. **Estágios de compra por sinal.** Target → Awareness → Consideration →
   Decision → Purchase ([6sense](https://6sense.com/guides/account-prioritization/)).
   Esses estágios se encaixam nos 7 estágios ABM que vocês já têm no Odoo.

---

## 4. Modelo de score

### 4.1 Score do contato (`x_abm_score`, 0–100)

**Fit, até 40 pontos. Calculado sozinho a partir dos campos que já existem:**

| Papel na decisão | pts | Senioridade | pts |
|---|--:|---|--:|
| Decisor | 25 | C suite / VP / Owner | 15 |
| Influenciador-chave | 20 | Director / Head | 12 |
| Influenciador | 12 | Manager | 8 |
| Usuário/Técnico | 8 | Senior | 4 |
| Usuário/Ponto de entrada | 5 | Entry / Intern | 0 |

**Engajamento, até 60 pontos.** Vem de um campo novo
`x_abm_status` no contato, que o vendedor atualiza direto na lista do comitê.
Parte dos status também é atualizada por automação:

| Status do contato | pts | Como é atualizado |
|---|--:|---|
| Não iniciado | 0 | padrão |
| Em cadência | 0 | automático, quando a cadência começa |
| Conexão aceita (LinkedIn) | 10 | vendedor |
| Interagiu (curtiu/comentou/visitou) | 15 | vendedor |
| Respondeu | 30 | **automático** quando chega e-mail do contato; vendedor no LinkedIn/WhatsApp |
| Reunião agendada | 60 | vendedor, ou automático quando uma reunião com ele é criada no Calendar |
| Sem interesse / Contato errado | −20 / fica fora | vendedor |

**Decaimento:** −5 pontos de engajamento a cada 30 dias sem nenhum toque novo
(cron diário), para o score não ficar "velho".

### 4.2 Score da conta (`x_abm_score_conta` em `crm.lead`, 0–100)

```
score_conta = fit_conta (0–30)
            + média dos 5 maiores scores de contato × 0,5   (0–50)
            + cobertura do comitê (0–20):
                +10 se ≥ 3 contatos com engajamento > 0
                +10 se algum Decisor ou Influenciador-chave respondeu
```

`fit_conta` sai do campo novo `x_abm_tier`: Tier 1 = 30, Tier 2 = 20,
Tier 3 = 10. Depois pode entrar sinal de intenção (visita no site via
`website.visitor`, formulário, evento).

### 4.3 Score → estágio (automático)

| Estágio | Regra de entrada | O que dispara |
|---|---|---|
| ABM · Conta-alvo | conta cadastrada, comitê mapeado | plano "Preparar conta" |
| ABM · Engajando | cadência iniciada (vendedor move) | plano "Cadência 21 dias" + tarefas por contato |
| ABM · MQL | score_conta ≥ 50 **e** ≥ 2 contatos engajados | alerta + ligação para o decisor em 24h |
| ABM · SQL | reunião agendada com alguém do comitê | plano "Pré-reunião" |
| Oportunidade / Proposta / Ganho | manual (vendedor) | planos de avanço (fase 2) |
| Nutrição (retorno) | fim da cadência com score < 20 | tag `ABM·Nutrição` + reabre em 90 dias |

A automação **só sobe** de estágio. Descer continua sendo decisão do vendedor.

---

## 5. A cadência (Tier 1 e Tier 2)

**Ondas por papel.** A cadência não aborda os 40 contatos de uma vez:

- **Onda A, pontos de entrada e influenciadores-chave (3–5 pessoas):**
  abre conversa, busca informação e indicação.
- **Onda B, decisores (1–3 pessoas):** entra a partir do Dia 3, já citando o
  contexto da conta (e, depois, a conversa com a onda A).
- **Onda C, demais influenciadores:** só LinkedIn e conteúdo, para aquecer.

Uma ação de servidor escolhe os contatos de cada onda pelo score de fit e cria
**uma tarefa por contato**, com nome, cargo e link do LinkedIn no resumo.
Exemplo: `D1 · LinkedIn · Conectar — Ademar Brasil (Product Manager)`.

### 5.1 Plano "Preparar conta" (estágio Conta-alvo)

| Quando | Tipo | Tarefa |
|---|---|---|
| D0 | Pesquisa | Plano da conta: 3 gatilhos (notícias, vagas, resultados), 3 hipóteses de dor, cases do setor |
| D0 | Pesquisa | Revisar comitê: preencher papel dos contatos sem papel, marcar Tier, conferir LinkedIn |
| D1 | To-Do | Definir o ângulo da mensagem e mover para **Engajando** (isso dispara a cadência) |

### 5.2 Plano "Cadência 21 dias" (estágio Engajando)

| Dia | Canal | Onda | Ação |
|---|---|---|---|
| D1 | LinkedIn | A+B | Visitar o perfil e seguir a empresa. Pedido de conexão **sem pitch** (nota curta citando um gatilho da conta) |
| D2 | LinkedIn | B | Engajar num post do decisor ou da empresa (comentário com substância) |
| D3 | E-mail | A | E-mail 1: insight específico da conta + pergunta aberta (sem pedir reunião) |
| D4 | LinkedIn | A+B | Mensagem para quem aceitou: agradecer e compartilhar conteúdo relevante (sem pitch) |
| D5 | Ligação | A | Ligação 1. Se não atender, deixa recado e manda WhatsApp curto se tiver o número |
| D7 | E-mail | B | E-mail 2 para o decisor: case/benchmark do setor, **pedido de 20 min** |
| D9 | LinkedIn | C | Onda C: conexões e engajamento leve (aquecer o resto do comitê) |
| D10 | Ligação | B | Ligação 2 para o decisor (ou assistente) |
| D12 | E-mail | A+B | E-mail 3 multi-thread: "falei com X do time de Y sobre Z…". Tier 1: convite para evento ou conteúdo exclusivo |
| D14 | Presente/Direct | B | **Só Tier 1:** algo físico ou personalizado (mini-estudo da marca, vídeo gravado para eles) |
| D17 | Ligação | A+B | Ligação 3 + LinkedIn voice/texto |
| D21 | E-mail | A+B | E-mail de encerramento ("fecho o assunto por aqui?") + **checkpoint de score** |

São 10 a 12 toques por pessoa-chave em 3 canais, dentro da faixa que a
pesquisa recomenda. Tier 2 usa o mesmo plano **sem** D2, D14 e o e-mail 3
personalizado, que passa a ser por cluster.

**D21 (checkpoint automático):**
- score_conta ≥ 50 → MQL (já teria subido antes, pela regra 4.3);
- 20–49 → nova rodada curta de 10 dias com a onda C e outro ângulo;
- < 20 → Nutrição: tag, remove as tarefas abertas, reabre em 90 dias.

### 5.3 Plano "MQL → reunião" (estágio MQL)

| Quando | Canal | Ação |
|---|---|---|
| D0 | Ligação | Ligar para o contato mais engajado em até 24h (tarefa urgente) |
| D1 | E-mail | Proposta de agenda com 2 horários + link do Appointments |
| D2 | LinkedIn | Mensagem ao decisor citando a conversa com o contato engajado |
| D4 | Ligação | Follow-up. Se marcar a reunião, mover para SQL |

### 5.4 Plano "Pré-reunião" (estágio SQL)

Checklist: confirmar participantes do comitê → preparar a pauta com as dores
levantadas → mandar agenda e material 24h antes → registrar o resultado e
mover para Oportunidade.

---

## 6. O que eu crio via API (pacote de implantação)

Tudo em modo **desativado** primeiro, com filtro obrigatório `team_id = 20`,
para vocês testarem numa conta (sugestão: Toyota do Brasil) antes de ligar.

1. **Campos novos:** `x_abm_status` (contato), `x_abm_tier`,
   `x_abm_score_conta`, `x_abm_ultimo_toque` e `x_abm_onda` (conta/contato).
2. **Tipos de atividade:** `ABM · LinkedIn conectar`, `ABM · LinkedIn
   engajar`, `ABM · LinkedIn mensagem`, `ABM · E-mail`, `ABM · Ligação`,
   `ABM · WhatsApp`, `ABM · Pesquisa de conta`, `ABM · Presente/Direct`.
   Cada um com ícone e roteiro padrão na nota.
3. **Planos de atividade (`crm.lead`):** Preparar conta, Cadência 21 dias
   (Tier 1), Cadência 21 dias (Tier 2), MQL → reunião, Pré-reunião.
4. **Modelos de e-mail** dos e-mails 1, 2, 3 e de encerramento, com
   variáveis (nome, empresa, cargo). O vendedor edita antes de enviar;
   nada sai sozinho, a menos que vocês peçam.
5. **Ações de servidor e automações:**
   - `ABM · Recalcular score`: quando muda papel/senioridade/status de um
     contato → recalcula o score do contato e o da conta;
   - `ABM · Iniciar cadência`: quando a conta entra em Engajando → cria as
     tarefas por contato e onda, e marca os contatos como "Em cadência";
   - `ABM · Resposta recebida`: e-mail recebido de contato da conta → status
     Respondeu + tarefa "Responder em até 4h";
   - `ABM · Promover por score`: score_conta ≥ 50 com ≥ 2 engajados → MQL;
   - `ABM · Checkpoint D21` (por data): decide nova rodada ou nutrição;
   - `ABM · Reativar nutrição` (por data, 90 dias) → volta para Conta-alvo;
   - cron diário de decaimento do score.
6. **Tela:** colunas `Papel`, `Senioridade`, `Status`, `Score` e
   `LinkedIn` na lista do comitê (`x_studio_comite`), editáveis ali mesmo, e
   ordenação por score.

Toda mudança fica registrada: o que eu criar leva o prefixo `ABM ·` no nome,
para localizar e desfazer fácil.

---

## 7. O que vocês precisam decidir antes de eu criar

1. **Tiers:** quais das 28 contas são Tier 1 (1:1) e quais Tier 2? Se não
   tiverem essa lista, sugiro Tier 1 = 8 a 10 contas de maior potencial.
2. **Canais:** usam WhatsApp na prospecção ABM? Existe envio de presente ou
   direct mail no Tier 1?
3. **E-mails:** prefere que o e-mail 1 saia automático por template ou que
   tudo fique como tarefa para o vendedor enviar?
4. **ABM BrandSpot (team 22):** os estágios são compartilhados. Aplico a
   mesma estrutura lá também ou só na Sétima?
5. **382 contatos sem papel:** classifico automaticamente pelo cargo
   (`function`) com regras de palavras-chave, ou vocês revisam antes?
6. **Pesos do score:** os números acima são ponto de partida. Revisar depois
   de 30 dias com dados reais.
