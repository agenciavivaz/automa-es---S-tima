# CHANGELOG · Relatório de resultados · Inbound Sétima v2

Versão do módulo: `vivaz_inbound` 19.0.2.1.0 · publicado em 15/10/2026 · PRD v1.1.
F0–F4 executadas. **F5 executada em 15/10/2026 com aprovação do Diego** (ver "19.0.2.1.0" abaixo).

## 19.0.2.1.0 — virada (F5) e ajustes pedidos na validação

- **Um só dashboard:** o menu "Dashboard" da v1 (`inbound_setima.menu_dashboard`, id 840) foi **arquivado** (`active = False`, não excluído; ação, assets e código da v1 continuam no banco e em `backup/20261015/`). A v2 passou a ser **CRM › Inbound Sétima › Dashboard**, visível para todos, como era a v1.
- **Largura total:** o relatório ocupa a tela inteira (padding de 24 px). O PRD previa um container de 1440 px (L1), mas a largura total foi um pedido do Diego.
- **Menu mais enxuto:** um único item **Configurações** (só Administrador) abre uma página com as quatro opções em cards (Comentários do analista, Apelidos de campanha, Metas por etapa, Ajustes), com a quantidade de registros de cada uma. Os quatro submenus antigos ficaram inativos.
- **Incidente corrigido (≈ 5 min):** a primeira publicação desta versão usou `min(100%, 420px)` no CSS. O libsass do Odoo não aceita essa sintaxe e a compilação do CSS do backend falhou. Corrigido e republicado em seguida; o CSS voltou a compilar sem erro. Prevenção: `deploy_v2.py` agora recusa `min()/max()/clamp()` no SCSS e, depois de importar, compila o CSS do backend no servidor e falha se houver erro.
- **Como desfazer a virada:** reativar o menu 840 e remover do `views.xml` os registros `inbound_setima.menu_dashboard` e `menu_dashboard_v2` (grupos), depois rodar o deploy.

Legenda: ✅ feito · ⚠️ feito com ressalva · ⏸ não feito (motivo)

## Ajustes solicitados (P0)

| # | Status | O que foi feito |
|---|---|---|
| A1 | ✅ | Registro de atividades mostra 10 itens, com botão **"Carregar mais (+10)"**, contador "mostrando 10 de N" e "Ver todas no Odoo" (lista de `mail.message` dos leads inbound no período). Os chips de tipo continuam e reiniciam a paginação em 10. Até 100 itens vêm de uma vez e são paginados no cliente, sem nova chamada. Acima de 100, o link final vira "Ver as N no Odoo". Separadores Hoje/Ontem/dd/MM (P1) incluídos. |
| A2 | ✅ | Seção "Oportunidades em aberto" removida, assim como a busca por contas relacionadas e qualquer menção no texto. A Hyundai Motor Brasil (ABM, "Cliente – expansão") não aparece em nenhum bloco (RN3). O espaço passou para o card fixo do acumulado. |
| A3 | ✅ | O "Resumo do período" em bullets virou o bloco **"Leitura do período"**, abaixo dos KPIs, com 3 colunas: Destaques · Pontos de atenção · Próximos passos · Vivaz. As regras D1–D3 e A1–A4 são determinísticas, com no máximo 3 itens por coluna, e o texto é montado por templates `tpl()` com `fmt*` pt-BR. O comentário do analista fica no modelo `x_vivaz_inb_comentario`, por período, com autor e data. "Editar comentário" abre o formulário em diálogo para Gerente de Vendas/Admin. Sem comentário: editores veem "Comentário do analista pendente"; leitores e o PDF escondem a coluna e as outras duas se expandem. |
| A4 | ✅ | "Situação e saúde da base" ocupa 4 col. ao lado do funil (8 col.), com a mesma altura (grid `stretch`: 504 px × 504 px a 1440 px). Donut de 120 px com a legenda ao lado, só etapas > 0. Indicadores: parados > 7 dias, sem próxima atividade, sem nenhum contato e perdidos (com o motivo mais frequente). Cada indicador abre a lista dos leads no Odoo e mostra até 5 nomes no tooltip. |
| A5 | ✅ | Card **"Receita acumulada do processo inbound"** fixo no topo à direita. Ignora o filtro e traz o rótulo "📌 ACUMULADO DO PROCESSO", fundo verde-claro, "desde 16/03/2026 · negócios originados no inbound, em qualquer pipeline", R$ 962.800, "2 contratos · ticket médio R$ 481,4 mil" e a lista dos contratos com link. A linha "No período (…)" respeita o filtro e fica verde quando há valor, com o badge "novo no período" no contrato. Texto "nenhum contrato fechado no período selecionado" removido. Aparece no Board e no PDF. Testado: mesmo valor em Este mês, 7 dias, Mês anterior, Este ano, Tudo e Personalizado sem dados (jan/2027). |

## Correções de métrica (P0)

