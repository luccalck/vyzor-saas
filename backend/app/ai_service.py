import os
import google.generativeai as genai
from dotenv import load_dotenv
import json
import re
from typing import Dict, List, Any
from . import cache 
import hashlib      

# Carrega as variáveis de ambiente
load_dotenv()

# Configura a API do Google
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("AVISO: A chave de API (GOOGLE_API_KEY) não foi encontrada.")
    else:
        genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    print(f"Erro ao configurar a API do Google: {e}")

# [!code ++]
# --- NOVA FUNÇÃO ---
# Esta função aplica o mapeamento gerado pela IA em todos os dados
def aplicar_mapeamento_etl(
    dados_completos: List[Dict[str, Any]],
    mapeamento_ia: Dict[str, Any]
) -> Dict[str, List[Dict]]:
    """
    Aplica localmente as regras de mapeamento da IA a um conjunto de dados completo.
    """
    resultados = {"financeiro": [], "produtos": [], "operacional": []}
    
    # Busca o objeto de mapeamentos dentro da resposta da IA
    mapeamentos = mapeamento_ia.get("mapeamentos", {})
    if not mapeamentos:
        print("AVISO IA: Mapeamento de ETL está vazio. Nenhum dado será transformado.")
        return resultados

    # Itera sobre cada linha dos dados originais
    for linha_original in dados_completos:
        # Itera sobre cada tabela de destino (financeiro, produtos, etc.)
        for tabela_destino, regras in mapeamentos.items():
            if tabela_destino not in resultados:
                continue
            
            nova_linha = {}
            
            # Aplica as regras de mapeamento (ex: "receita": "Valor da Venda")
            for campo_destino, campo_origem in regras.items():
                if campo_origem in linha_original:
                    nova_linha[campo_destino] = linha_original[campo_origem]
                else:
                    # Se um campo mapeado não for encontrado, é opcional.
                    # A validação pydantic (se validation_utils for reativado) cuidará dos campos obrigatórios.
                    pass
            
            # Adiciona a linha se algum dado foi mapeado para ela
            if nova_linha:
                resultados[tabela_destino].append(nova_linha)
                
    return resultados
# --- FIM DA NOVA FUNÇÃO ---


