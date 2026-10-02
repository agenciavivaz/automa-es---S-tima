# ABM Sétima (equipe 20) — regras do processo

Estado em 2026-10-02. Fotografia da configuração antes/depois em
`abm/backup/` (código das automações, rotina diária, campos e parâmetros).

## Início
- Parâmetro `abm.inicio = 2026-10-05`: nenhuma tarefa nasce com data anterior.
- Rotina **ABM · Fila de preparação** ativa, primeira execução 05/10 às 07h (BRT).
- Automações ativas: A1–A4, A6–A13, A15, A16.
- **Desligadas até os e-mails E1–E4 saírem do rascunho:** A5 (início da
  cadência) e A14 (onda 2). Ao ligar, nada mais precisa mudar.

## Fila de preparação (diária, dias úteis)
- Libera **4 contas/dia** (`abm.preparacao_contas_dia`), freio se a SDR tiver
  **10+** tarefas ABM vencidas/hoje (`abm.preparacao_limite_pendentes`).
- Ordem: tier → score (quem já engaja vai antes) → força do comitê → nome.
- Força com teto: 3 × mín(decisores, 2) + mín(influenciadores, 4) — máx. 10,
  para comitê grande não passar na frente só pelo volume.
- Tarefas, **todas no dia da liberação**: Validar comitê · LinkedIn – seguir e
  interagir · Definir trilha (configurador + uso de 3D; só se a trilha estiver
  "a definir"). Dossiê não é pré-requisito.
- Conta que fica Engajada antes de passar pela fila (A2/A3) recebe as mesmas
  tarefas de preparação junto com "Iniciar cadência".

## Score (soma dos sinais ativos; Fria < 30 ≤ Engajada < 60 ≤ Quente)
| Sinal | Pontos |
|---|---|
| Cadastro: formulário da LP, Lead Gen ou lead magnet | 60 |
| Braço erguido (quer saber mais, pediu material, aceitou reunião) | 60 |
| Resposta genuína sem interesse claro (dúvida, encaminhou, "agora não") | 30 |
| Ligação com conversa | 30 |
| Reagiu/comentou post · conexão aceita · visitou cases/lead magnet/contato | 15 |
| Visita ao site (Apollo) | 10 |
| Resposta automática / "recebido" · negativa · a classificar | 0 |
| LinkedIn Ads (relatório 30 dias) | 0–30, ver abaixo |

Sinais expiram em 30 dias (A13).

### LinkedIn Ads
`atualizar_score_linkedin_ads.py` lê o CSV de **Empresas** do Campaign
Manager (Last 30 days) e grava um sinal por conta que **substitui** o da semana
anterior (foto de 30 dias, não acumula). Pontos: nível de engajamento do
LinkedIn (Very Low 0 · Low 5 · Medium 10 · High 20 · Very High 25) +
interações (cliques + engajamentos pagos e orgânicos: 1–9 → 5, 10–29 → 10,
30+ → 15) + exposição (impressões pagas ÷ pessoas no comitê, mín. 10: ≥2 → 5,
≥4 → 10). Teto 30: mídia sozinha deixa a conta no máximo Engajada.

Rotina: tarefa semanal do Diego ("ABM · Relatório LinkedIn Ads (Claude Code)")
→ exporta o CSV e envia no Claude Code, que roda:

```bash
python atualizar_score_linkedin_ads.py relatorio.csv            # simula
python atualizar_score_linkedin_ads.py relatorio.csv --aplicar  # grava
```

### Respostas (e-mail e DM)
- E-mail recebido numa conta (A10): resposta automática, ausência ou só
  "recebido"/"ok, obrigado" vira sinal de 0 pts sem tarefa; convite de agenda
  aceito ("Aceito:") vira braço erguido (60) com tarefa de confirmar; o resto
  entra como "a classificar" (0) com tarefa para a SDR mudar o tipo.
- DM no LinkedIn/WhatsApp: a SDR registra o sinal com o tipo de resposta.
- Conta Quente (A4): se veio de cadastro, segue a tarefa de contato em 1h do
  formulário; se veio de braço erguido, tarefa "responder e agendar"; senão,
  ligação + WhatsApp para o comitê.

## Asset
Conteúdo de alto valor personalizado (ex.: lead magnet adaptado, estudo do
configurador da conta, demo 3D). Produção pedida ao gestor quando o decisor
aceita a conexão (A11); quando a URL é preenchida, a SDR recebe a tarefa de
enviar por mensagem no LinkedIn aos decisores conectados (A16).
