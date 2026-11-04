# LinkedIn · ABM Sétima — atualização de 04/11/2026

Relatórios recebidos em 04/11 e o que cada um alimentou:

| Relatório | Período | Uso |
|---|---|---|
| Empresas (`companies-export_508640297_2026-11-04`) | últimos 30 dias | **Leadscore e pipeline**: sinal `li_ads_relatorio` + `x_abm_exposicao` |
| Análise de visitantes da página (prints) | últimos 30 dias | **Notas nas contas e uma atividade** (seção 2) |
| Desempenho do conjunto de anúncios (`campaign_performance_report_5`) | 06/10–04/11 | este relatório (seção 3) |
| Demográfico (`demographics_report_5`) | 06/10–04/11 | este relatório (seção 3) |
| Conteúdo da página (`setimacc_content`) | 04/10–02/11 | este relatório (seção 4) |
| Visitantes da página (`setimacc_visitors`) | 04/10–02/11 | este relatório (seção 4) |

## 0. Relatórios que faltaram

1. **Seguidores da página** (`setimacc_followers`) não veio. Em 23/10 ele tinha vindo. Sem
   ele não dá para registrar o sinal "Seguiu a página" (+10).
2. **O demográfico veio duplicado.** `demographics_report_5` e `demographics_report_6` são
   idênticos, byte a byte. Se o segundo deveria ser outro recorte (outra campanha ou outro
   período), ele precisa ser exportado de novo.
3. **O relatório de conteúdo veio sem a aba de publicações.** Só veio a aba de métricas
   diárias, então não dá para ver post a post nem quem reagiu.
