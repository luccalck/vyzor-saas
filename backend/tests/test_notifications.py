from fastapi.testclient import TestClient
from app.auth import create_access_token
from app.models import Notificacao

def test_create_and_list_notifications(test_client: TestClient, test_user, db_session):
    """
    Testa a criação de uma notificação e depois a lista para confirmar.
    """
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Cria uma notificação
    notification_payload = {
        "titulo": "Teste de Notificação",
        "mensagem": "Esta é uma mensagem de teste.",
        "tipo": "info"
    }
    create_response = test_client.post("/notificacoes", headers=headers, json=notification_payload)
    assert create_response.status_code == 201
    created_notification = create_response.json()
    assert created_notification["titulo"] == "Teste de Notificação"
    assert created_notification["usuario_id"] == test_user.id

    # 2. Lista as notificações para verificar se a nova foi criada
    list_response = test_client.get("/notificacoes", headers=headers)
    assert list_response.status_code == 200
    notifications = list_response.json()
    assert len(notifications) > 0
    assert any(n["id"] == created_notification["id"] for n in notifications)

def test_mark_notification_as_read(test_client: TestClient, test_user, db_session):
    """
    Testa se uma notificação pode ser marcada como lida.
    """
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    # Cria uma notificação diretamente no banco para o teste
    new_notif = Notificacao(
        usuario_id=test_user.id,
        titulo="Para Ler",
        mensagem="Marcar como lida.",
        lida=False
    )
    db_session.add(new_notif)
    db_session.commit()
    db_session.refresh(new_notif)
    
    assert new_notif.lida is False

    # Marca como lida via API
    read_response = test_client.put(f"/notificacoes/{new_notif.id}/ler", headers=headers)
    assert read_response.status_code == 200

    # Verifica no banco se o status mudou
    db_session.refresh(new_notif)
    assert new_notif.lida is True
