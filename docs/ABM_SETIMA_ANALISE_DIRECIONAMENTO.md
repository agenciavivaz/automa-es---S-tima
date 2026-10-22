# ABM Sétima: análise crítica do direcionamento v0.1 + estrutura visual das atividades

> **Data:** 22/10/2026. **Analisa:** `ABM_SETIMA_DIRECIONAMENTO_ABORDAGEM.md` (rascunho v0.1).
> **Como foi feita:** cada proposta foi comparada com o **código real** das automações no Odoo 19
> (`grupo-setima.odoo.com`). O autor do rascunho não tinha esse código, então os trechos dele foram
> escritos às cegas. Aqui ficam registradas as correções e os achados novos.
> **Decisão do Diego:** o conteúdo de direcionamento (seção 2 do rascunho) **fica como está**. Esta análise
> só o reorganiza no formato visual das atividades.

---

## 1. Veredito geral

**O rascunho é bom e vale implementar quase inteiro.** O diagnóstico está certo: hoje quem move as contas é o
relógio, a carga vai explodir quando a cadência ligar e o dossiê é pré-requisito. A arquitetura é
preservada.

Três ressalvas mudam a ordem e a forma de fazer:

1. **🚨 Achado novo e crítico: a A9 nunca vai disparar** (seção 3, N1). Sem corrigir isso, as cadências
   **nunca terminam**, o teto de 8 contas simultâneas (P5) enche e trava de vez. Isso precisa entrar
   **antes de religar a A5**.
2. **Várias propostas marcadas como (b) são, na verdade, (a).** As notas de "Iniciar cadência", "Definir
   trilha", "Seguir/Interagir" e "Preparar reunião" vêm da **nota padrão do tipo de atividade**, não do
   código. Dá para editar pela tela, sem tocar em automação.
3. **Os trechos de código do rascunho têm erros que quebrariam a automação**: colisão de nome de variável,
   códigos de seleção errados, papel em minúscula e uma regra que se contradiz (seção 2).

---

## 2. Proposta a proposta

| # | Veredito | Tipo real | Correções em relação ao rascunho |
|---|---|---|---|
| **P1** Pausar A19 | ✅ Vale | (a) | Nenhuma. |
| **P2** Nota de "Iniciar cadência" | ✅ Vale | **(a)** | A2, A3 e A17 criam a tarefa **sem nota**, então o Odoo usa a nota padrão do tipo `act_iniciar_cadencia`. Basta editar o tipo de atividade, sem parâmetro `abm.dir.iniciar_cadencia`. Texto visual na seção 5.3. |
| **P3** Convite LinkedIn no Aquecendo | ✅ **Vale muito** (maior impacto) | (a) + (b) pequeno | **(a)** O texto "Seguir/Interagir" da preparação é a nota padrão do tipo `act_li_interagir`. O D3 da cadência usa o mesmo tipo, mas a A5 grava nota própria, então não é afetado. **(b)** Na A5, a condição real é `if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito'`. Trocar por `in ('enviado', 'aceito')` (os códigos estão confirmados). **A11:** o trecho do rascunho usa `contato`, `lead` e `'decisor'` em minúscula. No código real são `p`, `conta` e `p.x_abm_prioridade == 1 or p.x_abm_papel == 'Decisor'`. Trecho corrigido na seção 6.3. **Volume:** média de 2,2 decisores por conta (122 no total). Quatro contas por dia dão cerca de 9 convites por dia, dentro do limite semanal. As 32 contas já liberadas somam cerca de 70 convites: espalhar em 2 semanas. |
| **P4** Trilha feita sem o campo | ✅ Vale | (a) + (b) | **(a)** Editar a nota do tipo `act_trilha`. **(b)** Reconciliação: filtrar por `activity_type_id = act_trilha` (id 35), não por `summary ilike`. A tarefa recriada deve vencer em **+2 dias úteis**, não hoje, para não somar no freio da fila. **Variante C:** guardar a conta como "Configurador fraco" e marcar "variante C" na Ficha funciona, desde que a A5 detecte "variante c" nas Notas internas e use o direcionamento próprio dela (`abm.dir.*.variante_c`). Sem isso, a SDR recebe a instrução de configurador fraco para uma conta que tem configurador bom. Já está no código da seção 6. |
| **P5** Freio e teto | ⚠️ Vale **com N1 resolvido** | (a) + (b) | Manter o limite de pendentes em 10: ✅. Baixar contas por dia de 4 para 2: inofensivo, mas **quase não muda nada**, porque a fila só rodou 2 vezes em 14 dias úteis e o que libera contas é a A20. A alavanca real é a P6. Teto `abm.cadencia_max_ativas = 8`: ✅, mas **sem a correção N1 as contas não saem de "ativa"** e o teto vira bloqueio permanente. |
| **P6** A20 só por intenção | ✅ Vale | **(a)** | Dá para fazer **só no filtro da automação** (Odoo 19 aceita o operador `any`), sem código. Os códigos do rascunho estão errados. Os certos são `resposta_automatica`, `resposta_negativa`, `resposta_a_classificar`, `li_ads_relatorio`, `li_impressoes_semana` e `li_cliques`. **Contradição:** o rascunho exclui `outro` da intenção e, no complemento, registra o clique de anúncio como `outro`. Então o clique nunca furaria a fila. **Correção:** não excluir `outro`, porque sinal manual é deliberado. Filtro na seção 6.4. |
| **P7** Ligar o dossiê | ✅ **Essencial** | (a) | Além de gravar a Ficha em Notas internas (`description`), a A5 deve **copiar a Ficha para dentro da nota de cada atividade** num bloco recolhível. A SDR escreve o e-mail a partir da atividade e não deveria precisar abrir a conta. |
| **P8** Espelho antes da reunião | ✅ Vale | (a) | Hoje a nota padrão do tipo `act_preparar_reuniao` está **vazia**. Basta preenchê-la. "Atribuída também ao gestor" não dá: uma atividade só tem um responsável. A A8 já inscreve o gestor na conta. Se quiser uma tarefa para ele, é (b), uma linha. |
| **P9** Modelos e notas da A5 | ✅ Vale | (a) + (b) | **Erros no trecho:** (1) `nota += …` colide com a função `nota = lambda…` que já existe na A5 e quebraria a automação. A variável da nota se chama `html`. (2) "sem `def` por causa do safe_eval" está errado: a A2 já usa `def preparar(...)`. (3) Falta o mapa de toque, já que D8 e D14 usam o mesmo tipo `act_li_mensagem`. (4) **Manter o prefixo `[Cadência]` no resumo**: a A6 apaga as atividades pendentes por esse prefixo. Código corrigido e visual na seção 6. |
| **P10** Pequenos | ✅ Vale | (b) | Sem correções. |

