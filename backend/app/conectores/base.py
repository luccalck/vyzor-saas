from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Connector(ABC):
    """Interface base para conectores externos."""

    name: str = ""
    key: str = ""

    @abstractmethod
    def authenticate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Realiza autenticação (OAuth2, tokens, etc.)."""
        raise NotImplementedError

    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Verifica conectividade com a fonte externa."""
        raise NotImplementedError

    @abstractmethod
    def get_health(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Retorna status de saúde do conector (configuração, ping, quotas)."""
        raise NotImplementedError

    @abstractmethod
    def fetch(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Obtém dados da fonte externa com suporte a paginação/filters."""
        raise NotImplementedError

    @abstractmethod
    def push(self, config: Dict[str, Any], payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Envia dados para a fonte externa, quando aplicável."""
        raise NotImplementedError

    @abstractmethod
    def map_to_internal_models(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapeia estruturas externas para modelos internos da aplicação."""
        raise NotImplementedError