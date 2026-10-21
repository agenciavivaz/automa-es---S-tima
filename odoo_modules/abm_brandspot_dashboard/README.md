# ABM BrandSpot · Dashboard (módulo importado no Odoo)

Painel estratégico em **CRM → ABM BrandSpot → Dashboard**. É o mesmo painel do ABM Sétima
(`abm_setima_dashboard` v2, tag própria `abm_brandspot_dashboard`), lendo ao vivo a equipe
**ABM BrandSpot** (`crm.team` 22) e as atividades `ABM BrandSpot · …`. Nada é gravado.

Diferença: no card "Temperatura e cadência" há o bloco **Estúdio interno · tese**
(Já tem estúdio · Baixa qualidade · Indefinido · Não mapeado), clicável.

O CSS é uma cópia do da Sétima (mesmas classes `.o_vab`), para o painel não depender do
outro módulo. O menu pai `abm_brandspot.menu_pipeline` é criado por `abm_brandspot/estrutura.py`.

## Instalar / atualizar

```bash
python -m abm_brandspot.instalar_dashboard --aplicar
```

Envia o zip por `base.import.module` com "Forçar init" e confere se os bundles CSS/JS do
backend continuam compilando.
