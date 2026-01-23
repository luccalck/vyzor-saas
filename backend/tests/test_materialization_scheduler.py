from fastapi.testclient import TestClient
from app import crud, schemas
from app.auth import create_access_token

def test_get_scheduler_status_endpoint(test_client: TestClient, admin_user, monkeypatch):
    """Testa o endpoint que retorna o status do scheduler."""
    
    # Mock da função do CRUD para retornar um status controlado
    def mock_get_scheduler_status(db):
        return schemas.SchedulerStatusSchema(
            is_running=True,
            jobs=[
                schemas.JobInfoSchema(id='job1', name='Teste', trigger='interval[minutes=5]', next_run='2025-10-22T10:05:00+00:00')
            ],
            total_jobs=1
        )
        
    monkeypatch.setattr(crud, "get_scheduler_status", mock_get_scheduler_status)
    
    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.get("/admin/scheduler/status", headers=headers)
    
    assert response.status_code == 200
    status = schemas.SchedulerStatusSchema(**response.json())
    assert status.is_running is True
    assert status.total_jobs == 1
    assert status.jobs[0].name == 'Teste'

def test_add_custom_job_endpoint(test_client: TestClient, admin_user, monkeypatch):
    """Testa a adição de uma tarefa customizada via endpoint."""

    # Mock da função do CRUD para apenas retornar sucesso
    monkeypatch.setattr(crud, "add_custom_job", lambda db, job_request: True)
    
    token = create_access_token(data={"sub": admin_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    job_payload = {
        "job_id": "test_job_01",
        "name": "Job de Teste via API",
        "trigger_type": "interval",
        "trigger_config": {"minutes": 10},
        "function_name": "processar_alertas"
    }
    
    response = test_client.post("/admin/scheduler/jobs", headers=headers, json=job_payload)
    
    assert response.status_code == 200
    assert response.json() == {"success": True, "message": "Tarefa 'Job de Teste via API' adicionada com sucesso."}
