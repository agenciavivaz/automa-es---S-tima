# Processo ABM Sétima — da conta-alvo à reunião agendada

Referência completa do processo ABM (Account-Based Marketing) da Sétima como está configurado
no Odoo em **23/10/2026**: etapas, regras, leadscore, automações, atividades, rotinas e
dashboard. Fonte única para materiais de explicação do processo.

---

## 1. Visão geral

- **O que é:** um programa para abrir conversa com um grupo fechado de empresas-alvo
  (montadoras e fabricantes de veículos e máquinas). A oferta da Sétima é o **modelo 3D do
  produto do cliente** (configurador 3D e conteúdo para site, campanha e redes).
- **Lógica:** primeiro a conta é **aquecida** (anúncios no LinkedIn e interação no LinkedIn),
  depois recebe uma **cadência** de e-mails e mensagens para as pessoas certas, até virar
  **conversa** e **reunião**.
- **Onde fica:** Odoo → **CRM → ABM Setima**, com quatro menus:
  1. **Pipeline**: o kanban das contas, uma coluna por etapa.
  2. **Sinais ABM**: todos os sinais (eventos que geram pontos).
  3. **Atividades ABM**: todas as tarefas do processo.
  4. **Dashboard**: painel de acompanhamento.
- **Unidade de trabalho:** a **conta** (a empresa), não o lead individual. Cada conta é uma
  oportunidade da equipe "ABM Setima" ligada à empresa, e as pessoas da empresa formam o
  **comitê de compra**.

## 2. Pessoas e papéis

| Quem | Papel no processo |
|---|---|
| **Amanda** (SDR) | Executa as tarefas do dia a dia: preparação, LinkedIn, e-mails, classificação de respostas, agendamento. |
| **Diego** (gestor, Vivaz) | Recebe alertas e revisões, cuida do asset personalizado e roda o relatório semanal do LinkedIn Ads. |
| **Perfil do Savio** (LinkedIn) | Todas as ações no LinkedIn (seguir, curtir, conectar, mensagens) são feitas logado no perfil do Savio. |

As automações só criam tarefas para a Amanda e para o Diego.

## 3. Conceitos

### 3.1 Comitê de compra
São as pessoas da empresa cadastradas como contatos dela. Cada uma tem:

| Campo | Valores e significado |
|---|---|
| **Papel** | **Decisor** (P1): diretor, head, VP ou CMO de marketing, comunicação, marca ou marketing de produto; ou quem acumula marketing; sem líder de marketing, o gerente de marketing mais sênior. **Influenciador-chave** (P2): gerentes de marketing, mkt de produto, comunicação, branding, CRM, e-commerce, digital e CX; líderes de produto e de site/digital. **Influenciador** (P2/P3): coordenadores, especialistas e analistas de marketing; gerentes de produto (fora da cadência). **Aprovador** (P3): CEO, presidente, VP geral, gerente geral, financeiro, compras, comercial (só para escalada; fora da cadência). Também existem Usuário/Técnico, Usuário/Ponto de entrada e **Fora** (excluído). |
| **Prioridade** | 1 = decisor · 2 = influenciador-chave · 3 = demais · 9 = excluído. |
| **Área / Senioridade** | Área (Marketing, Produto, TI/Digital, Compras, Engenharia/Design, Comercial…) e senioridade (C suite, VP, Head, Director, Manager, Senior…). Definem o **ângulo** da mensagem (seção 8.3). |
| **Status do e-mail** | Verificado, Válido, Inválido, Indisponível, Extrapolado, catch-all. E-mail inválido ou indisponível não recebe e-mail da cadência. |
| **Conexão LinkedIn** | Não enviado → Enviado → **Aceito** (ou Recusado/expirado). |
| **Na cadência** | Marca quem recebe a cadência (até 3 pessoas por conta). |
| **Opt-out** | Pediu para não receber contato: sai de tudo (seção 9.6). |

Indicadores do comitê na conta: pessoas no comitê, decisores, conectados no LinkedIn e
e-mails válidos.

### 3.2 Tier
Prioridade estratégica da conta: **1**, **2** ou **3** (1 é a mais importante). Usado na ordem
da fila de preparação.

### 3.3 Trilha
Define o tipo de abordagem, a partir do site da conta:

| Trilha | Quando |
|---|---|
| **Sem configurador** | A marca não tem configurador 3D. |
| **Configurador fraco** | Tem configurador, mas ruim (só troca cor, sem interior, lento no celular). |
| **Configurador fraco · variante C** | O configurador é bom: a abordagem fala de **volume de conteúdo** para o lançamento, não de configurador. É marcada escrevendo "variante C" na Ficha da conta. |
| **A definir** | Ainda não avaliado. A cadência só pode começar com a trilha definida. |

