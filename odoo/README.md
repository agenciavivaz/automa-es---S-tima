# Camada de integração Odoo CRM (JSON-2)

Ferramental interno para **extrair, analisar e editar** dados do CRM das equipes
de venda **16, 17 e 21**, via a API JSON-2 do Odoo 19.

Não é produto: roda por CLI e foi feita para ser dirigida pelo Claude Code, que
lê os outputs (tabela no terminal, `--formato json`, CSV em `data/odoo/`).

- **Protocolo:** `POST https://<base>/json/2/<model>/<method>`, autenticação por
  chave de API em `Authorization: Bearer`, banco em `X-Odoo-Database`, corpo com
  parâmetros **nomeados** (`ids`, `context` e os argumentos do método).
- **XML-RPC / JSON-RPC:** não são usados e não há fallback para eles. Estão
  depreciados e saem do Odoo Online 21.1. Os scripts antigos na raiz do
  repositório ainda usam XML-RPC e não foram alterados.
- **Transação:** cada chamada roda na própria transação SQL. Não existe
  transação entre chamadas — o que precisa ser atômico tem que caber em uma
  chamada só.

---

## 1. Configuração

No `.env` (já está no `.gitignore`):

```bash
ODOO_URL=https://suaempresa.odoo.com
ODOO_DB=nome_do_banco
ODOO_API_KEY=<chave do usuário de serviço>      # perfil operacional
ODOO_ADMIN_API_KEY=<chave do usuário admin>     # perfil configuração (Fase 3)
```

As chaves saem de **Configurações → Usuários e Empresas → Usuários → aba
Preferências → Nova chave de API**. Chave de usuário comum expira em até 90
dias; só admin cria chave permanente. Expiração aparece como erro 401 legível,
não como exceção genérica.

Dependências: `pip install -r requirements.txt` (`requirements-dev.txt` inclui o
pytest). Rode os comandos a partir da raiz do repositório.

Primeiro comando a rodar, sempre:

```bash
python -m odoo.cli test-connection
```

Ele valida as duas chaves, mostra o usuário autenticado de cada uma e imprime os
nomes das equipes 16, 17 e 21 — se algum ID não bater com o nome esperado, pare
por aí.

---

## 2. Comandos

Todos aceitam `--formato json` (saída legível por máquina) e `--log-level DEBUG`.

### Conexão e schema

```bash
python -m odoo.cli test-connection
python -m odoo.cli schema modelos                       # o que dá para ler/editar
python -m odoo.cli schema fields crm.lead               # campos reais desta base
python -m odoo.cli schema fields crm.lead --customizados  # só os x_
python -m odoo.cli schema fields crm.lead --filtro revenue --refresh
```

`fields_get` é cacheado em `data/odoo/.schema/` com TTL de 24h (`--refresh`
ignora o cache). **A verdade sobre os campos é sempre a base**, não este
repositório: bases com histórico têm campos customizados.

### Extração

```bash
python -m odoo.cli extrair crm.lead --desde 2026-01-01 --ate 2026-06-30
python -m odoo.cli extrair crm.lead --campos id,name,stage_id,expected_revenue
python -m odoo.cli extrair crm.lead --domain '[["probability",">",50]]'
python -m odoo.cli extrair mail.activity --formato-arquivo json
```

Paginação em lotes de 500 é automática e invisível. O período filtra
`create_date` por padrão (`--campo-data date_closed` troca o campo). Saída em
`data/odoo/<modelo>_<timestamp>.csv`.

### Análises

```bash
python -m odoo.cli analisar funil --desde 2026-01-01 --por-equipe
python -m odoo.cli analisar tempo-estagio
python -m odoo.cli analisar parados --dias 14
python -m odoo.cli analisar origem
python -m odoo.cli analisar ganhos-perdas --campo-data date_closed
```

Filtros comuns: `--desde`, `--ate`, `--campo-data`, `--equipes 16,17`,
`--tipo opportunity|lead|todos`, `--sem-csv`.

Toda análise declara **período coberto, total considerado, quantos foram
descartados por dado faltante e quais equipes entraram**. O CSV carrega esse
mesmo cabeçalho.

Detalhes que mudam a leitura dos números:

- **funil** — conversão é a razão entre a contagem de um estágio e a do estágio
  anterior *no corte atual*, não coorte por lead.
- **tempo-estagio** — usa `mail.tracking.value` (histórico real) quando a chave
  consegue lê-lo; senão cai para `date_last_stage_update`, que mede só o estágio
  atual. O método usado sai declarado no output.
- **parados** — oportunidade aberta sem mensagem no chatter no período e sem
  atividade agendada. Sai agrupado por responsável, mais um CSV de detalhe.
- **origem** — taxa de ganho = ganhos / (ganhos + perdidos); abertos ficam fora
  do denominador e isso está no rodapé.
- **ganhos-perdas** — ganho = estágio `is_won` ou probabilidade 100; perdido =
  arquivado **com** motivo de perda. Arquivado sem motivo é contado à parte.

### Edição de dados (Fase 2)

**Dry-run é o padrão.** Sem `--apply`, nada é enviado ao Odoo.

```bash
# 1. veja o que aconteceria (antes → depois, registro a registro)
python -m odoo.cli editar crm.lead --ids 1042,1043 --vals '{"user_id": 7}'

# 2. execute
python -m odoo.cli editar crm.lead --ids 1042,1043 --vals '{"user_id": 7}' --apply

# seleção por domain (resolvida para IDs antes de qualquer escrita)
python -m odoo.cli editar crm.lead --domain '[["stage_id","=",12]]' \
    --vals '{"stage_id": 13}' --apply

# payload grande vem de arquivo
python -m odoo.cli criar crm.lead --vals @novos_leads.json --apply
```

