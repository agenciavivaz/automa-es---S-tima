# Inbound Sétima · Relatório de resultados v2 (módulo importado no Odoo)

Revisão do Dashboard Inbound conforme o PRD v1.1. Mesmo mecanismo da v1 (`inbound_setima`):
tela OWL (`ir.actions.client`, tag `vivaz_inbound_dashboard_v2`) que lê o CRM ao vivo com a
sessão de quem vê. A v1 não é alterada.

- **Menu:** CRM → Inbound Sétima → **Dashboard v2** (só Administrador até a aprovação).
- **Configurações do relatório** (só Administrador): comentários do analista, apelidos de
  campanha, metas por etapa e ajustes (`acumulado_desde`).
- **Código:** `static/src/calc.js` (cálculo puro, também usado na reconciliação),
  `data.js` (leituras), `dashboard.js/.xml/.scss` (tela).

Deploy, backup, reconciliação e documentação: pasta `inbound_v2/` na raiz do repositório
(`ARQUITETURA.md`, `CHANGELOG.md`, `RECONCILIACAO.md`).

```bash
python inbound_v2/scripts/deploy_v2.py            # plano
python inbound_v2/scripts/deploy_v2.py --aplicar  # importa (idempotente)
python inbound_v2/scripts/reconciliar.py          # CRM × dashboard, diferença tolerada 0
```
