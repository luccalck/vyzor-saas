# VYZOR — Plataforma de Gestão Integrada e Automação via IA

VYZOR é uma aplicação completa para gestão de dados, análise de indicadores, automação de processos e integração com fontes externas. O projeto é composto por um backend em FastAPI (Python 3.11), persistência com SQLAlchemy/Alembic, páginas de frontend estáticas para administração e testes, além de conectores modulares para CRMs/ERPs e bancos de dados externos.

## Sumário
- Visão Geral
- Principais Funcionalidades
- Arquitetura
- Estrutura do Projeto
- Requisitos
- Configuração
- Execução Local
- Banco de Dados e Migrações
- Testes Automatizados
- Integrações Externas (Fase 5)
- Endpoints Principais
- Frontend (páginas Supa)
- Deploy (Docker e CI/CD)
- Segurança
- Troubleshooting
- Roadmap
- Contribuição
- Licença

## Visão Geral
- Plataforma multi‑tenant com autenticação via JWT.
- Persistência de dados estruturada com SQLAlchemy e Alembic.
- Dashboards e indicadores customizados, com materialização e agendamento de tarefas.
- Conectores de referência (ex.: `mysql_readonly`, `hubspot`) com rotas de configuração, teste e health.
- Páginas frontend para login, integração e configuração rápida.

## Principais Funcionalidades
- Autenticação de usuários (`POST /login`) e perfis.
- Dashboards de negócio (usuário/admin) e indicadores customizados.
- ETL, cache e materialização com schedulers.
- Integrações por cliente com armazenamento de credenciais seguro e testes de conexão.
- Health checks agregados por conector.

## Arquitetura
- Backend: FastAPI 0.116, SQLAlchemy 2.0, Pydantic v2, Alembic.
- Frontend: páginas HTML/JS estáticas em `frontend/supa` que consomem APIs do backend.
- Banco: PostgreSQL (via `DATABASE_URL`).
- Integrações: conectores modulares com `ConnectorRegistry` e `Connector` base.
- Deploy: Docker e pipelines em `.github/workflows`.

## Estrutura do Projeto
```
vyzor/
├── backend/
│   ├── app/                # Código principal do backend
│   │   ├── main.py         # Entrypoint FastAPI
│   │   ├── auth.py         # Autenticação JWT
│   │   ├── models.py       # Modelos SQLAlchemy
│   │   ├── crud.py         # Operações de persistência
│   │   ├── schemas.py      # Schemas Pydantic
│   │   ├── routes/         # Rotas (ex.: integrações)
│   │   ├── conectores/     # Conectores (mysql_readonly, hubspot)
│   │   └── scheduler_service.py, cache_service.py, etc.
│   ├── requirements.txt    # Dependências do backend
│   ├── migrations/         # Scripts SQL auxiliares
│   └── tests/              # Testes automatizados
├── frontend/
│   └── supa/               # Páginas estáticas de admin/testes
├── alembic/                # Migrações Alembic
├── requirements.txt        # Dependências raiz
├── .env / security.env     # Configurações sensíveis
└── docs/                   # Documentação por fase
```

## Requisitos
- `Python 3.11`
- Banco de dados PostgreSQL acessível via `DATABASE_URL`.
- (Opcional) MySQL acessível para testes do conector `mysql_readonly`.

Dependências relevantes:
- Backend: ver `backend/requirements.txt`.
- Raiz: ver `requirements.txt`.

## Configuração
1. Configure variáveis de ambiente:
   - `DATABASE_URL`: URL de conexão PostgreSQL, ex.: `postgresql://user:pass@host:5432/dbname`.
   - Segredos de JWT e afins em `.env`/`security.env` (ex.: chaves de assinatura).
2. Ajuste `alembic.ini` se necessário (seção `sqlalchemy.url`).
3. Instale dependências:
   - `pip install -r requirements.txt`
   - `pip install -r backend/requirements.txt`

## Execução Local
- Executar backend (porta padrão local):
  - `cd backend`
  - `uvicorn app.main:app --host 127.0.0.1 --port 8000`
- Se a porta `8000` estiver ocupada:
  - `uvicorn app.main:app --host 127.0.0.1 --port 8001`
- A API ficará disponível em `http://127.0.0.1:8000/` (ou porta escolhida).

## Banco de Dados e Migrações
- Aplicar migrações Alembic:
  - `alembic upgrade head`