### 3.4 Ficha da conta e dossiê
- **Ficha** (Notas internas da conta): gatilho (lançamento, campanha), observações do site,
  modelo para a prévia, objeção provável. Alimenta a primeira linha dos e-mails.
- **Dossiê** (URL): estudo da conta. Não é pré-requisito da preparação, mas é item do
  checklist para iniciar a cadência.

### 3.5 Exposição
**Impressões pagas do LinkedIn Ads na conta (30 dias) ÷ pessoas no comitê** (mínimo de 10
pessoas no divisor). Mede o quanto a Sétima apareceu para a conta, não o quanto a conta
reagiu. Referências: **≥ 4** = exposição alta; **< 2** = exposição baixa.

---

## 4. Etapas do pipeline

| # | Etapa | O que significa | Como a conta entra |
|---|---|---|---|
| 1 | **Alvo** | Conta-alvo cadastrada, esperando a fila de preparação. | Cadastro da conta. |
| 2 | **Aquecendo** | Preparação liberada: comitê validado, LinkedIn (seguir/curtir), trilha. Recebe anúncios. | Pela fila diária (seção 6) ou por um sinal de intenção em Alvo (A20). |
| 3 | **Engajada** | Conta que **reagiu**: score ≥ 30. | Só pelo score (A2). |
| 4 | **Em cadência** | Sequência de 18 dias úteis de e-mail e LinkedIn em andamento. | A SDR move a conta depois do checklist "Iniciar cadência". |
| 5 | **Conversa** | Alguém respondeu com interesse ou se cadastrou. | Braço erguido ou formulário (A4) ou movida pela SDR. |
| 6 | **Reunião agendada** | Reunião marcada. | Movida pela SDR. |
| 7 | Reunião realizada | Reunião aconteceu. | Movida pela SDR (fora do escopo deste documento). |
| — | **Nutrição** | Cadência terminou sem resposta; volta a receber só anúncios. | Automático aos 35 dias de cadência sem sinal (A9) ou manual. |
| — | **Descartada** | Conta fora do programa. | Manual. |
| — | **Cliente – expansão** | Já é cliente; tratada como expansão. | Manual. |

**Regra central:** **Engajada é só para score ≥ 30.** Tempo em Aquecendo ou exposição a anúncios
não movem a conta para Engajada; geram outras ações (seção 7).

---

## 5. Leadscore

### 5.1 Como é calculado
- O score da conta é a **soma dos pontos dos sinais ativos**.
- **Todo sinal expira em 30 dias** (A13): sai do score, mas fica no histórico.
- Barra de score (percentual): 90 pontos = barra cheia.

### 5.2 Temperatura (faixa)

| Faixa | Score |
|---|---|
| **Fria** | < 30 |
| **Engajada** | 30 a 59 |
| **Quente** | ≥ 60 |

### 5.3 Tabela de sinais

| Sinal | Pontos | Como é registrado |
|---|---|---|
| Cadastro: formulário da LP, Lead Gen ou lead magnet | **60** | Automático (A15) |
| **Braço erguido**: quer saber mais, pediu material ou aceitou reunião | **60** | Classificação da SDR ou convite de agenda aceito (A10) |
| Resposta genuína sem interesse claro (dúvida, encaminhou, "agora não") | **30** | Classificação da SDR |
| Ligação com conversa | **30** | SDR |
| Reagiu ou comentou post do especialista | **15** | SDR (rotina semanal) |
| Conexão aceita | **15** | Automático ao marcar "Aceito" no contato (A11) |
| Visitou cases, lead magnet ou contato | **15** | SDR (rotina semanal, Apollo) |
| Seguiu a página da Sétima no LinkedIn | **10** | Manual (lista de seguidores da página) |
| Visita ao site (Apollo) | **10** | SDR (rotina semanal) |
| **LinkedIn Ads: relatório 30 dias** | **0 a 30** | Relatório semanal do gestor (5.4) |
| Resposta recebida (a classificar) | 0 | Automático (A10) até a SDR classificar |
| Resposta automática, ausência ou só "recebido" | 0 | Automático (A10) |
| Resposta negativa / sem interesse | 0 | Classificação da SDR |
| Outro | variável | Manual, pontos no campo "Pontos variáveis" |

Origens possíveis de um sinal: LinkedIn Ads, LinkedIn (manual), Apollo, Site, E-mail, WhatsApp,
Formulário, Ligação.

### 5.4 Pontuação do LinkedIn Ads
Uma vez por semana, o relatório **Empresas** do Campaign Manager (últimos 30 dias) gera um sinal
por conta. Ele é uma **foto**: substitui o da semana anterior, não acumula.

| Componente | Regra | Pontos |
|---|---|---|
| Nível de engajamento do LinkedIn | Very Low · Low · Medium · High · Very High | 0 · 5 · 10 · 20 · 25 |
| Interações (engajamentos pagos + orgânicos) | 0 · 1–9 · 10–29 · 30+ | 0 · 5 · 10 · 15 |
| Exposição (3.5) | < 2 · 2 a < 4 · ≥ 4 | 0 · 5 · 10 |
| **Teto** | | **30** |