Travas:

- acima de **50 registros** pede confirmação interativa mesmo com `--apply`
  (`--limite-confirmacao` ajusta);
- `--domain` vazio é recusado — em `write` isso atingiria a tabela inteira e o
  Odoo não tem desfazer;
- campo inexistente vira erro nomeando o campo e sugerindo os parecidos;
- criar lead exige `team_id` dentro das equipes permitidas;
- toda escrita aplicada vira uma linha em `data/odoo/audit.jsonl`
  (`python -m odoo.cli auditoria` lê as últimas).

Esta camada **não apaga registro**: não existe `unlink` em lugar nenhum do
pacote.

---

## 3. Escopo de equipes

`ALLOWED_TEAM_IDS = (16, 17, 21)` vive em `odoo/models.py` e em nenhum outro
lugar.

- Toda query em `crm.lead` recebe o filtro de equipe automaticamente, inclusive
  quando o domain do chamador usa `|` ou `!` — os domains são normalizados antes
  de combinar, então o `OR` de quem chama nunca escapa do `AND` da equipe.
- Antes de qualquer escrita, os alvos são relidos: **se um registro estiver fora
  do escopo, a operação inteira aborta** e os IDs bloqueados são nomeados. Não
  há filtragem silenciosa.
- `team_id` vazio conta como **fora** do escopo.
- `res.partner` não tem equipe: o contato só é editável se estiver ligado a pelo
  menos um lead das equipes permitidas.

> **Limitação honesta:** isso é trava de aplicação. Quem tem acesso ao
> repositório pode editar a constante. Para valer de verdade, a restrição
> precisa ser uma **regra de registro (`ir.rule`)** no usuário de serviço dentro
> do Odoo, com domain `[("team_id", "in", [16, 17, 21])]` sobre `crm.lead`.
> Recomendado ter os dois: `ir.rule` como trava real, a constante como
> documentação e mensagem de erro decente.

---

## 4. Segurança

- Credenciais só de variável de ambiente / `.env`. Nunca hardcoded, nunca em
  argumento de CLI, nunca em log. O CLI não tem `--api-key`.
- A chave é removida de qualquer mensagem de erro antes de a exceção subir, e
  `repr()` das credenciais mostra `chave=***`.
- `DEBUG` loga modelo, método e domain — nunca headers.
- Comandos de leitura (`schema`, `extrair`, `analisar`) abrem o cliente como
  **somente leitura**: uma tentativa de `write`/`create` ali é bloqueada no
  cliente, antes de virar requisição.
- A chave de admin só é lida dentro de `odoo/config/` — verificável por
  `grep -r ODOO_ADMIN_API_KEY odoo/`, que só deve apontar para
  `odoo/config/credentials.py`.
- `data/` está no `.gitignore`: extrações, cache de schema e auditoria não vão
  para o repositório.

---

## 5. Testes

```bash
pip install -r requirements-dev.txt
python -m pytest
```

75 testes, todos com HTTP mockado — nenhum bate na instância real. Cobrem o
cliente (headers, parâmetros nomeados, retry em 429/5xx, ausência de retry em
4xx, paginação, mascaramento da chave), o escopo de equipes (RE-01 a RE-04), as
análises (matemática e denominador), a edição (dry-run, limite de confirmação,
auditoria, abort por escopo) e os critérios de aceite que se verificam lendo o
código (separação de privilégio, ausência de `unlink`, ausência de XML-RPC).

---

## 6. Estado das fases

| Fase | Escopo | Estado |
|---|---|---|
| 1 | Cliente, schema, extração, 5 análises | implementada, **falta validar contra a base real** |
| 2 | Edição de dados com dry-run e auditoria | implementada, **falta validar contra a base real** |
| 3 | Campos, estágios, tags e automações (`config diff`/`config apply`) | **não implementada** |

A Fase 3 não foi escrita de propósito. O PRD manda cada fase só começar depois
da anterior estar funcionando e validada, e ela mexe no **schema de uma base de
produção**: campo criado é reversível, campo apagado leva os dados junto. Para
começar são necessários (a) Fases 1 e 2 validadas contra a base real e (b) uma
base de staging. Quando for a hora, ela entra em `odoo/config/apply.py` com
arquivos declarativos (`campos.yaml`, `estagios.yaml`, `automacoes.yaml`),
aplicação idempotente, `config diff` sem `--apply`, automações criadas
desativadas e com filtro de equipe obrigatório, e nada de deletar ou arquivar.

### Antes de rodar contra a base real

1. `python -m odoo.cli test-connection` — confirme a identidade de cada chave e
   os nomes das equipes 16/17/21.
2. Abra a página **`/doc`** da base (documentação dinâmica do Odoo, lista os
   modelos, campos e métodos daquela instalação, inclusive os `x_`) e confira os
   campos que você pretende usar, além das assinaturas de `write` e `create`.
   Os nomes de parâmetro do JSON-2 estão centralizados em `odoo/models.py`
   (`PARAM_VALS`, `PARAM_VALS_LIST`, …) — se a `/doc` divergir, o ajuste é em um
   ponto só.
3. `python -m odoo.cli schema fields crm.lead --customizados` para ver o que a
   base tem de campo customizado.
4. Rode as análises com `--desde` curto primeiro, confira os denominadores e só
   então amplie.
5. Na Fase 2, sempre dry-run antes do `--apply`, e confira `auditoria` depois.
