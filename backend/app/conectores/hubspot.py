from typing import Any, Dict, List, Optional

from .base import Connector


class HubSpotConnector(Connector):
    name = "HubSpot CRM"
    key = "hubspot"

    def authenticate(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Esta função seria usada no fluxo de callback OAuth para trocar o código por token
        return {"status": "not_implemented", "message": "Fluxo OAuth2 de autenticação não implementado no backend."}

    def test_connection(self, config: Dict[str, Any]) -> Dict[str, Any]:
        # Verifica se temos um token (mesmo que ainda não o obtenhamos de verdade)
        # O 'config' aqui contém as CREDENCIAIS que foram salvas no DB
        if not config:
            return {"status": "not_configured", "message": "Credenciais não fornecidas"}

        access_token = config.get("access_token") # Procurar por um token salvo dentro das credenciais

        if access_token:
             # Aqui você faria uma chamada real à API do HubSpot para testar
             # Exemplo: try: requests.get('https://api.hubapi.com/crm/v3/objects/contacts?limit=1', headers={'Authorization': f'Bearer {access_token}'})
             return {"status": "ok", "message": "Token de acesso encontrado (Simulado). Teste real da API não implementado."}
        else:
            client_id = config.get("client_id") # Verifica se ID/Secret existem nas credenciais
            client_secret = config.get("client_secret")
            if client_id and client_secret:
                 return {"status": "error", "message": "Client ID/Secret configurados, mas falta autorizar (Iniciar Autenticação) para obter o token."}
            else:
                 return {"status": "not_configured", "message": "Client ID e Client Secret não configurados."}


    def get_health(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        # O 'config' aqui seria o registro completo de 'IntegracaoCliente' salvo no DB
        details = {"connector": self.key, "message": "Ainda não configurado ou autorizado."}
        status = "not_configured"

        # Verifica se existe config (registro do DB) e se está habilitado
        if config and config.get("enabled"):
             # Extrai as credenciais de dentro do config (do campo 'credentials')
             credentials = config.get("credentials", {})
             client_id = credentials.get("client_id")
             access_token = credentials.get("access_token") # Procurar por token dentro de credentials

             if access_token:
                 status = "ok"
                 details["message"] = "Configurado e token de acesso presente (Simulado)."
             elif client_id:
                 status = "degraded" # Configurado mas não autorizado
                 details["message"] = "Configurado (Client ID encontrado), mas precisa de autorização OAuth."
             # else continua 'not_configured'

        return {"status": status, "details": details}

    def fetch(self, config: Dict[str, Any], params: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Implementação futura: usar access_token de 'config['credentials']' para buscar dados
        return []

    def push(self, config: Dict[str, Any], payload: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Implementação futura: usar access_token de 'config['credentials']' para enviar dados
        return {"status": "unsupported", "message": "Push ainda não implementado"}

    def map_to_internal_models(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # Implementação futura: mapear dados do HubSpot para modelos internos
        return data

