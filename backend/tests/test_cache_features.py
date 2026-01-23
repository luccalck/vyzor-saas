from datetime import date
from fastapi.testclient import TestClient
from app import crud, schemas
from app.auth import create_access_token

def test_get_cache_stats_endpoint(test_client: TestClient, admin_user, db_session):
    """
    Testa o endpoint de estatísticas do cache.
    Este teste é mais uma verificação de integração do endpoint do que da lógica do cache em si.
    """
    # Autentica como admin para acessar a rota
    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.get("/admin/cache/stats", headers=headers)
    
    # A resposta vai depender se o Redis está rodando ou não no ambiente de teste
    # O importante é que o endpoint responda com 200 OK
    assert response.status_code == 200
    stats = schemas.CacheStatsSchema(**response.json())
    assert stats.type in ["redis", "memory", "error"] # Aceita qualquer um dos status

def test_invalidate_cache_endpoint(test_client: TestClient, admin_user, db_session, monkeypatch):
    """
    Testa o endpoint de invalidação de cache, mockando a função do CRUD.
    """
    # Mocka a função do CRUD para não depender do Redis e para controlar o retorno
    def mock_invalidate_cache(db, request: schemas.CacheInvalidationRequest):
        return schemas.CacheInvalidationResponse(
            invalidated_keys=5,
            message="Mocked: 5 chaves invalidadas"
        )
    
    monkeypatch.setattr(crud, "invalidate_cache", mock_invalidate_cache)

    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    invalidation_request = {"pattern": "kpis*"}
    response = test_client.post("/admin/cache/invalidate", headers=headers, json=invalidation_request)
    
    assert response.status_code == 200
    resp_json = response.json()
    assert resp_json["invalidated_keys"] == 5
    assert "Mocked" in resp_json["message"]
