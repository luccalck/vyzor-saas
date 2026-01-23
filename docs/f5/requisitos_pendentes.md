# Fase 5 – Requisitos Pendentes (Integrações com Fontes Externas)

Status geral: Em planejamento. Não há conectores externos implementados no baseline atual (`origin/main`). Use os checklists abaixo para acompanhar.

## Checklist por Requisito (itens a implementar)
- [x] Definir interface base `Connector`
  - [x] Métodos: `authenticate`, `fetch`, `push`, `test_connection`, `get_health`, `map_to_internal_models`
- [x] Implementar `ConnectorRegistry`
  - [x] Chave do conector (`hubspot`, `mysql_readonly`, etc.) mapeada para classe
- [ ] Persistir configuração por cliente (`client_integrations`)
  - [ ] Campos: `cliente_id`, `connector_key`, `auth_type`, credenciais seguras, escopos, parâmetros
- [ ] Autenticação segura
  - [ ] Fluxo OAuth 2.0 (authorization code + refresh) para CRMs/ERPs
  - [ ] Tokens de API/Service Accounts para DBs/Analytics
- [ ] Rotas de administração
  - [ ] CRUD de integrações por cliente
  - [ ] Teste de conexão e health por conector/cliente
- [ ] Sincronização e agendamento
  - [ ] Jobs no `scheduler_service` por integração
  - [ ] Pull incremental e push quando aplicável; periodicidade configurável
- [ ] Cache e resiliência
  - [ ] Reuso de `cache_service` e invalidação dirigida
  - [ ] Retentativas exponenciais e circuit breaker simples
- [ ] Mapeamento e validação
  - [ ] Normalização de payloads externos para `models.*` via `schemas.*`
  - [ ] Inserção idempotente e regras em `crud.py`
- [ ] Observabilidade
  - [ ] Métricas: latência, erros, throughput, rate limit
  - [x] Endpoint `/integrations/healthz` agregador (stub)
- [ ] Segurança
  - [ ] Armazenamento de segredos (env/vault/KMS)
  - [ ] Mascaramento de logs e princípio do menor privilégio
- [ ] Testes e documentação
  - [ ] Testes de unidade (conectores) e integração (fluxo completo)
  - [x] Página frontend de teste `frontend/supa/integracoes.html` e documentação de uso

## Fases Sugeridas de Implementação (checklist)
- [x] Fase A – Foundation
  - [x] Interface `Connector`, `ConnectorRegistry`, modelos de configuração
- [ ] Fase B – Autenticação
  - [ ] OAuth 2.0 e tokens de API; armazenamento seguro
- [ ] Fase C – Administração
  - [ ] Rotas CRUD, teste de conexão, health
- [ ] Fase D – Conectores de Referência
  - [ ] `mysql_readonly` (leitura segura)
  - [ ] `hubspot` (CRM com OAuth)
- [ ] Fase E – Sincronização & Observabilidade
  - [ ] Jobs agendados, métricas por conector, cache/retentativas
  - [ ] `/integrations/healthz` com status agregados
- [ ] Fase F – Segurança & QA
  - [ ] Hardening de segredos/escopos
  - [ ] Testes automatizados e documentação final

## Entregáveis por Fase (checklist)
- [ ] A: Código base + registry + schemas de configuração
- [ ] B: Fluxos de autenticação com armazenamento seguro e renovação
- [ ] C: Endpoints admin e health checks
- [ ] D: Dois conectores funcionais (MySQL readonly, HubSpot)
- [ ] E: Sincronização periódica + métricas + cache/retentativas + painel de saúde
- [ ] F: Testes, documentação e runbook operacional

## Observações
- [ ] Reutilizar padrões de frontend existentes em páginas de teste/visualização (se necessárias), seguindo regras de conexão atuais
- [ ] Não remover linhas de código não relacionadas durante a implementação para preservar o baseline