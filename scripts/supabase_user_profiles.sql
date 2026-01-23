-- Supabase: criar tabela de perfis de usuário e políticas RLS
-- Execute este arquivo no SQL Editor do seu projeto Supabase

-- 1) Tabela para espelhar usuários do Auth
create table if not exists public.user_profiles (
  id uuid primary key,
  email text unique,
  created_at timestamptz default now(),
  last_login_at timestamptz
);

-- 2) Ativar RLS
alter table public.user_profiles enable row level security;

-- 2.1) Políticas RLS (Postgres não suporta "IF NOT EXISTS" em CREATE POLICY)
-- Removemos e recriamos para garantir idempotência

-- SELECT: usuário pode ler apenas seu próprio registro
drop policy if exists "select own profile" on public.user_profiles;
create policy "select own profile"
  on public.user_profiles
  for select
  using (id = auth.uid());

-- INSERT: usuário só pode inserir um registro com seu próprio id
drop policy if exists "insert own profile" on public.user_profiles;
create policy "insert own profile"
  on public.user_profiles
  for insert
  with check (id = auth.uid());

-- UPDATE: usuário só pode atualizar seu próprio registro
drop policy if exists "update own profile" on public.user_profiles;
create policy "update own profile"
  on public.user_profiles
  for update
  using (id = auth.uid())
  with check (id = auth.uid());

-- 3) (Opcional) Índice para consultas por email
create index if not exists idx_user_profiles_email on public.user_profiles (email);

-- Observação:
-- Este arquivo não cria trigger em auth.users. Em vez disso,
-- o frontend fará upsert do perfil ao efetuar login (ver app.js).
-- Se desejar trigger automática no cadastro, posso fornecer o script posteriormente.