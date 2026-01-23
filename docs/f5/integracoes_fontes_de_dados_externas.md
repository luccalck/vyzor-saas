# Fase 5 – Integrações com Fontes de Dados Externas

Checklists práticos para acompanhar requisitos do tópico, estado atual e o plano de implementação.

## Checklist de Requisitos do Tópico
- [ ] Conectar APIs da VYZOR a bancos de dados externos
- [ ] Integrar CRMs/ERPs/ferramentas analíticas (por cliente/escopo)
- [ ] Criar conectores modulares e reusáveis
- [ ] Implementar autenticação segura (OAuth 2.0, tokens, service accounts)
- [ ] Expor health checks e métricas por conector

## Checklist de Infraestrutura Já Disponível (reutilizável)
- [x] Autenticação interna via JWT (`POST /login`, `auth.py`)
- [x] Persistência interna via SQLAlchemy (`database.py`, `models.py`, `crud.py`)
- [x] Cache/Materialização com Redis ou memória (`cache_service.py`)
- [x] Agendador de tarefas periódicas (`scheduler_service.py`)
- [x] Health checks específicos de conectores externos (stub via `/integrations/healthz`)
- [x] Página de teste frontend `frontend/supa/integracoes.html` usando mesma conexão com backend
- [ ] Endpoints de administração para integrações por cliente

## Checklist de Arquitetura de Conectores (a implementar)
- [x] Interface base `Connector` com: `authenticate`, `fetch`, `push`, `test_connection`, `get_health`, `map_to_internal_models`
- [x] `ConnectorRegistry` com chave → classe (ex.: `hubspot`, `mysql_readonly`)
- [ ] Configuração por cliente (`client_integrations`) com `connector_key`, `auth_type`, escopos e credenciais seguras
- [x] Rotas base: `GET /integrations/connectors` e `GET /integrations/healthz`
- [ ] Rotas admin para criar/atualizar/listar/testar integrações
- [ ] Sincronização incremental (pull/push) com periodicidade configurável
- [ ] Cache e invalidação por cliente/fonte e parâmetros
- [ ] Mapeamento/validação de payloads externos para modelos internos

## Checklist de Segurança
- [ ] Armazenar segredos em local seguro (env/vault/KMS)
- [ ] Não logar tokens; mascarar credenciais em logs
- [ ] Princípio do menor privilégio (escopos mínimos)
- [ ] Rotação de tokens e renovação automática quando aplicável
- [ ] Auditoria de ações (quem configurou/ativou, quando e com quais escopos)

## Checklist de Observabilidade e Resiliência
- [x] `/integrations/healthz` agregando status por conector/cliente (stub)
- [ ] Métricas: latência, erros, throughput, rate limit
- [ ] Retentativas com backoff exponencial
- [ ] Circuit breaker simples e desativação temporária em falhas
- [ ] Logs estruturados com correlação por cliente/conector

## Checklist de Próximos Passos
- [x] Fase A: Interface `Connector`, `ConnectorRegistry`, modelos de configuração e rotas básicas
- [ ] Fase B: Fluxos de autenticação (OAuth 2.0 e tokens de API)
- [ ] Fase C: Endpoints admin de integrações (CRUD, teste de conexão, health)
- [ ] Fase D: Conectores de referência (`mysql_readonly` e `hubspot`)
- [ ] Fase E: Sincronização periódica, métricas por conector, cache/retentativas
- [ ] Fase F: Segurança (hardening de segredos/escopos), testes e documentação

Referência: detalhes e plano por fases em `docs/f5/requisitos_pendentes.md`.