---

## 3. Achados novos (não estavam no rascunho)

### N1 · 🚨 A A9 (cadência sem sinal → Nutrição) nunca dispara
- **Como funciona hoje:** a A9 dispara 35 dias depois de `x_abm_ref_inatividade`, que é a data mais recente entre `x_abm_cadencia_inicio` e `x_abm_ultimo_sinal_data`.
- **O problema:** `x_abm_ultimo_sinal_data` é a data do sinal mais recente de **qualquer tipo, ativo ou não**, e o **relatório de LinkedIn Ads gera sinal toda semana** para toda conta da campanha. A referência anda toda semana, os 35 dias nunca se completam e a conta fica em "Em cadência / ativa" para sempre.
- **Consequência:** a cadência termina no D18, mas a conta não sai. O teto de 8 (P5) enche em 4 dias e trava.
- **Correção mínima (a) + (b):**
  - (a) trocar o campo de data da A9 de `x_abm_ref_inatividade` para **`x_abm_cadencia_inicio`**, com 35 dias (cerca de 25 dias úteis, ou seja, D18 + uma semana de margem);
  - (b) no código da A9, antes de mover, **pular** a conta se ela tiver sinal de intenção depois do início da cadência (mesma lista de tipos da P6). Trecho na seção 6.5.
  - Não mexe em campo computado nem no dashboard.

### N2 · A nota padrão do tipo não aparece nas atividades da cadência
O Odoo usa `note or nota_padrão_do_tipo`. Como a A5 grava uma nota própria (a ficha da pessoa), **a instrução do tipo** ("Convite com nota curta…", "Enviar pelo chatter… trocar o destinatário") **não aparece** nas atividades de cadência. No documento de fluxo eu tinha descrito o contrário: fica corrigido aqui. Portanto, **todo o direcionamento da cadência precisa ser montado pela A5**, que é o que a seção 6 faz.

### N3 · A nota é uma foto do momento da criação
A A5 cria as 8 atividades no D1. A nota do D8 é escrita no D1. Por isso, nada que muda no caminho (status de conexão, Ficha atualizada) pode aparecer como "status atual". O desenho usa **instruções de conferência** ("abra o contato e confira Conexão"), não status.

