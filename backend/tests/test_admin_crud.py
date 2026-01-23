from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.auth import create_access_token
from app.models import Usuario, Departamento

def test_admin_can_create_department(test_client: TestClient, admin_user, db_session: Session):
    """Testa se um administrador pode criar um novo departamento."""
    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.post("/admin/departamentos/", headers=headers, json={"nome": "Recursos Humanos"})
    
    assert response.status_code == 201
    data = response.json()
    assert data["nome"] == "Recursos Humanos"
    
    # Verifica se foi realmente salvo no banco
    dep = db_session.query(Departamento).filter(Departamento.nome == "Recursos Humanos").first()
    assert dep is not None

def test_admin_can_list_users(test_client: TestClient, admin_user, test_user):
    """Testa se um administrador pode listar todos os usuários."""
    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.get("/admin/usuarios/", headers=headers)
    
    assert response.status_code == 200
    users = response.json()
    # Espera encontrar o admin_user, test_user e o usuário criado no conftest.py
    assert len(users) >= 2
    emails = [user["email"] for user in users]
    assert admin_user.email in emails
    assert test_user.email in emails

def test_non_admin_cannot_access_admin_routes(test_client: TestClient, test_user):
    """Testa se um usuário comum recebe erro 403 (Forbidden) ao tentar acessar rotas de admin."""
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.get("/admin/usuarios/", headers=headers)
    assert response.status_code == 403
    
    response_create_dep = test_client.post("/admin/departamentos/", headers=headers, json={"nome": "Marketing"})
    assert response_create_dep.status_code == 403
