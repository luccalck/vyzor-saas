from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from ..conectores.registry import get_registry
from ..conectores.hubspot import HubSpotConnector
from ..conectores.mysql_readonly import MySQLReadonlyConnector
# [!code ++]
# Imports necessários para os novos endpoints
from .. import crud, models, schemas, auth # [!code ++]
from ..database import get_db # [!code ++]


# Registrar conectores de referência
registry = get_registry()
registry.register(HubSpotConnector.key, HubSpotConnector)
registry.register(MySQLReadonlyConnector.key, MySQLReadonlyConnector)


router = APIRouter(prefix="/integrations", tags=["Integrações"])


@router.get("/connectors")
def list_connectors() -> Dict[str, list]:
    """Lista conectores disponíveis no registry."""
    return {"connectors": registry.list_connectors()}


@router.get("/healthz")
def integrations_healthz(
    db: Session = Depends(get_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user) # [!code ++]
) -> Dict[str, Any]:
    """Health agregado dos conectores, agora verificando configurações salvas."""
    health = {}

    # [!code ++]
    # --- CORREÇÃO: Auto-provisiona um cliente se o usuário não tiver um ---
    # Isso garante que um usuário novo sempre tenha um cliente associado
    # ao carregar esta página, resolvendo o problema de "usuário sem cliente".
    if not current_user.cliente_id:
        try:
            novo_cliente = crud.create_cliente(db, nome=f"Cliente {current_user.email}")
        except HTTPException as e:
            # Trata caso de concorrência ou se o nome já existir
            if e.status_code == 409:
                novo_cliente = db.query(models.Cliente).filter(models.Cliente.nome == f"Cliente {current_user.email}").first()
                if not novo_cliente:
                    raise # Se não achou, propaga o erro
            else:
                raise
        # Associa usuário ao novo cliente
        current_user.cliente_id = novo_cliente.id
        db.commit()
        db.refresh(current_user)
    # --- FIM DA CORREÇÃO ---

    # Busca configs salvas para o cliente deste usuário (agora garantido)
    configs_salvas_db = crud.get_integracoes_por_cliente(db, current_user.cliente_id) # [!code ++]
    configs_map = {c.connector_key: c for c in configs_salvas_db} # [!code ++]
    
    for item in registry.list_connectors():
        key = item["key"]
        cls = registry.get(key)
        if cls:
            connector = cls()
            # Passa a config salva (se existir) para o método get_health, sanitizada para dict
            config_salva = configs_map.get(key) # [!code ++]
            
            # [!code ++]
            # CORREÇÃO: Converte o objeto SQLAlchemy 'config_salva' para um dicionário
            # O traceback do 'AttributeError: ... model_dump' indica que
            # a conversão estava incorreta na sua versão local.
            config_dict = None
            if config_salva:
                config_dict = {
                    "id": config_salva.id,
                    "cliente_id": config_salva.cliente_id,
                    "connector_key": config_salva.connector_key,
                    "enabled": config_salva.enabled,
                    "credentials": config_salva.credentials,
                    "last_sync_ts": config_salva.last_sync_ts,
                    # Adicionado auth_type para consistência
                    "auth_type": config_salva.auth_type 
                }
            
            # [!code --]
            # Linha antiga que causava o AttributeError (baseado no seu traceback):
            # health[key] = connector.get_health(config=config_salva.model_dump() if config_salva else None)
            
            # Linha correta (usando o config_dict que acabamos de criar):
            health[key] = connector.get_health(config=config_dict)
    
    # O status 'degraded' aqui é um fallback, o frontend deve
    # idealmente verificar o status de cada conector individualmente.
    return {"status": "degraded", "details": health}


# [!code ++]
# --- NOVOS ENDPOINTS PARA CONFIGURAÇÃO --- # [!code ++]

@router.get( # [!code ++]
    "/{connector_key}/config", # [!code ++]
    response_model=schemas.IntegracaoConfigState, # [!code ++]
    tags=["Integrações"] # [!code ++]
) # [!code ++]
def get_configuration( # [!code ++]
    connector_key: str, # [!code ++]
    db: Session = Depends(get_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user) # [!code ++]
): # [!code ++]
    """Busca a configuração salva para um conector.""" # [!code ++]
    # Se não houver cliente associado, retorna estado padrão 'não configurado' com 200
    # Nota: A lógica de auto-provisionamento em /healthz deve
    # tornar este 'if' menos comum, mas é uma boa proteção.
    if not current_user.cliente_id:
        return {
            "exists": False,
            "connector_key": connector_key,
            "enabled": False,
            "id": None,
            "cliente_id": None,
            "last_sync_ts": None,
        }
    
    config = crud.get_integracao_config(db, current_user.cliente_id, connector_key) # [!code ++]
    if not config: # [!code ++]
        return {
            "exists": False,
            "connector_key": connector_key,
            "enabled": False,
            "id": None,
            "cliente_id": current_user.cliente_id,
            "last_sync_ts": None,
        }
    return {
        "exists": True,
        "connector_key": config.connector_key,
        "enabled": config.enabled,
        "id": config.id,
        "cliente_id": config.cliente_id,
        "last_sync_ts": config.last_sync_ts,
    } # [!code ++]