| ID | Status | O que foi feito |
|---|---|---|
| B1 | ✅ | O gerador de texto foi reescrito com `tpl("{x} …", {…})` e `fmtInt/fmtPct/fmtBrl/fmtHoras/fmtIntervalo`. Teste automático do regex do PRD (`[a-zA-Z0-9)][(]` e `,[^ \d]`) em todos os textos gerados nos 3 períodos: 0 ocorrências (`RECONCILIACAO.md`, `testes_calc.mjs`). |
| B2 | ✅ | Ver A5. A receita só aparece no card fixo, e a receita do período é uma linha secundária dentro dele. Nenhum outro bloco mostra receita: a coluna "Receita" da tabela por campanha (§7.6) **não** foi incluída por causa do critério de aceite do §12 / B2 (conflito no PRD, prevaleceu o aceite). |
| B3 | ✅ | RN3: só entram leads do time 16 e receita com a flag `x_origem_inbound`. A expansão Hyundai (id 21222) não tem a flag. Os contratos de outros pipelines também deixaram de inflar o funil de coorte. |
| B4 | ✅ | Tipos separados: **Convite para agendar** (texto, tentativa) e **Reunião agendada/realizada** (só `calendar.event` ou atividade de categoria Reunião). Palavra-chave nunca gera reunião (teste RN5). Resultado hoje: 9 convites em outubro e 0 reuniões, porque nenhuma reunião está registrada na agenda do Odoo. |
| B5 | ✅ | Chips de conversão em cinza. Verde/vermelho só com meta em "Metas por etapa" (modelo criado, vazio — D2). |
| B6 | ✅ | RN4: Este mês 01–15/10 × 01–15/09; Mês anterior × o mês antes dele; 7/30/90 dias e Personalizado × janela anterior de mesma duração; Trimestre/Ano × mesmos dias do anterior; Tudo sem delta. O intervalo comparado aparece no cabeçalho e no tooltip do delta. Delta em % só com base anterior ≥ 10; abaixo disso, absoluto e neutro. |
| B7 | ✅ | Operação mostra "Leads tocados no período: 36 (26 novos + 10 anteriores)". O PRD estimava 27 + 9; o CRM mostra que 1 dos 27 novos ainda não teve ação. |
| B8 | ✅ | Renomeado para **"Tempo até 1º contato"**: só toques de saída (WhatsApp/DataCrazy, e-mail, ligação, convite, reunião, atividade concluída), sem notas de pesquisa. Mediana verdadeira, com distribuição ≤1 h · 1–24 h · >24 h · sem contato. |
| B9 | ✅ | "% enviados ao DataCrazy" saiu do card de leads e virou "Cobertura da automação: 27/27 (100%)" na Operação. |

## Regras de negócio

| ID | Status | Observação |
|---|---|---|
| RN1 | ✅ | Mesmo critério da v1 (time 16, oportunidade, ativos + arquivados), documentado no código e no glossário. |
| RN2 | ✅ | Receita só com a flag "Originado no Inbound", em qualquer pipeline. |
| RN3 | ✅ | Ver B3. |
| RN4 | ✅ | Ver B6 (testes unitários cobrem os 5 casos). |
| RN5 | ✅ | Ver B4. |
| RN6 | ✅ | Todos os limites em America/Sao_Paulo e convertidos para UTC nas consultas (01/10 00:00 = 03:00 UTC, testado). |

## Layout, design e navegação

| ID | Status | O que foi feito |
|---|---|---|
| L1 | ⚠️ | Primeiro com `max-width: 1440px`; na 19.0.2.1.0 passou a ocupar a **largura total**, por pedido do Diego. Mantidos o padding de 24 px, o gap de 16 px e os 24 px entre seções. |
| L2 | ✅ | Ordem: Acumulado fixo + KPIs → Leitura → Funil/Saúde → Aquisição → Operação → Atividades → rodapé. |
| L3 | ✅ | Linhas do funil com 36 px, etapas zeradas em cinza e sem chip entre zeros. Nota de maturação quando o período tem < 30 dias ou termina hoje. |
| L4 | ✅ | Cards neutros (branco, borda cinza, raio 12 px), sem borda colorida no topo. A cor fica para semântica (bom/ruim/atenção) e para a paleta de campanhas. Exceção intencional do PRD: o card do acumulado. |
| L5 | ✅ | Barra de seções sticky com âncoras, rolagem suave e seção ativa. Toggle **Completo / Board**, persistido na URL (`?period=…&view=board`, mais `from/to` no Personalizado). |
| L6 | ✅ | Texto limitado a 2 linhas com "ver mais". Blocos com CNPJ, razão social, endereço ou capital social viram "Dados da empresa registrados" + "ver mais". O HTML é removido. |
| L7 | ✅ | Título `Empresa · Contato` (empresa = `partner_name` → `name`; contato = `contact_name` → e-mail), sem repetir quando são iguais. Clique abre o lead. |
| L8 | ✅ | Modelo **Apelidos de campanha** (nome UTM → apelido + cor), editável sem código, com 6 campanhas pré-cadastradas. Campanhas sem apelido recebem um automático (remove os `[…]`). A cor é a mesma no gráfico e na tabela, e o nome completo fica no tooltip. |
| L9 | ✅ | ⓘ com a definição em cada KPI, no funil e nos mini-indicadores. Glossário (modal) no rodapé com as definições do §8. |
| L10 | ✅ | Rodapé "Relatório preparado pela Vivaz para a Sétima · fonte: CRM Odoo · atualizado às HH:MM". |

