# Arquitetura · Relatório de resultados · Inbound Sétima (v1 e v2)

Fase 0 do PRD v1.1 (§10.1). Levantamento feito em 15/10/2026 via API JSON-2, somente leitura.

## 1. Ambiente

| Item | Valor |
|---|---|
| Versão | Odoo **19.0+e** (`/web/version` → `[19, 0, 0, "final", 0, "e"]`) |
| Hospedagem | **Odoo Online** (SaaS, domínio `*.odoo.com`) → sem módulo Python; só módulos de dados importados (`base_import_module`) |
| API | JSON-2 (`POST /json/2/<model>/<method>`, Bearer). A `ODOO_URL` da sessão vem com o sufixo `/odoo`; os scripts usam só esquema + host |
| Usuário da chave | Diego Rodrigues (uid 22), grupo Administrador (`base.group_system`) |
| Fuso / idioma | America/Sao_Paulo · pt_BR |

## 2. Como a v1 foi construída

A v1 **não** usa server actions, QWeb de relatório, crons nem `ir.config_parameter`. É uma **tela OWL**
(`ir.actions.client`) entregue por um módulo de dados importado (`inbound_setima`, 19.0.1.4.0),
que lê o CRM **ao vivo no navegador**, com a sessão de quem vê o painel (serviço `orm`).

| Registro | External ID | ID |
|---|---|---|
| Menu raiz "CRM › Inbound Sétima" | `inbound_setima.menu_root` | ir.ui.menu 838 |
| Menu "Pipeline" | `inbound_setima.menu_pipeline` | ir.ui.menu 839 |
| Menu "Dashboard" (v1) | `inbound_setima.menu_dashboard` | ir.ui.menu 840 (sem grupo) |
| Ação "Dashboard Inbound" (tag `inbound_setima_dashboard`) | `inbound_setima.action_dashboard` | ir.actions.client 1353 |
| Ação do pipeline (team 16) | `inbound_setima.action_pipeline` | ir.actions.act_window 1352 |
| Kanban / busca / form (x_origem_inbound) | `inbound_setima.view_kanban`, `view_search`, `view_search_origem`, `view_form_origem` | ir.ui.view 4679–4682 |
| Campos | `field_meta_conjunto` (`x_meta_conjunto`), `field_meta_anuncio` (`x_meta_anuncio`), `field_origem_inbound` (`x_origem_inbound`) | ir.model.fields 28868/28870/28872 |
| Assets (`web.assets_backend`) | `inbound_dashboard.js/.xml/.scss` | ir.asset 115–117, ir.attachment 7169–7171 |

- **Gráficos:** sem biblioteca. Barras empilhadas em CSS e donut em SVG inline. Isso explica por que aparecem no PDF.
- **PDF:** `window.print()` com `@media print` (esconde menus/botões). Não usa `ir.actions.report`.
- **Filtro de período:** estado interno do componente (presets + datas). **Não** ia para a URL.
- **Visual:** reaproveita as classes `.o_abm_*` do módulo `abm_setima_dashboard`.
- **Crons/automações:** nenhum ligado ao dashboard. As automações existentes (`ABM · …`, "Alterar vendedor - Amanda") são de outros processos.
- **Backup completo:** `inbound_v2/backup/20261015/` (`registros_v1.json` com todos os 20 registros do módulo, arch das views e o JS/XML/SCSS **publicado**, idêntico ao do repositório). Script: `inbound_v2/scripts/backup_v1.py`.

### Bugs de cálculo encontrados na v1 (além dos do PRD)

1. Leads perdidos que estavam na etapa **"Oportunidade" (id 17, da equipe 4, vinda da migração)** caíam em "Lead" no funil (índice não encontrado → 0). Afeta 3 leads.
2. A comparação usava o mês anterior **inteiro** para "Este mês" parcial (B6): "27 leads (–1)" comparava 01–15/10 com 01–30/09. Pela RN4, o certo é +26 (01–15/09 teve 1 lead).
3. Os contratos de outros pipelines entravam em **todas** as etapas do funil de coorte, misturando negócios fechados em março/agosto com leads de outubro.
4. Mediana do 1º contato calculada como o elemento "de cima" (`horas[floor(n/2)]`), não a mediana.

