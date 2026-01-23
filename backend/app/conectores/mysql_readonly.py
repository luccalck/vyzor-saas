from typing import Any, Dict, List, Optional

from .base import Connector


class MySQLReadonlyConnector(Connector):
    name = "MySQL Readonly"
    key = "mysql_readonly"

    def authenticate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "not_applicable", "message": "MySQL readonly geralmente usa credenciais estáticas"}

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Sem implementação real por enquanto
        return {"status": "not_configured", "message": "Credenciais/host não configurados"}

    def get_health(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {"status": "not_configured", "details": {"connector": self.key}}

    def fetch(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []

    def push(self, config: Dict[str, Any], payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {"status": "unsupported", "message": "Push não aplicável para readonly"}

    def map_to_internal_models(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return data