4. **A Análise de visitantes veio só em prints, e parciais.** Há trechos entre um print e
   outro que ficaram de fora (ex.: o item acima de "Especialista em cumprimento na empresa XP
   Inc."). A lista nominal só existe na página do LinkedIn, sem exportação.

## 1. Leadscore (relatório de Empresas)

Aplicado às 14:36 UTC com `importar_linkedin_ads_abm.py`. O mesmo script foi usado na foto
de 30/10 e agora entrou em `main` com testes. A foto de 04/11 **substituiu** a de 30/10,
conforme a régua da seção 5.4 do processo: nível 0/5/10/20/25, interações 0/5/10/15 e
exposição 0/5/10, com teto de 30.

- 58 contas ativas avaliadas, **52 pontuam** (eram 47), 47 fotos anteriores desativadas.
- 6 contas sem pontos de Ads: Harley-Davidson, Jetour, KIA, Kawasaki, LS Tractor e Sany.
  Harley, Jetour, Kawasaki, LS Tractor e Sany seguem com **0 impressões**. A KIA teve 10 para
  8 pessoas no comitê, o que dá exposição abaixo de 2.
- **Nenhuma conta mudou de faixa**, então nenhuma automação disparou:
  - quentes: Nissan 80 (era 75) e Yamaha 70;
  - engajadas: Scania 30 e Marcopolo 30;
  - frias: 55, com máximo de 25 (Jacto, Honda Brasil e JLR).
- Somando as contas, de 30/10 para 04/11: impressões passaram de 10.246 para **15.515**
  (+51%) e interações de 197 para **245**.

| Conta | 30/10 (nível · interações · impr. · pts) | 04/11 |
|---|---|---|
| Marcopolo S.A. | High · 78 · 369 · 30 | Medium · 81 · 600 · 30 |
| Jacto | Low · 9 · 251 · 20 | Low · 10 · 375 · **25** |
| JLR Brasil | High · 3 · 9 · 25 | Medium · 3 · 42 · 25 |
| Nissan do Brasil | Very Low · 7 · 340 · 15 | Very Low · 12 · 501 · **20** |
| John Deere | Very Low · 8 · 1.557 · 15 | Very Low · 14 · 2.150 · **20** |
| CNH · GWM · General Motors | 0 interações · 10 | 6–7 interações · **15** |
| Volvo Trucks | Low · 3 · 80 · 15 | Very Low · 3 · 123 · **10** |
| JAC, Porsche (antes 0) | — | exposição ≥ 4 · **10** |
| Liebherr, Geely, Leapmotor (antes 0) | — | exposição 2–3,9 · **5** |

Fora do ABM, as duas de maior engajamento são clientes: **Volkswagen Caminhões e Ônibus**
(Very High, 469 interações orgânicas) e **Volkswagen do Brasil** (Low, 61 interações). As
duas estão arquivadas na equipe 20 como Cliente – expansão e ficam fora do score de propósito.

## 2. Visitantes da página (prints) → notas e atividade

Uma nota no chatter de cada conta ABM que aparece nos prints. A régua não tem sinal para
visita à página, então essas notas **não pontuam**.

| Conta | Visitante |
|---|---|
| AGCO Corporation | **Thiago Carmona de Paula**, Dealer Performance Manager – Fendt/Valtra, visitou há 25 dias. Não está no comitê. |
| Ford Brasil | Gerente de produtos |
| Toyota do Brasil | Especialista em Marketing |
| Honda Brasil | Gerente de tecnologia |
| Grupo CAOA | Vendedor de automóveis |
| Sany Brasil | alguém da SANY América Latina |
| Land Rio | alguém da empresa |

- Atividade **"[Oportunidade] Thiago Carmona de Paula … avaliar incluir no comitê"**, do tipo
  ABM · Rotina semanal, para o Diego, com prazo em 05/11.
- Também visitaram: um gerente de tecnologia da VW Caminhões (cliente arquivado, ficou sem
  nota) e um designer de UX da **Fóton Informática**. A Fóton é a página errada que já está na
  lista de empresas do Ads (ver item 8 do relatório de 23/10) e continua recebendo 329
  impressões.
- A tarefa recorrente "Relatório LinkedIn Ads → Claude Code" foi concluída. A próxima ficou
  para 09/11, com o passo a passo apontando para `importar_linkedin_ads_abm.py`.

## 3. Campanhas (06/10–04/11)

| Campanha | Investido | Impr. | Cliques | CTR | CPM | CPC | Engaj. | Views completas |
|---|---|---|---|---|---|---|---|---|
| [T][ABM][Eng] - Sétima | R$ 4.838,07 | 7.245 | 63 | 0,87% | R$ 668 | R$ 77 | 88 | 38 |
| [T][ABM][Alc][LP] - 3D | R$ 2.686,47 | 5.904 | 44 | 0,75% | R$ 455 | R$ 61 | 55 | 12 |
| [M][ABM][Leadnativo] - 3D | R$ 2.722,77 | 2.806 | 19 | 0,68% | R$ 970 | R$ 143 | 35 | 15 |
| **Total** | **R$ 10.247,31** | **15.955** | **126** | **0,79%** | **R$ 642** | **R$ 81** | 178 | 65 |

- **Conversão continua em zero**: 0 leads, 0 conversões e 0 seguidores vindos de anúncio. A
  Leadnativo abriu 12 formulários e nenhum foi enviado. A [Alc][LP] teve **0 cliques para a
  landing page** no período; a de engajamento teve 6.
- Vídeo: 17.003 reproduções e só **65 completas** (0,4%).
- Entrega por semana (todas as campanhas):

  | Semana ISO | Investido | Impr. | Cliques | CTR |
  |---|---|---|---|---|
  | 41 (06–11/10) | R$ 1.762 | 1.896 | 13 | 0,69% |
  | 42 (12–18/10) | R$ 1.181 | 1.202 | 14 | 1,16% |
  | 43 (19–25/10) | R$ 2.100 | 3.284 | 31 | 0,94% |
  | 44 (26/10–01/11) | R$ 3.602 | 7.372 | 54 | 0,73% |
  | 45 (02–04/11, parcial) | R$ 1.602 | 2.201 | 14 | 0,64% |

  A entrega mais que dobrou na semana 44, mas o CTR caiu. Em 16/10 e 18/10 não houve entrega.

### Demográfico (06/10–04/11)

| Recorte | Impr. | Cliques | CTR |
|---|---|---|---|
| Empresas com 10.001+ funcionários | 57,8% | 63,5% | 0,87% |
| Função Marketing | 30,2% | 27,8% | 0,73% |
| Gerente + Sênior | 59,5% | 55,6% | — |
| Diretor, VP e C-level | 9,4% | 16,7% (21 cliques) | 1,18% a 2,84% |
| Cargo "Especialista de produtos" | 10,3% | 4,0% | 0,30% |
| Setor "Publicidade e propaganda" | 7,5% | 12,7% | 1,34% |

- Por empresa, os cliques se concentram em **VW do Brasil (22)**, John Deere (11), VW
  Caminhões (10), Stellantis (9) e AGCO (9).
- O cargo "Especialista de produtos" continua sendo o maior gasto com o pior CTR. Já era
  ponto de atenção no baseline.
- A soma dos setores passa de 100% porque a empresa pode ter mais de um setor. Agências de
  publicidade aparecem com 7,5% das impressões, o que é público fora do alvo.

## 4. Página da Sétima (04/10–02/11)

- Impressões: **28.629**, das quais 98,7% patrocinadas. Só **360 orgânicas**, com 11 reações
  e 0 comentários em 30 dias.
- Visualizações da página: **103** (55 visitantes únicos somando os dias). Quem visita é
  sobretudo de Marketing (17) e Arte e design (16), nos níveis Iniciante (37) e Sênior (33),
  de empresas com 11 a 50 funcionários (28) e do setor Publicidade (17). É mais o mercado
  de agências do que as montadoras.

## 5. O que fica pendente

1. Mandar o export de **seguidores** e o **demográfico correto** (o segundo arquivo veio
   repetido).
2. Tirar **Fóton Informática** e as demais páginas erradas da lista de empresas do Ads.
3. Conferir a página na lista das 5 contas com 0 impressões (Harley, Jetour, Kawasaki,
   LS Tractor e Sany).
4. A versão do dashboard instalada no Odoo (19.0.2.0.0) está só no branch
   `claude/funny-faraday-qut9cx`, enquanto `main` tem a 19.0.1.0.0. Antes de reinstalar o
   módulo a partir de `main`, é preciso unificar as duas, ou o painel volta para a versão
   antiga. O painel lê sinais e exposição ao vivo, então os números acima já aparecem nele.
