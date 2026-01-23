# Fase 4 – Implementação das Funcionalidades Principais: APIs

Este documento descreve, endpoint por endpoint, o estado atual, como consultar e exemplos de uso. Vamos avançar tópico a tópico.

## 1. Dashboards Interativos (consulta, filtros, visualização dinâmica)
Status: Implementado

Endpoints disponíveis:
- `GET /dashboard/kpis` – KPIs dinâmicos por usuário.
- `GET /dashboard/vendas-por-categoria` – Dados para gráfico de vendas por categoria.
- `GET /dashboard/filtros-disponiveis` – Lista de filtros possíveis (categorias, departamentos, colaboradores, período).
- `POST /dashboard/interativo` – Pacote completo do dashboard com filtros aplicados (inclui `metricas_comparativas`, gráficos e `alertas`).
- `POST /dashboard/grafico-receita-tempo` – Dados para gráfico de linha (receita ao longo do tempo).
- `POST /dashboard/grafico-vendas-categoria` – Dados para gráfico de pizza (vendas por categoria).
- `POST /dashboard/grafico-performance-colaboradores` – Dados para gráfico de barra (performance colaboradores).
- `POST /dashboard/top-produtos` – Lista de top produtos com filtros aplicados.

Autenticação:
- Todas as rotas exigem `Authorization: Bearer <TOKEN>` (usuário autenticado).

Filtros aceitos (`schemas.FiltrosDashboard`):
- `data_inicio` (AAAA-MM-DD) | `data_fim` (AAAA-MM-DD)
- `categoria_produto` | `departamento` | `colaborador`

Exemplos de uso:
- Obter filtros disponíveis:
  ```bash
  curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/dashboard/filtros-disponiveis
  ```
- Obter o pacote completo do dashboard com filtros:
  ```bash
  curl -X POST http://localhost:8000/dashboard/interativo \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{
             "data_inicio": "2024-01-01",
             "data_fim": "2024-03-31",
             "categoria_produto": "Eletronicos"
           }'
  ```
- Gráfico de receita ao longo do tempo:
  ```bash
  curl -X POST http://localhost:8000/dashboard/grafico-receita-tempo \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "data_inicio": "2024-01-01", "data_fim": "2024-03-31" }'
  ```
- Gráfico de vendas por categoria:
  ```bash
  curl -X POST http://localhost:8000/dashboard/grafico-vendas-categoria \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "data_inicio": "2024-01-01", "data_fim": "2024-03-31", "categoria_produto": "Eletronicos" }'
  ```
- Gráfico de performance de colaboradores:
  ```bash
  curl -X POST http://localhost:8000/dashboard/grafico-performance-colaboradores \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "data_inicio": "2024-01-01", "data_fim": "2024-03-31", "departamento": "Atendimento" }'
  ```
- Top produtos (com filtros):
  ```bash
  curl -X POST http://localhost:8000/dashboard/top-produtos \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "data_inicio": "2024-01-01", "data_fim": "2024-03-31" }'
  ```

## 2. Geração de Relatórios (PDF, Excel, exportações customizadas)
Status: Implementado

Endpoints disponíveis:
- `POST /dashboard/gerar-relatorio-ia` – Gera relatório analítico em Markdown via IA.
- `POST /dashboard/exportar-relatorio-pdf` – Exporta o relatório (Markdown gerado pela IA) para PDF.
- `POST /dashboard/exportar-relatorio-excel` – Exporta para Excel com duas abas: `Relatorio` (Markdown) e `Dados <Tipo>` (tabelas).

Parâmetros:
- `tipo_relatorio` (query param): `financeiro` | `produtos` | `operacional`

Pré-requisitos:
- Ter dados importados (via `/importacoes/` e upload em `/ai/classificar-e-inserir/{importacao_id}`).

Exemplos de uso:
- Gerar relatório em Markdown:
  ```bash
  curl -X POST "http://localhost:8000/dashboard/gerar-relatorio-ia?tipo_relatorio=financeiro" \
       -H "Authorization: Bearer <TOKEN>"
  ```
- Baixar em PDF:
  ```bash
  curl -X POST "http://localhost:8000/dashboard/exportar-relatorio-pdf?tipo_relatorio=produtos" \
       -H "Authorization: Bearer <TOKEN>" -o relatorio_produtos.pdf
  ```