### N4 · O que o Odoo 19 aceita de formatação na nota (testado em 22/10)
| Funciona | É removido ou alterado |
|---|---|
| `background-color`, `color`, `padding`, `margin`, `border-radius`, `font-weight`, `font-size`, `line-height`, `width` | `border-left` (barra lateral colorida) |
| `<table>` com `border`, `<ol>`, `<ul>`, `<hr>` | `<blockquote>` vira "citação de e-mail" e o Odoo **recolhe o conteúdo** |
| `<details>` / `<summary>` (bloco recolhível) | — |
| Emojis | — |

O teste foi uma atividade criada e apagada na hora (id 2155).

### N5 · Papel "Comercial/Vendas" sem ângulo
Há 30 pessoas de prioridade 1 ou 2 em **Comercial/Vendas**, área que a tabela 2.7 não cobre. É coerente com o ajuste por segmento do próprio rascunho, então foi incluído um ângulo: "configurador como ferramenta do vendedor e da concessionária".

---

## 4. Ordem revista

**Antes de religar a A5**
1. Diego aprova e responde às perguntas da seção 3.6 do rascunho.
2. **P1**: pausar a A19.
3. **N1**: corrigir a A9 (data + trecho).
4. **P2, P3a, P4a, P8**: notas dos tipos de atividade (só tela, seção 5).
5. **P9**: assuntos e esqueletos dos 8 modelos; parâmetros `abm.dir.*` (seção 7); A5 com o novo bloco visual e a condição do D1 Conectar (seção 6), **com a A5 ainda desligada**.
6. **P4b**: reconciliação de trilha na fila.
7. **P5**: `cadencia_max_ativas = 8` (deixar `contas_dia` em 4 é aceitável).
8. **P6**: filtro da A20. Pode vir antes, porque é só filtro.
9. **P7**: dossiês e Fichas das 6 contas em Engajada e das 13 que chegam em ~28/10.
10. **Validação**: rodar a ação da A5 manualmente sobre uma conta de teste e conferir o visual das 8 atividades.

**Piloto, depois e P10:** como no rascunho.

---

## 5. Estrutura visual das atividades

Preview: `preview_atividades_abm.html`, enviado junto. É fiel ao HTML que vai para o Odoo.

### 5.1 Princípios
- **Uma atividade, uma leitura de cima para baixo**, na ordem em que a SDR precisa: *o que é → para quê → para quem → como escrever → cuidado → links → apoio → conferir*.
- **Cor por canal no cabeçalho**: e-mail em grafite `#1f2937`, LinkedIn em azul `#0a66c2`, preparação em roxo `#7c3aed`, ligação e WhatsApp (A4) em verde `#15803d`.
- **Caixas com significado fixo**:
  - 🎯 azul claro: objetivo;
  - ⚠️ amarelo: cuidado da trilha;
  - ⛔ vermelho: condição que impede o toque;
  - ✅ verde: checklist antes de enviar;
  - cinza: dados.
- **Selos** no topo: trilha, modelo de e-mail e limite de palavras ou caracteres.
- **Ficha da conta recolhida** (`<details>`), para não poluir, mas a um clique.
- Nada de `border-left` nem `<blockquote>` (ver N4).

### 5.2 Blocos da atividade de cadência (montados pela A5)

| # | Bloco | Conteúdo | Origem |
|---|---|---|---|
| 1 | Cabeçalho | emoji + canal + nome do toque · "D{n} de 18 · Onda {n}" | mapa de toques |
| 2 | Selos | trilha · modelo `ABM · E{n} · {trilha}` (e-mails) · limite | conta + parâmetro |
| 3 | 🎯 Objetivo | 1 frase | `abm.dir.<toque>.<trilha>` (linha `OBJETIVO:`) |
| 4 | ⛔ Condição | só no D8 e no D14: "Só com conexão aceita…" | fixo |
| 5 | 👤 Para quem | tabela: pessoa, papel · prioridade · área, **ângulo do papel**, e-mail + status, LinkedIn | contato + `abm.dir.papel.<chave>` |
| 6 | 🧱 Como escrever | lista numerada | parâmetro (linhas `1.`, `2.`…) |
| 7 | ⚠️ Cuidado | caixa amarela | parâmetro (linhas `!`) |
| 8 | 🔗 Links | link da conta com UTM do canal · dossiê | conta |
| 9 | 📋 Ficha da conta | recolhida, cópia das Notas internas | `conta.description` |
| 10 | ✅ Antes de enviar | checklist curto (só e-mails) | `abm.dir.checklist_email` |

### 5.3 Notas dos tipos de atividade (editar em CRM → Configuração → Tipos de atividade → Nota padrão)