- Com o teto de 30, mídia sozinha leva a conta no máximo ao limite de Engajada.
- "Interações" contam cliques no anúncio, reações, comentários, compartilhamentos e novos
  seguidores. Visualização de vídeo não conta. O LinkedIn não informa quem interagiu.
- Uma empresa com várias páginas no LinkedIn (ex.: Scania Group + Scania Latin America + Scania
  Brasil) tem todas registradas na conta: os números são somados e vale o maior nível.
- O sinal do Ads **não** tira a conta de Alvo (só sinais de intenção fazem isso, A20).

---

## 6. Etapa 1 → 2: da conta-alvo à preparação

### 6.1 Entrada em Alvo (A1)
Ao entrar em Alvo, a conta fica marcada como **Na fila** de preparação.

### 6.2 Fila de preparação (rotina diária, dias úteis, 7h)
- Libera **até 4 contas por dia** (parâmetro `abm.preparacao_contas_dia`).
- **Ordem da fila:** tier → score (quem já reage vai antes) → força do comitê → nome.
  - Força do comitê = 3 × mín(decisores, 2) + mín(influenciadores-chave, 4); máximo 10, para
    um comitê grande não passar na frente só pelo volume.
- **Freio:** se a SDR tiver **10 ou mais** tarefas ABM vencidas ou para hoje
  (`abm.preparacao_limite_pendentes`), nada é liberado no dia.
- Não roda em fim de semana nem feriado (lista `abm.feriados`). Nenhuma tarefa nasce antes de
  `abm.inicio` (05/10/2026).
- Ao liberar, a conta vai para **Aquecendo** e recebe as **tarefas de preparação**, todas para o
  mesmo dia:

| Tarefa (para a SDR) | Quando aparece | O que fazer |
|---|---|---|
| **Validar comitê** | Só se o comitê não foi validado no Apollo ou não tem decisor | Confirmar cargo atual no LinkedIn e ajustar papel e prioridade. Sem ninguém de marketing: avisar o gestor. |
| **LinkedIn – seguir e curtir** | Sempre | Pelo perfil do Savio: **seguir** e **curtir 1 post** de cada Decisor e Influenciador-chave (a lista vem na tarefa, com link). **Sem convite** nesta etapa. |
| **Definir trilha** | Se a trilha está "a definir" | Com dossiê: usar o diagnóstico. Sem dossiê: testar o site (configurador existe? 3D? interior? velocidade? **no celular**), registrar links e prints na Ficha e **gravar o campo Trilha** antes de concluir. |

- A rotina diária também reabre "Definir trilha" se a tarefa foi concluída com o campo vazio, e
  conclui sozinha a tarefa se o campo já foi preenchido.

### 6.3 Atalho: sinal de intenção em Alvo (A20)
Se uma conta em Alvo recebe um sinal de intenção com pontos (visita ao site, reação a post,
formulário etc.; **não** vale Ads nem resposta automática/negativa/a classificar), ela **sai da
fila na hora**: vai para Aquecendo com as tarefas de preparação. Princípio: quem dá atenção
recebe atenção.

---

## 7. Etapa 2: Aquecendo

Enquanto está em Aquecendo, a conta recebe anúncios e a interação da preparação. Há três saídas:

### 7.1 Engajou: score ≥ 30 → Engajada (A2)
- A conta vai para **Engajada** e a SDR recebe **Iniciar cadência** (seção 8.1).
- Se a preparação ainda não tinha sido feita, as tarefas de preparação vêm junto.
- Se o sinal foi formulário ou braço erguido, a conta vai **direto para Conversa** (seção 9).
- Não entra na cota semanal: Engajada por score tem prioridade.

### 7.2 Exposição alta sem engajar: Pronta p/ abordagem (A17)
- **Gatilho:** 14 dias em Aquecendo com exposição ≥ 4.
- A conta **continua em Aquecendo** e recebe a etiqueta **"ABM · Pronta p/ abordagem"**.
- SDR recebe **"[Pronta p/ abordagem] LinkedIn – conectar decisores"**: convite pelo perfil do
  Savio para os decisores ainda sem convite, nota de até 200 caracteres com algo do perfil da
  pessoa ou da Ficha, **sem link e sem pitch**; depois marcar **Conexão = Enviado** no contato.
