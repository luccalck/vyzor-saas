from fastapi.testclient import TestClient

def test_get_available_predictive_models(test_client: TestClient):
    """Testa o endpoint que lista os modelos preditivos disponíveis."""
    response = test_client.get("/analise-preditiva/modelos")
    
    assert response.status_code == 200
    payload = response.json()
    
    assert "alvos" in payload
    assert "modelos" in payload
    assert "periodicidades" in payload
    assert "receita_mensal" in payload["alvos"]
    assert any(modelo["nome"] == "tendencia_linear" for modelo in payload["modelos"])
