# ABM Sétima · Dashboard (módulo importado no Odoo)

Painel estratégico em **CRM → ABM Setima → Dashboard** (logo abaixo de "Atividades ABM").
É uma tela OWL (`ir.actions.client`, tag `abm_setima_dashboard`) que lê **ao vivo**, com a
sessão do próprio usuário, os dados da equipe ABM Setima (`crm.team` 20):

- `crm.lead`: score, faixa, tier, etapa, cadência, comitê e exposição de cada conta;
- `x_abm_sinal`: sinais no período (linha do tempo por origem, tipos, últimos sinais);
- `mail.activity` com tipo `ABM · …`: abertas (hoje / no prazo / atrasadas) e concluídas
  (arquivadas, `date_done`) no período.

Nada é gravado: o painel só lê.

## O que mostra

- **Seletor de período**: 7 dias, **30 dias (padrão)**, 90 dias, este mês, mês anterior, tudo
  e personalizado (datas). O padrão de 30 dias é a mesma janela do relatório LinkedIn Ads e da
  expiração dos sinais que formam o score. Filtro por tier.
- **KPIs** com variação contra o período anterior de mesma duração.
- Sinais ao longo do tempo (empilhado por origem), origem dos sinais, tipos de sinal.
- Jornada das contas por etapa, temperatura (fria < 30, engajada 30–59, quente ≥ 60), cadência e tiers.
- **Onde agir agora**: engajadas/quentes sem cadência, sem sinal há 21+ dias, comitê sem
  decisor e contas com atividade atrasada.
- Execução das atividades por tipo, agenda dos próximos 7 dias e tabela por conta (ordenável).

Tudo é clicável e abre a lista/ficha correspondente no Odoo.

## Instalar / atualizar

Odoo Online não aceita Python em módulos importados; este só tem XML e assets.

```bash
cd odoo_modules && zip -r /tmp/abm_setima_dashboard.zip abm_setima_dashboard
```

Depois, em **Apps → Importar módulo** (modo desenvolvedor), envie o zip marcando
"Forçar init" para atualizar. Também dá para importar pela API (`base.import.module`,
campos `module_file` + `force`, método `import_module`) com uma chave de administrador.
