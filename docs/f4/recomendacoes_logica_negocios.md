# Recomendações e Próximos Passos — Lógica de Negócios (Fase 4 / Tópico 2)

Este documento consolida recomendações práticas e um plano de ação para evoluir a lógica de negócios do backend, considerando o estado atual do código e os itens ausentes/parciais identificados em `docs/f4/nao_feitos_logica_negocios.md`.

## Status Resumido
- ETL com IA, validações básicas e dashboards on-demand: implementados.
- Alertas padrão e limiares por cliente: implementados parcialmente.
- Testes de regras de negócio: ampliados (KPIs, alertas e endpoint de dashboard); seguir expandindo.
- Catálogo de insights: agora disponível via heurísticas e endpoint (`POST /insights/catalogo`).
- Personalização de indicadores, agendador, cache/materialização: pendentes.

## Recomendações por Tópico

1) Personalização de indicadores por cliente
- Modelagem: criar `clientes`, `indicadores_customizados` e `indicadores_cliente_map`.
- DSL segura: catálogo de agregações pré-aprovadas (SUM, AVG, COUNT, MIN/MAX) com parâmetros (período, filtros) e proibição de execuções arbitrárias.
- Execução: serviço que traduz DSL em SQL parametrizado, respeitando contexto (`importacoes_usuario`).
- Observabilidade: armazenar execuções e resultados para auditoria.

2) Alertas e notificações proativas
- Unificar preferências (por usuário/cliente) com limiares de indicadores — permitir canais (in-app, email, webhook).
- Agendador (APScheduler/Celery) para:
  - Pré-agregar métricas mais utilizadas.
  - Avaliar limiares e disparar notificações.
- Histórico: tabela `alertas_emitidos` para rastreio e deduplicação.

3) Cache e materialização de métricas
- Cache por janela/filtros (Redis) com chave padrão: `user:{id}:dash:{hash_filtros}`.
- Materialização: tabelas de métricas consolidadas para períodos fechados (dia/semana/mês), atualizadas por jobs.
- Invalidação: estratégias simples (TTL) e invalidação por importação nova.

4) Testes de regras de negócio
- Cobrir funções do `crud.py` centrais: `get_metricas_comparativas`, `get_grafico_*`, `get_top_produtos_filtrados`, `gerar_alertas_dashboard` com combinações de filtros.
- Testes de limiares (operadores `below`/`above`) e preferência de usuário (sobrescritas).
- Testes de catálago de insights: validar geração por cenários e tolerância a dados faltantes.

5) Catálogo de insights (heurístico + IA)
- Heurísticas atuais: receita em queda, NPS baixo, categoria destaque, colaborador com menor NPS, top produto.
- Próximas heurísticas:
  - Queda acentuada por categoria/departamento.
  - Margem crítica (lucro/receita abaixo de limiar).
  - Variação anormal semana a semana.
- Integração IA (opcional): resumir e classificar insights por severidade e ação recomendada.
- Persistência: opcionalmente manter histórico em `insights_gerados` para analytics e explicabilidade.

## Roadmap Prático

Fase A — Fundamentos de personalização
- Criar modelos e migrações Alembic para indicadores customizados.
- Implementar serviço de avaliação (DSL → SQL seguro) e endpoint admin para cadastrar.

Fase B — Alertas proativos e cache
- Introduzir APScheduler (dev) para pré-cálculo de métricas frequentes e avaliação de limiares.
- Implementar cache Redis com TTL e invalidação por importações novas.

Fase C — Insights e explicabilidade
- Expandir heurísticas e adicionar classificação de prioridade.
- Opcional: persistir insights e enriquecer com IA para recomendações acionáveis.

Fase D — Qualidade e testes
- Adicionar bateria de testes cobrindo cálculos, filtros e alertas.
- Monitorar cobertura e tempo de resposta; ajustar índices e consultas quando necessário.

## Riscos e Mitigações
- Complexidade de DSL: iniciar com catálogo limitado de funções e parâmetros bem definidos.
- Performance: usar índices adequados, limitar cardinalidade dos filtros, aplicar cache.
- Segurança: proibir qualquer execução dinâmica fora do catálogo; validar entradas rigorosamente.
- Manutenção: documentar indicadores e seus owners; versionar mudanças de regras.

## Métricas de Sucesso
- Latência média dos endpoints de dashboard < 300ms em dados médios.
- Taxa de acerto dos alertas (correspondência com eventos reais) > 80%.
- Taxa de utilização do insights catálogo por usuários ativos > 50%.
- Cobertura de testes das funções de negócio > 70%.

## Próximos Passos Imediatos
- Planejar e criar migrações para indicadores customizados.
- Introduzir um job simples de pré-cálculo semanal (APScheduler) para métricas mais acessadas.
- Implementar cache de `get_dashboard_interativo` por filtro.
- Ampliar testes para `get_metricas_comparativas` com cenários de variação forte.
- Mapear mais 3 heurísticas de insights e adicionar ao gerador.