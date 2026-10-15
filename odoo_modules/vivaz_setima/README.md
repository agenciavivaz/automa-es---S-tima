# Sétima · Resultado comercial (módulo importado no Odoo)

Cria **CRM → Sétima** (logo depois de Inbound Sétima) com:

- **Pipeline**: oportunidades da equipe **Pipeline Sétima** (`crm.team` 4) nas telas padrão do CRM.
- **Dashboard**: tela OWL (`ir.actions.client`, tag `vivaz_setima_dashboard`) no mesmo desenho do
  Relatório Inbound, que lê o CRM ao vivo com a sessão de quem vê. Nada é gravado.

## O que mostra

- **Filtro de período** (padrão: este ano) com comparação: mês/trimestre/ano contra os mesmos dias do
  período anterior.
- **KPIs**: receita, negócios ganhos, ticket médio por projeto (com mediana), clientes atendidos (e novos),
  taxa de conversão e pipeline gerado, cada um com a variação.
- **Leitura do período** gerada por regras: destaques e pontos de atenção (queda de receita, meses sem
  ganho lançado, concentração em um cliente, perdas sem motivo, oportunidades sem valor, cobertura).
- **Acumulado do ano** fixo (não muda com o filtro), comparado com o mesmo período do ano anterior.
- **Evolução**: receita (ou pipeline gerado) mês a mês contra o ano anterior e histórico anual desde 2020.
- **Clientes e projetos**: ranking de clientes com participação e concentração; 10 maiores projetos.
- **Tipo de projeto**: receita, ticket, conversão e pipeline aberto por tipo; mix de receita.
- **Vendedores**: só aparece quando há 2+ vendedores com resultado no período.
- **Pipeline**: gerado no período e no ano, aberto por etapa (com ponderado), cobertura, ciclo de venda,
  motivos de perda e saúde (sem valor, parados 30+ dias, previsão vencida).

Tudo é clicável e abre os negócios no Odoo. Definições no **Glossário** (rodapé da tela).

## Regras

- Receita = valor esperado dos ganhos; data de ganho = "Data de Ganho", senão a do Pipedrive, senão
  `date_closed`. Entrada = criação no Pipedrive, senão `create_date`. Negócios "Teste…" ficam de fora.
- Cliente = empresa comercial do contato (`ALIAS_CLIENTE` em `calc.js` junta nomes duplicados, ex.: VW).
- **Tipo de projeto**: o CRM não tem esse campo. Vem da etiqueta `Tipo: <tipo>` no negócio, quando
  existe; senão do nome do projeto por palavra-chave (`TIPOS` em `calc.js`).

## Código, conferência e deploy

- `static/src/calc.js` (cálculo puro), `data.js` (leitura), `dashboard.js/.xml/.scss` (tela).
- SCSS: o Odoo compila com libsass. Não use `min()`, `max()` nem `clamp()` (o deploy recusa).

```bash
cd setima_resultados && npm install && cd ..
NODE_USE_ENV_PROXY=1 node setima_resultados/scripts/valores_dashboard.mjs year prev_year  # números fora do Odoo
python setima_resultados/scripts/deploy.py            # plano
python setima_resultados/scripts/deploy.py --aplicar  # importa (idempotente) e confere os bundles
```
