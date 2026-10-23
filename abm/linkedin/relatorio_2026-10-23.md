# LinkedIn · ABM Sétima — atualização de 23/10/2026

Relatórios recebidos em 23/10 e o que cada um alimenta hoje:

| Relatório | Período | Uso atual |
|---|---|---|
| Empresas (`companies-export_…_2026-10-23`) | últimos 30 dias | **Pipeline e score** (sinal `li_ads_relatorio` + `x_abm_exposicao`) |
| Desempenho das campanhas | 01–23/10 | nenhum |
| Demográfico | 01–23/10 | nenhum |
| Conteúdo da página | 22/09–21/10 | nenhum |
| Seguidores da página | 22/09–21/10 | nenhum |

## 1. Pipeline e score (relatório de Empresas)

Aplicado às 13:54 UTC pelo script `atualizar_abm_linkedin_setima.py` (branch
`claude/determined-heisenberg-aahi3u`). Conferido conta a conta contra o CSV:
**57 contas casadas, 0 diferenças** de pontos ou exposição.

- 29 contas pontuam (mesmo número de 14/10); 15 contas com **0 impressões** em 30 dias;
  13 com impressões abaixo do corte de exposição (< 2 por pessoa do comitê).
- Volkswagen do Brasil (Low) e VW Caminhões e Ônibus (Medium, o único Medium) estão
  **arquivadas** na equipe 20 como clientes e ficam fora do score de propósito.
- Volvo Trucks perdeu o sinal: 69 impressões ÷ 37 no comitê = 1,9 (< 2) → 10 → 0 pts.
- Faixa: **todas as 59 contas ativas seguem frias** (score < 30). Máximo: Honda Brasil 25.

### Evolução por conta (nível · interações · impressões · pontos)

| Conta | 02/10 | 14/10 | 23/10 |
|---|---|---|---|
| Honda Brasil | High · 20 · 88 · 30 | Low · 26 · 388 · 20 | Low · 23 · 440 · 25 |
| Jacto | Very Low · 0 · 48 · 10 | Low · 10 · 182 · 25 | Low · 6 · 200 · 20 |
| AGCO Corporation | — | Very Low · 13 · 564 · 20 | Very Low · 10 · 640 · 20 |
| Stellantis South America | Very Low · 3 · 191 · 5 | Very Low · 11 · 872 · 20 | Very Low · 9 · 990 · 15 |
| Toyota do Brasil | — | Very Low · 10 · 272 · 20 | Very Low · 5 · 310 · 15 |
| Scania Group | — | Low · 4 · 68 · 15 | Low · 4 · 78 · 15 |
| John Deere | — | Very Low · 8 · 1.069 · 15 | Very Low · 7 · 1.184 · 15 |
| Marcopolo S.A. | Very High · 63 · 51 · 30 | Very Low · 0 · 248 · 10 | Very Low · 0 · 277 · 10 |

Demais 21 contas: Very Low, 0 interações, só pontos de exposição (5 ou 10).

| Foto | Contas pontuando | Low+ | Impressões | Interações | Views de vídeo | Contas com interação | Exposição ≥ 4 |
|---|---|---|---|---|---|---|---|
| 02/10 | 10 | 2 | 823 | 86 | 265 | 3 | 3 |
| 14/10 | 29 | 3 | 6.454 | 82 | 2.108 | 7 | 19 |
| 23/10 | 29 | 3 | 7.199 | 64 | 2.372 | 7 | 20 |

Em 9 dias entraram só +745 impressões nas contas: **as três campanhas ficaram sem
entrega de 16 a 20/10**. As interações caíram (82 → 64) porque a janela de 30 dias
perdeu dias melhores do que os que entraram.

## 2. Campanhas (01–23/10) contra o baseline (15/09–14/10)

| Campanha | Investido | Impr. | Cliques | CTR | CPM | CPC | Engaj. |
|---|---|---|---|---|---|---|---|
| [T][ABM][Eng] - Sétima | R$ 1.867,02 | 2.116 | 28 | 1,32% | R$ 882 | R$ 67 | 1,75% |
| [T][ABM][Alc][LP] - 3D | R$ 1.892,82 | 2.240 | 14 | 0,62% | R$ 845 | R$ 135 | 0,67% |
| [M][ABM][Leadnativo] - 3D | R$ 1.902,13 | 1.820 | 14 | 0,77% | R$ 1.045 | R$ 136 | 1,21% |
| **Total** | **R$ 5.661,97** | **6.176** | **56** | **0,91%** | **R$ 917** | **R$ 101** | 1,20% |
| Baseline (Alc + Leadnativo) | R$ 3.544,91 | 4.514 | 28 | 0,62% | R$ 785 | R$ 126 | — |