- Comitê sem decisor: em vez disso, o gestor recebe "[Comitê] … enriquecer".
- **Liberação da cadência (cota semanal):** a rotina diária libera **"[Pronta p/ abordagem]
  Iniciar cadência"** para **1 conta por dia útil, até 3 por semana** (`abm.cadencia_por_semana`),
  na ordem de **maior exposição**. Só libera se:
  - a cota da semana não foi cumprida;
  - contas em cadência + contas aguardando início somam **menos de 8** (`abm.cadencia_max_ativas`);
  - o freio da SDR não está ativo (menos de 10 tarefas vencidas ou para hoje).
  A conta segue em Aquecendo até a SDR fazer o checklist e mover para Em cadência.
- **Por quê:** o anúncio cria familiaridade com a Sétima. Se a conta viu bastante anúncio e não
  reagiu, a abordagem direta tende a ser mais fácil do que esperar um engajamento que talvez
  não venha. Na mensagem, **não** se diz "vi que você viu o anúncio": usa-se o mesmo assunto e a
  mesma prova dos anúncios.

### 7.3 Exposição baixa (A18)
- **Gatilho:** 14 dias em Aquecendo com exposição < 2.
- Gestor recebe **"[Mídia] Exposição baixa"**: conferir se a página da empresa está certa na
  lista do LinkedIn Ads e se o "Nome no LinkedIn" da conta bate com o relatório.

### 7.4 21 dias sem engajar (A3)
- **Gatilho:** 21 dias em Aquecendo.
- A conta **continua em Aquecendo**. Gestor recebe **"[Revisar] 21 dias aquecendo sem
  engajar"** com score, exposição e sinais fora do Ads. Decide: manter, trocar a abordagem
  (trilha, criativo, página no LinkedIn) ou mover para Nutrição.

---

## 8. Etapa 3 → 4: Engajada e cadência

### 8.1 Iniciar cadência (checklist)
Tarefa da SDR, criada pela A2 (Engajada) ou pela cota semanal (Pronta p/ abordagem):

1. Dossiê anexado e link no campo "Dossiê (URL)".
2. **Ficha da conta** preenchida nas Notas internas.
3. **Trilha** preenchida (não pode ficar "a definir").
4. Até **3 pessoas** marcadas **"Na cadência"**, com papéis diferentes e com decisor.
5. Contas em cadência agora **< 8**.

Checklist ok → **mover a conta para Em cadência**.

- **Alerta (A19):** conta há 7 dias em Engajada sem iniciar a cadência → o gestor recebe
  "[Prazo] Engajada há 7 dias sem iniciar cadência".

### 8.2 A cadência (A5)
Ao entrar em **Em cadência**, a conta fica com cadência **Ativa**, **Onda 1**, e a SDR recebe
todas as tarefas da sequência. Se ninguém foi marcado "Na cadência", o sistema escolhe até 3
pessoas (prioridade 1, Decisor ou Influenciador-chave; e-mail verificado primeiro). Se a trilha
estiver "a definir", vem a tarefa "Definir trilha antes do primeiro e-mail" e os e-mails usam o
modelo "Sem configurador".

**Sequência (18 dias úteis, para cada pessoa na cadência):**

| Dia útil | Canal | Toque | Limite | Para quem |
|---|---|---|---|---|
| D1 | E-mail | **E1 · Observação** | até 120 palavras | todos com e-mail válido |
| D3 | LinkedIn | **Conectar** | até 200 caracteres | Decisor e Influenciador-chave, se a conexão ainda não foi enviada nem aceita |
| D3 | LinkedIn | **Interagir** | 1 frase | todos |
| D5 | E-mail | **E2 · Prova** | até 90 palavras | todos com e-mail válido |
| D8 | LinkedIn | **Mensagem de valor** | até 300 caracteres | Decisor e Influenciador-chave **com conexão aceita** |
| D11 | E-mail | **E3 · Convite** | até 110 palavras | todos com e-mail válido |
| D14 | LinkedIn | **Follow-up** | até 300 caracteres | Decisor e Influenciador-chave **com conexão aceita** |
| D18 | E-mail | **E4 · Encerramento** | até 60 palavras | todos com e-mail válido |

- Dias úteis contam sem fins de semana e feriados.
- **D8 e D14 só com conexão aceita:** a SDR confere o campo Conexão LinkedIn; se não estiver
  "Aceito", marca a tarefa como feita sem enviar.
- **Ligação e WhatsApp não entram na cadência fria**: só quando a conta fica quente ou chega
  formulário (seção 9).
- **E-mails são enviados pela SDR**, pelo chatter da conta, da caixa da SDR, com o modelo
  indicado na tarefa (**ABM · E1/E2/E3/E4 · Sem configurador** ou **· Configurador fraco**),
  trocando o destinatário para a pessoa da tarefa. Nada é enviado automaticamente.
- Cada tarefa de cadência traz: objetivo, pessoa (cargo, papel, prioridade, área), ângulo, como
  escrever, cuidados, link da conta com UTM, dossiê e cópia da Ficha. Nos e-mails, vem também o
  checklist "Antes de enviar".

### 8.3 Direcionamento das mensagens

