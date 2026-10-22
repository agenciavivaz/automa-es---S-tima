# ABM Sétima — Estrutura da automação, jornada da conta e cadência (estado atual)

> **Para quem é este documento:** um agente de LLM que vai escrever os **textos padrão da
> cadência** (e-mails E1–E4 e mensagens de LinkedIn) com base na **trilha** e no **dossiê**
> de cada conta. Não é material para a BDR.
>
> **Fonte:** configuração lida diretamente do Odoo (`grupo-setima.odoo.com`) em **22/10/2026**:
> automações, ações de servidor, ação agendada, tipos de atividade, modelos de e-mail,
> campos e parâmetros do sistema. Nada aqui é desenho teórico: é o que está rodando.
> Onde o desenho e o que está ativo divergem, isso está sinalizado com ⚠️.

---

## 0. Resumo em 10 linhas

1. A equipe **ABM Setima** (`crm.team` 20) trabalha **contas-alvo** (montadoras e marcas de veículos/máquinas no Brasil), cada uma um `crm.lead`. Hoje: 61 contas, todas com a SDR **Amanda** (user 31); gestor **Diego** (user 22).
2. A oferta é a **Sétima NGI** (3D + IA + automação): digital twin do veículo, **configurador 3D web**, imagens/vídeos que substituem fotografia. Case principal: **configurador do VW Tera**.
3. A conta anda por 10 etapas: **Alvo → Aquecendo → Engajada → Em cadência → Conversa → Reunião agendada → Reunião realizada**, com saídas para **Nutrição**, **Descartada** e **Cliente – expansão**.
4. A temperatura vem de um **score de sinais** (anúncios, site, LinkedIn, e-mail, formulário) que expiram em 30 dias: **fria < 30, engajada 30–59, quente ≥ 60**.
5. Uma **fila diária** libera 4 contas/dia para preparação (comitê, LinkedIn, **definir trilha**). Sinal antecipa a liberação.
6. A **trilha** é a variável que escolhe o texto: **Sem configurador** ou **Configurador fraco**.
7. A **cadência fria** é só **e-mail + LinkedIn**, 18 dias úteis, até 3 pessoas do comitê: D1 conectar + E1, D3 interagir, D5 E2, D8 mensagem LinkedIn, D11 E3, D14 follow-up LinkedIn, D18 E4.
8. **Nenhum envio é automático.** O Odoo cria uma atividade por ponto de contato; a SDR envia usando o modelo indicado.
9. ⚠️ Os **8 modelos de e-mail estão em rascunho**, por isso a automação que gera a cadência (**A5**) está **desligada de propósito**. O que destrava a operação é exatamente o trabalho deste agente.
10. Ligação e WhatsApp só entram quando a conta fica **quente** ou chega **formulário**. Asset personalizado só vai para **decisor que aceitou conexão**.

---

## 1. Peças da estrutura

### 1.1 Etapas do pipeline (ABM Setima)

| ID | Etapa | Significado | Como a conta entra |
|---|---|---|---|
| 87 | **Alvo** | Conta na lista, aguardando a vez na fila | Manual (importação/cadastro) |
| 88 | **Aquecendo** | Preparação liberada; só exposição (anúncios LinkedIn) e interação leve | Fila diária ou sinal (A20) |
| 89 | **Engajada** | Hora de iniciar a cadência | Automática: score ≥ 30 (A2), 21 dias aquecendo (A3) ou 14 dias com exposição ≥ 4 (A17) |
| 90 | **Em cadência** | Cadência de e-mail + LinkedIn rodando | **Manual** (SDR move o card) → dispararia a A5 |
| 91 | **Conversa** | Houve resposta real / braço erguido | Manual ou automática (A2/A4 com formulário ou resposta positiva) |
| 92 | **Reunião agendada** | — | Manual |
| 93 | **Reunião realizada** | — | Manual |
| 94 | **Nutrição** | Cadência terminou sem resposta | Automática: 35 dias sem sinal em cadência (A9) |
| 95 | **Descartada** | — | Manual |
| 96 | **Cliente – expansão** | Clientes atuais (VW do Brasil, Hyundai, VW Caminhões) — fora da cadência fria | Manual |

### 1.2 Campos da conta (`crm.lead`) relevantes para os textos

