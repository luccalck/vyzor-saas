# Guia de APIs (Dashboards, Notificações e Análise Preditiva)

Este guia explica como autenticar, descobrir valores válidos e executar os endpoints de dashboard com o payload de filtros abaixo:

```json
{
  "data_inicio": "string",
  "data_fim": "string",
  "categoria_produto": "string",
  "departamento": "string",
  "colaborador": "string",
  "valor_minimo": 0,
  "valor_maximo": 0
}
```

## 1) Pré-requisitos
- Base URL padrão: `http://localhost:8000`.
- Tenha um usuário criado e dados importados.
- Os endpoints exigem autenticação via Bearer Token.

## 2) Autenticação (obter token)
1. Faça login para obter o token:
   
   ```bash
   curl -X POST "http://localhost:8000/login" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=seu.email@empresa.com&password=sua_senha"
   ```
   
   Resposta esperada:
   ```json
   { "access_token": "<SEU_TOKEN>", "token_type": "bearer" }
   ```
2. Guarde o token e use-o no header `Authorization: Bearer <SEU_TOKEN>` em todas as chamadas de dashboard.

## 3) Descobrir valores válidos (filtros disponíveis)
Antes de montar o payload, consulte os filtros disponíveis para o seu usuário:

```bash
curl -X GET "http://localhost:8000/dashboard/filtros-disponiveis" \
  -H "Authorization: Bearer <SEU_TOKEN>"
```

Resposta típica:
```json
{
  "categorias_produto": ["Eletrônicos", "Moda", "Home"],
  "departamentos": ["Comercial", "Suporte"],
  "colaboradores": ["Ana Silva", "Bruno Souza"],
  "periodo_dados": { "data_inicio": "2024-01-01", "data_fim": "2024-07-31" }
}
```

Use exatamente os valores retornados (mesma grafia/acentos) para evitar resultados vazios.

## 4) Como preencher o payload de filtros
- `data_inicio` e `data_fim`: datas no formato `YYYY-MM-DD`. Se omitir, o endpoint não limita o início/fim.
- `categoria_produto`: uma das categorias retornadas em `categorias_produto`.
- `departamento`: um dos nomes retornados em `departamentos`.
- `colaborador`: um dos nomes retornados em `colaboradores`.
- `valor_minimo` e `valor_maximo`: valores numéricos (R$). Observação: atualmente estes campos não são aplicados nos gráficos individuais; podem ser deixados em branco. Eles existem para futura filtragem por faixa de valor.

Todos os campos são opcionais; filtros ausentes são ignorados.

## 5) Endpoints de Dashboard e exemplos

### 5.1) Receita ao longo do tempo
Endpoint: `POST /dashboard/grafico-receita-tempo`

- Filtros usados: `data_inicio`, `data_fim`.
- Ignora: `categoria_produto`, `departamento`, `colaborador`, `valor_minimo`, `valor_maximo`.

Exemplo:
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-receita-tempo" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30"
  }'
```
Resposta: `DadosGraficoLinha` com `labels` (ex.: "2024-01", "2024-02"...) e `datasets` (Receita e Lucro).

### 5.2) Vendas por categoria (pizza)
Endpoint: `POST /dashboard/grafico-vendas-categoria`

- Filtros usados: `data_inicio`, `data_fim`, `categoria_produto` (opcional; se não enviar, retorna todas as categorias).

Exemplo (filtrando por Eletrônicos):
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-vendas-categoria" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Eletrônicos"
  }'
```
Resposta: `DadosGraficoPizza` com `labels` (categorias) e `data` (receita por categoria).

### 5.3) Performance por colaboradores (barra)
Endpoint: `POST /dashboard/grafico-performance-colaboradores`

- Filtros usados: `data_inicio`, `data_fim`, `departamento` (opcional), `colaborador` (opcional).

Exemplo (por departamento):
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-performance-colaboradores" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-03-01",
    "data_fim": "2024-06-30",
    "departamento": "Comercial"
  }'
```
Resposta: `DadosGraficoBarra` com `labels` (colaboradores) e `data` (NPS médio).

### 5.4) Top produtos
Endpoint: `POST /dashboard/top-produtos`

- Filtros usados: `data_inicio`, `data_fim`, `categoria_produto` (opcional).
- Retorna por padrão o Top 10.

Exemplo:
```bash
curl -X POST "http://localhost:8000/dashboard/top-produtos" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Moda"
  }'
```
Resposta: lista de objetos `{ nome, categoria, unidades_vendidas, receita_total }`.

### 5.5) Dashboard completo (agregado)
Endpoint: `POST /dashboard/interativo`

- Aceita o mesmo payload e retorna:
  - `kpis`, `metricas_comparativas`, `grafico_receita_tempo`, `grafico_vendas_categoria`, `grafico_performance_colaboradores`, `top_produtos`, `alertas`.

Exemplo (combinando filtros):
```bash
curl -X POST "http://localhost:8000/dashboard/interativo" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-02-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Eletrônicos",
    "departamento": "Comercial"
  }'
