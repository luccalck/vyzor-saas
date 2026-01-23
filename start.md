Guia Rápido: Ambiente de Desenvolvimento VYZOR (Atualizado)
Este guia reflete o estado atual do código: usamos FastAPI no backend, Redis como cache e não utilizamos mais Reflex para frontend.

Pré-requisitos
- Docker Desktop em execução.
- Ambiente virtual Python ativo (Windows PowerShell): `./venv/Scripts/Activate.ps1`.
- Arquivo `.env` na raiz com pelo menos:
  - `DATABASE_URL` (ex.: URL do Supabase PostgreSQL)
  - `JWT_SECRET` (chave para tokens JWT)
  - `ENVIRONMENT=development` (para permitir o seed de desenvolvimento)

Passo 1: Iniciar o cache (Redis)
- Inicie o contentor Redis:
  - `docker start vyzor-redis`
- Se ainda não existir, crie-o:
  - `docker run -d -p 6379:6379 --name vyzor-redis redis`

Passo 2: Migrar a base de dados (Alembic)
- Garanta que `DATABASE_URL` está definido no `.env`.
- Aplique todas as migrações pendentes:
  - `alembic upgrade head`
- Observação: todas as mudanças de esquema devem ser feitas via código + Alembic.

Passo 3: Popular dados mínimos de desenvolvimento (seed)
- Com `ENVIRONMENT=development` no `.env`, execute:
  - `python -m backend.app.seed_dev`
- O script cria:
  - Departamento "Vendas" e usuário admin `admin@local.dev`.
  - Uma importação básica e registros SAAS (financeiro/produtos/operacional).
  - Indicadores e metas simples.

Passo 4: Iniciar o backend (FastAPI / Uvicorn)
- Com o venv ativo, execute:
  - `uvicorn backend.app.main:app --reload --env-file .env
- Backend disponível em `http://127.0.0.1:8000`.

Resumo do ambiente
- Cache (Redis): `localhost:6379` (Docker)
- Backend (API): `http://127.0.0.b1:8000`

Notas importantes
- Não utilizamos Reflex atualmente; qualquer referência anterior foi removida.
- Evite executar o seed em produção: o script só roda com `ENVIRONMENT=development`.
- Se alterar modelos, gere migração com:
  - `alembic revision --autogenerate -m "descrição"`
  - `alembic upgrade head`
- Não chame `Base.metadata.create_all()` no código; use apenas migrações Alembic para criar/alterar tabelas.
- Integridade: garantimos índices únicos compatíveis com os modelos em `usuarios.email`, `saas_registros_financeiros.id_transacao` e `saas_registros_operacionais.id_evento`.

## Verificação e manutenção de índices (Alembic-only)

- Para verificar os índices atuais, rode: `python scripts/inspect_indexes.py` (usa `DATABASE_URL` ou fallback do `alembic.ini`).
- Índices esperados nas tabelas SAAS:
  - `saas_registros_financeiros`: `ix_saas_financeiros_id_transacao` (UNIQUE)
  - `saas_registros_operacionais`: `ix_saas_operacionais_id_evento` (UNIQUE)
  - `saas_registros_produtos`: `ix_saas_produtos_id_venda` e `ix_saas_produtos_sku_produto`
- Aplique mudanças de schema somente via Alembic: `alembic upgrade head`.
- Evite criar índices/constraints fora do Alembic para prevenir nomes duplicados e drift.
- Se precisar corrigir inconsistências, crie uma nova migration com `op.create_index`/`op.drop_index` conforme necessário.
