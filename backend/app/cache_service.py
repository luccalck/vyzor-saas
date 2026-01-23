"""
Serviço de Cache e Materialização de Métricas
Implementa Redis para cache inteligente por janela temporal e filtros
"""

import json
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
import os
import redis
from sqlalchemy.orm import Session

from . import crud, models, schemas

logger = logging.getLogger(__name__)

@dataclass
class CacheConfig:
    """Configuração de cache para diferentes tipos de métricas"""
    ttl_seconds: int
    refresh_threshold: float  # Porcentagem do TTL para refresh automático
    max_size_mb: int
    compression: bool = True

class CacheService:
    """Serviço de cache inteligente para métricas"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        # Permitir override do Redis URL via env
        redis_url = os.getenv("REDIS_URL", redis_url)
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()  # Testa conexão
            logger.info("Conexão com Redis estabelecida")
        except Exception as e:
            logger.warning(f"Redis não disponível, usando cache em memória: {str(e)}")
            self.redis_client = None
            self._memory_cache = {}
        
        # Configurações de cache por tipo de métrica (valores padrão)
        self.cache_configs = {
            'metricas_comparativas': CacheConfig(
                ttl_seconds=3600,  # 1 hora
                refresh_threshold=0.8,
                max_size_mb=50
            ),
            'kpis_dinamicos': CacheConfig(
                ttl_seconds=1800,  # 30 minutos
                refresh_threshold=0.7,
                max_size_mb=20
            ),
            'vendas_categoria': CacheConfig(
                ttl_seconds=7200,  # 2 horas
                refresh_threshold=0.9,
                max_size_mb=30
            ),
            'indicadores_customizados': CacheConfig(
                ttl_seconds=900,  # 15 minutos
                refresh_threshold=0.6,
                max_size_mb=40
            ),
            'relatorios': CacheConfig(
                ttl_seconds=14400,  # 4 horas
                refresh_threshold=0.8,
                max_size_mb=100
            )
        }
        
        # Aplicar overrides de TTL/refresh via variáveis de ambiente
        self._apply_env_overrides()

    def _apply_env_overrides(self) -> None:
        """Aplica overrides de TTL e refresh_threshold a partir de env vars.
        Suporta defaults globais e por tipo:
        - CACHE_TTL_DEFAULT (segundos)
        - CACHE_REFRESH_THRESHOLD_DEFAULT (0.0-1.0)
        - CACHE_TTL_<TIPO>
        - CACHE_REFRESH_THRESHOLD_<TIPO>
        Onde <TIPO> é o nome do tipo em maiúsculas com underscores.
        """
        ttl_default = os.getenv("CACHE_TTL_DEFAULT")
        refresh_default = os.getenv("CACHE_REFRESH_THRESHOLD_DEFAULT")
        
        for metric_type, cfg in self.cache_configs.items():
            key_suffix = metric_type.upper().replace('-', '_')
            ttl_env = os.getenv(f"CACHE_TTL_{key_suffix}")
            ref_env = os.getenv(f"CACHE_REFRESH_THRESHOLD_{key_suffix}")
            
            # TTL por tipo ou default
            try:
                if ttl_env is not None:
                    cfg.ttl_seconds = int(ttl_env)
                elif ttl_default is not None:
                    cfg.ttl_seconds = int(ttl_default)
            except ValueError:
                logger.warning(f"CACHE_TTL_{key_suffix} inválido, mantendo {cfg.ttl_seconds}s")
            
            # Refresh threshold por tipo ou default
            try:
                if ref_env is not None:
                    cfg.refresh_threshold = float(ref_env)
                elif refresh_default is not None:
                    cfg.refresh_threshold = float(refresh_default)
            except ValueError:
                logger.warning(f"CACHE_REFRESH_THRESHOLD_{key_suffix} inválido, mantendo {cfg.refresh_threshold}")
    
    def _generate_cache_key(self, metric_type: str, **params) -> str:
        """Gera chave única para cache baseada no tipo de métrica e parâmetros"""
        # Remove parâmetros None e ordena para consistência
        clean_params = {k: v for k, v in params.items() if v is not None}
        params_str = json.dumps(clean_params, sort_keys=True, default=str)
        
        # Gera hash para chave compacta
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        
        return f"vyzor:cache:{metric_type}:{params_hash}"
    
    def _serialize_data(self, data: Any) -> str:
        """Serializa dados para armazenamento no cache"""
        try:
            if hasattr(data, 'dict'):  # Pydantic models
                return json.dumps(data.dict(), default=str)
            elif isinstance(data, list) and data and hasattr(data[0], 'dict'):
                return json.dumps([item.dict() for item in data], default=str)
            else:
                return json.dumps(data, default=str)
        except Exception as e:
            logger.error(f"Erro ao serializar dados para cache: {str(e)}")
            return json.dumps({"error": "serialization_failed"})
    
    def _deserialize_data(self, data_str: str) -> Any:
        """Deserializa dados do cache"""
        try:
            return json.loads(data_str)
        except Exception as e:
            logger.error(f"Erro ao deserializar dados do cache: {str(e)}")
            return None
    
    def get(self, metric_type: str, **params) -> Optional[Any]:
        """Recupera dados do cache"""
        cache_key = self._generate_cache_key(metric_type, **params)
        
        try:
            if self.redis_client:
                # Usa Redis
                cached_data = self.redis_client.get(cache_key)
                if cached_data:
                    # Verifica se precisa de refresh
                    ttl = self.redis_client.ttl(cache_key)
                    config = self.cache_configs.get(metric_type)
                    
                    if config and ttl > 0:
                        remaining_ratio = ttl / config.ttl_seconds
                        if remaining_ratio < config.refresh_threshold:
                            logger.info(f"Cache para {metric_type} próximo do vencimento, marcando para refresh")
                            # Aqui poderia disparar refresh assíncrono
                    
                    return self._deserialize_data(cached_data)
            else:
                # Usa cache em memória
                cache_entry = self._memory_cache.get(cache_key)
                if cache_entry:
                    if datetime.now() < cache_entry['expires_at']:
                        return cache_entry['data']
                    else:
                        del self._memory_cache[cache_key]
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao recuperar do cache: {str(e)}")
            return None
    
    def set(self, metric_type: str, data: Any, **params) -> bool:
        """Armazena dados no cache"""
        cache_key = self._generate_cache_key(metric_type, **params)
        config = self.cache_configs.get(metric_type)
        
        if not config:
            logger.warning(f"Configuração de cache não encontrada para {metric_type}")
            return False
        
        try:
            serialized_data = self._serialize_data(data)
            
            if self.redis_client:
                # Usa Redis
                self.redis_client.setex(
                    cache_key,
                    config.ttl_seconds,
                    serialized_data
                )
                logger.debug(f"Dados armazenados no Redis para {metric_type}")
            else:
                # Usa cache em memória
                expires_at = datetime.now() + timedelta(seconds=config.ttl_seconds)
                self._memory_cache[cache_key] = {
                    'data': self._deserialize_data(serialized_data),
                    'expires_at': expires_at
                }
                logger.debug(f"Dados armazenados em memória para {metric_type}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao armazenar no cache: {str(e)}")
            return False
    
    def invalidate(self, metric_type: str, **params) -> bool:
        """Invalida entrada específica do cache"""
        cache_key = self._generate_cache_key(metric_type, **params)
        
        try:
            if self.redis_client:
                result = self.redis_client.delete(cache_key)
                return result > 0
            else:
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
                    return True
                return False
                
        except Exception as e:
            logger.error(f"Erro ao invalidar cache: {str(e)}")
            return False
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalida múltiplas entradas baseadas em padrão"""
        try:
            if self.redis_client:
                keys = self.redis_client.keys(f"vyzor:cache:{pattern}*")
                if keys:
                    return self.redis_client.delete(*keys)
                return 0
            else:
                # Para cache em memória, busca por padrão simples
                keys_to_delete = [
                    key for key in self._memory_cache.keys()
                    if pattern in key
                ]
                for key in keys_to_delete:
                    del self._memory_cache[key]
                return len(keys_to_delete)
                
        except Exception as e:
            logger.error(f"Erro ao invalidar por padrão: {str(e)}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        try:
            if self.redis_client:
                info = self.redis_client.info()
                return {
                    'type': 'redis',
                    'connected_clients': info.get('connected_clients', 0),
                    'used_memory': info.get('used_memory_human', '0B'),
                    'keyspace_hits': info.get('keyspace_hits', 0),
                    'keyspace_misses': info.get('keyspace_misses', 0),
                    'total_keys': len(self.redis_client.keys('vyzor:cache:*'))
                }
            else:
                return {
                    'type': 'memory',
                    'total_keys': len(self._memory_cache),
                    'memory_usage': f"{len(str(self._memory_cache))} bytes"
                }
                
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas do cache: {str(e)}")
            return {'type': 'error', 'message': str(e)}

class CachedMetricsService:
    """Serviço que integra cache com as funções de métricas existentes"""
    
    def __init__(self, db: Session, cache_service: CacheService):
        self.db = db
        self.cache = cache_service
    
    def get_metricas_comparativas_cached(
        self,
        usuario_id: int,
        filtros: schemas.FiltrosDashboard
    ) -> List[schemas.MetricaComparativa]:
        """Versão com cache das métricas comparativas"""
        
        # Tenta recuperar do cache
        cached_result = self.cache.get(
            'metricas_comparativas',
            usuario_id=usuario_id,
            data_inicio=getattr(filtros, 'data_inicio', None),
            data_fim=getattr(filtros, 'data_fim', None),
            categoria_produto=getattr(filtros, 'categoria_produto', None),
            departamento=getattr(filtros, 'departamento', None),
            colaborador=getattr(filtros, 'colaborador', None)
        )
        
        if cached_result:
            logger.debug("Métricas comparativas recuperadas do cache")
            # Reconstrói lista de MetricaComparativa
            return [schemas.MetricaComparativa(**item) for item in cached_result]
        
        # Se não está no cache, calcula e armazena
        logger.debug("Calculando métricas comparativas (cache miss)")
        result = crud.get_metricas_comparativas(
            db=self.db,
            usuario_id=usuario_id,
            filtros=filtros
        )
        
        # Armazena no cache
        self.cache.set(
            'metricas_comparativas',
            result,
            usuario_id=usuario_id,
            data_inicio=getattr(filtros, 'data_inicio', None),
            data_fim=getattr(filtros, 'data_fim', None),
            categoria_produto=getattr(filtros, 'categoria_produto', None),
            departamento=getattr(filtros, 'departamento', None),
            colaborador=getattr(filtros, 'colaborador', None)
        )
        
        return result

    def get_kpis_dinamicos_cached(self, usuario_id: int) -> List[schemas.Kpi]:
        """Versão com cache dos KPIs dinâmicos"""
        
        cached_result = self.cache.get('kpis_dinamicos', usuario_id=usuario_id)
        
        if cached_result:
            logger.debug("KPIs dinâmicos recuperados do cache")
            return [schemas.Kpi(**kpi) for kpi in cached_result]
        
        logger.debug("Calculando KPIs dinâmicos (cache miss)")
        result = crud.get_kpis_dinamicos(db=self.db, usuario_id=usuario_id)
        
        self.cache.set('kpis_dinamicos', result, usuario_id=usuario_id)
        
        return result
    
    def get_vendas_por_categoria_cached(self, usuario_id: int) -> List[schemas.VendasCategoria]:
        """Versão com cache das vendas por categoria"""
        
        cached_result = self.cache.get('vendas_categoria', usuario_id=usuario_id)
        
        if cached_result:
            logger.debug("Vendas por categoria recuperadas do cache")
            return [schemas.VendasCategoria(**venda) for venda in cached_result]
        
        logger.debug("Calculando vendas por categoria (cache miss)")
        result = crud.get_vendas_por_categoria(db=self.db, usuario_id=usuario_id)
        
        self.cache.set('vendas_categoria', result, usuario_id=usuario_id)
        
        return result
    
    def invalidate_user_cache(self, usuario_id: int):
        """Invalida todo o cache relacionado a um usuário"""
        patterns = [
            f"*usuario_id:{usuario_id}*",
            f"kpis_dinamicos*{usuario_id}*",
            f"vendas_categoria*{usuario_id}*"
        ]
        
        total_invalidated = 0
        for pattern in patterns:
            total_invalidated += self.cache.invalidate_pattern(pattern)
        
        logger.info(f"Invalidadas {total_invalidated} entradas de cache para usuário {usuario_id}")
    
    def invalidate_client_cache(self, cliente_id: int):
        """Invalida todo o cache relacionado a um cliente"""
        total_invalidated = self.cache.invalidate_pattern(f"*cliente_id:{cliente_id}*")
        logger.info(f"Invalidadas {total_invalidated} entradas de cache para cliente {cliente_id}")

# Instância global do cache
cache_service = CacheService()

def get_cache_service() -> CacheService:
    """Retorna a instância do serviço de cache"""
    return cache_service

def get_cached_metrics_service(db: Session) -> CachedMetricsService:
    """Retorna o serviço de métricas com cache"""
    return CachedMetricsService(db, cache_service)