def classificar_e_transformar_dados_com_ia(
    colunas_originais: List[str],
    # [!code --]
    # dados_completos: List[Dict[str, Any]],
    # [!code ++]
    dados_amostra: List[Dict[str, Any]], # Alterado para receber apenas uma amostra
    esquemas_saas: Dict[str, List[str]]
# [!code --]
# ) -> Dict[str, List[Dict]]:
# [!code ++]
) -> Dict[str, Any]: # Alterado para retornar um JSON de mapeamento
    """
    Usa a IA para classificar os dados de entrada e mapeá-los para os esquemas SaaS de destino.
    AGORA RETORNA O MAPEAMENTO, NÃO OS DADOS TRANSFORMADOS.
    """
    # --- ALTERAÇÃO OBRIGATÓRIA: Atualizado para o modelo gemini-1.5-flash ---
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    Você é um sistema de ETL (Extração, Transformação e Carga) inteligente. Sua tarefa é analisar as colunas de um arquivo e gerar um JSON de "mapeamento" para as tabelas de destino: 'financeiro', 'produtos', 'operacional'.

    1. **Analise as colunas de origem:** {json.dumps(colunas_originais)}
    2. **Analise os esquemas de destino:** {json.dumps(esquemas_saas, indent=2)}
    3. **Examine algumas linhas de amostra para entender o contexto:** {json.dumps(dados_amostra, indent=2, default=str)}

    **Sua Missão:**
    Gerar um objeto JSON que define como mapear as "colunas de origem" para as "colunas de destino".

    **Formato da Resposta OBRIGATÓRIO:**
    Responda APENAS com um objeto JSON. O objeto deve ter uma chave "mapeamentos".
    Dentro de "mapeamentos", crie chaves para "financeiro", "produtos", e "operacional".
    Para cada tabela, crie um objeto onde a "chave" é o CAMPO DE DESTINO (ex: "receita") e o "valor" é o CAMPO DE ORIGEM (ex: "Valor da Venda").
    Se uma tabela de destino não tiver mapeamento, use um objeto vazio {{}}.

    Exemplo de Resposta (Mapeamento):
    ```json
    {{
      "mapeamentos": {{
        "financeiro": {{
          "id_transacao": "ID da Transacao",
          "data_transacao": "Data",
          "receita": "Valor da Venda",
          "custo": "Custo Produto"
        }},
        "produtos": {{
          "id_venda": "ID da Transacao",
          "sku_produto": "SKU",
          "quantidade_vendida": "Qtd"
        }},
        "operacional": {{}}
      }}
    }}
    ```
    """

    try:
        response = model.generate_content(prompt)
        text_response = response.text.strip()
        
        # Expressão regular aprimorada para extrair o JSON de forma mais confiável
        match = re.search(r'```json\s*(\{.*?\})\s*```', text_response, re.DOTALL)
        if not match:
             match = re.search(r'(\{.*?\})', text_response, re.DOTALL)

        if match:
            json_str = match.group(1)
            return json.loads(json_str)
        else:
            print("AVISO IA: Nenhum JSON válido (mapeamento) encontrado na resposta. Resposta recebida:")
            print(text_response)
            raise ValueError("Nenhum JSON de mapeamento válido encontrado na resposta da IA.")
            
    except Exception as e:
        print(f"Erro ao processar com a IA: {e}")
        # [!code --]
        # return {"financeiro": [], "produtos": [], "operacional": []}
        # [!code ++]
        return {{"mapeamentos": {}}} # Retorna mapeamento vazio em caso de erro

def gerar_relatorio_com_ia(tipo_relatorio: str, dados_formatados: str) -> str:
    """
    Gera um relatório detalhado em formato Markdown com base nos dados consolidados.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = f"""
    Você é um Analista de Negócios Sênior da VYZOR. Sua tarefa é criar um relatório executivo detalhado em formato Markdown.
    Tipo de Relatório Solicitado: {tipo_relatorio.capitalize()}
    Dados Consolidados para Análise:
    ---
    {dados_formatados}
    ---
    Estrutura Obrigatória do Relatório (use formatação Markdown):
    1.  **Título:** # Relatório ...
    2.  **Período da Análise:** ## Período ...
    3.  **Sumário Executivo:** ## Sumário ...
    4.  **Principais Indicadores (KPIs):** ## KPIs ...
    5.  **Análise Detalhada:** ## Análise ...
    6.  **Recomendações:** ## Recomendações ...
    7.  **Conclusão:** ## Conclusão ...
    Baseie TODAS as suas conclusões estritamente nos dados fornecidos.
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erro ao gerar relatório com a IA: {e}")
        return "# Erro ao Gerar Relatório\n\nNão foi possível conectar ao serviço de IA."

# --- NOVA FUNÇÃO DE INSIGHTS COM IA ---
def gerar_insights_com_ia(dados_formatados: str, usuario_id: int) -> List[Dict[str, Any]]: 
    """
    Usa a IA para gerar insights acionáveis em formato JSON.
    AGORA COM CACHE: Busca no Redis antes de chamar a IA.
    """
    # 1. Criar uma chave de cache estável
    dados_hash = hashlib.md5(dados_formatados.encode()).hexdigest()
    cache_key = cache.make_key("insights_ia", usuario_id, dados_hash)
    
    # 2. Tentar buscar do cache
    try:
        cached_insights = cache.get_json(cache_key)
        if cached_insights:
            print(f"INFO IA: Insights encontrados no cache para usuário {usuario_id}.")
            return cached_insights
    except Exception as e:
         print(f"AVISO IA: Falha ao consultar cache. Gerando novamente. Erro: {e}")

    # 3. Se não estiver no cache, gerar e salvar
    print(f"INFO IA: Gerando novos insights (cache miss) para usuário {usuario_id}.")

    # Define o schema JSON que esperamos da IA (baseado em schemas.InsightItem)
    json_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "tipo": { 
                    "type": "STRING",
                    "enum": ["financeiro", "produto", "operacional"]
                },
                "titulo": { "type": "STRING" },
                "resumo": { "type": "STRING" },
                "prioridade": {
                    "type": "STRING",
                    "enum": ["baixa", "media", "alta"]
                },
                # [!code --]
                # "metadados": { "type": "OBJECT" } # <- CAUSA DO ERRO: Objeto sem 'properties'
            },
            "required": ["tipo", "titulo", "resumo", "prioridade"]
        }
    }

    model = genai.GenerativeModel(
        'gemini-2.5-flash',
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=json_schema
        )
    )

    prompt = f"""
    Você é um Analista de Negócios Sênior da VYZOR.
    Sua tarefa é analisar os dados consolidados a seguir e gerar 3 a 5 insights acionáveis e concisos.
    Concentre-se em identificar quedas repentinas, tendências positivas, oportunidades de melhoria ou pontos críticos de atenção.
    
    Regras:
    - Baseie-se ESTRITAMENTE nos dados fornecidos.
    - Gere insights curtos e diretos.
    - Defina a prioridade (baixa, media, alta) com base na urgência ou impacto.
    - Você PODE incluir um campo "metadados" como um objeto JSON simples (ex: {{"valor_atual": 1500, "meta": 2000}}) se for relevante para o insight.
    
    Dados Consolidados para Análise:
    ---
    {dados_formatados}
    ---
    
    Gere a lista de insights no formato JSON solicitado.
    """

    try:
        response = model.generate_content(prompt)
        # O .text já virá como uma string JSON por causa do response_mime_type
        insights_list = json.loads(response.text)
        
        # 4. Salvar no cache antes de retornar
        try:
            cache.set_json(cache_key, insights_list, ttl_seconds=3600)
            print(f"INFO IA: Novos insights salvos no cache para usuário {usuario_id}.")
        except Exception as e:
            print(f"AVISO IA: Falha ao salvar insights no cache. Erro: {e}")
            
        return insights_list
        
    except Exception as e:
        print(f"Erro ao gerar insights com a IA: {e}")
        # Retorna um insight de erro se a IA falhar
        return [{
            "tipo": "operacional",
            "titulo": "Erro na Geração de Insight",
            "resumo": "Não foi possível conectar ao serviço de IA para gerar insights.",
            "prioridade": "alta",
            "metadados": {"erro": str(e)}
        }]