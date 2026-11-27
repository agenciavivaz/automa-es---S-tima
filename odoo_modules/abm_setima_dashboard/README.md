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
