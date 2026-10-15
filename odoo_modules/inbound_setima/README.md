# Inbound Sétima · Pipeline (módulo importado no Odoo)

Cria **CRM → Inbound Sétima → Pipeline** (ao lado de ABM Setima), com as oportunidades
da equipe **Inbound Sétima** (`crm.team` 16) e as etapas atuais dela
(Lead → MQL → Discovery → SQL → Oportunidade Setima).

O card do kanban segue o desenho do ABM Sétima, adaptado ao inbound:

- borda colorida pelo SLA do próximo contato: vermelho = atrasado, amarelo = hoje,
  verde = agendado, cinza = sem próximo contato;
- contato/empresa, prioridade (estrelas), etiquetas e valor esperado;
- e-mail e telefone (WhatsApp) direto no card;
- próxima atividade com prazo, responsável e dias na etapa.

Sem regras, sinais ou automações: a estrutura do inbound será construída em cima deste
pipeline. Instalar/atualizar: zip da pasta e **Apps → Importar módulo** (com "Forçar init").

## Dashboard (CRM → Inbound Sétima → Dashboard)

Relatório de resultados e de trabalho para o cliente, lido ao vivo do CRM. Usa o visual do
Dashboard ABM (depende de `abm_setima_dashboard`).

- **Período:** padrão "Este mês"; também mês anterior, 7/30/90 dias, trimestre, ano, tudo e
  datas personalizadas. Comparação com o período anterior (mês contra mês nos presets mensais).
- **Base:** leads da equipe 16 (ativos e perdidos) que *entraram* no período: data de criação
  no Pipedrive para os migrados, senão a criação no Odoo.
- **Funil:** cada lead conta até a etapa mais avançada que atingiu (perdido fica na etapa em
  que foi perdido; ganho conta em todas). Mostra % do total e % de conversão etapa a etapa.
- **Quebras:** campanha, conjunto de anúncios, criativo, plataforma e etapa atual.
- **O que estamos fazendo:** notas, e-mails e atividades concluídas nos leads, classificados
  por palavra-chave (Reunião / agendamento, E-mail, WhatsApp / DataCrazy, Ligação, Pesquisa,
  Outros), por pessoa e ao longo do tempo, com o registro completo e o tempo até o 1º registro.
- **Resumo do período** em texto e botão **Exportar PDF** (impressão só do relatório).
- **Receita gerada:** soma os negócios **ganhos** de qualquer pipeline marcados com o campo
  **"Originado no Inbound"** (`x_origem_inbound`, na ficha do negócio, ao lado das etiquetas;
  filtro de mesmo nome na busca). A data do contrato é "Data de Ganho"
  (`x_studio_data_de_ganho`, aparece como "Data do contrato" quando o negócio é marcado); se
  vazia, usa a data de ganho do CRM. Esses contratos entram em todas as etapas do funil e no
  KPI de oportunidades quando a data cai no período.
- **Oportunidades em aberto:** negócios em aberto marcados como "Originado no Inbound" e os
  em aberto das contas que já fecharam pelo inbound (conta = 2º trecho do nome
  "NN/NNNN - Conta - Projeto", ou a empresa do contato), em qualquer pipeline.
- Marcados hoje: 25/0172 Hyundai – Experiência Interativa 3D (R$ 650.000, 16/03/2026) e
  26/0085 Hyundai – Filme Copa do Mundo Nacionalização (R$ 312.800, 17/08/2026).