```

## 6) Boas práticas e dicas
- Sempre consulte `/dashboard/filtros-disponiveis` para montar filtros válidos.
- Datas devem ficar dentro do `periodo_dados` retornado; fora disso, o resultado pode vir vazio.
- Strings são comparadas exatamente (respeite acentos e maiúsculas/minúsculas).
- Se a resposta vier vazia, amplie o período e remova filtros até aparecerem dados.
- `valor_minimo`/`valor_maximo` estão reservados para futuros usos; hoje podem ser omitidos.

---
Se quiser, adiciono exemplos com valores do seu banco (categorias, departamentos e colaboradores reais) para tornar o guia ainda mais direto ao seu contexto.

## 7) Exemplos de teste prontos por endpoint

Abaixo estão payloads completos com valores de exemplo e comandos `curl` prontos.

### 7.1) Gráfico Receita Tempo — payload e curl

Payload completo (campos extras são ignorados por este endpoint):
```json
{
  "data_inicio": "2024-01-01",
  "data_fim": "2024-06-30",
  "categoria_produto": "Eletrônicos",
  "departamento": "Comercial",
  "colaborador": "Ana Silva",
  "valor_minimo": 0,
  "valor_maximo": 0
}
```
Curl:
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-receita-tempo" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Eletrônicos",
    "departamento": "Comercial",
    "colaborador": "Ana Silva",
    "valor_minimo": 0,
    "valor_maximo": 0
  }'
```

### 7.2) Gráfico Vendas Categorias — payload e curl

Payload completo (este endpoint usa `data_inicio`, `data_fim` e opcionalmente `categoria_produto`):
```json
{
  "data_inicio": "2024-01-01",
  "data_fim": "2024-06-30",
  "categoria_produto": "Eletrônicos",
  "departamento": "Comercial",
  "colaborador": "Ana Silva",
  "valor_minimo": 0,
  "valor_maximo": 0
}
```
Curl:
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-vendas-categoria" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Eletrônicos",
    "departamento": "Comercial",
    "colaborador": "Ana Silva",
    "valor_minimo": 0,
    "valor_maximo": 0
  }'
```

### 7.3) Gráfico Performance Colaboradores — payload e curl

Payload completo (este endpoint usa `data_inicio`, `data_fim`, `departamento` e opcionalmente `colaborador`):
```json
{
  "data_inicio": "2024-03-01",
  "data_fim": "2024-06-30",
  "categoria_produto": "Eletrônicos",
  "departamento": "Comercial",
  "colaborador": "Ana Silva",
  "valor_minimo": 0,
  "valor_maximo": 0
}
```
Curl:
```bash
curl -X POST "http://localhost:8000/dashboard/grafico-performance-colaboradores" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-03-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Eletrônicos",
    "departamento": "Comercial",
    "colaborador": "Ana Silva",
    "valor_minimo": 0,
    "valor_maximo": 0
  }'
```

### 7.4) Top Produtos — payload e curl

Payload completo (este endpoint usa `data_inicio`, `data_fim` e opcionalmente `categoria_produto`):
```json
{
  "data_inicio": "2024-01-01",
  "data_fim": "2024-06-30",
  "categoria_produto": "Moda",
  "departamento": "Comercial",
  "colaborador": "Ana Silva",
  "valor_minimo": 0,
  "valor_maximo": 0
}
```
Curl:
```bash
curl -X POST "http://localhost:8000/dashboard/top-produtos" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "data_inicio": "2024-01-01",
    "data_fim": "2024-06-30",
    "categoria_produto": "Moda",
    "departamento": "Comercial",
    "colaborador": "Ana Silva",
    "valor_minimo": 0,
    "valor_maximo": 0
  }'
```

### 7.5) Criar Notificação — Example Value e curl

Example Value (troque apenas os valores):
```json
{
  "titulo": "<TITULO>",
  "mensagem": "<MENSAGEM>",
  "tipo": "<info|warning|danger>",
  "canal": "<in_app|email|web>",
  "prioridade": "<baixa|normal|alta>",
  "url_acao": "<URL_OPCIONAL>"
}
```
Admin (direcionando para outro usuário):
```json
{
  "usuario_id": <USUARIO_ID>,
  "titulo": "<TITULO>",
  "mensagem": "<MENSAGEM>",
  "tipo": "<info|warning|danger>",
  "canal": "<in_app|email|web>",
  "prioridade": "<baixa|normal|alta>",
  "url_acao": "<URL_OPCIONAL>"
}
```
Curl (com placeholders):
```bash
curl -X POST "http://localhost:8000/notificacoes" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "titulo": "<TITULO>",
    "mensagem": "<MENSAGEM>",
    "tipo": "<info|warning|danger>",
    "canal": "<in_app|email|web>",
    "prioridade": "<baixa|normal|alta>",
    "url_acao": "<URL_OPCIONAL>"
  }'
