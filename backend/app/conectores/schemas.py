from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClientIntegrationConfig(BaseModel):
    """Configuração por cliente para uma integração externa."""

    cliente_id: int = Field(..., description="ID do cliente")
    connector_key: str = Field(..., description="Chave do conector (ex.: hubspot, mysql_readonly)")
    auth_type: str = Field(..., description="Tipo de autenticação: oauth2, api_token, basic, service_account")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="Segredos/credenciais de acesso")
    scopes: List[str] = Field(default_factory=list, description="Escopos/permissions do provedor")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parâmetros adicionais do conector")
    enabled: bool = Field(default=True, description="Se a integração está ativa para o cliente")
    last_sync_ts: Optional[str] = Field(default=None, description="Carimbo de tempo da última sincronização")