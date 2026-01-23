from fastapi.testclient import TestClient
from fastapi import UploadFile
from app.auth import create_access_token
import io

def test_etl_flow_with_mocked_ia(test_client: TestClient, test_user, monkeypatch):
    """
    Testa o endpoint de ETL (/ai/classificar-e-inserir) de ponta a ponta,
    mockando a chamada à API de IA para não depender de serviço externo.
    """
    # 1. Mock do serviço de IA
    def mock_classify_and_transform(cols, data, schemas):
        # Simula a IA retornando dados classificados
        return {
            "financeiro": [
                {"id_transacao": "TX123", "data_transacao": "2025-10-22", "receita": 150.75}
            ],
            "produtos": [],
            "operacional": []
        }
    
    # 2. Mock das funções de inserção no banco de dados
    inserted_data = {}
    def mock_insert_financial_data(db, registros, importacao_id):
        inserted_data['financeiro'] = registros
        return len(registros)

    monkeypatch.setattr("app.ai_service.classificar_e_transformar_dados_com_ia", mock_classify_and_transform)
    monkeypatch.setattr("app.crud.inserir_dados_financeiros_em_lote", mock_insert_financial_data)
    monkeypatch.setattr("app.crud.inserir_dados_produtos_em_lote", lambda db, r, i: 0)
    monkeypatch.setattr("app.crud.inserir_dados_operacionais_em_lote", lambda db, r, i: 0)

    # 3. Preparação da requisição
    token = create_access_token(data={"sub": test_user.email})
    headers = {"Authorization": f"Bearer {token}"}
    
    # Simula a criação de um registro de importação primeiro
    importacao_response = test_client.post(
        "/importacoes/",
        headers=headers,
        json={"nome_arquivo": "teste.csv", "tipo_arquivo": "text/csv", "usuario_id": test_user.id}
    )
    assert importacao_response.status_code == 201
    importacao_id = importacao_response.json()["id"]

    # 4. Simula o upload do arquivo
    file_content = b"col1,col2,col3\nval1,val2,val3"
    files = {"file": ("test.csv", io.BytesIO(file_content), "text/csv")}
    
    etl_response = test_client.post(f"/ai/classificar-e-inserir/{importacao_id}", headers=headers, files=files)

    # 5. Verificações
    assert etl_response.status_code == 200
    data = etl_response.json()
    assert data["mensagem"] == "Dados classificados, validados e inseridos com sucesso!"
    assert data["registros_financeiros_inseridos"] == 1
    
    # Verifica se a função de inserção mockada foi chamada com os dados corretos
    assert len(inserted_data.get('financeiro', [])) == 1
    assert inserted_data['financeiro'][0]['id_transacao'] == "TX123"