| Campo | Rótulo | Valores / uso |
|---|---|---|
| `x_abm_trilha` | ABM · Trilha | `sem_config` (Sem configurador), `config_fraco` (Configurador fraco), `a_definir` |
| `x_abm_tier` | ABM · Tier | 1, 2, 3 (hoje quase todas são Tier 2) |
| `x_abm_score` / `x_abm_faixa` | Score / Faixa | soma dos sinais ativos; fria/engajada/quente |
| `x_abm_preparacao` | ABM · Preparação | `fila`, `liberada`, `pular` |
| `x_abm_cadencia_status` | ABM · Cadência | `nao_iniciada`, `ativa`, `pausada`, `concluida` |
| `x_abm_onda` | ABM · Onda | 1 ou 2 (2ª leva de contatos do comitê) |
| `x_abm_dossie_url` | ABM · Dossiê (URL) | ⚠️ **vazio nas 61 contas hoje** |
| `x_abm_asset_url` | Asset personalizado (URL) | preencher dispara envio ao decisor (A16) |
| `x_abm_link_email` | Link e-mail | `https://www.setima.cc/PT?utm_source=email&utm_medium=abm_1a1&utm_campaign=abm-setima-montadoras&utm_content=<conta>` |
| `x_abm_link_linkedin` | Link LinkedIn | idem com `utm_source=linkedin_dm` |
| `x_abm_link_whatsapp` | Link WhatsApp | idem com `utm_source=whatsapp` |
| `x_abm_exposicao` | Exposição | impressões de LinkedIn Ads por pessoa do comitê (30 dias) |
| `x_abm_estudio` | Estúdio interno | `tem_estudio`, `estudio_baixa`, `indefinido` (usado no ABM BrandSpot, não na Sétima) |

### 1.3 Campos do contato do comitê (`res.partner`, filho da empresa)

| Campo | Valores |
|---|---|
| `x_abm_papel` | Decisor, Influenciador-chave, Influenciador, Usuário/Técnico, Usuário/Ponto de entrada, Fora |
| `x_abm_prioridade` | 1 (decisor), 2 (influenciador), 3, 9 (excluído) |
| `x_abm_senioridade` | C suite, Vp, Owner, Head, Director, Manager, Senior, Entry, Intern |
| `x_abm_area` | Marketing, Compras, Produto, TI/Digital, Financeiro, Engenharia/Design, … |
| `x_abm_na_cadencia` | se a pessoa recebe a cadência |
| `x_abm_li_conexao` | Não enviado, Enviado, Aceito, Recusado/expirado |
| `x_email_status` | Verificado, Válido, Inválido, Indisponível, Extrapolado, catch-all |
| `x_abm_canal_inicial` | E-mail + LinkedIn, LinkedIn primeiro, E-mail arriscado → LinkedIn |
| `x_abm_optout` | opt-out cancela tudo da pessoa (A12) |

### 1.4 Sinais e score (`x_abm_sinal`)

Cada sinal vale pontos e **expira em 30 dias** (A13). Score = soma dos sinais ativos.

| Sinal | Pontos |
|---|---|
| Reagiu/comentou post do especialista | 15 |
| Conexão aceita no LinkedIn | 15 |
| Seguiu a página da Sétima | 10 |
| Visita ao site (Apollo) | 10 |
| Visitou cases, lead magnet ou contato | 15 |
| Resposta genuína sem interesse claro (dúvida, encaminhou, "agora não") | 30 |
| Ligação com conversa | 30 |
| **Formulário** (LP, Lead Gen, lead magnet) | **60** |
| **Braço erguido** (quer saber mais, pediu material, aceitou reunião) | **60** |
| Resposta automática / "recebido" / negativa / a classificar | 0 |
| LinkedIn Ads (relatório 30 dias) e "Outro" | variável |

Faixas: **fria < 30 · engajada 30–59 · quente ≥ 60**.

### 1.5 Parâmetros do sistema (`abm.*`)

| Chave | Valor | Uso |
|---|---|---|
| `abm.team_id` | 20 | equipe |
| `abm.sdr_user_id` | 31 (Amanda) | dona das atividades |
| `abm.gestor_user_id` | 22 (Diego) | recebe alertas e tarefas de asset |
| `abm.preparacao_contas_dia` | 4 | contas liberadas por dia útil |
| `abm.preparacao_limite_pendentes` | 10 | freio da fila |
| `abm.inicio` | 2026-10-05 | nenhuma tarefa nasce antes desta data |
| `abm.feriados` | lista 2026–2027 | prazos só em dias úteis |

### 1.6 Automações (estado em 22/10/2026)

