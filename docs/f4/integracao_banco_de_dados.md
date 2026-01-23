# Fase 4 — Tópico 3: Integração com Banco de Dados

## Objetivos
- Conectar APIs ao modelo de dados criado na Fase 3, usando SQLAlchemy.
- Otimizar consultas para reduzir latência, evitar N+1 e apoiar paginação/filtragem.
- Implementar cache seletivo para respostas com alto custo computacional, com invalidação segura.

## Estado Atual
- Conexão com BD via `backend/app/database.py` usando `DATABASE_URL` e `READ_DATABASE_URL` (replica de leitura opcional).
- Sessões `get_db()` (escrita) e `get_read_db()` (leitura) com `SessionLocal` e pooling do SQLAlchemy.
- Logs de slow query configuráveis (`SLOW_QUERY_MS`) e timeout por instrução (`DB_STATEMENT_TIMEOUT_MS`).
- Inicialização condicional do schema por env: `CREATE_DB_SCHEMA_ON_START` desabilitado por padrão; migrations SQL em `backend/migrations/*.sql`.
- Middleware de slow request com limiar `SLOW_REQUEST_MS` e paginação capada pelo env `API_MAX_LIMIT`.
- Endpoints administrativos de cache implementados: `GET /admin/cache/stats`, `POST /admin/cache/invalidate`.

## Conexão e Gestão de Sessão
- engine configurado com overrides via env (`echo`, `pool_size`, `max_overflow`, `pool_recycle`, `pool_timeout`).
- `connect_args` dinâmico para PostgreSQL: `sslmode` e `statement_timeout` via `DB_STATEMENT_TIMEOUT_MS`.
- Sessões por request (`Depends(get_db)`/`Depends(get_read_db)`) com `yield` e `db.close()` ao final.
- Réplica de leitura: usar `get_read_db` em endpoints de leitura intensiva para aliviar a primária.
- Em produção: desabilitar `echo` e ajustar pool via variáveis de ambiente conforme carga.

## Mapeamento de APIs para Modelos
- Autenticação: `POST /login` vincula a `models.Usuario` e valida credenciais.
- Usuários/Departamentos: CRUD em `/admin/usuarios` e `/admin/departamentos` usando `Session` e schemas Pydantic.
- Importações e ETL: registros em `models.Importacao` e processamento via `ai_service/validation_utils`.
- Dashboard: agregações e filtros em rotas `/dashboard/*` lendo tabelas de vendas/clientes/indicadores.
- Indicadores e Limiares: `router_indicadores` e `router_limiares` interagem com `indicadores_customizados` e `limiares_indicadores`.
- Notificações: CRUD básico em `/notificacoes` ligado a `models.Notificacao`.

## Padrões de Consultas
- Projeções: selecionar apenas colunas necessárias (`query(...).with_entities(...)`).
- Filtragem no BD: aplicar filtros do `schemas.FiltrosDashboard` no SQL, não em memória.
- Paginação: usar `limit/offset` e ordenação determinística.
- Carregamento de relações: `selectinload/joinedload` para evitar N+1 em listagens.
- Índices: garantir índices nos campos usados em filtros/joins (ver Alembic e scripts/inspeções).

## Otimizações de Performance
- Agregações: pré-agregar por período (dia/semana/mês) quando possível.
- Materialização: considerar views materializadas para relatórios pesados e atualizar por scheduler.
- Profile: habilitar logs de tempo por rota, medir p95/p99 e revisar planos de execução (`EXPLAIN ANALYZE`).
- Batch: operações em lote para updates/deletes massivos; evitar commit por item.

## Estratégia de Cache
- Camada: `backend/app/cache_service.py` com chaves de cache e estatísticas.
- Invalidação: `POST /admin/cache/invalidate` aceita `CacheInvalidationRequest` (por padrão, prefixo/padrão/chaves específicas).
- TTL: configurar TTLs distintos por métrica com overrides via env; incluir filtros/cliente/usuário nas chaves para evitar colisões.
- Cache de leitura: aplicar em endpoints de agregação e catálogos estáveis; evitar cache em mutações.

## Observabilidade
- Métricas: coletar tempo de resposta, taxa de acerto do cache, taxa de invalidação.
- Logs: registrar consultas >N ms, incluir parâmetros e cardinalidade.
- Requests lentos: middleware com limiar `SLOW_REQUEST_MS` registra método e caminho.
- Alertas: integrar com `alerts_service` para quedas de performance e picos de erro.

## Boas Práticas de Produção
- Migrations: usar Alembic para evolução do schema, desabilitar `create_all` em produção.
- CORS: restringir origens confiáveis no deploy.
- Conexões: limitar pool e reciclar para evitar quedas de conexões persistentes.
- Segurança: parametrização de queries, validação de payloads via Pydantic.

## Checklist de Integração
- [x] Revisar índices nas colunas filtradas/ordenadas/associadas (ver `backend/migrations/0003_indices_saas.sql`).
- [x] Aplicar `selectinload/joinedload` onde houver N+1 (indicadores/limiares; usuários/importações).
- [x] Implementar paginação consistente nas listagens (indicadores/limiares; admin já usa `skip/limit`).
- [x] Configurar TTLs por métrica com overrides via env e chaves parametrizadas.
- [x] Configurar invalidação dirigida após mutações (cliente/usuário).
- [x] Medir tempos de consulta e ajustar queries/índices (logs de slow query via `SLOW_QUERY_MS`).
- [x] Parametrizar `echo` e pool via env; desativado em produção por configuração.
- [x] Padronizar uso de migrations SQL e desabilitar `Base.metadata.create_all` no startup em produção.