- Scripts auxiliares em `scripts/`:
  - `scripts/list_all_tables.py`, `scripts/inspect_tables.py`, `scripts/inspect_indexes.py`.

## Testes Automatizados
- Execução de testes:
  - `cd backend`
  - `pytest -q`
- Suite de testes cobre autenticação, cache, ETL, agendador, relatórios e regras de negócio.

## Integrações Externas (Fase 5)
- Interface base `Connector` com métodos: `authenticate`, `fetch`, `push`, `test_connection`, `get_health`, `map_to_internal_models`.
- Registro de conectores via `ConnectorRegistry` (`hubspot`, `mysql_readonly`).
- Persistência de configuração por cliente em `integracoes_cliente`.
- Endpoints principais:
  - `GET /integrations/connectors`: lista conectores disponíveis.
  - `GET /integrations/healthz`: health agregado por conector/cliente.
  - `GET /integrations/{connector_key}/config`: retorna estado `IntegracaoConfigState` (200, `exists=true/false`).
  - `POST /integrations/{connector_key}/configure`: salva credenciais por cliente.
  - `POST /integrations/{connector_key}/test`: testa conexão usando credenciais salvas.

### Conector MySQL Readonly
- Dependência: `PyMySQL` (já adicionada).
- Credenciais esperadas: `host`, `port` (padrão `3306`), `user`, `password` (pode ser vazio), `database` (opcional).
- Teste de conexão executa `SELECT 1` e retorna:
  - `status: ok` em sucesso
  - `status: error` com mensagem em falha
  - `status: not_configured` se faltarem `host` ou `user`
- Health reporta `ok`, `degraded` (credenciais presentes mas conexão falhou) ou `not_configured`.

### Fluxo sem cliente associado
- Usuários sem `cliente_id` não recebem 403 em leitura de configuração; o `GET /config` retorna `exists=false` (200).
- `POST /configure` e `POST /test` fazem auto‑provisionamento: criam/associam um cliente ao usuário para salvar/testar a integração.

## Endpoints Principais (exemplos)
- `POST /login`: autenticação; retorna token JWT.
- `GET /dashboard/filtros-disponiveis`: filtros do dashboard interativo.
- `GET /integrations/connectors` e `GET /integrations/healthz`: catálogo e saúde de conectores.
- Ver `backend/app/main.py` e `backend/app/routes/` para demais rotas.

## Frontend (páginas Supa)
- Localização: `frontend/supa/`.
- Páginas úteis:
  - `login.html`: autenticação e armazenamento de token.
  - `integracoes.html`: grid de conectores, modal de configuração e botões de salvar/testar.
  - `configuracoes.html`, `usuarios.html`, `index.html`: utilitários e navegação.
- As páginas chamam a API do backend, usando token JWT salvo em `localStorage`.

## Deploy (Docker e CI/CD)
- Docker:
  - `backend/Dockerfile` prepara imagem com `uvicorn` servindo `app.main:app`.
- CI/CD:
  - Pipelines em `.github/workflows/` para backends `dev` e `prod`.

## Segurança
- Não expor credenciais em respostas de leitura.
- Armazenar segredos em `.env`/`security.env` ou vault.
- Princípio do menor privilégio (escopos mínimos por conector).
- Evitar logs de tokens e segredos.

## Troubleshooting
- Porta ocupada ao iniciar:
  - Use outra porta: `--port 8001`.
- `DATABASE_URL` ausente:
  - Defina no ambiente ou em `alembic.ini`.
- Falha no teste do MySQL:
  - Verifique se o serviço MySQL está ativo, host/porta corretos e usuário/senha compatíveis.
- Dependência não instalada:
  - `pip install -r backend/requirements.txt` (inclui `PyMySQL`).

## Roadmap
- Fase B: Fluxos de autenticação externa (OAuth 2.0 / tokens) e armazenamento seguro.
- Fase C: Endpoints admin para CRUD de integrações.
- Fase D: Conectores funcionais (MySQL/HubSpot) com sincronização.
- Fase E: Métricas, cache/retentativas, observabilidade.
- Fase F: Hardening de segurança, testes e documentação final.

## Contribuição
- Abra issues e PRs com descrição clara.
- Siga o padrão de código e não remova linhas não relacionadas (preservar baseline).

## Licença
Consulte o arquivo `LICENSE` na raiz do repositório.