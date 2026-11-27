# ABM Sétima · Dashboard (módulo importado no Odoo)

Painel estratégico em **CRM → ABM Setima → Dashboard** (logo abaixo de "Atividades ABM").
É uma tela OWL (`ir.actions.client`, tag `abm_setima_dashboard`) que lê **ao vivo**, com a
sessão do próprio usuário, os dados da equipe ABM Setima (`crm.team` 20):

- `crm.lead`: score, faixa, tier, etapa, cadência, comitê, exposição e data de criação de cada conta;
- `x_abm_sinal`: relatórios do LinkedIn Ads (janela do período) e sinais de intenção (histórico).

Nada é gravado: o painel só lê.

## Visual

Mesma identidade do Relatório Inbound e do Resultado Sétima (CSS escopado em `.o_vab`): cabeçalho com
período e comparação, barra de seções fixa, KPIs com variação colorida, cards neutros com cor só onde há
significado e rodapé com glossário e exportação em PDF.

## O que mostra (19.0.3.1.0)

Escopo CSS próprio `.o_vas` (o painel do ABM BrandSpot usa `.o_vab` e, com o mesmo prefixo, um sobrescrevia o outro).

1. **Resumo**: contas no programa, **novas contas** no período, **cobertura** (% de contas com sinal que
   pontuou; comparada em p.p. com a base da época e mostrada "sem as novas"), sinais de intenção,
   respostas genuínas e contas engajadas/quentes.
2. **Sinais de intenção** (ações de pessoas das contas; o relatório 30d do LinkedIn Ads não entra):
   série semanal por origem, tipos (o "Outro" é desmembrado pelo resumo do sinal) e últimos sinais.
3. **Jornada das contas**: etapa atual com as novas do período, temperatura, prontidão e cadência.
4. **Visão por conta**: score, intenção no período, último sinal de intenção, **mídia · frequência**,
   comitê (decisores / pessoas) e cadência.

**Frequência de mídia** (19.0.3.2.0): campos `x_abm_midia_freq`, `x_abm_midia_impressoes`,
`x_abm_midia_publico` e `x_abm_midia_periodo` em `crm.lead`, criados pelo próprio módulo
(`views/midia_fields.xml`). Frequência = impressões do LinkedIn Ads na empresa ÷ público estimado na
segmentação, sendo o público = pessoas no Brasil com os cargos da campanha no Apollo × fator de calibragem
(público total do LinkedIn ÷ total do Apollo nas contas da lista; em 27/11: 4.800 ÷ 2.732 = 1,76).
Faixas: < 2× baixa, 2–4× construindo, 4–8× ideal, > 8× saturando. Informativo: não entra no score.
Primeira carga em 27/11/2026 (impressões de 01–27/11, 22 contas), ainda manual.

## Mídia · LinkedIn Ads (19.0.4.0.0)

Seção "Mídia" (logo após o Resumo), para o especialista decidir e para reportar à liderança. Lê três modelos
criados pelo próprio módulo (`views/midia_models.xml`, modelos "manual", leitura para usuários internos):

| Modelo | O que é | Origem |
|---|---|---|
| `x_abm_midia_dia` | dia × campanha: investimento, impressões, cliques, LP, formulário, engajamento, vídeo | aba `diario_campanha` |
| `x_abm_midia_empresa` | semana × empresa (impressões, cliques), casada com a conta pelo "Nome no LinkedIn" | aba `empresas_abm` |
| `x_abm_midia_segmento` | período × frente × senioridade / função / cargo | adAnalytics com pivôs MEMBER_* |

Carga: `python atualizar_midia_abm.py --planilha <export.xlsx> [--cargos <cargos.json>] --aplicar` (upsert por
`x_name`, rodar de novo só atualiza). Primeira carga em 27/11/2026: 190 dias × campanha (21/09–26/11, R$ 23.128),
96 empresas da semana 17–23/11 (28 casadas com contas ABM) e 150 linhas de público (21/09–26/11).

O que a seção mostra, com filtro de **frente** (Comitê · Sétima = campanhas de comitê das contas ABM; Educação ·
BrandSpot = `[Comite] - Educação`, que mira contas do ABM BrandSpot; Todas):

1. KPIs com variação contra o período anterior: valor investido, CPM, CTR, CPC, frequência média das contas
   (impressões ÷ público estimado, medição `x_abm_midia_*`) e retenção de vídeo (até o fim ÷ views de 2s).
2. **Leitura para decisão**: regras que viram frases para o board (senioridade de quem vê, dispersão de CPM entre
   campanhas, retenção do vídeo, cobertura das contas, contas aquecidas sem cadência, mídia sem conversão, empresas
   do setor impactadas fora da lista).
3. Investimento por semana com CPM, funil de retenção (impressão → view 2s → fim) e ação gerada (engajamento,
   cliques, LP, formulário, leads).
4. Tabela de campanhas (investimento, CPM, CTR, CPC, engajamento, retenção, formulário).
5. Público: senioridade agrupada em decisores / gerência / execução, funções e top 12 cargos (coleta pontual,
   não segue o filtro de período).
6. Mídia por conta ABM: distribuição por faixa de frequência e tabela com a **próxima ação de mídia** (sem entrega →
   incluir na lista; < 2× ampliar; 2–4× manter; 4–8× acionar cadência se a conta não está em contato; > 8× trocar
   criativo/reduzir verba).

Fora do painel por decisão de 27/11/2026: nível LinkedIn Ads por conta e a "Frequência"
(`x_abm_exposicao` = impressões pagas da empresa inteira ÷ pessoas do comitê no CRM, que infla o número).

## Instalar / atualizar

Odoo Online não aceita Python em módulos importados; este só tem XML e assets.

```bash
python setima_resultados/scripts/deploy.py --modulo=abm_setima_dashboard            # plano
python setima_resultados/scripts/deploy.py --modulo=abm_setima_dashboard --aplicar  # importa e confere os bundles
```

Ou, em **Apps → Importar módulo** (modo desenvolvedor), envie o zip marcando
"Forçar init" para atualizar. Também dá para importar pela API (`base.import.module`,
campos `module_file` + `force`, método `import_module`) com uma chave de administrador.