**Por toque e trilha**

| Toque | Objetivo e estrutura |
|---|---|
| **E1 · Sem configurador** | Abrir com um fato desta conta e conseguir um "sim, mostra". 1) gatilho ou observação da Ficha (1–2 frases, só desta conta); 2) o que isso implica para o papel da pessoa; 3) prova: configurador 3D do VW Tera (1 frase); 4) pergunta: "vale eu montar uma prévia do [modelo da Ficha]?"; 5) P.S. com o link da conta. Só dizer que não há configurador se isso foi visto no site; concorrente só se a Ficha disser qual. |
| **E1 · Configurador fraco** | Mesma estrutura. Descrever o que se viu (sem interior, só troca de cor, lento no celular) **sem chamar de ruim**: quem recebe pode ter feito. Testar no celular antes de escrever. |
| **E1 · Variante C** | Abrir com o volume de conteúdo do lançamento (versões × cores × canais); prova: o mesmo modelo 3D do Tera gera site, social e OOH; pergunta: "vale eu montar uma cena de campanha do [modelo]?". Não falar de configurador. Sem gatilho, despriorizar a conta. |
| **E1 · A definir** | Definir a trilha antes de enviar. Abrir pelo gatilho de lançamento; ângulo "um modelo 3D, todas as peças"; não falar do site deles. |
| **E2 · Prova** | Retomar o E1 em meia frase (sem "conforme e-mail anterior"); case em 3 linhas (situação, o que foi feito, o que mudou); uma pergunta sobre como fazem hoje. |
| **E3 · Convite** | 20 minutos: gatilho de reserva da Ficha; o que a pessoa vai ver (o modelo dela em 3D, como se produz, custo por peça); objeção provável respondida em 1 frase; duas opções de dia. |
| **E4 · Encerramento** | Encerrar sem queimar a conta: reconhecer que pode não ser o momento; duas saídas (quem cuida disso, ou voltar perto do próximo gatilho). Sem "último e-mail", culpa ou urgência inventada. |
| **LinkedIn · Conectar** | Pelo perfil do Savio, nota de até 200 caracteres com o gatilho da Ficha ou algo do perfil. Sem link, sem pitch. Ao concluir: Conexão = Enviado. |
| **LinkedIn · Interagir** | Ser visto sem pedir nada: comentário real (uma frase com opinião ou pergunta) em post da pessoa ou da marca sobre produto ou lançamento. Nunca citar a Sétima. |
| **LinkedIn · Mensagem de valor** | Entregar algo útil sem pedir nada: trecho do Tera, um dado, uma observação sobre o lançamento ou a calculadora de ROI. Sem asset personalizado, sem convite de reunião. |
| **LinkedIn · Follow-up** | Retomar o E3 ou o D8 e oferecer o espelho em uma pergunta. Se a pessoa já respondeu em qualquer canal, não enviar: atualizar a conta. |

**Ângulo por papel**

| Papel | Ângulo |
|---|---|
| Decisor de marketing | Um único modelo 3D do carro paga várias produções: site, campanha e pós-lançamento. |
| Marca | O mesmo arquivo gera o volume de peças que social e OOH pedem, com a mesma cara. |
| Produto | Dá para ter imagens de todas as versões antes de o carro estar pronto para foto. |
| Digital | Configurador leve no celular, com cada montagem virando lead para a concessionária. |
| Compras | Custo concentrado na digitalização inicial; certificação TISAX para lançamento sigiloso. |
| Engenharia | Modelo fiel ao produto real, aprovado uma vez e reutilizado. |
| Comercial | Configurador como ferramenta do vendedor e da concessionária: o cliente chega com o carro montado. |
| Geral | Fale do carro deles: um modelo 3D, todas as peças. |

**Checklist de todo e-mail:** a primeira linha só serve para esta conta · todo fato tem fonte ·
1 pergunta, 1 link · sem colchete sobrando · mais do carro deles que da Sétima · nada de "vi que
você visitou" · destinatário trocado para a pessoa da tarefa.

### 8.4 Conexão aceita e asset (A11 e A16)
- Ao marcar **Conexão = Aceito** num contato (A11):
  - entra o sinal "Conexão aceita" (+15);
  - SDR recebe **"[Cadência] Mensagem pós-conexão"** para o próximo dia útil;
  - se a pessoa é **decisora** e a conta está em Engajada, Em cadência ou Conversa, o gestor
    recebe **"Asset personalizado"** (prazo de cerca de 5 dias úteis).
- **Asset** = conteúdo de alto valor personalizado para a conta (lead magnet adaptado, estudo do
  configurador dela, demo 3D de um produto dela). Não faz parte da cadência padrão.