**ABM · Iniciar cadência** (P2)
```html
<div style="background-color:#7c3aed; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">🚦 INICIAR CADÊNCIA · checklist de entrada</div>
<ol style="margin:10px 0; padding-left:20px">
<li>Dossiê anexado e link em <b>ABM · Dossiê (URL)</b>.</li>
<li><b>Ficha da conta</b> preenchida nas Notas internas.</li>
<li><b>Trilha</b> preenchida (não pode ficar “a definir”).</li>
<li>Até <b>3 pessoas</b> marcadas “Na cadência”, papéis diferentes, com decisor.</li>
<li>Decisores com convite de LinkedIn enviado (Conexão = Enviado).</li>
<li>Contas em cadência agora <b>&lt; 8</b>.</li>
</ol>
<div style="background-color:#fff7d6; color:#713f12; padding:8px 12px; border-radius:6px">⏸️ <b>Cadência automática desligada até o aviso.</b> Faça de 1 a 5 e deixe a conta em Engajada. Não mova para Em cadência.</div>
```
Quando a A5 for religada, trocar a caixa amarela por: `✅ Com 1 a 6 ok, mova o card para Em cadência: as atividades são criadas sozinhas.`

**ABM · Definir trilha** (P4a)
```html
<div style="background-color:#7c3aed; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">🧭 DEFINIR TRILHA</div>
<p style="margin:8px 0 4px; font-weight:bold">Com dossiê: use o diagnóstico</p>
<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb; margin-bottom:8px">
<tr><td style="background-color:#f9fafb; padding:4px 8px; width:45%">A · Sem configurador 3D</td><td style="padding:4px 8px">→ <b>Sem configurador</b></td></tr>
<tr><td style="background-color:#f9fafb; padding:4px 8px">B · Configurador ruim</td><td style="padding:4px 8px">→ <b>Configurador fraco</b></td></tr>
<tr><td style="background-color:#f9fafb; padding:4px 8px">Configurador 3D bom</td><td style="padding:4px 8px">→ <b>Configurador fraco</b> + escrever “variante C” na Ficha</td></tr>
</table>
<p style="margin:8px 0 4px; font-weight:bold">Sem dossiê: teste o site</p>
<ol style="margin:0 0 8px; padding-left:20px">
<li><b>Configurador:</b> existe? 3D ou só fotos? Interior? Velocidade? <b>Teste no celular.</b></li>
<li><b>3D na comunicação:</b> a marca usa 3D/CGI em lançamentos, site, redes e catálogos?</li>
<li>Registre na Ficha os links e prints que justificam a escolha (viram a 1ª linha do E1).</li>
</ol>
<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px">⛔ <b>Só conclua depois de gravar o campo Trilha.</b> Tarefa concluída com o campo vazio é reaberta pela rotina diária.</div>
```

**ABM · LinkedIn – Seguir/Interagir** (P3a: vale para a preparação; o D3 da cadência tem nota própria)
```html
<div style="background-color:#0a66c2; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">👍 LINKEDIN · PREPARAÇÃO</div>
<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb; margin:8px 0">
<tr><td style="background-color:#f9fafb; padding:4px 8px; width:32%"><b>Todos</b></td><td style="padding:4px 8px">Seguir a pessoa e a página da marca. Reagir ou comentar 1 post relevante (comentário real vale mais que curtida).</td></tr>
<tr><td style="background-color:#f9fafb; padding:4px 8px"><b>Decisores</b> (prioridade 1)</td><td style="padding:4px 8px">2 dias úteis depois da interação: <b>convite</b> sem nota ou com nota de até 200 caracteres, sem pitch. Marcar <b>Conexão = Enviado</b>.</td></tr>
<tr><td style="background-color:#f9fafb; padding:4px 8px"><b>Influenciadores</b></td><td style="padding:4px 8px">Só seguir e interagir.</td></tr>
</table>
```

**ABM · Preparar reunião** (P8)
```html
<div style="background-color:#15803d; color:#ffffff; padding:8px 12px; border-radius:6px; font-weight:bold; font-size:14px">📅 PREPARAR REUNIÃO</div>
<div style="background-color:#fee2e2; color:#7f1d1d; padding:8px 12px; border-radius:6px; margin-top:8px">⛔ <b>Configurador espelho pronto?</b> Confira o modelo indicado na Ficha. Se não estiver pronto, produza antes ou remarque. Não faça a reunião sem o espelho: é o que foi prometido.</div>
```

---

## 6. Código (trechos mínimos, para o Claude Code aplicar)

> Regra: ler a ação atual, aplicar **só** o trecho e registrar antes/depois na nota da automação e no commit.

