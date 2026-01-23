"""
Serviço para avaliação segura de indicadores customizados.
Implementa DSL controlado para transformar configurações JSON em queries SQL seguras.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
from .models import IndicadorCustomizado, LimiarIndicador
from .database import get_db

class IndicadorEvaluationError(Exception):
    """Exceção para erros na avaliação de indicadores customizados."""
    pass

class IndicadorService:
    """Serviço para avaliação de indicadores customizados com DSL seguro."""
    
    # Tabelas permitidas para consulta
    TABELAS_PERMITIDAS = {
        'saas_registros_financeiros': {
            'campos': ['receita', 'custo', 'lucro', 'data_transacao', 'centro_custo', 'categoria_financeira'],
            'alias': 'rf'
        },
        'saas_registros_produtos': {
            'campos': ['quantidade_vendida', 'preco_unitario', 'data_venda', 'categoria_produto', 'nome_produto'],
            'alias': 'rp'
        },
        'saas_registros_operacionais': {
            'campos': ['duracao_minutos', 'avaliacao_nps', 'data_evento', 'departamento', 'tipo_evento'],
            'alias': 'ro'
        }
    }
    
    # Agregações permitidas
    AGREGACOES_PERMITIDAS = ['SUM', 'AVG', 'COUNT', 'MIN', 'MAX']
    
    # Operadores permitidos para filtros
    OPERADORES_PERMITIDOS = ['=', '>', '<', '>=', '<=', '!=', 'LIKE', 'IN']
    
    def __init__(self, db: Session):
        self.db = db
    
    def validar_config_indicador(self, config: Dict[str, Any]) -> bool:
        """
        Valida se a configuração do indicador está no formato correto e é segura.
        
        Formato esperado:
        {
            "tabela": "saas_registros_financeiros",
            "agregacao": "SUM",
            "campo": "receita",
            "filtros": [
                {"campo": "data_transacao", "operador": ">=", "valor": "2024-01-01"},
                {"campo": "categoria_financeira", "operador": "=", "valor": "vendas"}
            ],
            "agrupamento": ["centro_custo"],
            "periodo_dias": 30
        }
        """
        required_fields = ['tabela', 'agregacao', 'campo']
        
        # Verificar campos obrigatórios
        for field in required_fields:
            if field not in config:
                raise IndicadorEvaluationError(f"Campo obrigatório '{field}' não encontrado na configuração")
        
        # Validar tabela
        if config['tabela'] not in self.TABELAS_PERMITIDAS:
            raise IndicadorEvaluationError(f"Tabela '{config['tabela']}' não é permitida")
        
        # Validar agregação
        if config['agregacao'].upper() not in self.AGREGACOES_PERMITIDAS:
            raise IndicadorEvaluationError(f"Agregação '{config['agregacao']}' não é permitida")
        
        # Validar campo
        tabela_info = self.TABELAS_PERMITIDAS[config['tabela']]
        if config['campo'] not in tabela_info['campos']:
            raise IndicadorEvaluationError(f"Campo '{config['campo']}' não é permitido para tabela '{config['tabela']}'")
        
        # Validar filtros se existirem
        if 'filtros' in config:
            self._validar_filtros(config['filtros'], config['tabela'])
        
        # Validar agrupamento se existir
        if 'agrupamento' in config:
            self._validar_agrupamento(config['agrupamento'], config['tabela'])
        
        return True
    
    def _validar_filtros(self, filtros: List[Dict], tabela: str):
        """Valida os filtros do indicador."""
        tabela_info = self.TABELAS_PERMITIDAS[tabela]
        
        for filtro in filtros:
            if 'campo' not in filtro or 'operador' not in filtro or 'valor' not in filtro:
                raise IndicadorEvaluationError("Filtro deve conter 'campo', 'operador' e 'valor'")
            
            if filtro['campo'] not in tabela_info['campos']:
                raise IndicadorEvaluationError(f"Campo '{filtro['campo']}' não é permitido para filtros")
            
            if filtro['operador'].upper() not in self.OPERADORES_PERMITIDOS:
                raise IndicadorEvaluationError(f"Operador '{filtro['operador']}' não é permitido")
            
            # Validação básica de SQL injection
            valor_str = str(filtro['valor'])
            if re.search(r'[;\'"\\]|--|\bDROP\b|\bDELETE\b|\bUPDATE\b|\bINSERT\b', valor_str, re.IGNORECASE):
                raise IndicadorEvaluationError("Valor do filtro contém caracteres não permitidos")
    
    def _validar_agrupamento(self, agrupamento: List[str], tabela: str):
        """Valida os campos de agrupamento."""
        tabela_info = self.TABELAS_PERMITIDAS[tabela]
        
        for campo in agrupamento:
            if campo not in tabela_info['campos']:
                raise IndicadorEvaluationError(f"Campo de agrupamento '{campo}' não é permitido")
    
    def construir_query_indicador(self, config: Dict[str, Any], usuario_id: int) -> Tuple[str, Dict]:
        """
        Constrói uma query SQL segura baseada na configuração do indicador.
        Retorna a query e os parâmetros para execução segura.
        """
        self.validar_config_indicador(config)
        
        tabela = config['tabela']
        tabela_info = self.TABELAS_PERMITIDAS[tabela]
        alias = tabela_info['alias']
        
        # Construir SELECT
        agregacao = config['agregacao'].upper()
        campo = config['campo']
        select_clause = f"{agregacao}({alias}.{campo}) as valor"
        
        # Adicionar agrupamento ao SELECT se existir
        group_fields = []
        if 'agrupamento' in config:
            group_fields = config['agrupamento']
            group_select = ', '.join([f"{alias}.{field}" for field in group_fields])
            select_clause = f"{group_select}, {select_clause}"
        
        # Construir FROM com JOIN para importações do usuário
        from_clause = f"""
        FROM {tabela} {alias}
        INNER JOIN importacoes i ON {alias}.importacao_id = i.id
        """
        
        # Construir WHERE
        where_conditions = [f"i.usuario_id = :usuario_id"]
        params = {'usuario_id': usuario_id}
        
        # Adicionar filtros customizados
        if 'filtros' in config:
            for idx, filtro in enumerate(config['filtros']):
                param_name = f"filtro_{idx}"
                where_conditions.append(f"{alias}.{filtro['campo']} {filtro['operador']} :{param_name}")
                params[param_name] = filtro['valor']
        
        # Adicionar filtro de período se especificado
        if 'periodo_dias' in config:
            where_conditions.append(f"{alias}.data_transacao >= CURRENT_DATE - INTERVAL ':periodo_dias days'")
            params['periodo_dias'] = config['periodo_dias']
        
        where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Construir GROUP BY se necessário
        group_clause = ""
        if group_fields:
            group_clause = "GROUP BY " + ', '.join([f"{alias}.{field}" for field in group_fields])
        
        # Montar query final
        query = f"""
        SELECT {select_clause}
        {from_clause}
        {where_clause}
        {group_clause}
        """
        
        return query.strip(), params
    
    def avaliar_indicador(self, indicador_id: int, usuario_id: int) -> List[Dict[str, Any]]:
        """
        Avalia um indicador customizado e retorna os resultados.
        """
        # Buscar o indicador
        indicador = self.db.query(IndicadorCustomizado).filter(
            IndicadorCustomizado.id == indicador_id,
            IndicadorCustomizado.ativo == True
        ).first()
        
        if not indicador:
            raise IndicadorEvaluationError(f"Indicador {indicador_id} não encontrado ou inativo")
        
        # Verificar se o usuário tem acesso (mesmo cliente)
        # TODO: Implementar verificação de cliente_id quando disponível
        
        try:
            config = indicador.config_json
            query, params = self.construir_query_indicador(config, usuario_id)
            
            # Executar query
            result = self.db.execute(text(query), params)
            rows = result.fetchall()
            
            # Converter para lista de dicionários
            columns = result.keys()
            return [dict(zip(columns, row)) for row in rows]
            
        except Exception as e:
            raise IndicadorEvaluationError(f"Erro ao avaliar indicador: {str(e)}")
    
    def avaliar_limiar(self, limiar_id: int, usuario_id: int) -> Dict[str, Any]:
        """
        Avalia um limiar de indicador e retorna se foi violado.
        """
        # Buscar o limiar
        limiar = self.db.query(LimiarIndicador).filter(
            LimiarIndicador.id == limiar_id,
            LimiarIndicador.ativo == True
        ).first()
        
        if not limiar:
            raise IndicadorEvaluationError(f"Limiar {limiar_id} não encontrado ou inativo")
        
        try:
            config = limiar.config_json
            query, params = self.construir_query_indicador(config, usuario_id)
            
            # Executar query
            result = self.db.execute(text(query), params)
            row = result.fetchone()
            
            if not row:
                return {
                    'violado': False,
                    'valor_atual': None,
                    'valor_limite': float(limiar.valor_limite),
                    'operador': limiar.operador,
                    'mensagem': limiar.mensagem
                }
            
            valor_atual = float(row[0]) if row[0] is not None else 0.0
            valor_limite = float(limiar.valor_limite)
            
            # Verificar violação baseada no operador
            violado = False
            if limiar.operador == 'above':
                violado = valor_atual > valor_limite
            elif limiar.operador == 'below':
                violado = valor_atual < valor_limite
            
            return {
                'violado': violado,
                'valor_atual': valor_atual,
                'valor_limite': valor_limite,
                'operador': limiar.operador,
                'mensagem': limiar.mensagem,
                'prioridade': limiar.prioridade,
                'canal': limiar.canal
            }
            
        except Exception as e:
            raise IndicadorEvaluationError(f"Erro ao avaliar limiar: {str(e)}")

def get_indicador_service(db: Session = None) -> IndicadorService:
    """Factory function para criar instância do serviço."""
    if db is None:
        db = next(get_db())
    return IndicadorService(db)

# Função auxiliar para instanciar o serviço
def get_indicador_service(db):
    """Retorna uma instância do IndicadorService."""
    return IndicadorService(db)