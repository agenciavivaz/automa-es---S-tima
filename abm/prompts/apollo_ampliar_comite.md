# Prompt — ampliar contas e comitês ABM Sétima via Apollo

> Anexar junto: o CSV de contas (`companyname, companywebsite, ...`).

---

Você vai montar, usando o **Apollo**, a lista de contas e os **comitês de compra** para
a prospecção ABM da **Sétima** (estúdio de CGI/3D e configuradores de produto para
montadoras e fabricantes de veículos e máquinas). O resultado será importado no Odoo,
então siga **exatamente** o formato de saída do final.

## 1. Contas (CSV anexo)

- Use **somente** as colunas `companyname` e `companywebsite`. As colunas de LinkedIn,
  cidade, estado e setor do arquivo estão **desalinhadas** (ex.: Volkswagen aponta para
  a página da Audi). Ignore-as e localize cada empresa no Apollo **pelo domínio**.
- Se o domínio não achar a empresa, busque pelo nome + país Brasil. Se houver mais de
  uma organização possível (matriz global × subsidiária Brasil), escolha a **operação
  brasileira** e registre a global em `dominios_extra`.
- **Contas que já existem no ABM:** NÃO montar o comitê do zero. Só completar quem está
  sem decisor ou com comitê fraco: **Toyota, Caoa Chery, Leapmotor, RAM, Renault, Zeekr,
  Triumph, Mitsubishi, Kia, Scania**. Pular estas, que já têm comitê completo:
  Volkswagen (vw.com.br), Hyundai, Jeep, Stellantis, Honda, Nissan, Ford,
  Mercedes-Benz, Volvo Cars, BYD, Yamaha, Marcopolo, Volvo Buses, John Deere e AGCO.
- **Todas as outras 77 são novas.** Atenção: Land Rover ≠ "Land Rio" (concessionária),
  e Volkswagen Caminhões e Ônibus, Volvo Trucks e Volvo Construction Equipment são
  contas **separadas** de VW do Brasil e Volvo Cars.
- Ignore concessionárias, revendas e distribuidores; queremos a montadora/fabricante.

## 2. Quem buscar (comitê)

Pessoas **baseadas no Brasil** (ou com cargo regional LATAM/South America baseadas no
Brasil), nas áreas que compram ou influenciam conteúdo visual, lançamento de produto e
experiência digital:

- Marketing, Marketing de Produto, Brand, Comunicação, Mídia/Growth
- Produto / Planejamento de Produto / Lançamentos
- Digital, E-commerce, CX, Site/Configurador
- Engenharia/Design (design de produto, visualização, CAD)
- Compras de marketing/indiretos/serviços (procurement que contrata agência/estúdio)
- Comercial/Vendas (somente diretoria e gerência de marketing de vendas/trade)

### Classificação (obrigatória para cada pessoa)

| prioridade | papel | quem |
|---|---|---|
| **1** | Decisor | C-level, VP, Diretor(a), Head das áreas acima |
| **2** | Influenciador-chave | Gerente/Head **diretamente** ligado a configurador, 3D/CGI, conteúdo de produto, lançamentos ou site |
| **2** | Influenciador | Gerentes e coordenadores sêniores das áreas acima |
| **3** | Usuário/Ponto de entrada | Analistas, especialistas, coordenadores júnior das áreas acima |
| **9** | Fora | RH, Finanças/Auditoria, Jurídico, TI de infraestrutura, manufatura/qualidade, concessionárias. **Não trazer**, a não ser que já tenha vindo junto |

**Tamanho do comitê por conta (alvo):** até **5** prioridade 1, **6 a 12** prioridade 2,
até **10** prioridade 3. Total entre ~10 e 25. Comitê grande não é melhor: priorize
qualidade e cobertura (pelo menos 1 decisor de Marketing ou Produto por conta).

`area` (use exatamente um destes): Marketing · Compras/Procurement · Produto ·
TI/Digital · Financeiro/Controladoria · Engenharia/Design · Compliance/Jurídico ·
Comercial/Vendas · Operações · RH · Outros

`senioridade` (use exatamente um destes): C suite · Vp · Owner · Head · Director ·
Manager · Senior · Entry · Intern

## 3. Dados de contato e créditos

- **E-mail:** revelar para prioridade 1, 2 e 3. Trazer o status do Apollo convertido
  para: Verificado · Válido · Extrapolado · catch-all · Indisponível · Inválido.
- **Telefone/celular:** só para **prioridade 1 e 2**. Antes de gastar créditos de
  telefone, me mostre a **estimativa de créditos** e espere meu OK.
- Sempre traga a URL do LinkedIn da pessoa e o **Apollo Contact ID**.
- Antes de começar, me mostre quantos créditos o trabalho todo deve consumir. Faça
  primeiro **3 contas como amostra** (sugestão: General Motors, Fiat e Iveco) e espere
  minha validação antes de rodar o resto.

## 4. Saída: dois CSVs (UTF-8, vírgula, cabeçalho exatamente assim)

**`abm_contas.csv`**, uma linha por conta:

```
conta,dominio,dominios_extra,nome_linkedin,linkedin_empresa_url,segmento,cidade,estado,pais,funcionarios,apollo_org_id,situacao,observacao
```

- `conta`: nome comercial no Brasil (ex.: "General Motors do Brasil").
- `nome_linkedin`: o nome **exato** da página da empresa no LinkedIn (é o que aparece
  no relatório do LinkedIn Ads e é usado para cruzar o score).
- `segmento`: carros · motos · caminhões e ônibus · máquinas agrícolas ·
  máquinas de construção · implementos rodoviários
- `situacao`: `nova` ou `completar`.
- `observacao`: ambiguidades (ex.: "global x Brasil", "não achei no Apollo").

**`abm_comite.csv`**, uma linha por pessoa:

```
dominio_conta,nome,cargo,prioridade,papel,area,senioridade,email,email_status,telefone,celular,linkedin_url,cidade,estado,pais,departamento_apollo,apollo_contact_id
```

- `dominio_conta` deve ser igual ao `dominio` da conta no outro arquivo.
- `papel` e `prioridade` conforme a tabela da seção 2.
- Não repetir pessoas (mesmo Apollo Contact ID ou mesmo e-mail).

No final, um resumo por conta: total de pessoas por prioridade, quantos e-mails
verificados e créditos gastos.
