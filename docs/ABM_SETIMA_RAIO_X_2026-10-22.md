# ABM Sétima: raio-x da operação em 22/10/2026

> **Para quem é este documento:** o agente de LLM que vai **revisar possíveis melhorias** no
> fluxo ABM Sétima. Leia junto com `ABM_SETIMA_FLUXO_E_CADENCIA.md`, que descreve a estrutura.
> Aqui está a **foto da operação**: o que está atrasado, o que vem pela frente, como as contas
> estão distribuídas e o que os dados mostram de atrito.
>
> **Fonte:** leitura direta do Odoo (`grupo-setima.odoo.com`) em **quinta, 22/10/2026**.
> O processo começou em **05/10/2026** (`abm.inicio`), ou seja, está com **~2,5 semanas de operação**.

---

## ⛔ Regra para o agente: melhorar sem desmontar

O fluxo **está rodando em produção** com uma SDR (Amanda) e um gestor (Diego). As propostas devem:

1. **Preferir ajustes de parâmetro, texto ou instrução** (nota de tipo de atividade, parâmetros `abm.*`,
   prazos) a mudanças de lógica.
2. **Não alterar** as etapas do pipeline, os campos existentes, a fórmula do score ou os IDs/xmlids
   (`abm_setima.*`). O dashboard (`odoo_modules/abm_setima_dashboard`) lê esses campos.
3. **Não religar a A5 (Início da cadência) nem a A14 (Onda 2).** Elas estão desligadas de propósito até
   os e-mails E1–E4 ficarem prontos.
4. Toda proposta deve dizer: **o que muda · onde (automação, parâmetro, tipo de atividade) · risco ·
   como desfazer**. Classificar cada uma em **(a) só configuração**, **(b) pequena mudança de código em
   uma automação** e **(c) mudança estrutural**. A prioridade é (a), depois (b). Propostas do tipo (c)
   ficam só registradas.
5. Nada de envio automático para o cliente. A decisão de manter os toques manuais é intencional.

---

## 1. Números do dia

| Indicador | Valor |
|---|---|
| Contas na equipe ABM Setima | **61** (todas com a Amanda) |
| Pessoas mapeadas nos comitês | **1.507** (média de ~25 por conta) |
| E-mails verificados ou válidos | **764** (51%) |
| Comitês validados no Apollo | **58 de 61** (Leapmotor e Land Rio sem decisor) |
| Pessoas conectadas no LinkedIn | **0** |
| Cadências ativas | **0** (A5 desligada) |
| Atividades abertas | **24**: 10 atrasadas, 6 para hoje, 8 futuras |
| Atividades concluídas desde 05/10 | **80**, sendo **58 (72%) concluídas depois do prazo** |
| Sinais registrados | **48** (35 ativos) |
| Contas em faixa engajada ou quente por score | **0 entre as prospects** (só a VW Caminhões, cliente, está quente) |
| Fila de preparação | **Travada pelo freio**: 14 tarefas vencidas ou para hoje, com limite de 10 |

---

## 2. Distribuição das contas

### Por etapa
| Etapa | Contas |
|---|---|
| Alvo (na fila) | 26 |
| Aquecendo | 26 |
| Engajada | 6 (Marcopolo, Jacto, Randoncorp, Honda Brasil, CNH, Nissan) |
| Em cadência | 0 (a Nissan foi devolvida para Engajada hoje; tinha sido movida à mão sem a A5) |
| Cliente – expansão | 3 (VW do Brasil, VW Caminhões e Ônibus, Hyundai) |
| Conversa em diante | 0 |

### Por preparação, trilha e cadência
| Campo | Distribuição |
|---|---|
| Preparação | liberada 32 · na fila 26 · vazio 2 (clientes) · pular 1 |
| Trilha | **a definir 40** · sem configurador 12 · configurador fraco 9 |
| Cadência | não iniciada 61 |
| Faixa | fria 60 · quente 1 (VW Caminhões, cliente) |