### 6.1 A5 · passos com chave de toque e D1 Conectar
**Antes**
```python
    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', ''),
        (1, 'act_email', 'E-mail', 'E1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', ''),
        (5, 'act_email', 'E-mail', 'E2'),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem de valor', ''),
        (11, 'act_email', 'E-mail', 'E3'),
        (14, 'act_li_mensagem', 'LinkedIn – Follow-up', ''),
        (18, 'act_email', 'E-mail', 'E4'),
    ]
    ...
        for dia, tipo, canal, email_cod in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao == 'aceito':
```
**Depois**
```python
    passos = [
        (1, 'act_li_conectar', 'LinkedIn – Conectar', '', 'li_conectar'),
        (1, 'act_email', 'E-mail', 'E1', 'e1'),
        (3, 'act_li_interagir', 'LinkedIn – Interagir', '', 'li_interagir'),
        (5, 'act_email', 'E-mail', 'E2', 'e2'),
        (8, 'act_li_mensagem', 'LinkedIn – Mensagem de valor', '', 'li_valor'),
        (11, 'act_email', 'E-mail', 'E3', 'e3'),
        (14, 'act_li_mensagem', 'LinkedIn – Follow-up', '', 'li_followup'),
        (18, 'act_email', 'E-mail', 'E4', 'e4'),
    ]
    ...
        for dia, tipo, canal, email_cod, toque in passos:
            if tipo == 'act_li_conectar' and p.x_abm_li_conexao in ('enviado', 'aceito'):
```
Aplicar o mesmo na A14 (Onda 2), que tem uma cópia da lista.

