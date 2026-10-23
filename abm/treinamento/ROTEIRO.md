# Treinamento ABM Sétima · contas [TREINO]

Sete contas fictícias no pipeline **CRM → ABM Setima**, cada uma numa etapa. Elas são
levadas até lá pelas **automações reais**, então as tarefas, notas e sinais são
iguais aos do dia a dia. Nada envia e-mail. Contatos terminam em "(treino)" e usam
e-mails `@….treino.invalid`.

| Card | Etapa | O que aconteceu (automação) | Tarefas que aparecem |
|---|---|---|---|
| 1 · Aurora Motors | Alvo | Conta-alvo na fila | nenhuma |
| 2 · Boreal Caminhões | Aquecendo | Visitou o site em Alvo → **A20** tira da fila | Amanda: seguir e curtir (lista do comitê) · Definir trilha |
| 3 · Cometa Máquinas | Aquecendo · *Pronta p/ abordagem* | 14 dias com exposição ≥ 4 → **A17** | Amanda: conectar decisores |
| 4 · Delta Agrícola | Engajada | Reagiu a post + visitou cases = 30 pts → **A2** | Amanda: Iniciar cadência (checklist) |
| 5 · Estrela Ônibus | Em cadência | Checklist feito → **A5** · decisor aceitou a conexão → **A11** | Amanda: 8 toques × 3 pessoas (D1 a D18) + mensagem pós-conexão · Diego: asset personalizado |
| 6 · Fênix Motos | Conversa | Braço erguido em cadência → **A4** → **A6** para a cadência | Amanda: responder e agendar |
| 7 · Gama Implementos | Aquecendo | 21 dias sem engajar → **A3** | Diego: revisar a conta |

## Exercícios (no Odoo, como no dia a dia)

1. **Card 2 · Preparação.** Abrir "seguir e curtir" e ver a lista de decisores. Em
   "Definir trilha", preencher o campo **Trilha** e marcar a tarefa como feita.
2. **Card 3 · Conexão antecipada.** No contato Marina Duarte, mudar **Conexão LinkedIn**
   para *Enviado*. Depois para *Aceito*: a A11 cria o sinal (+15) e a mensagem pós-conexão.
3. **Card 4 · Iniciar cadência.** Seguir o checklist da tarefa: trilha, dossiê, até 3
   pessoas com **Na cadência**. Marcar como feita e **mover para Em cadência**: a A5
   cria na hora os 8 toques para cada pessoa.
4. **Card 5 · Rotina da cadência.** Abrir o E1 (D1): ler direcionamento, ângulo e
   checklist. **Não enviar**: marcar como feita. Exercícios extras:
   - registrar uma resposta: aba Sinais → novo sinal "Resposta recebida (a classificar)" e
     depois classificar o tipo;
   - preencher **Asset (URL)** com qualquer link: a A16 cria "Enviar asset" para o decisor
     conectado;
   - marcar **Opt-out** em um contato: a A12 cancela as tarefas dele.
5. **Card 6 · Conversa.** Ver que a cadência foi cancelada sozinha. Concluir "responder e
   agendar" e **mover para Reunião agendada**: a A8 cria "Preparar reunião".
6. **Card 7 · Revisão do gestor.** Decidir: manter, trocar abordagem ou **mover para
   Nutrição** (a A6 encerra o que estiver aberto).

Os exercícios podem ser repetidos: `limpar` e `criar` de novo recriam tudo do zero.

## Comandos (rodados pelo Claude Code ou por quem tem a chave da API)

```bash
python abm/treinamento/treino_abm.py criar --apply        # cria os 7 cards
python abm/treinamento/treino_abm.py criar 4 5 --apply    # só alguns cenários
python abm/treinamento/treino_abm.py status               # etapa, score e tarefas de cada card
python abm/treinamento/treino_abm.py limpar --apply       # apaga contas, contatos, sinais e tarefas
```

## Cuidados

- **Antes do primeiro uso:** criar a etiqueta "ABM · Treinamento" (parâmetro
  `abm.tag_treino_id`) e aplicar `fila_preparacao_com_treino.py` na rotina
  "ABM · Fila de preparação". Sem isso, as tarefas de treino contam no freio da Amanda
  e travam a liberação de contas reais.
- Enquanto existirem, os cards de treino aparecem no pipeline, em Atividades ABM e no
  dashboard. **Rodar `limpar` no fim do treinamento.**
- Automações de tempo (A3, A13, A17, A18) também agiriam nos cards se eles ficassem
  semanas no sistema: mais um motivo para limpar.