## 3. Dicionário de métricas: campos reais (§8 preenchido)

| Métrica | Definição implementada | Campos / modelo reais |
|---|---|---|
| Lead inbound (RN1) | `crm.lead` com `team_id = 16` (Inbound Sétima), `type = opportunity`, ativo **ou** arquivado. Mesmo critério da v1 | `team_id`, `type`, `active` |
| Leads no período | data de entrada no período (início 00:00 e fim 23:59:59 em America/Sao_Paulo, convertidos para UTC) | `x_pipedrive_add_time` se preenchido (migrados), senão `create_date`. Hoje nenhum lead do time 16 tem `x_pipedrive_add_time`, então na prática vale `create_date` |
| Etapa alcançada (funil/MQL/SQL+) | **etapa atual** do lead (método da v1, sem histórico); ganho conta em todas; perdido fica na etapa em que foi perdido. Etapas de outra equipe são casadas por nome | `stage_id` → `crm.stage` do time 16: Lead (68), MQL (51), Discovery (64), SQL (52), Oportunidade Setima (77); `won_status` |
| MQL | etapa atual ∈ {MQL, Discovery, SQL, Oportunidade Setima, Oportunidade} **ou** `won_status = won` | idem |
| SQL+ | etapa atual ∈ {SQL, Oportunidade Setima, Oportunidade} ou ganho | idem |
| Reunião agendada (RN5) | `calendar.event` com `opportunity_id` = lead inbound criado no período + `mail.activity` com `activity_category = meeting` criada no período (sem evento ligado, para não contar duas vezes) | `calendar.event.opportunity_id/create_date`, `mail.activity.activity_category/calendar_event_id` |
| Reunião realizada | evento ativo com `start` no período e já passado + atividade Reunião concluída (`active = False`, `date_done`) | idem |
| Convite para agendar | nota/e-mail cujo texto pede agenda (`agenda`, `agendar`, `marcar(mos)`, `reunião`, `disponibilidade`…). É tentativa e nunca vira reunião | `mail.message.body` |
| Tempo até 1º contato (B8, D1) | mediana em horas corridas entre a entrada e o 1º toque de saída: mensagem classificada como WhatsApp/DataCrazy, e-mail, ligação, convite ou reunião, ou atividade concluída (exceto pesquisa). Notas de pesquisa/“outros” não contam | `mail.message` (`message_type` comment/email, `date`, `body`), `mail.activity.date_done` |
| Receita no período (RN2) | soma de `expected_revenue` dos ganhos com "Originado no Inbound", qualquer pipeline, com data do contrato no período | `x_origem_inbound`, `won_status = won`, data = `x_studio_data_de_ganho`, senão `date_closed` |
| Receita acumulada (A5, D5) | mesmo critério, sem período, desde `acumulado_desde` (vazio = 1º contrato: 16/03/2026) | idem + `x_vivaz_inb_ajuste` |
| Leads tocados (B7) | leads inbound com ≥ 1 ação no período (qualquer data de entrada), separados em novos (da coorte) e anteriores | `mail.message.res_id`, `mail.activity.res_id`, `calendar.event.opportunity_id` |
| Cobertura da automação (B9) | leads do período com a tag DataCrazy (posta pelo `sincronizar_odoo_datacrazy.py` após o envio) | `tag_ids` ∋ `crm.tag` "DataCrazy" |
| Parado | lead do período aberto, sem mudar de etapa há > 7 dias e sem atividade com prazo ≥ hoje | `date_last_stage_update`, `mail.activity.date_deadline` |
| Sem sucesso | texto com `tentativa`, `sem contato`, `não atend`, `sem resposta`, `inválid` (critério da v1) | `mail.message.body` |
| Expansão (RN3) | fora de todos os blocos: só entram leads do time 16 e receita com flag. A Hyundai Motor Brasil (id 21222, ABM Setima, "Cliente – expansão") não tem a flag | — |

