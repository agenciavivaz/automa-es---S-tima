# Dashboard Inbound Sétima · v2

- `ARQUITETURA.md`: Fase 0 (ambiente, como a v1 foi feita, campos reais do §8) e arquitetura da v2.
- `CHANGELOG.md`: cada item A/B/L/RN/D do PRD → o que foi feito, além das pendências.
- `RECONCILIACAO.md`: última reconciliação (Este mês, Mês anterior, Este ano).
- `backup/20261015/`: backup completo da v1 publicada.
- `scripts/`: `backup_v1.py`, `deploy_v2.py`, `reconciliar.py`, `valores_dashboard.mjs`, `testes_calc.mjs`.

Preparação: `pip install -r requirements.txt` e `cd inbound_v2 && npm install`.
Os scripts Node usam `NODE_USE_ENV_PROXY=1` quando há proxy de saída.
Credenciais: `ODOO_URL`, `ODOO_DB` e `ODOO_API_KEY` do ambiente (nunca gravadas).