- Mesmas duas campanhas do baseline, agora: R$ 3.794,95 · 4.060 impr · 28 cliques ·
  CTR 0,69% · CPM R$ 935 · CPC R$ 136. A campanha de engajamento é a melhor das três.
- Depois da ampliação de cargos (21–23/10, 3 dias, 23/10 parcial): CTR 1,09% (antes
  0,86%), CPM R$ 1.024 (antes R$ 889), 427 impr/dia (antes 326). Cedo para concluir: o
  baseline pede 2 a 3 semanas.
- Vídeo: 2.119 views (34% das impressões), mas só **21 completas** (1%). Permanência
  média de 5 s.
- **Conversão: zero.** 0 conversões e 0 leads nas três; 9 formulários de Lead Gen
  abertos e nenhum enviado; a campanha [Alc][LP] teve **0 cliques para a landing page**
  em 18 dias de entrega (a de engajamento teve 3). 0 seguidores vindos de anúncio.

### Demográfico (01–23/10) contra o baseline

| Recorte | Baseline (até 14/10) | 01–23/10 |
|---|---|---|
| Função Marketing | 48,6% impr · 75% cliques | 40,9% impr · 42,9% cliques |
| Gestão de produtos | — | 18,4% impr · 26,8% cliques |
| "Especialista de produtos" | 16,8% impr · 0 cliques | 14,8% impr · 3 cliques |
| Diretor, VP e C-level | — | 9,9% impr · 5 cliques (8,9%) |
| Empresas com 10.001+ funcionários | — | 56% impr · 52% cliques |

## 3. Página da Sétima (22/09–21/10)

- Seguidores: **+19 líquidos** em 30 dias (todos orgânicos, 0 patrocinados), nenhum
  novo desde 15/10. Só 117 seguidores são de fabricantes de veículos.
- Conteúdo orgânico: **2 publicações**, as duas de 30/09 sobre BrandSpot/SENAI CIMATEC
  (331 e 410 impressões). Nenhuma sobre 3D/configurador. Depois de 02/10 as impressões
  orgânicas ficam em 3–50/dia, por isso não há reação a post para virar sinal.

## 4. Métricas que ficam de fora hoje

**Score / pipeline (por conta)**
1. **Clique pago** entra junto com reação e play de vídeo em "interações". Seis contas
   clicaram: AGCO 8, John Deere 7, Stellantis 6, Toyota 5, Honda 4, Jacto 4.
2. **Views de vídeo** só aparecem no texto do sinal; não pontuam nem viram campo.
3. **Nada do relatório fica em campo** além da exposição: nível, cliques, interações,
   impressões e vídeo ficam só no texto do sinal. O dashboard não consegue mostrar a
   tendência por conta (Honda caiu de High para Low; Marcopolo de Very High para Very Low).
4. **Seguiu a página** continua manual: o relatório de seguidores não traz empresa.

**Dashboard**
5. Nenhum dado de campanha: investimento, CPM, CPC, CTR, alcance, frequência, vídeo,
   permanência, cliques na LP, formulários, conversões.
6. Nenhum dado da página: seguidores e publicações.
7. Nenhum recorte demográfico (senioridade e função de quem vê e de quem clica).

**Qualidade da segmentação** (não é métrica, mas distorce as métricas acima)
8. A lista de empresas do LinkedIn tem páginas erradas: Fóton Informática (40 impr.),
   Montana Química, Kawasaki UAE, BMW Motorrad Chile, Honda Motorcycle India, Jetour
   (Angola), Gwm Medicina e Consultoria, Triumph for Carriers, Guerra LLP, Chevrolet Via
   Capital, Cambui Veículos, DAF France, entre outras.
9. 15 contas ABM tiveram 0 impressões em 30 dias: General Motors, Harley-Davidson, GWM,
   Jetour, Audi, Porsche, JLR, MG, Geely, CAOA Chery, JAC, Kawasaki, Dafra, LS Tractor e
   Sany. Vale conferir se a página delas na lista é a certa.
