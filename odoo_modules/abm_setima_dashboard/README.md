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

## O que mostra (19.0.3.0.0 · leitura para o board)

O painel separa as duas naturezas de sinal:

- **LinkedIn Ads · relatório 30d** é uma *foto* semanal de cada empresa. Nunca é somado: vale a
  **última leitura** de cada conta, comparada com a primeira leitura do período.
- **Sinais de intenção** são ações de pessoas das contas (visitas, follow, formulário, respostas…).

Seções:

1. **Resumo** (uma linha de KPIs): contas no programa, **novas contas** no período, **cobertura**
   (% de contas com sinal que pontuou; compara em p.p. com a base que existia no período anterior e
   mostra o % "sem as novas"), sinais de intenção, respostas genuínas e contas engajadas/quentes.
2. **Engajamento**: nível LinkedIn Ads por conta (Muito alto → Muito baixo, sem leitura), sinais de
   intenção por tipo (o tipo "Outro" é desmembrado pelo resumo do sinal, ex.: "Visitou o perfil do
   especialista", "Visitou a página da Sétima"), série semanal por origem e últimos sinais (quem fez o quê).
3. **Jornada das contas**: etapa atual com as novas do período, temperatura, prontidão (comitê com
   decisor, comitê mapeado, aquecidas em cadência) e cadência.
4. **Visão por conta**: score, nível LinkedIn, frequência (impressões por pessoa do comitê), intenção no
   período, último sinal de intenção, comitê (decisores / pessoas) e cadência. Contas novas com selo.

Saíram por serem operacionais ou repetidas: leitura do período, card "Programa hoje", "Onde agir agora",
"Execução" (atividades e agenda) e o KPI de atividades atrasadas. O painel não lê mais `mail.activity`.

Tudo é clicável e abre a lista/ficha correspondente no Odoo.

## Instalar / atualizar

Odoo Online não aceita Python em módulos importados; este só tem XML e assets.

```bash
python setima_resultados/scripts/deploy.py --modulo=abm_setima_dashboard            # plano
python setima_resultados/scripts/deploy.py --modulo=abm_setima_dashboard --aplicar  # importa e confere os bundles
```

Ou, em **Apps → Importar módulo** (modo desenvolvedor), envie o zip marcando
"Forçar init" para atualizar. Também dá para importar pela API (`base.import.module`,
campos `module_file` + `force`, método `import_module`) com uma chave de administrador.