### Score das prospects (só as que têm pontos)
O score mais alto entre as prospects é **25 (Jacto)**. Nenhuma chegou a 30, que é o corte de engajada.
Quase todos os pontos vêm do **relatório de LinkedIn Ads** (sinal `li_ads_relatorio`, lançado pelo gestor).

| Score | Contas |
|---|---|
| 20–25 | Jacto 25, Toyota, Stellantis, Honda Brasil, AGCO (20) |
| 10–15 | Scania, John Deere 15; Volvo CE, Caterpillar, Komatsu, Stara, Randoncorp, CNH, Zeekr, Nissan, Mitsubishi, Marcopolo, Yamaha, Ford, BYD (10) |
| 5 | JCB, Librelato, Royal Enfield, Iveco, Volvo Cars, Renault, Mercedes-Benz, Honda |

### Exposição (impressões de LinkedIn Ads por pessoa do comitê, 30 dias), contas em Aquecendo
| Faixa | Contas |
|---|---|
| ≥ 4 (A17 antecipa a cadência) | Caterpillar 12,9 · Komatsu 12,6 · Stara 11,5 · Yamaha 9,2 · Volvo CE 7,8 · AGCO 7,5 · John Deere 6,9 · Zeekr 6,7 · Stellantis 6,6 · Mitsubishi 5,9 · Ford 5,3 · BYD 5,1 · Toyota 5,0 |
| 2 a 4 | Iveco 3,5 · Renault 3,4 · Librelato 3,1 · Mercedes 3,0 · Scania 2,8 · Volvo Cars 2,4 · JCB 2,3 · Honda 2,3 · Royal Enfield 2,2 |
| 0 (A18 alerta) | Harley-Davidson, Grupo CAOA, BMW, General Motors (liberadas em 21/10, ainda fora do relatório de Ads) |

### Como as contas foram liberadas
| Data | Contas | Origem |
|---|---|---|
| 05/10 | 6 | 4 pela fila + 2 por sinal |
| 14/10 | 22 | **por sinal (A20)**: o relatório de LinkedIn Ads deu pontos a contas em Alvo, e todas furaram a fila de uma vez |
| 21/10 | 4 | pela fila |
| Demais dias úteis | 0 | freio ativo (≥ 10 tarefas vencidas ou para hoje) |

---

## 3. Atividades atrasadas (10)

| Prazo | Conta | Atividade | Responsável |
|---|---|---|---|
| 14/10 | Honda Brasil | [Prazo] Engajada há 5 dias úteis sem iniciar cadência (A19) | Diego |
| 21/10 | Marcopolo S.A. | [Prazo] Engajada há 5 dias úteis sem iniciar cadência (A19) | Diego |
| 21/10 | BMW Group Brasil | LinkedIn seguir/interagir + Definir trilha | Amanda |
| 21/10 | General Motors | LinkedIn seguir/interagir + Definir trilha | Amanda |
| 21/10 | Grupo CAOA | LinkedIn seguir/interagir + Definir trilha | Amanda |
| 21/10 | Harley-Davidson | LinkedIn seguir/interagir + Definir trilha | Amanda |

Fora do pipeline: a tarefa "Relatório LinkedIn Ads → Claude Code" do Diego (no contato "ABM – Rotinas")
está vencida desde **05/10**, mas os sinais de Ads foram lançados em 02/10 e 14/10.

## 4. Para hoje (6) e previstas (8)

| Prazo | Conta | Atividade |
|---|---|---|
| **22/10** | Marcopolo S.A. | Definir trilha + **Iniciar cadência** |
| **22/10** | Jacto | **Iniciar cadência** |
| **22/10** | Randoncorp | **Iniciar cadência** |
| **22/10** | VW Caminhões e Ônibus | **Ligação ×2**: "Formulário: contato em até 1h útil – Adriano Macieira" (duplicada) |
| 26/10 | Honda Brasil | Definir trilha (a trilha já está preenchida) + Iniciar cadência |
| 26/10 | Jacto, Randoncorp | Definir trilha |
| 26/10 | CNH, Nissan | Definir trilha + Iniciar cadência |
| 26/10 | (rotina) | Rotina semanal ABM (Amanda) |

