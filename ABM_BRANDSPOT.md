# ABM BrandSpot (equipe 22) — regras do processo

Estado em 2026-10-21. Mesmo processo do ABM Sétima (equipe 20): mídia no LinkedIn
gera sinais, sinais formam o score, o score move a conta (Alvo → Aquecendo →
Engajada → Em cadência → Conversa → Reunião), e a SDR recebe as tarefas certas
na hora certa. **Mesmos pesos de sinal, mesma cadência, mesma fila diária.**

Tese do primeiro ciclo: grandes instituições de educação já têm estúdio interno
para gravar/transmitir aulas; para ampliar, precisam de mais estúdio — e podem
alugar em vez de construir. Sem case ainda; a prova é o showroom em São Paulo.

## Onde fica no Odoo
CRM → **ABM BrandSpot** (ao lado de ABM Setima): Pipeline · Sinais ABM ·
Atividades ABM · Dashboard. Mesmo visual de card, ficha e painel da Sétima.

## O que muda em relação à Sétima
| | Sétima | BrandSpot |
|---|---|---|
| Qualificação da conta | Trilha (configurador fraco / sem configurador) | **Estúdio interno**: Já tem estúdio · Baixa qualidade · Indefinido |
| Tarefa de preparação | Definir trilha | **Mapear estúdio** (site, YouTube, LinkedIn, vagas de audiovisual/EAD) |
| E-mails (rascunho) | 4 etapas × 2 trilhas | 4 etapas × 3 situações de estúdio (12 modelos) |
| Prova / CTA | Case + 20 min | Estrutura do estúdio + **visita ao showroom** (ou 20 min online) |
| Asset | Demo 3D / estudo do configurador | Construir × alugar, gravação-teste no showroom, vídeo-amostra |
| Tipos de atividade | `ABM · …` | `ABM BrandSpot · …` (cada menu Atividades mostra só a sua frente) |
| Freio da fila | Conta tarefas `ABM · …` da SDR | Conta as **duas frentes** (`ABM%`): a SDR é a mesma |

Campos, sinais (`x_abm_sinal`), pesos, expiração em 30 dias (A13) e as telas de
atividades são **compartilhados** entre as duas frentes.

## Contas (primeiro ciclo)
- 91 contas do export do Apollo (`abm_brandspot/contas/`) em **Alvo · Tier 2**,
  preparação "na fila", SDR Amanda, campanha "ABM BrandSpot Educação", links com
  UTM `utm_campaign=abm-brandspot-educacao`, Apollo Account Id na descrição.
- 5 delas já existiam na equipe 22 (G4, Senai SP, Descomplica, Alura, Arco) e
  foram atualizadas; 10 reaproveitaram empresas que já existiam no Odoo.
- Os 22 cards antigos da equipe 22 fora da lista viraram **Tier 3** (backlog):
  continuam no programa, mas a fila prepara a lista antes. Nada foi apagado.
- As 7 etapas antigas da equipe 22 ("ABM · Conta-alvo" …) foram renomeadas para
  as novas; nenhuma conta mudou de etapa.
- **Comitê ainda não importado.** As empresas antigas têm 324 contatos de uma
  tentativa anterior (248 da área Produto, todos com prioridade 0): revalidar.

## Ligado / desligado
- Ligadas: A1–A4, A6–A12, A15, A16 (A13 é a da Sétima, vale para as duas).
- **Desligadas**, como na Sétima: A5 (início da cadência) e A14 (onda 2), até os
  e-mails E1–E4 saírem do rascunho.
- **Fila diária de preparação: desligada** até o comitê ser importado (senão
  cada conta liberada ganha "Validar comitê" com comitê vazio). Ao ligar:
  Configurações → Técnico → Ações agendadas → "ABM BrandSpot · Fila de preparação".
- Parâmetro `abm_brandspot.inicio = 2026-10-26`: nenhuma tarefa nasce antes.

## Scripts (idempotentes; sem `--aplicar` só simulam)
```bash
python -m abm_brandspot.estrutura [--aplicar]                  # etapas, campos, tipos, e-mails, telas, menus, automações, fila
python -m abm_brandspot.criar_contas contas.csv [--aplicar]    # CSV de CONTAS exportado do Apollo
python -m abm_brandspot.instalar_dashboard [--aplicar]         # módulo odoo_modules/abm_brandspot_dashboard
```
O código das automações está em `abm_brandspot/codigo.py` (mesmo da Sétima,
lido ao vivo em 2026-10-21, com as diferenças da tabela acima). Rodar a
estrutura de novo atualiza código/telas, mas **não** religa nem desliga nada nem
mexe nos parâmetros: isso fica como estiver no Odoo.

Testado ponta a ponta numa conta de teste (apagada): A2, A4, A6, A7, A11, A15 e
o código da A5, além da fila em modo simulação.

## Otimizações em relação à Sétima
Aplicadas:
1. **Estúdio interno** no lugar da trilha, com checklist objetivo de pesquisa e
   o valor "Indefinido" como estado válido (não trava a cadência).
2. **Freio compartilhado** da SDR: a fila do BrandSpot não libera conta se a
   Amanda já tem 10+ tarefas ABM vencidas/hoje somando as duas frentes (hoje: 8).
3. **Estrutura versionada**: a da Sétima foi montada direto no Odoo e o que está
   no repositório (branches não mergeados) já divergiu do que roda; a do
   BrandSpot é recriável a partir deste repositório.
4. **Dashboard com o termômetro da tese**: distribuição de "Estúdio interno"
   (clicável) — mostra se a tese se confirma conforme a SDR mapeia as contas.
5. **Showroom como CTA** nas tarefas de conta quente, conversa e asset.

Recomendadas (decisão de vocês):
1. Fila da Sétima contar as duas frentes (`'ABM%'` em vez de `'ABM · %'` na
   ação "ABM · Fila de preparação"): hoje ela ignora as tarefas do BrandSpot.
2. **Persona do comitê**: decisor em EAD/Educação Digital, Produção de
   conteúdo/Audiovisual, Inovação acadêmica e Marketing; Compras/Facilities como
   influenciador. O `importar_comite_apollo.py` (branch `zen-archimedes`) está
   fixo na equipe 20/tag Montadoras e mapeia áreas de montadora: parametrizar.
3. **Limpeza de ICP da lista** antes da mídia: 19 contas fora de educação pura
   (5 governo/prefeituras, 6 saúde, 4 TI, FTD, isaac, Grupo Positivo,
   WebTraining sem dados), Credeal (fábrica de papel) e domínios suspeitos
   (NVP → nvp.com, Governo MT → seguranca.mt.gov.br, Eleva → institutosalta.com).
   Governo compra por licitação: ciclo e abordagem diferentes.
4. **Famílias de conta**: Sesc (6), Senai (5), Sesi (4), FGV (2), Firjan (2),
   Marista (2), Grau (2) — definir conta-mãe ou um dono por família para não
   abordar o mesmo comitê duas vezes.
5. **Proximidade do showroom**: 35 das 91 contas são de SP. Como a visita é o
   CTA, priorizar SP (ex.: Tier 1 para SP com estúdio confirmado) ou oferecer
   gravação-teste/remoto para as de fora.
6. **Sinal de vaga aberta** (produtor audiovisual, editor, designer
   instrucional, coordenador EAD) via Apollo job postings, como novo tipo de
   sinal (ex.: 15 pts) — é o indício mais direto de que a produção está crescendo.
7. Relatório do LinkedIn Ads: o `atualizar_score_linkedin_ads.py` é da equipe 20;
   parametrizar a equipe para rodar com o CSV da campanha BrandSpot.