- Baixar em Excel:
  ```bash
  curl -X POST "http://localhost:8000/dashboard/exportar-relatorio-excel?tipo_relatorio=operacional" \
       -H "Authorization: Bearer <TOKEN>" -o relatorio_operacional.xlsx
  ```

## 3. Sistema de Alertas e Notificações
Status: Implementado

- Alertas integrados ao payload do `POST /dashboard/interativo` em `alertas`.
- Notificações de usuário: listar, criar, marcar como lida, deletar; além de preferências.

Endpoints disponíveis:
- `GET /notificacoes?somente_nao_lidas=true|false` – Lista notificações do usuário.
- `POST /notificacoes` – Cria uma notificação (admin pode direcionar para outro usuário via `usuario_id`).
- `PUT /notificacoes/{notificacao_id}/ler` – Marca a notificação como lida.
- `DELETE /notificacoes/{notificacao_id}` – Remove a notificação.
- `GET /notificacoes/preferencias` – Lê preferências de notificação (cria padrão se não existir).
- `PUT /notificacoes/preferencias` – Atualiza preferências de notificação.

Exemplos de uso:
- Listar apenas não lidas:
  ```bash
  curl -H "Authorization: Bearer <TOKEN>" "http://localhost:8000/notificacoes?somente_nao_lidas=true"
  ```
- Criar notificação (usuário corrente):
  ```bash
  curl -X POST http://localhost:8000/notificacoes \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "titulo": "Queda de Receita", "mensagem": "Receita caiu 12%", "tipo": "warning" }'
  ```
- Marcar como lida:
  ```bash
  curl -X PUT -H "Authorization: Bearer <TOKEN>" http://localhost:8000/notificacoes/1/ler
  ```
- Preferências (ler/atualizar):
  ```bash
  curl -H "Authorization: Bearer <TOKEN>" http://localhost:8000/notificacoes/preferencias
  curl -X PUT http://localhost:8000/notificacoes/preferencias \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "canal_email": true, "limiar_queda_receita_percentual": 15 }'
  ```

## 4. Módulo de Análise Preditiva (usando IA integrada)
Status: Implementado (parcial)

Endpoints disponíveis:
- `POST /predict/receita` – Previsão de receita agregada por período (mensal/semanal).
- `POST /predict/demanda-produto` – Previsão de demanda (quantidade vendida) por SKU ou por categoria.

Parâmetros comuns:
- `periodicidade`: `mensal` (default) | `semanal`
- `horizonte`: número de períodos futuros (default: `3`)

Detalhes por endpoint:
- `POST /predict/receita`
  - Corpo (JSON): `{ "periodicidade": "mensal|semanal", "horizonte": 3, "data_inicio": "AAAA-MM-DD", "data_fim": "AAAA-MM-DD" }`
  - Resposta: `{ historico: [{label, valor}], previsao: [{label, valor}], resumo }`
- `POST /predict/demanda-produto`
  - Corpo (JSON): `{ "sku_produto": "SKU123", "categoria_produto": "Eletronicos", "periodicidade": "mensal|semanal", "horizonte": 3 }`
  - Resposta: `{ historico: [{label, valor}], previsao: [{label, valor}], resumo }`

Modelo de previsão:
- Tendência linear simples sobre séries agregadas por período (valores negativos truncados para 0).
- Base de dados: registros do usuário autenticado (`RegistroFinanceiro` e `RegistroProduto`).

Exemplos de uso:
- Prever receita mensal nos próximos 3 meses:
  ```bash
  curl -X POST http://localhost:8000/predict/receita \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "periodicidade": "mensal", "horizonte": 3, "data_inicio": "2024-01-01", "data_fim": "2024-03-31" }'
  ```
- Prever demanda de um SKU por mês (próximos 4 períodos):
  ```bash
  curl -X POST http://localhost:8000/predict/demanda-produto \
       -H "Authorization: Bearer <TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{ "sku_produto": "SKU123", "periodicidade": "mensal", "horizonte": 4 }'
  ```

## 5. Autenticação e Controle de Acesso por Nível de Usuário
Status: Implementado

- `POST /login` – emite `access_token` (Bearer).
- Rotas do usuário: protegidas por `Depends(auth.get_current_user)`.
- Rotas de admin (`/admin/*`): protegidas por `Depends(auth.get_current_admin_user)`.

## 6. Testar e Documentar Cada Endpoint
Status: Em progresso

- Documentação interativa disponível em `GET /docs` (OpenAPI).
- Próximo passo: adicionar testes automáticos (pytest) para dashboards, relatórios e notificações.