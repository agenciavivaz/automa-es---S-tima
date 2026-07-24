-- ============================================================================
-- Calculadora de ROI NGI (Sétima) — schema Supabase
-- PRD seção 8.2. Rodar no SQL Editor do projeto.
-- ============================================================================

-- Benchmarks editáveis pelo time, sem deploy
create table if not exists benchmarks (
  id            uuid primary key default gen_random_uuid(),
  setor         text not null,
  chave         text not null,
  valor         numeric not null,
  unidade       text,
  fonte         text,
  atualizado_em timestamptz default now(),
  unique (setor, chave)
);

-- Cada execução da calculadora (inclusive sem lead)
create table if not exists calculos (
  id            uuid primary key default gen_random_uuid(),
  share_id      text unique not null,
  session_id    text not null,
  inputs        jsonb not null,
  resultados    jsonb not null,
  setor         text,
  concluido     boolean default false,
  criado_em     timestamptz default now()
);

-- Leads capturados no gate
create table if not exists leads (
  id            uuid primary key default gen_random_uuid(),
  calculo_id    uuid references calculos(id),
  nome          text not null,
  email         text not null,
  empresa       text,
  cargo         text,
  email_tipo    text,          -- 'corporativo' | 'gratuito'
  score         integer,
  tier          text,          -- 'A' | 'B' | 'C'
  utm           jsonb,
  crm_synced    boolean default false,
  criado_em     timestamptz default now()
);

-- Eventos para funil e análise de drop-off
create table if not exists eventos (
  id            uuid primary key default gen_random_uuid(),
  calculo_id    uuid references calculos(id),
  tipo          text not null,
  payload       jsonb,
  criado_em     timestamptz default now()
);

create index if not exists calculos_criado_em_idx on calculos (criado_em desc);
create index if not exists calculos_setor_idx on calculos (setor);
create index if not exists leads_tier_idx on leads (tier);
create index if not exists leads_email_idx on leads (lower(email));
create index if not exists eventos_tipo_idx on eventos (tipo, criado_em desc);

-- ============================================================================
-- RLS: benchmarks é público somente-leitura; o resto só via service role.
-- Os route handlers usam a service role key, que ignora RLS. Nenhuma dessas
-- tabelas é exposta ao client.
-- ============================================================================
alter table benchmarks enable row level security;
alter table calculos   enable row level security;
alter table leads      enable row level security;
alter table eventos    enable row level security;

drop policy if exists benchmarks_leitura_publica on benchmarks;
create policy benchmarks_leitura_publica
  on benchmarks for select
  to anon, authenticated
  using (true);

-- calculos, leads e eventos ficam sem policy: nenhum acesso anon/authenticated.

-- ============================================================================
-- Benchmarks — PLACEHOLDERS. Pendência bloqueante de launch (PRD 5.3).
-- Substituir por valores validados pelo time da Sétima e backtestados contra
-- 2-3 projetos reais ANTES de publicar a ferramenta.
-- `setor = '*'` indica valor global (não varia por setor).
-- ============================================================================
insert into benchmarks (setor, chave, valor, unidade, fonte) values
  ('automotivo',    'custo_diaria', 45000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('maquinas_agro', 'custo_diaria', 38000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('bens_consumo',  'custo_diaria', 18000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('moda',          'custo_diaria', 22000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('eletronicos',   'custo_diaria', 20000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('outro',         'custo_diaria', 20000, 'BRL', 'PLACEHOLDER — validar com time Sétima'),
  ('simples',       'custo_twin_por_sku',  4500, 'BRL', 'PLACEHOLDER — tabela de precificação interna'),
  ('medio',         'custo_twin_por_sku', 12000, 'BRL', 'PLACEHOLDER — tabela de precificação interna'),
  ('complexo',      'custo_twin_por_sku', 28000, 'BRL', 'PLACEHOLDER — tabela de precificação interna'),
  ('*', 'custo_desdobramento_peca',  180, 'BRL',  'PLACEHOLDER — tabela de precificação interna'),
  ('*', 'custo_reshoot_variacao',   2800, 'BRL',  'PLACEHOLDER — a definir'),
  ('*', 'custo_adaptacao_mercado', 15000, 'BRL',  'PLACEHOLDER — a definir'),
  ('*', 'custo_pos_producao_peca',   450, 'BRL',  'PLACEHOLDER — a definir'),
  ('*', 'custo_manutencao_twin',     900, 'BRL',  'PLACEHOLDER — a definir'),
  ('*', 'fator_dias_por_diaria',     3.5, 'dias', 'PLACEHOLDER — setup, logística e aprovação'),
  ('*', 'uplift_conversao',         0.09, 'ratio', 'LP da Sétima (+9% em vendas)'),
  ('*', 'uplift_engajamento',       0.66, 'ratio', 'LP da Sétima (+66% de engajamento)')
on conflict (setor, chave) do nothing;

-- ============================================================================
-- LGPD: exclusão de dados por e-mail (PRD 8.7).
-- select excluir_dados_do_lead('pessoa@empresa.com');
-- ============================================================================
create or replace function excluir_dados_do_lead(p_email text)
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  removidos integer;
begin
  with alvo as (
    delete from leads where lower(email) = lower(p_email) returning calculo_id
  )
  select count(*) into removidos from alvo;

  return removidos;
end;
$$;
