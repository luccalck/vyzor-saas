from fastapi.testclient import TestClient
from app import schemas

def test_login_success(test_client: TestClient, test_user):
    """
    Testa o endpoint de login com credenciais corretas.
    Usa as fixtures 'test_client' e 'test_user' do conftest.
    """
    login_data = {
        "username": test_user.email,
        "password": "testpassword"
    }
    response = test_client.post("/login", data=login_data)
    
    assert response.status_code == 200
    token = schemas.Token(**response.json())
    assert token.token_type == "bearer"
    assert "access_token" in response.json()

def test_login_failure_wrong_password(test_client: TestClient, test_user):
    """Testa o endpoint de login com senha incorreta."""
    login_data_wrong_pass = {
        "username": test_user.email,
        "password": "wrongpassword"
    }
    response = test_client.post("/login", data=login_data_wrong_pass)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"

def test_login_failure_wrong_email(test_client: TestClient):
    """Testa o endpoint de login com um email que não existe."""
    login_data_wrong_email = {
        "username": "nonexistent@example.com",
        "password": "testpassword"
    }
    response = test_client.post("/login", data=login_data_wrong_email)
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Email ou senha incorretos"