| Código | Nome | Gatilho | O que faz | Ativa |
|---|---|---|---|---|
| — | Fila de preparação | Ação agendada, dia útil 07h | Libera até 4 contas de Alvo → Aquecendo + tarefas de preparação | ✅ |
| A1 | Entrou em Alvo | Etapa vira Alvo | Marca `preparacao = fila` | ✅ |
| A2 | Ficou engajada | Faixa vira engajada/quente em Alvo/Aquecendo/Nutrição | → Engajada (ou Conversa se formulário/braço erguido), libera preparação, cria **Iniciar cadência** | ✅ |
| A3 | 21 dias aquecendo | 21 dias em Aquecendo | → Engajada + **Iniciar cadência** | ✅ |
| A4 | Conta quente | Faixa vira quente | Formulário/braço erguido → Conversa + tarefa de resposta; senão **Ligação** (hoje) e **WhatsApp** (próximo dia útil) para quem está na cadência ou decisores | ✅ |
| **A5** | **Início da cadência** | Etapa vira Em cadência | Escolhe até 3 pessoas, marca cadência ativa, **cria as 8 atividades por pessoa** | ⚠️ **Desligada** (e-mails em rascunho) |
| A6 | Parar cadência | Etapa vira Conversa, Nutrição ou Descartada | Apaga atividades `[Cadência]` pendentes; status pausada/concluída | ✅ |
| A7 | Conversa | Etapa vira Conversa | Tarefa **Agendar reunião** | ✅ |
| A8 | Reunião agendada | Etapa vira Reunião agendada | Tarefa **Preparar reunião**; gestor segue a conta | ✅ |
| A9 | Cadência sem sinal | 35 dias sem sinal desde o início da cadência/último sinal | → Nutrição | ✅ |
| A10 | E-mail recebido | E-mail chega na conta | Classifica (automática/aceite/a classificar), cria sinal e tarefa | ✅ |
| A11 | Conexão aceita | Contato com conexão = Aceito | Sinal +15, tarefa **Mensagem pós-conexão**; se decisor, tarefa de **asset personalizado** para o gestor | ✅ |
| A12 | Opt-out | Contato marcado opt-out | Apaga todas as atividades da pessoa | ✅ |
| A13 | Sinal expira | 30 dias após o sinal | Desativa o sinal (sai do score) | ✅ |
| A14 | Onda 2 | 21 dias de cadência sem resposta | Coloca até 2 novos contatos (prioridade 2–3) na mesma cadência | ⚠️ **Desligada** |
| A15 | Formulário de conta-alvo | Lead de outra equipe com e-mail do domínio da conta | Tarefa **contato em até 1h útil** + sinal formulário (60) | ✅ |
| A16 | Asset pronto | Campo Asset preenchido | Tarefa **Enviar asset** por LinkedIn para decisores conectados | ✅ |
| A17 | 14 dias aquecendo com exposição | 14 dias em Aquecendo com exposição ≥ 4 | → Engajada + **Iniciar cadência** | ✅ |
| A18 | Exposição baixa aos 14 dias | 14 dias em Aquecendo com exposição < 2 | Alerta ao gestor (conferir lista do LinkedIn Ads) | ✅ |
| A19 | Engajada sem cadência | 7 dias em Engajada sem cadência | Alerta ao gestor | ✅ |
| A20 | Sinal em conta Alvo | Score > 0 com a conta em Alvo | Fura a fila: → Aquecendo + preparação | ✅ |

---

## 2. Passo a passo da jornada da conta

### Passo 1 — Alvo (na fila)
- A conta é cadastrada com domínio, tier e comitê (contatos importados do Apollo, já com papel e prioridade).
- A1 marca `Na fila`. A conta recebe **anúncios do LinkedIn Ads** sobre o comitê desde já.
- **Nenhum contato direto** acontece aqui.

### Passo 2 — Liberação para preparação (Alvo → Aquecendo)
Disparo, o que vier primeiro:
- **Fila diária** (07h, dia útil): ordena por **tier → score → força do comitê** (até 2 decisores × 3 pts + até 4 influenciadores × 1 pt) **→ nome** e libera as **4 primeiras**. **Freio:** se a SDR tem ≥ 10 atividades ABM vencidas/para hoje, nada é liberado.
- **A20:** qualquer sinal (score > 0) com a conta em Alvo libera na hora.
- **A2:** se a conta ficar engajada direto, é liberada e já vai para Engajada.

Tarefas criadas (todas no mesmo dia):
1. **Validar comitê** — só se o comitê não foi validado no Apollo ou não tem decisor.
2. **LinkedIn – Seguir/Interagir** — *"Seguir e reagir a 1 post relevante. Sem convite."*
3. **Definir trilha** — só se a trilha está vazia/a definir.

