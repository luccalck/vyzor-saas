from fastapi.testclient import TestClient
from app.auth import create_access_token
from app import crud, ai_service

def test_export_pdf_report(test_client: TestClient, test_user, monkeypatch):
    """Testa o endpoint de exportação de relatório para PDF."""
    
    # Mock das funções do CRUD e AI para não dependerem de banco ou API externa
    monkeypatch.setattr(crud, "obter_dados_para_relatorio", lambda db, uid, tipo: [{"coluna": "valor"}])
    monkeypatch.setattr(crud, "formatar_dados_para_relatorio", lambda db, uid, tipo: '{"dados": "mock"}')
    monkeypatch.setattr(ai_service, "gerar_relatorio_com_ia", lambda tipo, dados: "# Relatório Teste PDF")
    monkeypatch.setattr(crud, "log_activity", lambda *args, **kwargs: None) # Ignora o log

    # Cria um token para o usuário de teste
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    response = test_client.post("/dashboard/exportar-relatorio-pdf?tipo_relatorio=financeiro", headers=headers)
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "relatorio_financeiro.pdf" in response.headers["content-disposition"]

def test_export_excel_report(test_client: TestClient, test_user, monkeypatch):
    """Testa o endpoint de exportação de relatório para Excel."""

    monkeypatch.setattr(crud, "obter_dados_para_relatorio", lambda db, uid, tipo: [{"coluna": "valor"}])
    monkeypatch.setattr(crud, "formatar_dados_para_relatorio", lambda db, uid, tipo: '{"dados": "mock"}')
    monkeypatch.setattr(ai_service, "gerar_relatorio_com_ia", lambda tipo, dados: "# Relatório Teste Excel")
    monkeypatch.setattr(crud, "log_activity", lambda *args, **kwargs: None)

    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    response = test_client.post("/dashboard/exportar-relatorio-excel?tipo_relatorio=produtos", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert "relatorio_produtos.xlsx" in response.headers["content-disposition"]

def test_generate_ia_report_no_data(test_client: TestClient, test_user, monkeypatch):
    """Testa a geração de relatório quando não há dados, esperando um erro 404."""
    
    # Mock para simular que não há dados para o relatório
    monkeypatch.setattr(crud, "obter_dados_para_relatorio", lambda db, uid, tipo: [])

    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}

    response = test_client.post("/dashboard/gerar-relatorio-ia?tipo_relatorio=financeiro", headers=headers)
    
    assert response.status_code == 404
    assert "Não há dados suficientes" in response.json()["detail"]