### 6.2 A5 · bloco visual (substitui a montagem de `html` dentro do loop)
Definir **uma vez**, antes do `for conta in records:` (sem conflito com `nota` e `esc`, que já existem):
```python
DIR = lambda chave: (ICP.get_param(chave) or '').strip()
SENIOR = ('C suite', 'Vp', 'Owner', 'Head', 'Director')
AREA_PAPEL = {'Marketing': 'marca', 'Produto': 'produto', 'TI/Digital': 'digital',
              'Compras/Procurement': 'compras', 'Engenharia/Design': 'engenharia',
              'Comercial/Vendas': 'comercial'}
TOQUE_INFO = {
    'li_conectar': ('🤝', 'LINKEDIN · CONECTAR', '#0a66c2', 'até 200 caracteres'),
    'e1': ('✉️', 'E-MAIL E1 · OBSERVAÇÃO', '#1f2937', 'até 120 palavras'),
    'li_interagir': ('👍', 'LINKEDIN · INTERAGIR', '#0a66c2', '1 frase'),
    'e2': ('✉️', 'E-MAIL E2 · PROVA', '#1f2937', 'até 90 palavras'),
    'li_valor': ('💬', 'LINKEDIN · MENSAGEM DE VALOR', '#0a66c2', 'até 300 caracteres'),
    'e3': ('✉️', 'E-MAIL E3 · CONVITE', '#1f2937', 'até 110 palavras'),
    'li_followup': ('💬', 'LINKEDIN · FOLLOW-UP', '#0a66c2', 'até 300 caracteres'),
    'e4': ('✉️', 'E-MAIL E4 · ENCERRAMENTO', '#1f2937', 'até 60 palavras'),
}
TRILHA_ROTULO = {'sem_config': 'Sem configurador', 'config_fraco': 'Configurador fraco',
                 'variante_c': 'Configurador fraco · variante C', 'a_definir': 'A definir'}
CAIXA = 'padding:8px 12px; border-radius:6px; margin-bottom:10px; '
SELO = 'padding:2px 8px; border-radius:10px; font-size:12px; '
CEL_L = '<td style="background-color:#f9fafb; padding:4px 8px; width:28%; color:#6b7280">'
CEL_R = '<td style="padding:4px 8px">'
negrito = lambda s: ''.join([('<b>%s</b>' if i % 2 else '%s') % esc(parte) for i, parte in enumerate(s.split('**'))])

def papel_key(p):
    if p.x_abm_area == 'Marketing' and p.x_abm_senioridade in SENIOR:
        return 'decisor_mkt'
    return AREA_PAPEL.get(p.x_abm_area or '', 'geral')

def trilha_key(conta):
    if 'variante c' in (conta.description or '').lower():
        return 'variante_c'
    return conta.x_abm_trilha if conta.x_abm_trilha in ('sem_config', 'config_fraco') else 'a_definir'

def direcao(toque, tk):
    return (DIR('abm.dir.%s.%s' % (toque, tk))
            or (tk == 'variante_c' and DIR('abm.dir.%s.config_fraco' % toque))
            or DIR('abm.dir.%s.geral' % toque) or '')

def partes(txt):
    """Formato do parâmetro: OBJETIVO: … | 1. passo | ! cuidado | demais linhas = texto."""
    objetivo, passos, alertas, outros = '', [], [], []
    for linha in (txt or '').split('\n'):
        l = linha.strip()
        if not l:
            continue
        num, sep, resto = l.partition('. ')
        if l.upper().startswith('OBJETIVO:'):
            objetivo = l[9:].strip()
        elif sep and num.isdigit():
            passos.append(resto.strip())
        elif l.startswith('!'):
            alertas.append(l[1:].strip())
        else:
            outros.append(l)
    return objetivo, passos, alertas, outros
```
Dentro do loop, **no lugar** do bloco que hoje monta `html` (de `html = '<p><b>%s</b> — %s…` até o `if tipo == 'act_li_mensagem': …`):
```python
            emoji, titulo, cor, limite = TOQUE_INFO[toque]
            tk = trilha_key(conta)
            objetivo, passos_dir, alertas, outros = partes(direcao(toque, tk))
            link = conta.x_abm_link_email if tipo == 'act_email' else conta.x_abm_link_linkedin
            html = ('<div style="background-color:%s; color:#ffffff; %s font-weight:bold; font-size:14px">%s %s '
                    '<span style="font-weight:normal; color:#d1d5db">· D%s de 18 · Onda %s</span></div>') % (
                cor, CAIXA, emoji, titulo, dia, conta.x_abm_onda or 1)
            html += '<p style="margin:6px 0 10px"><span style="background-color:#fde8e2; color:#9a3412; %s">Trilha: %s</span> ' % (SELO, TRILHA_ROTULO[tk])
            if email_cod:
                html += '<span style="background-color:#f3f4f6; color:#374151; %s">Modelo: ABM · %s · %s</span> ' % (SELO, email_cod, rotulo)
            html += '<span style="background-color:#f3f4f6; color:#374151; %s">%s</span></p>' % (SELO, limite)
            if toque in ('li_valor', 'li_followup'):
                html += ('<div style="background-color:#fee2e2; color:#7f1d1d; %s">⛔ <b>Só com conexão aceita.</b> Abra o contato e '
                         'confira o campo <b>Conexão LinkedIn</b>. Se não estiver “Aceito”, marque como feita sem enviar.</div>') % CAIXA
            if objetivo:
                html += '<div style="background-color:#eef2ff; color:#1e3a8a; %s">🎯 <b>Objetivo:</b> %s</div>' % (CAIXA, negrito(objetivo))
            angulo = DIR('abm.dir.papel.%s' % papel_key(p)) or DIR('abm.dir.papel.geral')
            html += '<p style="font-weight:bold; margin:0 0 4px">👤 Para quem</p>'
            html += '<table style="width:100%; border-collapse:collapse; border:1px solid #e5e7eb; margin-bottom:10px">'
            html += '<tr>%sPessoa</td>%s<b>%s</b> — %s</td></tr>' % (CEL_L, CEL_R, esc(p.name), esc(p.function) or '-')
            html += '<tr>%sPapel</td>%s%s · Prioridade %s · %s</td></tr>' % (
                CEL_L, CEL_R, esc(p.x_abm_papel) or '-', p.x_abm_prioridade or '-', esc(p.x_abm_area) or '-')
            if angulo:
                html += '<tr>%sÂngulo</td>%s%s</td></tr>' % (CEL_L, CEL_R, negrito(angulo))
            if tipo == 'act_email':
                html += '<tr>%sE-mail</td>%s%s (%s)</td></tr>' % (CEL_L, CEL_R, esc(p.email) or '-', esc(p.x_email_status) or 'sem status')
            if p.x_linkedin_url:
                html += '<tr>%sLinkedIn</td>%s<a href="%s" target="_blank">%s</a></td></tr>' % (
                    CEL_L, CEL_R, esc(p.x_linkedin_url), esc(p.x_linkedin_url))
            html += '</table>'
            if passos_dir or outros:
                html += '<p style="font-weight:bold; margin:0 0 4px">🧱 Como escrever</p>'
                for o in outros:
                    html += '<p style="margin:0 0 6px">%s</p>' % negrito(o)
                if passos_dir:
                    html += '<ol style="margin:0 0 10px; padding-left:20px">%s</ol>' % ''.join(['<li>%s</li>' % negrito(x) for x in passos_dir])
            for a in alertas:
                html += '<div style="background-color:#fff7d6; color:#713f12; %s">⚠️ %s</div>' % (CAIXA, negrito(a))
            html += '<p style="font-weight:bold; margin:0 0 4px">🔗 Links</p><p style="margin:0 0 10px">'
            html += 'Link da conta: %s<br/>Dossiê: %s</p>' % (esc(link) or '-', esc(conta.x_abm_dossie_url) or '<b>sem dossiê</b>')
            if conta.description:
                html += ('<details style="margin-bottom:10px"><summary style="font-weight:bold">📋 Ficha da conta '
                         '(cópia do início da cadência)</summary><div style="background-color:#f9fafb; %s font-size:12px">%s</div></details>') % (
                    CAIXA, conta.description)
            if tipo == 'act_email':
                html += '<div style="background-color:#f0fdf4; color:#14532d; %s">✅ <b>Antes de enviar:</b> %s</div>' % (
                    CAIXA, negrito(DIR('abm.dir.checklist_email')))
```
O resumo `'[Cadência] D%s %s – %s (%s)'` e o `activity_schedule(...)` continuam **iguais** (a A6 depende do prefixo).