### Passo 3 — Aquecendo (preparação + exposição)
A SDR faz as tarefas de preparação. A **definição de trilha** segue esta instrução (texto literal do Odoo):

> Definir a trilha da conta (campo Trilha):
> - **Configurador:** o site da conta tem configurador de produto/veículo? Testar: qualidade visual, 3D ou só fotos, velocidade, mobile.
> - **3D na comunicação:** a marca usa 3D/CGI em lançamentos, site, redes e catálogos? Ou só foto/vídeo tradicional?
> - Escolher a trilha: **Configurador fraco** (existe, mas é pobre) ou **Sem configurador**.
> - Registrar na nota da conta os links e prints que justificam a escolha (**vão virar a primeira linha personalizada do E1**).

A conta sai de Aquecendo por:
- **Score ≥ 30** → Engajada (A2);
- **14 dias com exposição ≥ 4** impressões/pessoa do comitê → Engajada (A17);
- **21 dias** em Aquecendo → Engajada (A3);
- exposição < 2 aos 14 dias → só alerta o gestor (A18), a conta fica.

### Passo 4 — Engajada (decidir e iniciar a cadência)
Toda entrada em Engajada cria a tarefa **Iniciar cadência** para a SDR:

> Revisar a trilha (e dossiê/asset, se houver). Marcar "Na cadência" em até 3 pessoas e mover para Em cadência.
> **Atenção: enquanto os e-mails E1–E4 estiverem em rascunho a cadência automática fica desligada. Não mover para Em cadência até o aviso de que os e-mails estão prontos.**

Sem cadência em 7 dias → alerta ao gestor (A19).

### Passo 5 — Em cadência (A5 — quando estiver ligada)
Ao mover o card para **Em cadência**, a A5:
1. Escolhe as pessoas: quem está marcado **Na cadência**; se ninguém, as **3 primeiras de prioridade 1–2** (ordem: prioridade → e-mail verificado/válido → nome). Exclui opt-out, prioridade 9 e papel "Fora".
2. Grava `cadencia_status = ativa`, `cadencia_inicio = hoje`, `onda = 1`.
3. Se a trilha ainda está **a definir**, cria a tarefa "Definir trilha antes do primeiro e-mail" e **usa o modelo "Sem configurador" como padrão**.
4. Cria as atividades da seção 3 para cada pessoa.

### Passo 6 — Durante a cadência (reações automáticas)
- **E-mail recebido** (A10): auto-resposta/"recebido"/"ok" → sinal 0, sem tarefa; assunto "Aceito:" → tarefa de confirmar reunião; qualquer outro → tarefa **Classificar resposta** (SDR classifica: negativa 0, neutra 30, braço erguido 60 → Conversa).
- **Conexão aceita** (A11): +15 pts, tarefa **Mensagem pós-conexão**; se decisor, o gestor recebe a tarefa de **asset personalizado** (prazo 6 dias úteis).
- **Asset pronto** (A16): ao colar a URL, tarefa **Enviar asset** via LinkedIn ao decisor conectado (*"Mensagem curta no LinkedIn, oferecendo 20 min para mostrar."*).
- **Conta quente** (A4): tarefas de **Ligação** (hoje) e **WhatsApp** (próximo dia útil, via DataCrazy) — *"Conta quente (score X). Ofereça 20 min."*
- **Formulário** (A15): tarefa de contato em até 1h útil.
- **Opt-out** (A12): cancela tudo da pessoa.
- **Onda 2** (A14, desligada): aos 21 dias sem resposta, mais 2 contatos entram na mesma sequência.

### Passo 7 — Saídas
- **Conversa** (A7): para a cadência (A6) e cria **Agendar reunião**.
- **Reunião agendada** (A8): cria **Preparar reunião**.
- **35 dias sem sinal** (A9): → **Nutrição**; A6 encerra a cadência como concluída.
- **Descartada**: A6 apaga as atividades pendentes.

---

## 3. A cadência como está hoje (detalhe por ponto de contato)

**Canais:** só **e-mail** e **LinkedIn**. Sem ligação, sem WhatsApp, sem asset na cadência fria.
**Dias:** dias úteis a partir do início (D1 = dia em que entrou em cadência).
**Para cada pessoa** (até 3 na onda 1):

