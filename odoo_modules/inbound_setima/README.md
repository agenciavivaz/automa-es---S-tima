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