- Quando o gestor preenche **Asset (URL)** na conta (A16), a SDR recebe **"[Cadência] Enviar
  asset"** para cada decisor conectado: mensagem curta no LinkedIn oferecendo 20 minutos. Sem
  decisor conectado: "Asset pronto: definir para quem enviar".

### 8.5 Onda 2 (A14)
21 dias após o início da cadência, **sem nenhuma resposta**: entram **até 2 pessoas novas** do
comitê (Decisor ou Influenciador-chave ainda fora da cadência), com a mesma sequência de 8
toques. A conta passa para Onda 2. Sem contatos elegíveis, só fica uma nota.

### 8.6 Fim da cadência sem resposta (A9)
35 dias após o início da cadência, ainda em Em cadência:
- **com** algum sinal de intenção desde o início (exclui Ads, resposta automática, negativa e a
  classificar): a conta fica para decisão manual;
- **sem** sinal de intenção: vai para **Nutrição** (a cadência é encerrada).

---

## 9. Respostas, conta quente e Conversa

### 9.1 E-mail recebido (A10)
Quando chega e-mail na conta, de um contato do comitê ou de um domínio da conta:

| Tipo identificado | Regra | Resultado |
|---|---|---|
| **Resposta automática** | Assunto ou corpo com "resposta automática", "out of office", "ausência", "férias", "não entregue" etc., ou só "recebido"/"ok, obrigado" (até 4 palavras, sem pergunta) | Sinal 0 pts, nota na conta, sem tarefa |
| **Convite aceito** | Assunto começa com "Aceito:" / "Accepted:" | Sinal **braço erguido (60)** + tarefa "Convite aceito: confirmar e mover para Reunião agendada" |
| **A classificar** | Qualquer outra resposta | Sinal 0 pts + tarefa **Classificar resposta** |

### 9.2 Classificar resposta (SDR)
Na aba Sinais da conta, alterar o tipo do sinal "Resposta recebida (a classificar)":
- **Automática, ausência ou só "recebido"** → 0 pts, nada a fazer;
- **Negativa / sem interesse** → 0 pts; se pediu para não receber, marcar **opt-out**;
- **Genuína sem interesse claro** (pergunta, encaminhou, "agora não, me procure em X") → **30
  pts**; responder e seguir a cadência;
- **Braço erguido** (gostou, quer saber mais, pediu material ou proposta, aceitou ou sugeriu
  reunião) → **60 pts** (conta quente); responder no mesmo dia e mover para **Conversa**.

Resposta por **DM no LinkedIn** ou **WhatsApp**: a SDR registra o sinal com o tipo de resposta
e a origem correta.

### 9.3 Conta quente: score ≥ 60 (A4)
O gestor passa a seguir a conta. Depende do que levou a conta a quente:

| Caso | Ação |
|---|---|
| **Formulário** (já existe a tarefa "Formulário:") | Conta vai para **Conversa**; seguir a tarefa de contato do formulário. |
| **Braço erguido** | SDR recebe **"[Quente] Braço erguido: responder e agendar"** para hoje (responder e propor 20 min) e a conta vai para **Conversa**. |
| **Outros sinais** | Para cada pessoa na cadência (ou decisores) **com telefone**: **"[Quente] Ligar"** hoje + **"[Quente] WhatsApp"** no próximo dia útil (se a ligação não for atendida; enviar pelo DataCrazy). Sem telefone: "[Quente] Conta quente sem telefone: buscar número do decisor". |

### 9.4 Formulário de pessoa de conta-alvo (A15)
Quando entra um lead de **outra equipe** (inbound: LP, Lead Gen, lead magnet) com e-mail do
domínio de uma conta ABM:
- tarefa **"Formulário: contato em até 1h útil – [pessoa]"** (ligação, para hoje; vai para a
  SDR, ou para o gestor se a conta é Cliente – expansão);
- sinal **Cadastro (60 pts)** → conta quente → A4 leva para Conversa;
- nota com link entre a conta ABM e o lead de inbound. Não duplica se a mesma pessoa já tem
  tarefa aberta.

### 9.5 Conversa (A6 e A7)
- Ao entrar em Conversa, **a cadência para** (A6): todas as tarefas "[Cadência]" abertas são
  canceladas e o status vira **Pausada**.
- A SDR recebe **"Agendar reunião"** para o mesmo dia útil (A7), a menos que já exista a tarefa do formulário ou do
  braço erguido.
- A6 também age em **Nutrição** (status **Concluída**) e **Descartada** (Pausada).

### 9.6 Opt-out (A12)
Ao marcar opt-out num contato: todas as tarefas ligadas a ele são canceladas, ele sai da
cadência e fica uma nota na conta. Contatos com opt-out deixam de contar no comitê.

---

## 10. Etapa 6: Reunião agendada (A8)
Ao mover para **Reunião agendada**:
- SDR recebe **"Preparar reunião"** para o mesmo dia (ou o próximo dia útil), com o aviso: **configurador espelho
  pronto?** Conferir o modelo indicado na Ficha; se não estiver pronto, produzir antes ou
  remarcar. Não fazer a reunião sem o espelho: é o que foi prometido.
