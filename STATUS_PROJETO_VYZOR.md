# Vyzor — Relatório de Status e Organização do Projeto

Este documento apresenta, de forma objetiva e profissional, o escopo geral, a organização, a arquitetura e o status atual do projeto Vyzor, para entrega e avaliação pela empresa.

## Escopo e Objetivo
- Plataforma para gestão integrada de dados, indicadores e automação de processos.
- Backend em FastAPI com integrações modulares (ex.: MySQL Readonly, HubSpot) e persistência via SQLAlchemy/Alembic.
- Frontend web para administração, configuração e testes de integrações.
- Suporte a multi‑tenant, autenticação JWT e observabilidade básica.

## Organização do Projeto
- Raiz do repositório contém documentação, requisitos, scripts e arquivos de configuração.
- Backend: `backend/` com código FastAPI, modelos, schemas, rotas, testes e Dockerfile.
- Frontend provisório: `frontend/supa/` com páginas HTML/JS estáticas para administração.
- Frontend final (em desenvolvimento): `atualizando/` com estrutura Flask/HTML/CSS/JS que será consolidada e implantada na versão final.
- Documentação por fase: `docs/` (F3, F4, F5) com guias de APIs, integrações e infraestrutura.
- Migrações: `alembic/` (versionadas) e scripts SQL auxiliares em `backend/migrations/` e `scripts/`.
- Dependências: `requirements.txt` (raiz) e `backend/requirements.txt`.
- Licença: `LICENSE` (MIT).

## Arquitetura Técnica
- Backend: FastAPI (Python 3.11), SQLAlchemy 2.x, Alembic, Pydantic v2.
- Banco de dados: PostgreSQL via `DATABASE_URL`.
- Conectores: arquitetura baseada em `Connector` e `ConnectorRegistry` (ex.: `mysql_readonly`, `hubspot`).
- Frontend: páginas estáticas em `frontend/supa` e projeto em atualização em `atualizando/` (Flask/HTML/JS).
- Deploy/CI: Dockerfile do backend e pipelines em `.github/workflows` (ambientes dev/prod).

## Estrutura (resumo)
```
vyzor/
├── backend/                # FastAPI, modelos, rotas, conectores, testes
├── frontend/supa/          # Frontend provisório (HTML/JS estático)
├── atualizando/            # Frontend final (em evolução)
├── alembic/                # Migrações Alembic
├── docs/                   # Documentação por fases e guias
├── requirements.txt        # Dependências raiz
├── backend/requirements.txt# Dependências do backend
├── scripts/                # Utilitários e inspeções de BD
├── LICENSE                 # Licença MIT
└── README.md               # Visão geral do projeto
```

## Estado Atual — Frontend
- Provisório em uso: `frontend/supa/` (páginas `index.html`, `login.html`, `integracoes.html`, `configuracoes.html`, `usuarios.html`).
  - Funções: login, exibição de conectores, modal de configuração e teste de integrações.
  - Consome APIs do backend com token JWT.
- Final em desenvolvimento: `atualizando/` (Flask/HTML/JS/CSS).
  - Status: em atualização para consolidar design, rotas e integração completa.
  - Planejamento: quando 100% concluído, será implantado como frontend definitivo.
 - Observação: o frontend provisório não está 100% completo; serve para validar funcionalidades principais (login, configurações e testes de integrações).

## Estado Atual — Backend
- Entrypoint: `backend/app/main.py` (FastAPI).
- Persistência: `backend/app/models.py`, `backend/app/crud.py`, migrações Alembic.
- Autenticação: `backend/app/auth.py` com JWT.
- Integrações: `backend/app/routes/integrations.py` e `backend/app/conectores/`.
- Testes automatizados: `backend/tests/` cobrindo autenticação, cache, ETL, regras de negócio e relatórios.
- Integrações implementadas:
  - MySQL Readonly: `backend/app/conectores/mysql_readonly.py` com `test_connection` real via `PyMySQL` (ping/`SELECT 1`) e `get_health`.
  - HubSpot: base estruturada (em progresso conforme docs), seguindo padrão de `Connector`.
 - Status: praticamente 100% concluído; novas alterações serão pontuais conforme adaptações e necessidades do frontend.
 - Testes completos pelo Swagger/Docs da FastAPI: acessar `http://localhost:8000/docs` ou `http://localhost:8001/docs` (dependendo da porta utilizada).

## Principais Endpoints
- Autenticação:
  - `POST /login` — retorna JWT.
- Integrações:
  - `GET /integrations/connectors` — lista conectores disponíveis.
  - `GET /integrations/{connector_key}/config` — estado da configuração por cliente.
  - `POST /integrations/{connector_key}/configure` — salva credenciais por cliente.
  - `POST /integrations/{connector_key}/test` — executa teste de conexão com credenciais salvas.
  - `GET /integrations/healthz` — health agregado por conector.
- Dashboards/Relatórios: conforme serviços e rotas já implementadas (`backend/app/routes/` e serviços associados).

## Execução Local (desenvolvimento)
- Variáveis de ambiente:
  - `DATABASE_URL` para PostgreSQL.
  - Segredos JWT e configs em `.env`/`security.env`.
- Dependências:
  - `pip install -r requirements.txt`
  - `pip install -r backend/requirements.txt`
- Iniciar API:
  - `uvicorn app.main:app --host 127.0.0.1 --port 8000` (na pasta `backend/`).
  - Alternativa (evitar conflito): `--port 8001`.
- Script de inicialização unificado (Windows):
  - `frontatualizado/Finalvyzor/Ambiente/iniciar_projeto.bat` cria venv, instala deps, inicia backend e frontend.
 - Testar backend completo via Swagger:
   - Após iniciar, abrir `http://localhost:8000/docs` ou `http://localhost:8001/docs` no navegador.

## Segurança
- Licença MIT em `LICENSE`.
- Credenciais de integrações não são retornadas nas leituras de configuração.
- JWT para autenticação e autorização.
- Observabilidade e logs básicos em execução local; sem exposição de segredos em logs.

## Deploy e CI/CD
- Backend: `backend/Dockerfile` para containerização.
- Workflows: `.github/workflows/main_vyzor-backend-dev.yml` e `main_vyzor-backend-prod.yml` para automação de build/deploy.
- Estratégia: implantar inicialmente com frontend provisório; migrar para `atualizando/` assim que concluir o frontend final.

## Integrações Externas (status)
- MySQL Readonly:
  - `PyMySQL` adicionado às dependências.
  - `test_connection` real, `get_health` atualizado.
  - Frontend provisório permite salvar e testar configurações.
- HubSpot:
  - Estrutura base pronta; implementação completa alinhada ao planejamento (`docs/f5/`).

## Pendências e Próximos Passos
- Consolidar `atualizando/` como frontend final (design, rotas, integração completa e testes E2E).
- Expandir conectores e fluxos (OAuth, tokens, escopos mínimos).
- Observabilidade (métricas, logs estruturados, tracing) e hardening de segurança.
- Documentação adicional (guia de operações, SLO/SLI, modelos de dados estendidos).

## Referências Úteis
- `README.md` — Visão geral detalhada.
- `docs/` — Guias por fase (APIs, lógica de negócios, integração de dados e infraestrutura).
- `scripts/` — Inspeção de tabelas, índices e migrações.
- `frontend/supa/` e `atualizando/` — Frontends (provisório e final).

---
Este relatório reflete o estado atual do repositório e orienta a avaliação e o planejamento de próximos passos, incluindo a transição do frontend provisório para o frontend final em `atualizando/` quando estiver 100% concluído.