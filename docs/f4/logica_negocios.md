# Fase 4 — Tópico 2: Lógica de Negócios

Este documento descreve como o backend transforma dados brutos em métricas e insights, valida e trata os dados, automatiza cálculos para dashboards e estrutura a personalização de indicadores por cliente.

## Objetivos
- Implementar regras que transformam os dados brutos em métricas e insights.
- Criar camadas de tratamento e validação dos dados.
- Automatizar cálculos e geração de estatísticas para dashboards.
- Estruturar sistema para permitir personalização de indicadores por cliente.

---

## Visão Geral da Implementação

- ETL inteligente com IA para classificar e transformar dados brutos em esquemas SaaS padronizados.
- Camadas de validação baseadas em Pydantic e verificações de integridade nos endpoints.
- KPIs dinâmicos, métricas comparativas, gráficos e alertas gerados sob demanda via SQL agregações.
- Personalização por cliente através de isolamento por usuário (subconsulta `importacoes_usuario`) e filtros dinâmicos.

---

## Transformação de Dados em Métricas e Insights

- Endpoint ETL: `POST /ai/classificar-e-inserir/{importacao_id}`
  - Lê arquivo (`.csv` ou `.xlsx`), padroniza valores nulos e envia para `ai_service.classificar_e_transformar_dados_com_ia`.
  - Insere registros normalizados em lote via `crud.inserir_dados_*_em_lote` nas tabelas SaaS.
  - Referências:
    - Código: `backend/app/main.py` (função `classificar_e_inserir_com_ia`).
    - Serviço: `backend/app/ai_service.py` (função `classificar_e_transformar_dados_com_ia`).
    - Inserção: `backend/app/crud.py` (funções `inserir_dados_financeiros_em_lote`, `inserir_dados_produtos_em_lote`, `inserir_dados_operacionais_em_lote`).

- KPIs e Insights:
  - Usuário: `crud.get_kpis_dinamicos` e `crud.get_kpis_dinamicos_filtrados`.
  - Global (Admin): `crud.get_kpis_globais`.
  - Métricas comparativas: `crud.get_metricas_comparativas` (com detecção de tendência e percentual de mudança).
  - Alertas: `crud.gerar_alertas_dashboard` (ex.: queda relevante de receita, NPS baixo).
  - Catálogo de insights: `crud.gerar_catalogo_insights` (heurístico) e endpoint `POST /insights/catalogo` (tipos: financeiro/produto/operacional; priorização e metadados).
  - Dados para relatórios com IA: `crud.obter_dados_para_relatorio` + `crud.formatar_dados_para_relatorio`.

---

## Tratamento e Validação de Dados

- Schemas Pydantic (tipos, campos obrigatórios e normalização):
  - `schemas.RegistroFinanceiroBase`, `schemas.RegistroProdutoBase`, `schemas.RegistroOperacionalBase`.
  - `schemas.FiltrosDashboard` (validação básica de filtros para gráficos e KPIs).

- Verificações nos endpoints:
  - Autorização por usuário: todos os cálculos e consultas utilizam `current_user` e subconsulta `importacoes_usuario`.
  - Formatos de data: `crud.get_metricas_comparativas` valida datas e retorna vazio em caso de erro (`ValueError`).
  - Leituras de arquivo com tratamento de exceções (`HTTPException 400`).
  - Integridade de inserção: operações em lote com `bulk_insert_mappings` e rollback em erros.

- Integridade no banco via Alembic:
  - Índices únicos e não-únicos nas tabelas `saas_registros_financeiros`, `saas_registros_produtos`, `saas_registros_operacionais`.
  - Migrações: `alembic/versions/e1a2b3c4d5e6_add_saas_tables.py` e `f1c2d3e4f5a6_cleanup_optimize_db.py`.

---

## Cálculos Automatizados para Dashboards

- Endpoints de Dashboard Interativo:
  - `GET /dashboard/filtros-disponiveis` → `crud.get_filtros_disponiveis`.
  - `POST /dashboard/grafico-receita-tempo` → `crud.get_grafico_receita_tempo`.
  - `POST /dashboard/grafico-performance-colaboradores` → `crud.get_grafico_performance_colaboradores`.
  - `POST /dashboard/top-produtos` → `crud.get_top_produtos_filtrados`.

- Composição completa de dashboard:
  - `crud.get_dashboard_interativo` retorna: KPIs, métricas comparativas, gráficos (linha/pizza/barra), top produtos e alertas.

- Técnicas e agregações:
  - Somatórios (`SUM`), médias (`AVG`), ordenações e `GROUP BY` para períodos, categorias e colaboradores.
  - Cálculo de margem e receitas em `obter_dados_para_relatorio`.

- Observação atual:
  - Os cálculos contam com aceleração por cache e materialização. Funções com versão "cached" foram adicionadas para métricas comparativas, KPIs dinâmicos e vendas por categoria. Há suporte a estatísticas e invalidação de cache, além de uma rotina de materialização programável.

---

## Personalização de Indicadores por Cliente

- Isolamento por usuário:
  - Todas as consultas para KPIs, gráficos e relatórios filtram por `importacoes_usuario` (subconsulta derivada de `current_user.id`).

- Filtros dinâmicos:
  - `schemas.FiltrosDashboard` + `crud.get_filtros_disponiveis` permitem personalizar por período, departamento, colaborador e categoria de produto, refletindo o contexto do cliente.

- Preferências e limites:
  - Estrutura existente para preferências de notificação (`models.PreferenciasNotificacao`) com `limiar_queda_receita_percentual` — pode ser integrada a `gerar_alertas_dashboard` em evolução.

- Migrações SaaS:
  - Tabelas padronizadas e índices suportam multi-tenant por importação/usuário.

---

## Endpoints Relacionados

- Administração:
  - `GET /admin/dashboard/kpis` → KPIs globais.
  - `GET /admin/atividades` → atividades de usuários (auditoria).

- Dashboard Interativo (usuário):
  - `GET /dashboard/filtros-disponiveis`
  - `POST /dashboard/grafico-receita-tempo`
  - `POST /dashboard/grafico-performance-colaboradores`
  - `POST /dashboard/top-produtos`

- ETL e Relatórios:
  - `POST /ai/classificar-e-inserir/{importacao_id}`
  - Exportações: `GET /relatorios/exportar/pdf`, `GET /relatorios/exportar/excel` (com auditoria).

- Preditivo:
  - `POST /predict/receita` (tendência baseada em agregações)
  - `GET /analise-preditiva/modelos`

- Insights:
  - `POST /insights/catalogo` → catálogo de insights heurísticos.

---

## Critérios Atendidos

- Transformação: dados brutos tratados e mapeados para tabelas SaaS; KPIs e insights calculados.
- Validação: schemas Pydantic, autorização por usuário, tratamento de datas/arquivos, rollback em erros.
- Automatização: agregações SQL e composição de dashboards com métricas e gráficos.
- Personalização: indicadores por usuário/cliente via subconsulta, filtros dinâmicos e estruturas de preferência.

---

## Observações de Escopo e Próximos Passos

- Alertas: evoluir uso de `limiar_queda_receita_percentual` e canais por cliente.
- Cache e materialização: já implementados com estatísticas e invalidação; otimizar TTLs e chaves.
- Automação: scheduler ativo com jobs periódicos; ampliar catálogo de tarefas e monitoramento.
- Filtros: expandir faixas de valor, lojas e centros de custo; fortalecer multi-tenant.
- Insights: manter catálogo e considerar persistência histórica (`insights_gerados`).
- Testes: ampliados cobrindo cache, materialização e scheduler; seguir aumentando cobertura.