- O gestor passa a seguir a conta.

---

## 11. Tipos de atividade

Todas começam com "ABM · " e aparecem em **Atividades ABM**.

| Tipo | Quem | Origem |
|---|---|---|
| Validar comitê | SDR | Preparação |
| LinkedIn – Seguir/Interagir | SDR | Preparação e cadência (D3) |
| Definir trilha | SDR | Preparação, A5, rotina diária |
| LinkedIn – Conectar | SDR | A17 (antecipado) e cadência (D3) |
| Iniciar cadência | SDR | A2 e cota semanal |
| E-mail | SDR | Cadência (D1, D5, D11, D18) |
| LinkedIn – Mensagem | SDR | Cadência (D8, D14), pós-conexão (A11), enviar asset (A16) |
| Classificar resposta | SDR | A10 |
| Agendar reunião | SDR | A4, A7, A10 |
| Ligação | SDR (ou gestor) | A4, A15 |
| WhatsApp | SDR | A4 |
| Preparar reunião | SDR | A8 |
| Preparar asset | Gestor | A11 |
| Dossiê da conta | — | Rodar o dossiê, definir a trilha, colar a URL |
| Rotina semanal | Gestor / SDR | Alertas de revisão (A3, A17, A18, A19) e rotina semanal |
| Relatório LinkedIn Ads (Claude Code) | Gestor | Rotina semanal |

**Prefixos no resumo da tarefa:** `[Preparação]`, `[Pronta p/ abordagem]`, `[Cadência] D# …`,
`[Quente]`, `[Revisar]`, `[Mídia]`, `[Prazo]`, `[Comitê]`, `Formulário:`.

### 11.1 Menu Atividades ABM
Kanban agrupado por tipo de atividade, lista (com botão Feito), calendário e pivô. Filtros:
Minhas, Atrasadas, Hoje, Atrasadas + hoje, Próximos 7 dias, Preparação, Cadência, Quente /
formulário, Rotinas; agrupamentos por etapa, responsável, conta e prazo (dia).

---

## 12. Rotinas semanais

| Rotina | Quem | O que faz |
|---|---|---|
| **Relatório LinkedIn Ads** (segunda-feira) | Gestor | Campaign Manager → Plano → **Empresas** → visão Engagement, últimos 30 dias → exportar CSV → enviar ao Claude Code, que atualiza o sinal de Ads e a exposição de cada conta (5.4). Revisar empresas fora do ABM com engajamento alto (candidatas a conta-alvo). |
| **Rotina semanal** (segunda-feira, 15 min) | SDR | 1) **Apollo → visitantes do site, últimos 7 dias**: para cada domínio de conta ABM, registrar "Visita ao site" ou, se foi em cases/lead magnet/contato, "Visitou cases, lead magnet ou contato". 2) **Posts do especialista**: quem do comitê reagiu ou comentou → registrar "Reagiu ou comentou post". 3) Olhar no pipeline quais contas mudaram de faixa. O LinkedIn Ads não é registrado à mão. |

---

## 13. Automações (resumo)

| Código | Nome | Gatilho | Efeito |
|---|---|---|---|
| A1 | Entrou em Alvo | Conta entra em Alvo | Marca "Na fila" |
| A2 | Ficou engajada | Score passa de fria para ≥ 30 (em Alvo, Aquecendo ou Nutrição) | Engajada + Iniciar cadência (formulário/braço erguido → Conversa) |
| A3 | 21 dias aquecendo → gestor revisa | 21 dias em Aquecendo | Tarefa de revisão para o gestor (não move) |
| A4 | Conta quente | Score passa a ≥ 60 | Agendar / ligar / WhatsApp; Conversa |
| A5 | Início da cadência | Conta entra em Em cadência | Cria os 8 toques por pessoa |
| A6 | Parar cadência | Conta entra em Conversa, Nutrição ou Descartada | Cancela tarefas de cadência |
| A7 | Conversa | Conta entra em Conversa | Agendar reunião |
| A8 | Reunião agendada | Conta entra em Reunião agendada | Preparar reunião |
| A9 | Cadência sem sinal | 35 dias de cadência | Nutrição se não houve sinal de intenção |
| A10 | E-mail recebido | E-mail chega na conta | Classifica e cria sinal/tarefa |
| A11 | Conexão aceita | Contato com Conexão = Aceito | Sinal +15, mensagem pós-conexão, asset (decisor) |
| A12 | Opt-out | Contato marcado opt-out | Cancela tarefas da pessoa |
| A13 | Sinal expira | 30 dias da data do sinal | Sinal sai do score |
| A14 | Onda 2 | 21 dias de cadência sem resposta | +2 pessoas na cadência |
| A15 | Formulário de conta-alvo | Lead de inbound com domínio de conta ABM | Tarefa de contato em 1h + sinal 60 |
| A16 | Asset pronto | Asset (URL) preenchido | Enviar asset aos decisores conectados |
| A17 | 14 dias aquecendo com exposição → pronta p/ abordagem | 14 dias em Aquecendo com exposição ≥ 4 | Etiqueta + conectar decisores (não move) |
| A18 | Exposição baixa aos 14 dias | 14 dias em Aquecendo com exposição < 2 | Alerta de mídia para o gestor |
| A19 | Engajada sem cadência | 7 dias em Engajada sem cadência | Alerta para o gestor |
| A20 | Sinal em conta Alvo | Sinal de intenção com a conta em Alvo | Aquecendo + preparação |
| Rotina diária | Fila de preparação (7h, dias úteis) | — | Libera até 4 contas/dia para preparação; libera até 3 "Pronta p/ abordagem" por semana para cadência; reconcilia "Definir trilha" |