```

Observação:
- Para os gráficos, valores de `categoria_produto`, `departamento` e `colaborador` devem existir nos dados do seu usuário (consulte `/dashboard/filtros-disponiveis`).
- `valor_minimo` e `valor_maximo` podem ser mantidos como `0` por enquanto; hoje não impactam o resultado dos endpoints de gráficos.

## 8) Guia de Análise Preditiva

Os endpoints de análise preditiva usam os seus dados históricos para gerar projeções simples por tendência linear.

### 8.1) Previsão de Receita — Example Value e curl
Endpoint: `POST /predict/receita`

Example Value (troque apenas os valores):
```json
{
  "periodicidade": "<mensal|semanal>",
  "horizonte": <MESES_INT>,
  "data_inicio": "<YYYY-MM-DD>",
  "data_fim": "<YYYY-MM-DD>"
}
```
Curl (com placeholders):
```bash
curl -X POST "http://localhost:8000/predict/receita" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "periodicidade": "<mensal|semanal>",
    "horizonte": <MESES_INT>,
    "data_inicio": "<YYYY-MM-DD>",
    "data_fim": "<YYYY-MM-DD>"
  }'
```
Resposta esperada:
```json
{
  "periodicidade": "mensal",
  "horizonte": 3,
  "historico": [{ "label": "2024-01", "valor": 12345.0 }],
  "previsao": [{ "label": "2024-02", "valor": 13000.0 }],
  "resumo": "Previsão baseada em tendência linear simples. Valores negativos são truncados a zero."
}
```

### 8.2) Previsão de Demanda de Produto — Example Value e curl
Endpoint: `POST /predict/demanda-produto`

Example Value (troque apenas os valores):
```json
{
  "sku_produto": "SKU-ELE-001",
  "categoria_produto": "Eletrônicos",
  "periodicidade": "mensal",
  "horizonte": 6
}
```
Curl (com placeholders):
```bash
curl -X POST "http://localhost:8000/predict/demanda-produto" \
  -H "Authorization: Bearer <SEU_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_produto": "<SKU_OPCIONAL>",
    "categoria_produto": "<CATEGORIA_OPCIONAL>",
    "periodicidade": "<mensal|semanal>",
    "horizonte": <MESES_INT>
  }'
```
Resposta esperada:
```json
{
  "sku_produto": "ABC-123",
  "categoria_produto": "Eletrônicos",
  "periodicidade": "mensal",
  "horizonte": 3,
  "historico": [{ "label": "2024-01", "valor": 120.0 }],
  "previsao": [{ "label": "2024-02", "valor": 130.0 }],
  "resumo": "Previsão de demanda baseada em tendência linear simples."
}
```

Dicas para melhores resultados:
- Use `GET /dashboard/filtros-disponiveis` para descobrir categorias e período válido ao montar os filtros.
- Se não enviar `sku_produto` nem `categoria_produto`, a previsão considera todos os produtos do seu usuário.
- Garanta histórico suficiente (várias linhas no período escolhido) para a tendência linear.
- `periodicidade` controla o agrupamento: `mensal` (`YYYY-mm`) ou `semanal` (`YYYY-WW`).

## 9) Troubleshooting

### Erro 404 em Análise Preditiva

Se você receber erro 404 ao usar `/predict/demanda-produto`, isso significa que não há dados suficientes para o SKU/categoria especificados.

**Soluções:**
1. Use `GET /dashboard/filtros-disponiveis` para ver SKUs e categorias disponíveis
2. Verifique se há dados históricos suficientes (pelo menos 30 dias)
3. Use SKUs do seed de desenvolvimento:
   - `SKU-ELE-001` (Headset - Eletrônicos)
   - `SKU-ELE-002` (Teclado - Eletrônicos)  
   - `SKU-AC-010` (Mouse Pad - Acessórios)

### Exemplo de teste com dados do seed:
```bash
curl -X POST "http://localhost:8000/predict/demanda-produto" \
  -H "Authorization: Bearer SEU_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "sku_produto": "SKU-ELE-001",
    "categoria_produto": "Eletrônicos",
    "data_inicio": "2025-01-01",
    "data_fim": "2025-12-31"
  }'
```

## 10) Dicas Importantes

- Use `GET /dashboard/filtros-disponiveis` para obter valores válidos antes de fazer consultas
- Para análise preditiva, certifique-se de ter dados históricos suficientes (pelo menos 3 meses)
- Campos opcionais em notificações: `tipo`, `prioridade`, `data_expiracao`