| Dia | Atividade | Modelo / instrução | Regras de exceção |
|---|---|---|---|
| D1 | LinkedIn – Conectar | *"Convite com nota curta citando o dossiê. Ao concluir, marcar Conexão = Enviado."* | Não é criada se já conectado |
| D1 | **E-mail E1** | Modelo `ABM · E1 · {trilha}` | Não é criada se e-mail inválido/indisponível/vazio |
| D3 | LinkedIn – Interagir | *"Seguir e reagir a 1 post relevante. Sem convite."* | — |
| D5 | **E-mail E2** | Modelo `ABM · E2 · {trilha}` | idem E1 |
| D8 | LinkedIn – Mensagem de valor | *"Só se a conexão foi aceita; senão, marcar como feita. Conteúdo de valor (case, dado, post), sem asset e sem pitch."* | Só faz sentido com conexão aceita |
| D11 | **E-mail E3** | Modelo `ABM · E3 · {trilha}` | idem E1 |
| D14 | LinkedIn – Follow-up | mesma regra do D8 | idem D8 |
| D18 | **E-mail E4** | Modelo `ABM · E4 · {trilha}` | idem E1 |

**O que a SDR vê em cada atividade** (gerado pela A5):

```
Título: [Cadência] D{dia} {canal} – {Nome} ({Cargo})

{Nome} — {Cargo}
Papel: {papel} · Prioridade: {1|2}
LinkedIn: {url do perfil}
E-mail: {email} ({status})
Telefone: {telefone}
Link da conta: {x_abm_link_email ou x_abm_link_linkedin}
Dossiê: {x_abm_dossie_url}
Trilha: {Sem configurador|Configurador fraco} · Modelo: ABM · E{n} · {trilha}   ← só nos e-mails
```

Instrução padrão de todo e-mail: *"Enviar pelo chatter da conta, da caixa do SDR, usando o modelo indicado. Trocar o destinatário para a pessoa da tarefa."*

---

## 4. Os modelos de e-mail (o que o agente vai escrever)

### 4.1 Estado atual
8 modelos (`mail.template`, modelo `crm.lead`), **todos em rascunho**:

| Modelo | Assunto atual | Ideia registrada no rascunho |
|---|---|---|
| `ABM · E1 · Sem configurador` / `· Configurador fraco` | `{{ empresa }} · Observação da conta` | Observação específica da conta (lançamento recente, configurador atual) + link |
| `ABM · E2 · …` | `{{ empresa }} · Prova` | Case VW Tera em 3 linhas + uma pergunta |
| `ABM · E3 · …` | `{{ empresa }} · Oferta` | Convite para 20 min: case + calculadora de ROI (sem asset personalizado) |
| `ABM · E4 · …` | `{{ empresa }} · Encerramento` | Encerramento educado, porta aberta |

Corpo atual de todos: `[RASCUNHO … — reescrever. Ideia: …] Olá, / Link: / Material:`.

### 4.2 Restrições técnicas que o texto precisa respeitar
- O modelo renderiza sobre a **conta** (`object` = `crm.lead`), **não sobre a pessoa**. O destinatário é trocado à mão pela SDR. Portanto **o nome e o cargo da pessoa não entram automaticamente** — usar `[nome]` como marcador que a SDR troca, ou escrever sem vocativo nominal.
- Variáveis disponíveis no modelo (exemplos): `object.partner_id.name` (empresa), `object.name` (conta), `object.x_abm_link_email` (link com UTM do e-mail), `object.x_abm_asset_url`, `object.x_abm_dossie_url`, `object.user_id.name` (SDR). No assunto usa-se `{{ … }}`; no corpo HTML, `<t t-out="object.campo"/>`.
- **Sempre usar `x_abm_link_email`** como link do e-mail (a UTM identifica a conta e o canal; a visita volta como sinal).
- Um modelo serve **todas as contas da mesma trilha**. A personalização por conta (gatilho do dossiê, primeira linha do E1) é feita pela SDR na hora do envio — o texto padrão deve deixar **um espaço marcado** para isso, especialmente no E1 (ex.: `[OBSERVAÇÃO DA CONTA: lançamento/configurador — do dossiê]`).
- Se a trilha estiver "a definir", a A5 manda usar o modelo **Sem configurador** — ele precisa funcionar como texto genérico seguro.

### 4.3 Diretrizes de conteúdo (do processo de dossiê da Sétima)
- **Duas trilhas, dois ângulos:**
  - **Sem configurador:** "a concorrência já tem; o digital twin do seu carro vira configurador, social e OOH".
  - **Configurador fraco:** "o configurador que vocês já têm, com o realismo e a velocidade do VW Tera".