**Parâmetros:** contas/dia na fila = 4 · freio = 10 tarefas vencidas ou para hoje · teto de
contas em cadência = 8 · cota de cadência por exposição = 3/semana · início do programa =
05/10/2026 · feriados nacionais 2026–2027.

---

## 14. Dashboard (CRM → ABM Setima → Dashboard)

Painel que lê o CRM ao vivo; não grava nada. Tudo é clicável e abre a lista ou a ficha
correspondente.

- **Filtros:** período (7 dias, **30 dias** — padrão, mesma janela do Ads e da expiração dos
  sinais —, 90 dias, este mês, mês anterior, tudo, personalizado) e **tier**. Os indicadores
  comparam com o período anterior de mesma duração. Exporta PDF.
- **Card fixo "Programa hoje"** (não muda com o período): contas no programa e ativas, score
  médio, distribuição por faixa, cadências ativas, % de contas com decisor, top 4 contas por
  score e quantas reagiram no período.
- **Resultado do período (KPIs):**

| KPI | Definição |
|---|---|
| Contas com sinal | Contas distintas com pelo menos um sinal no período (e % da base) |
| Sinais captados | Sinais registrados no período e pontos gerados |
| Respostas | Sinais de resposta (e-mail, DM, classificadas) e braços erguidos |
| Atividades concluídas | Atividades ABM concluídas no período e % no prazo |
| Atividades atrasadas | Abertas com prazo vencido hoje, abertas e para hoje |
| Score médio | Média do score atual; engajadas e quentes |

- **Leitura do período:** destaques e pontos de atenção gerados por regras (variação de sinais,
  origem principal, conta mais ativa, braços erguidos, contas frias, alertas, % no prazo).
- **Sinais:** linha do tempo empilhada por origem, origem dos sinais, tipos de sinal, últimos
  sinais.
- **Jornada das contas:** posição no pipeline por etapa, temperatura (fria/engajada/quente),
  status da cadência (não iniciada, ativa, pausada, concluída) e tiers.
- **Onde agir agora:**
  - engajadas/quentes sem cadência ativa ("transformar atenção em conversa");
  - sem sinal há 21+ dias, em Aquecendo, Engajada ou Em cadência ("pararam de reagir");
  - comitê sem decisor mapeado ("sem decisor a cadência não chega a quem assina");
  - contas com atividade atrasada ("execução travada").
- **Execução:** atividades por tipo (concluídas, no prazo, hoje, atrasadas) e agenda dos
  próximos 7 dias.
- **Visão por conta:** tabela ordenável por score, sinais, exposição, atividades ou nome, com
  etapa, faixa, barra de score, último sinal, cadência, comitê (decisores/total) e exposição.
- **Glossário** no rodapé.

---

## 15. Jornada resumida

```
Alvo ──(fila diária, 4/dia, freio 10)──▶ Aquecendo ──(score ≥ 30, A2)──▶ Engajada
  │                                       │   │                              │
  └──(sinal de intenção, A20)─────────────┘   │                     Iniciar cadência
                                              │                              │
              (14 dias, exposição ≥ 4, A17) ──┤                              ▼
              Pronta p/ abordagem ──(cota 3/semana)──▶ Iniciar cadência ──▶ Em cadência (A5: 8 toques, 18 dias úteis)
              (14 dias, exposição < 2, A18) ──┤ alerta de mídia                  │
              (21 dias, A3) ──────────────────┘ gestor revisa                    │
                                                                                 │
             braço erguido / formulário / score ≥ 60 (A4, A10, A15) ────────────▶ Conversa (A6 para a cadência, A7 agendar)
             35 dias sem sinal de intenção (A9) ─────────────────────────────────▶ Nutrição
                                                                                 │
                                                                     Reunião agendada (A8 preparar reunião)
```