## Demais itens do §7

- §7.1: os chips de período foram mantidos e o filtro/modo fica na URL. ✅
- §7.6: toggle Leads | MQLs, todos os dias no eixo X, legenda com totais, abas mantidas, colunas `Leads (barra) · MQL · % MQL · SQL+ · Ganhos · Perdidos`, linha Total, ordenação por clique e colunas **Investimento · CPL · Custo/MQL** reservadas e ocultas (D3). ✅
- §7.7: mini-indicadores, gráfico diário por tipo e tabela com `Total` e `Sem sucesso`. ⚠️ Mantive o tipo **Ligação**, que não está na lista do PRD: há várias tentativas de ligação pelo API4COM nas notas, e jogá-las em "Outros" esconderia trabalho da operação.
- §7.10: o PDF usa `window.print()` como na v1. O botão "Exportar PDF" abre um menu com **Board (recomendado)** e Completo. Saída em A4 paisagem, sem filtros, barra ou botões, com `break-inside: avoid` nos cards, títulos de seção sem órfãos e gráficos visíveis (são CSS/SVG). Atividades sempre ocultas no PDF. ✅
- Estados vazios: todas as seções têm uma frase (testado com 01–10/01/2027). ✅

## Decisões em aberto (§14) — padrão aplicado

| ID | Padrão aplicado |
|---|---|
| D1 | SLA em **horas corridas**. |
| D2 | **Sem metas**: cores neutras. Modelo "Metas por etapa" criado vazio; ao cadastrar (ex.: etapa `MQL`, 20%), o chip do funil passa a ficar verde ou vermelho. |
| D3 | Investimento na fase 2: colunas reservadas e ocultas. |
| D4 | O modo Completo fica disponível para todos que acessam o menu; Board é só um toggle. |
| D5 | Data do 1º negócio inbound ganho (16/03/2026). Configurável em *Configurações do relatório › Ajustes › acumulado_desde*. |
| D6 | Expansões não contam (RN3). |

## Decisões técnicas a registrar

1. **Funil por etapa atual, não por histórico.** É o método da v1 e o que pode ser reconciliado com `search_count`. O histórico (`mail.tracking.value`) mostra 18 movimentos MQL → Lead, 4 Discovery → MQL e 2 SQL → MQL na base. No método atual, um lead que voltou de etapa conta na etapa para onde voltou. A alternativa por histórico está no backlog ("funil em modo fluxo").
2. **Saúde da base calculada sobre os leads do período**, para seguir o filtro como o resto da página. Com o filtro "Tudo", vale para a base inteira.
3. **Leitura dos dados por período** (§10.3): a v1 carregava todo o histórico de leads e mensagens. A v2 consulta só o período e a comparação, mais as mensagens dos leads da coorte (para o 1º contato). A única exceção é o card fixo.
4. **SCSS em CSS puro**, sem variáveis do Odoo, e seletores sob `.o_vin`: um erro de compilação no bundle de backend afetaria todos os usuários. O bundle foi compilado no servidor e o código transpilado pelo próprio Odoo foi executado e renderizado sem erros no harness.

## Pendências e riscos

1. **Validação visual dentro do Odoo pelo Diego.** A chave de API não abre sessão web. Validei renderizando os arquivos publicados (e o JS transpilado pelo servidor) com OWL 2.8.4, a mesma versão do Odoo 19, em Chromium a 1440/1024/390 px e em PDF, contra dados reais.
2. **Reuniões = 0** é dado real: não há `calendar.event` nem atividade Reunião nos leads inbound. Para o KPI funcionar, a operação precisa agendar as reuniões pelo Odoo (botão Reunião do lead), não só anotar no chatter.
3. **1º contato depende das notas manuais.** O envio automático do DataCrazy só deixa a tag, sem data. Se o `sincronizar_odoo_datacrazy.py` postar uma nota "Enviado ao DataCrazy" com a hora do envio, o SLA passa a medir a automação também (mudança fora deste escopo).
4. **"Sem sucesso"** segue o critério da v1 (por texto). Frases como "sem retorno", "caixa postal" e "fica mudo" não entram. Sugestão: ampliar a lista depois de validar com a Amanda.
5. **Desempenho:** no Node, pela rede da sandbox, o cálculo levou 2,4–2,8 s por período, com chamadas em paralelo. No navegador, dentro do Odoo, deve ficar abaixo disso; confirmar o critério de < 2 s na validação.
6. **F5 executada em 15/10/2026:** pelo PRD, a v1 fica arquivada (não excluída) por 30 dias, até 14/11/2026.