### 6.3 A11 · asset só a partir de Engajada (P3)
**Antes**
```python
    if decisor and not ja_tem:
```
**Depois**
```python
    etapas_asset = [env.ref('abm_setima.stage_engajada').id, env.ref('abm_setima.stage_em_cadencia').id,
                    env.ref('abm_setima.stage_conversa').id]
    if decisor and not ja_tem and conta.stage_id.id in etapas_asset:
```

### 6.4 A20 · só intenção (P6): só o filtro da automação
**Antes:** `[('team_id', '=', 20), ('stage_id', '=', 87), ('x_abm_score', '>', 0)]`
**Depois:**
```python
[('team_id', '=', 20), ('stage_id', '=', 87),
 ('x_abm_sinal_ids', 'any', [('x_ativo', '=', True),
   ('x_tipo', 'not in', ['li_ads_relatorio', 'li_impressoes_semana', 'li_cliques',
                         'resposta_automatica', 'resposta_negativa', 'resposta_a_classificar'])])]
```
O código da A20 testa `x_abm_score > 0` de novo por dentro, o que continua verdadeiro e não precisa mudar.

### 6.5 A9 · encerrar a cadência de verdade (N1)
- **(a)** Campo de data: `x_abm_ref_inatividade` → **`x_abm_cadencia_inicio`** (manter 35 dias).
- **(b) Antes**
```python
for conta in records:
    conta.write({'stage_id': env.ref('abm_setima.stage_nutricao').id})
```
**Depois**
```python
SEM_INTENCAO = ('li_ads_relatorio', 'li_impressoes_semana', 'li_cliques',
                'resposta_automatica', 'resposta_negativa', 'resposta_a_classificar')
for conta in records:
    vivos = conta.x_abm_sinal_ids.filtered(lambda s: s.x_ativo and s.x_tipo not in SEM_INTENCAO
        and s.x_data and conta.x_abm_cadencia_inicio and s.x_data.date() >= conta.x_abm_cadencia_inicio)
    if vivos:
        nota(conta, 'Cadência encerrada no prazo, mas com sinal de intenção: conta mantida para decisão manual.')
        continue
    conta.write({'stage_id': env.ref('abm_setima.stage_nutricao').id})
```

---

## 7. Parâmetros `abm.dir.*` no formato visual

Formato: `OBJETIVO:` vira a caixa azul · `1.`, `2.` viram a lista "Como escrever" · `!` vira a caixa amarela ·
`**texto**` vira negrito · as demais linhas viram parágrafo. **O conteúdo é o do rascunho, sem mudança de direção.**