Agenda depois de 26/10: **vazia**. Não há nenhuma tarefa criada além dessa data.

## 5. O que vem pelas automações de tempo (sem ninguém fazer nada)

| Quando (aprox.) | Automação | Efeito previsto |
|---|---|---|
| **~28/10** | **A17** (14 dias em Aquecendo com exposição ≥ 4) | **13 contas vão para Engajada no mesmo dia**, cada uma com a tarefa "Iniciar cadência" |
| ~28/10 | A18 | Nenhuma das contas de 14/10 está abaixo de 2: sem alerta |
| **~04/11** | **A3** (21 dias em Aquecendo) | As **9 restantes** de 14/10 vão para Engajada, com mais 9 "Iniciar cadência" |
| ~04/11 | A18 | Alertas de exposição baixa para Harley, CAOA, BMW e GM, se continuarem em 0 |
| **~04/11 e ~11/11** | **A19** (7 dias em Engajada sem cadência) | **Um alerta por conta para o gestor**: até 22 alertas, porque a cadência não pode começar (A5 desligada) |
| ~11/11 | A3 | Harley, CAOA, BMW e GM vão para Engajada |
| contínuo | Freio da fila | Com 14 ou mais tarefas abertas, as **26 contas em Alvo** não entram |

**Resultado esperado em ~3 semanas:** cerca de **28 contas paradas em Engajada**, com "Iniciar cadência" vencida e alertas
diários ao gestor, sem poder avançar enquanto os e-mails estiverem em rascunho.

---

## 6. Atritos e anomalias que os dados mostram

Cada item traz evidência e uma sugestão de mudança **mínima**, como ponto de partida para o agente.

### 6.1 A trilha é marcada como feita sem o campo preenchido
- **Evidência:** Zeekr, Stellantis e BYD tiveram a tarefa "Definir trilha" concluída em 20/10, mas o campo continua `a_definir`. A Honda Brasil é o caso contrário: o campo está preenchido e a tarefa continua aberta.
- **Mínimo:** reforçar a instrução no tipo de atividade ("só concluir depois de preencher o campo Trilha"). Ajuste de código opcional: ao concluir, se o campo continuar vazio, reabrir a tarefa ou postar um aviso.

### 6.2 A cadência está bloqueada, mas as automações de tempo continuam empurrando contas
- **Evidência:** a A5 está desligada, enquanto A17, A3 e A19 seguem ativas. Isso gera a onda da seção 5 (Iniciar cadência e alertas sem saída).
- **Mínimo:** decidir se A19 deve ficar em pausa enquanto a A5 estiver desligada, ou se a nota da "Iniciar cadência" deve deixar claro o que a SDR faz nesse meio-tempo (definir trilha, marcar "Na cadência", conectar no LinkedIn).

### 6.3 Nenhuma conexão de LinkedIn enviada
- **Evidência:** 0 pessoas conectadas. Na cadência, "LinkedIn – Conectar" só acontece no D1, e a A5 está desligada. Toda a parte de LinkedIn depende de conexão aceita (A11, A16, mensagens D8 e D14).
- **Mínimo:** avaliar se o "Conectar" com os decisores pode entrar na **preparação** (Aquecendo), sem depender da A5. Como a conexão leva dias para ser aceita, isso adiantaria o processo.

