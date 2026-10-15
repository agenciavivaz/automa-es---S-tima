# Inbound Sétima · Relatório de resultados v2 (módulo importado no Odoo)

Revisão do Dashboard Inbound conforme o PRD v1.1. Mesmo mecanismo da v1 (`inbound_setima`):
tela OWL (`ir.actions.client`, tag `vivaz_inbound_dashboard_v2`) que lê o CRM ao vivo com a
sessão de quem vê. Substitui o dashboard da v1, cujo menu fica arquivado.

- **Menu:** CRM → Inbound Sétima → **Dashboard** (desde a F5; o menu da v1 foi arquivado).
- **Configurações** (só Administrador): página com comentários do analista, apelidos de
  campanha, metas por etapa e ajustes (`acumulado_desde`).
- **Código:** `static/src/calc.js` (cálculo puro, também usado na reconciliação),
  `data.js` (leituras), `dashboard.js/.xml/.scss` (tela), `config.js` (página de configurações).
- **SCSS:** o Odoo compila com libsass. Não use `min()`, `max()` nem `clamp()` (o deploy recusa).

Deploy, backup, reconciliação e documentação: pasta `inbound_v2/` na raiz do repositório
(`ARQUITETURA.md`, `CHANGELOG.md`, `RECONCILIACAO.md`).

```bash
python inbound_v2/scripts/deploy_v2.py            # plano
python inbound_v2/scripts/deploy_v2.py --aplicar  # importa (idempotente)
python inbound_v2/scripts/reconciliar.py          # CRM × dashboard, diferença tolerada 0
```