**Dado observado (impacta a leitura):** os leads inbound não têm **nenhuma** `mail.activity` nem `calendar.event`.
Todo o trabalho da operação está em **notas** da Amanda. Por isso "Reuniões" = 0 enquanto as reuniões não forem
registradas na agenda do Odoo (ver pendências no CHANGELOG).

## 4. Como a v2 foi construída

Mesmo mecanismo da v1, em registros novos, módulo importado **`vivaz_inbound`** (19.0.2.0.0), que depende de `inbound_setima` (sem alterá-lo).

```
navegador (sessão do usuário)
  └─ ir.actions.client "vivaz_inbound_dashboard_v2"
       dashboard.js  ── OWL: estado, URL (?period=&view=), navegação, PDF
         ├─ data.js  ── leituras ORM limitadas ao período + comparação (search/search_read)
         └─ calc.js  ── funções PURAS: período/RN4, classificação/RN5, funil, KPIs, leitura, acumulado
                         (o mesmo arquivo roda no Node para a reconciliação)
       dashboard.xml / dashboard.scss ── template e CSS puro escopado em .o_vin
```

| Registro v2 | External ID | ID |
|---|---|---|
| Ação cliente (tag `vivaz_inbound_dashboard_v2`) | `vivaz_inbound.action_dashboard_v2` | ir.actions.client 1358 |
| Menu **CRM › Inbound Sétima › Dashboard v2** (só Administrador) | `vivaz_inbound.menu_dashboard_v2` | ir.ui.menu 841 |
| Menu **Configurações do relatório** (só Administrador) | `vivaz_inbound.menu_config` (+ `menu_config_comentario/campanha/meta/ajuste`) | ir.ui.menu 842–846 |
| Modelos §9.4 | `model_comentario` (`x_vivaz_inb_comentario`), `model_campanha` (`x_vivaz_inb_campanha`), `model_meta` (`x_vivaz_inb_meta`), `model_ajuste` (`x_vivaz_inb_ajuste`) | ir.model 1220/1222/1224/1226 |
| Acessos | leitura para Usuário interno; comentário editável por Gerente de Vendas e Administrador; demais só Administrador | 8 ir.model.access |
| Telas de configuração | `view_comentario_list/form`, `view_campanha_list`, `view_meta_list`, `view_ajuste_list` + 4 act_window | ir.ui.view 4683–4687, act_window 1354–1357 |
| Dados iniciais (`noupdate`) | 6 apelidos de campanha com cor fixa; ajuste `acumulado_desde` vazio (D5) | x_vivaz_inb_campanha / x_vivaz_inb_ajuste |
| Assets | `calc.js`, `data.js`, `dashboard.js/.xml/.scss` em `web.assets_backend` | ir.asset 118–122 |

Total: **60 registros** com external ID `vivaz_inbound.*`.

### Deploy e scripts (`inbound_v2/scripts/`)

| Script | Função |
|---|---|
| `backup_v1.py` | backup da v1 (somente leitura) |
| `deploy_v2.py [--aplicar]` | zip do módulo → `base.import.module` (force). Idempotente: upsert por external ID. Confere instalado, duplicados = 0 e v1 sem alteração (`write_date`). Rodado 4× nesta sessão: sempre 60 registros |
| `valores_dashboard.mjs` | roda `calc.js` + `data.js` do módulo no Node, contra o CRM real |
| `reconciliar.py` | consultas independentes (`search_count`/`read_group`) × dashboard, para 3 períodos → `RECONCILIACAO.md` |
| `testes_calc.mjs` | testes das funções puras (RN4, RN5, RN6, B1, formatação) |

Dependência dos scripts Node: `cd inbound_v2 && npm install` (luxon). Proxy da sandbox: `NODE_USE_ENV_PROXY=1`.

### Escritas feitas no Odoo
Só os registros técnicos do módulo `vivaz_inbound` e os dados de configuração do §9.4 (6 apelidos + 1 ajuste).
**Nenhuma escrita em `crm.lead`, `mail.message`, `res.partner` ou outro dado de negócio.** A v1 (`inbound_setima`) não foi tocada.