### 6.4 O score depende quase só do LinkedIn Ads
- **Evidência:** dos 48 sinais, 43 são do relatório de Ads. Não há nenhum registro de visita ao site, de visita a cases ou de reação a post desde 05/10. A "Rotina semanal" da Amanda (Apollo e posts do especialista) não gerou nenhum sinal.
- **Mínimo:** revisar se a rotina semanal está sendo feita e se o passo a passo dela está claro. Sem esses sinais, o score não diferencia as contas, e a fila ordena praticamente por tier e por nome.

### 6.5 O freio da fila trava quase sempre
- **Evidência:** a fila liberou contas em só 2 dos 14 dias úteis. As atividades são concluídas em blocos (14/10: 28; 16/10: 29; 20/10: 21), e 72% delas depois do prazo.
- **Mínimo:** revisar `abm.preparacao_limite_pendentes` (10) e `abm.preparacao_contas_dia` (4) à luz da capacidade real. Considerar se as tarefas do gestor devem contar no freio (hoje só contam as da SDR).

### 6.6 O relatório de Ads libera muitas contas de uma vez
- **Evidência:** em 14/10, 22 contas saíram de Alvo ao mesmo tempo pela A20 (score > 0 vindo do relatório de Ads), ignorando o ritmo de 4 por dia e o freio.
- **Mínimo:** avaliar se o sinal de Ads deve continuar furando a fila, ou se a A20 deve valer só para sinais de intenção (site, formulário, resposta, interação com post).

### 6.7 Tarefa de formulário duplicada e disparando em conta cliente
- **Evidência:** a mesma pessoa (Adriano Macieira, VW) se cadastrou duas vezes (15/10 e 16/10). A A15 criou **2 tarefas de ligação** e **2 sinais de 60 pts** (score 160) numa conta **Cliente – expansão**.
- **Mínimo:** fazer a A15 ignorar o cadastro se já existir uma tarefa "Formulário:" aberta para o mesmo e-mail. Definir se clientes de expansão devem receber a mesma tarefa.

### 6.8 Sinais de resposta em oportunidades fora do ABM
- **Evidência:** 6 sinais "Resposta recebida (a classificar)" da A10, criados entre 06/10 e 15/10, estão em oportunidades que parecem jobs de outra frente (ex.: "26/0165 - ORBX - Jetour", "26/0168 - Barry Company - Heinz"), de uma empresa que a chave de API não consegue ler. A A10 filtra `team_id = 20` e não foi editada depois de 02/10.
- **Mínimo:** confirmar se essas oportunidades já estiveram na equipe 20, ou se a A10 está disparando fora do escopo. Os sinais valem 0 ponto, mas poluem a base.

### 6.9 Possível conta duplicada: Honda
- **Evidência:** existem "Honda" (Aquecendo, score 5) e "Honda Brasil" (Engajada, score 20, trilha definida).
- **Mínimo:** confirmar se são operações diferentes (por exemplo, motos e automóveis). Se não forem, unificar.

### 6.10 Prazos e textos inconsistentes
- A19 dispara depois de **7 dias corridos**, mas a mensagem diz "**5 dias úteis**".
- A19 cria a tarefa com o tipo "Rotina semanal" (`act_rotina`), o que confunde os filtros e o dashboard.
- O dossiê fala em tier A/B/C e trilha A/B/"3D bom". O Odoo usa tier 1/2/3 e só duas trilhas.
- `x_abm_dossie_url` está **vazio nas 61 contas**: a atividade de cadência sempre mostra "Dossiê: -".

---

## 7. O que o agente deve entregar

1. Lista de melhorias priorizadas, cada uma com **o que muda · onde · tipo (a/b/c) · risco · como desfazer · impacto esperado**.
2. Ao menos uma proposta para os itens **6.1, 6.2, 6.3 e 6.5**, que são os que mais travam a operação agora.
3. Para cada proposta do tipo (b), o **trecho de código antes e depois** da automação envolvida. Nada de reescrever a automação inteira.
4. Uma recomendação de **sequência**: o que fazer antes de religar a A5 e o que fazer depois.