| Chave | Valor |
|---|---|
| `abm.dir.e1.sem_config` | `OBJETIVO: abrir com um fato desta conta e conseguir um “sim, mostra”.`<br>`1. **Gatilho ou observação da Ficha** (1–2 frases). Só desta conta.`<br>`2. **O que isso implica para o papel** desta pessoa (use o Ângulo acima).`<br>`3. **Prova:** configurador 3D do VW Tera (1 frase, já vem no modelo).`<br>`4. **Pergunta de interesse:** “vale eu montar uma prévia do [modelo da Ficha]?”`<br>`5. **P.S.** com o link da conta.`<br>`! **Sem configurador:** só diga que não há configurador se você viu no site. Concorrente só se a Ficha disser qual.` |
| `abm.dir.e1.config_fraco` | mesmas linhas 1 a 5 do E1 +<br>`! **Configurador fraco:** descreva o que viu (sem interior, troca só de cor, lento no celular) sem chamar de ruim ou fraco: quem recebe pode ter feito. **Teste no celular antes de escrever.**` |
| `abm.dir.e1.variante_c` | `OBJETIVO: abrir com o volume de conteúdo que o lançamento exige e conseguir um “sim, mostra”.`<br>`1. **Gatilho da Ficha** (lançamento, campanha).`<br>`2. **Volume:** versões × cores × canais que esse lançamento pede.`<br>`3. **Prova:** o mesmo modelo 3D do Tera gera site, social e OOH.`<br>`4. **Pergunta:** “vale eu montar uma cena de campanha do [modelo]?”`<br>`! **Variante C:** o configurador deles é bom. Não fale de configurador. Sem gatilho, a conta deve ser despriorizada.` |
| `abm.dir.e1.a_definir` | `OBJETIVO: o ideal é definir a trilha antes de enviar.`<br>`1. Abra pelo **gatilho de lançamento**.`<br>`2. Ângulo: **um modelo 3D, todas as peças**.`<br>`! **Trilha não definida:** não fale do site deles.` |
| `abm.dir.e2.geral` | `OBJETIVO: prova.`<br>`1. Retome o E1 em meia frase (sem “conforme e-mail anterior”).`<br>`2. **Case em 3 linhas:** situação, o que foi feito, o que mudou.`<br>`3. **Uma pergunta** sobre como eles fazem hoje.`<br>`Sem configurador: modelo 3D como origem de site **e** de campanha. Configurador fraco: realismo, interior, velocidade, mobile.` |
| `abm.dir.e3.geral` | `OBJETIVO: 20 minutos.`<br>`1. **Gatilho de reserva** da Ficha.`<br>`2. **O que ele vai ver:** o modelo dele em 3D, como se produz, custo por peça depois do modelo pronto.`<br>`3. **Objeção provável** da Ficha respondida em 1 frase.`<br>`4. **Duas opções de dia.**` |
| `abm.dir.e4.geral` | `OBJETIVO: encerrar sem queimar a conta.`<br>`1. Reconheça que pode não ser o momento.`<br>`2. **Duas saídas:** quem cuida disso, ou voltar perto do próximo gatilho.`<br>`! Sem “último e-mail”, culpa ou urgência inventada.` |
| `abm.dir.li_conectar.geral` | `OBJETIVO: estar na rede da pessoa antes do E2.`<br>`1. Se o convite já foi enviado na preparação, **marque como feita**.`<br>`2. Senão: nota de até 200 caracteres com o gatilho ou algo do perfil.`<br>`3. Ao concluir: **Conexão = Enviado**.`<br>`! Sem link, sem pitch.` |
| `abm.dir.li_interagir.geral` | `OBJETIVO: ser visto sem pedir nada.`<br>`1. Post da pessoa ou da marca sobre produto ou lançamento.`<br>`2. **Comentário real** (uma frase com opinião ou pergunta) vale mais que curtida.`<br>`! Nunca citar a Sétima no comentário.` |
| `abm.dir.li_valor.geral` | `OBJETIVO: entregar algo útil sem pedir nada.`<br>`1. Um trecho do Tera, um dado, uma observação sobre o lançamento dele ou a calculadora de ROI.`<br>`2. Sem asset personalizado, sem convite de reunião.` |
| `abm.dir.li_followup.geral` | `OBJETIVO: retomar o fio e oferecer o espelho.`<br>`1. Retome o E3 ou o D8.`<br>`2. Ofereça o espelho **em uma pergunta**.`<br>`! Se ele já respondeu em qualquer canal, **não envie**: atualize a conta.` |
| `abm.dir.papel.decisor_mkt` | `Um único modelo 3D do carro paga várias produções: site, campanha e pós-lançamento.` |
| `abm.dir.papel.produto` | `Dá para ter imagens de todas as versões antes de o carro estar pronto para foto.` |
| `abm.dir.papel.digital` | `Configurador leve no celular, com cada montagem virando lead para a concessionária.` |
| `abm.dir.papel.marca` | `O mesmo arquivo gera o volume de peças que social e OOH pedem, com a mesma cara.` |
| `abm.dir.papel.compras` | `Custo concentrado na digitalização inicial; certificação TISAX para lançamento sigiloso.` |
| `abm.dir.papel.engenharia` | `Modelo fiel ao produto real, aprovado uma vez e reutilizado.` |
| `abm.dir.papel.comercial` | `Configurador como ferramenta do vendedor e da concessionária: o cliente chega com o carro montado.` (novo, N5) |
| `abm.dir.papel.geral` | `Fale do carro deles: um modelo 3D, todas as peças.` |
| `abm.dir.checklist_email` | `1ª linha só serve para esta conta · todo fato tem fonte · 1 pergunta, 1 link · sem colchete sobrando · mais do carro deles que da Sétima · nada de “vi que você visitou” · **destinatário trocado para a pessoa da tarefa**` |
| `abm.cadencia_max_ativas` | `8` |
