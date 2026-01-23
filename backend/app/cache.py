import os
import json
import hashlib
from typing import Any, Optional, Iterable
import logging # [!code ++]
from decimal import Decimal # [!code ++]

import redis

# [!code ++]
# Configura um logger para este módulo
logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None

# [!code ++]
# --- CORREÇÃO: Adiciona um encoder customizado para 'Decimal' ---
class CustomJSONEncoder(json.JSONEncoder):
    """Encoder JSON customizado para lidar com tipos que o 'json' padrão não lida."""
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Converte Decimal para float, que é JSON serializável
            return float(obj)
        # Deixa o encoder padrão tratar o resto
        return super().default(obj)
# --- FIM DA CORREÇÃO ---


def get_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.Redis.from_url(url, decode_responses=True)
    return _redis_client


def make_key(namespace: str, *parts: Iterable[Any]) -> str:
    joined = ":".join(str(p) for p in parts if p is not None)
    if len(joined) > 120:
        digest = hashlib.md5(joined.encode()).hexdigest()
        joined = f"{joined[:32]}:{digest}"
    return f"vyzor:{namespace}:{joined}"


def get_json(key: str) -> Optional[Any]:
    c = get_client()
    # [!code ++]
    # --- CORREÇÃO: Adiciona try/except para lidar com Redis offline ---
    try:
        raw = c.get(key)
        return json.loads(raw) if raw is not None else None
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"AVISO: Não foi possível conectar ao Redis para buscar cache. Erro: {e}")
        return None # Retorna None (cache miss) se o Redis estiver offline
    # --- FIM DA CORREÇÃO ---


def set_json(key: str, value: Any, ttl_seconds: int = 300) -> None:
    c = get_client()
    # [!code ++]
    # --- CORREÇÃO: Adiciona try/except para lidar com Redis offline e Erros de Tipo ---
    try:
        # Usa o encoder customizado para converter Decimal para float
        json_value = json.dumps(value, cls=CustomJSONEncoder)
        c.setex(key, ttl_seconds, json_value)
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"AVISO: Não foi possível conectar ao Redis para salvar cache. Erro: {e}")
        pass # Apenas ignora a falha ao salvar o cache
    except TypeError as e:
        # Captura outros erros de serialização que possam ocorrer
        logger.error(f"ERRO DE SERIALIZAÇÃO JSON no cache.set_json: {e}. Valor: {str(value)[:200]}...")
        pass # Não quebra a aplicação se o cache falhar ao serializar
    # --- FIM DA CORREÇÃO ---


def invalidate_prefix(prefix: str) -> int:
    c = get_client()
    deleted = 0
    pattern = f"{prefix}*"
    # [!code ++]
    # --- CORREÇÃO: Adiciona try/except para lidar com Redis offline ---
    try:
        for k in c.scan_iter(match=pattern):
            c.delete(k)
            deleted += 1
    except redis.exceptions.ConnectionError as e:
        logger.warning(f"AVISO: Não foi possível conectar ao Redis para invalidar cache. Erro: {e}")
        return 0
    # --- FIM DA CORREÇÃO ---
    return deleted


def invalidate_usuario(usuario_id: int) -> int:
    total = 0
    total += invalidate_prefix(make_key("kpis", usuario_id))
    total += invalidate_prefix(make_key("kpis_filtrados", usuario_id))
    total += invalidate_prefix(make_key("filtros", usuario_id))
    total += invalidate_prefix(make_key("dashboard", usuario_id))
    return total