@router.post( # [!code ++]
    "/{connector_key}/configure", # [!code ++]
    response_model=schemas.IntegracaoConfig, # [!code ++]
    tags=["Integrações"] # [!code ++]
) # [!code ++]
def configure_integration( # [!code ++]
    connector_key: str, # [!code ++]
    config_in: schemas.IntegracaoConfigCreate, # [!code ++]
    db: Session = Depends(get_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user) # [!code ++]
): # [!code ++]
    """Cria ou atualiza a configuração de uma integração.""" # [!code ++]
    # Auto-provisiona um cliente se o usuário ainda não estiver associado
    if not current_user.cliente_id:
        try:
            novo_cliente = crud.create_cliente(db, nome=f"Cliente {current_user.email}")
        except HTTPException as e:
            # Se já existir com esse nome, tenta buscar por nome
            if e.status_code == 409:
                novo_cliente = db.query(models.Cliente).filter(models.Cliente.nome == f"Cliente {current_user.email}").first()
                if not novo_cliente:
                    raise
            else:
                raise
        # Associa usuário ao novo cliente
        current_user.cliente_id = novo_cliente.id
        db.commit()
        db.refresh(current_user)
        
    # Valida se o conector existe no registry
    if not registry.get(connector_key): # [!code ++]
        raise HTTPException(status_code=404, detail="Conector não encontrado.") # [!code ++]
    
    config = crud.create_or_update_integracao( # [!code ++]
        db, current_user.cliente_id, connector_key, config_in # [!code ++]
    ) # [!code ++]
    return config # [!code ++]


@router.post( # [!code ++]
    "/{connector_key}/test", # [!code ++]
    response_model=schemas.TestConnectionResponse, # [!code ++]
    tags=["Integrações"] # [!code ++]
) # [!code ++]
def test_integration( # [!code ++]
    connector_key: str, # [!code ++]
    # [!code ++]
    # --- CORREÇÃO: Aceita um body opcional com credenciais para teste ---
    config_in: Optional[schemas.TestConnectionRequest] = None, # [!code ++]
    db: Session = Depends(get_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user) # [!code ++]
): # [!code ++]
    """
    Testa a conexão de uma integração.
    Se 'credentials' forem fornecidas no body, testa elas.
    Senão, testa as credenciais salvas no banco.
    """ # [!code ++]
    # Auto-provisiona um cliente se o usuário ainda não estiver associado
    if not current_user.cliente_id:
        try:
            novo_cliente = crud.create_cliente(db, nome=f"Cliente {current_user.email}")
        except HTTPException as e:
            if e.status_code == 409:
                novo_cliente = db.query(models.Cliente).filter(models.Cliente.nome == f"Cliente {current_user.email}").first()
                if not novo_cliente:
                    raise
            else:
                raise
        current_user.cliente_id = novo_cliente.id
        db.commit()
        db.refresh(current_user)
    
    # 1. Busca o conector
    connector_cls = registry.get(connector_key) # [!code ++]
    if not connector_cls: # [!code ++]
        raise HTTPException(status_code=404, detail="Conector não encontrado.") # [!code ++]
        
    connector_instance = connector_cls() # [!code ++]
    
    # [!code ++]
    # 2. Determina quais credenciais testar
    credentials_to_test = None
    
    # Se o usuário enviou credenciais no body (teste em tempo real), usa elas
    if config_in and config_in.credentials:
         credentials_to_test = config_in.credentials
    else:
        # Senão, busca as credenciais salvas no DB (teste de config salva)
        config_db = crud.get_integracao_config(db, current_user.cliente_id, connector_key) # [!code ++]
        if not config_db or not config_db.credentials: # [!code ++]
            return {"status": "not_configured", "message": "Integração não configurada. Salve as credenciais primeiro."} # [!code ++]
        credentials_to_test = config_db.credentials
    # [!code --]
    
    # 3. Executa o teste de conexão
    # Passamos apenas as credenciais para o método de teste
    test_result = connector_instance.test_connection(credentials_to_test) # [!code ++]
    
    return test_result # [!code ++]