- **Provas:** configurador 3D do **VW Tera** (case principal); configurador da **Hyundai** em produção; marcas atendidas: Volkswagen (VW, VWFS, VW Caminhões e Ônibus), Toyota, Embraer; experiências interativas **+66% de engajamento e +9% em vendas** (dado da Sétima); 60+ projetos em 2025.
- **Isca:** **configurador espelho** — demo gerada com IA usando um modelo atual da própria conta.
- **CTA:** conversa de **20 minutos** para ver o configurador espelho com o carro da própria marca.
- **Objeções e respostas** (úteis para E3/E4 e follow-ups): 3D encarece → custo está na digitalização inicial, cada peça seguinte é fração; 3D parece artificial → realismo NGI indistinguível de foto, mostrar o Tera; já temos agência → Sétima entra como parceira técnica, o twin é ativo da marca; a matriz define o configurador → configurador global raramente cobre versões/cores/preços do Brasil; lançamento já fechado → o twin serve para o próximo facelift e para o conteúdo pós-lançamento.
- **Tom:** direto, sem jargão de agência, português do Brasil. E-mail frio **até 120 palavras**, gatilho na primeira linha. LinkedIn **até 300 caracteres**.
- **Regras da cadência fria:** sem pitch na primeira mensagem de LinkedIn; mensagens de LinkedIn D8/D14 com **valor** (case, dado, post), **sem asset**; asset personalizado só depois de decisor conectado (fora da cadência padrão).

### 4.4 O dossiê (entrada do agente)
Gerado pela skill **"dossie-de-guerrilha"** (um `.docx` por conta). Estrutura fixa:
1. Capa + resumo para o consultor (por que agora, ângulo, contato prioritário)
2. Raio-X da conta (site, porte, matriz/grupo, portfólio no Brasil, fábricas, agência)
3. Diagnóstico do configurador (sem configurador / 2D / 3D fraco / 3D bom) + observações
4. Gatilhos: data · fato · como usar · fonte
5. Comitê e contatos (nome · cargo · papel · abordagem)
6. Ângulo de venda (tese, case, isca espelho, objeções)
7. Mensagens prontas (e-mail frio, LinkedIn, abertura WhatsApp/ligação)
8. Fontes

Princípio: **todo gatilho é específico, verificável, datado e com fonte**. Sem gatilho, não inventar.

---

## 5. Divergências e lacunas (o agente deve saber)

| # | Ponto | Impacto nos textos |
|---|---|---|
| 1 | ⚠️ **A5 e A14 desligadas** até os e-mails ficarem prontos | Nenhuma cadência roda hoje; os textos são o bloqueio |
| 2 | ⚠️ **`x_abm_dossie_url` vazio em todas as 61 contas** | O dossiê não está ligado no Odoo; a SDR não tem o link na atividade. Os textos não podem depender de ler o dossiê dentro do Odoo |
| 3 | Trilha no dossiê usa **A/B + "Configurador 3D bom"**; no Odoo só existem **Sem configurador / Configurador fraco** | Conta com "3D bom" não tem modelo próprio — cai em uma das duas ou é despriorizada |
| 4 | Tier no dossiê é **A/B/C**; no Odoo é **1/2/3** | Só informativo |
| 5 | A skill de dossiê fala em cadência de 30–40 dias com telefone e WhatsApp; **o Odoo roda 18 dias úteis só com e-mail + LinkedIn** | Escrever para a cadência do Odoo (seção 3) |
| 6 | E3 cita **calculadora de ROI** | Existe `calculadora-roi/` neste repositório; confirmar a URL pública antes de usar no texto |
| 7 | 40 das 61 contas ainda com trilha **a definir** | O modelo "Sem configurador" vai ser o mais usado no início |

---

## 6. Entrega esperada do agente (sugestão)

Para cada trilha (**Sem configurador** e **Configurador fraco**):
- **E1, E2, E3, E4:** assunto (com `{{ object.partner_id.name or object.name }}`) + corpo (≤ 120 palavras, com marcador de personalização no E1 e link `x_abm_link_email`).
- **LinkedIn D1** (nota de convite, ≤ 300 caracteres, citando o gatilho do dossiê).
- **LinkedIn D8** (mensagem de valor, sem pitch, sem asset).
- **LinkedIn D14** (follow-up curto).
- Opcional: mensagem **pós-conexão** (A11) e **envio de asset** (A16) para decisor.
