from fastapi.testclient import TestClient
from app import crud, schemas
from app.auth import create_access_token
from decimal import Decimal

# Mock de um limiar para ser usado nos testes
class MockLimiar:
    def __init__(self, nome, operador, valor_limite, mensagem=None):
        self.nome = nome
        self.operador = operador
        self.valor_limite = valor_limite
        self.mensagem = mensagem or f"Alerta para {nome}"
        self.prioridade = "media"
        self.canal = "sistema"

def test_alert_on_revenue_drop(monkeypatch):
    """
    Testa se um alerta de 'warning' é gerado para queda de receita padrão.
    """
    # Mock da função que busca métricas para simular uma queda de receita
    def mock_get_metricas_comparativas(db, usuario_id, filtros):
        return [
            schemas.MetricaComparativa(
                nome="Receita Total",
                valor_atual=Decimal("800"),
                valor_anterior=Decimal("1000"),
                percentual_mudanca=Decimal("-20.0"),
                tendencia="baixa"
            )
        ]
    monkeypatch.setattr(crud, "get_metricas_comparativas", mock_get_metricas_comparativas)
    
    # Mock da função que busca limiares para garantir que não há limiares customizados
    monkeypatch.setattr(crud, "list_limiares_cliente", lambda db, cliente_id: [])

    alertas = crud.gerar_alertas_dashboard(db=None, usuario_id=1, filtros=schemas.FiltrosDashboard())
    
    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "warning"
    assert "Queda na Receita" in alertas[0]["titulo"]

def test_alert_on_low_nps(monkeypatch):
    """
    Testa se um alerta de 'danger' é gerado para NPS médio baixo.
    """
    def mock_get_metricas_comparativas(db, usuario_id, filtros):
        return [
            schemas.MetricaComparativa(
                nome="NPS Médio",
                valor_atual=Decimal("5.5"),
                valor_anterior=Decimal("7.0"),
                percentual_mudanca=Decimal("-21.4"),
                tendencia="baixa"
            )
        ]
    monkeypatch.setattr(crud, "get_metricas_comparativas", mock_get_metricas_comparativas)
    monkeypatch.setattr(crud, "list_limiares_cliente", lambda db, cliente_id: [])

    alertas = crud.gerar_alertas_dashboard(db=None, usuario_id=1, filtros=schemas.FiltrosDashboard())

    assert len(alertas) == 1
    assert alertas[0]["tipo"] == "danger"
    assert "NPS Baixo" in alertas[0]["titulo"]

def test_custom_threshold_alert_overrides_default(monkeypatch):
    """
    Testa se um alerta customizado de limiar substitui o alerta padrão.
    """
    def mock_get_metricas_comparativas(db, usuario_id, filtros):
        return [
            schemas.MetricaComparativa(
                nome="Receita Total",
                valor_atual=Decimal("800"),
                valor_anterior=Decimal("1000"),
                percentual_mudanca=Decimal("-20.0"),
                tendencia="baixa"
            )
        ]
    monkeypatch.setattr(crud, "get_metricas_comparativas", mock_get_metricas_comparativas)

    # Mock para retornar um limiar customizado para queda de receita
    mock_limiar = MockLimiar(nome="Receita Total", operador="below", valor_limite=Decimal("15"), mensagem="ATENÇÃO: Queda de receita crítica!")
    monkeypatch.setattr(crud, "list_limiares_cliente", lambda db, cliente_id: [mock_limiar])

    alertas = crud.gerar_alertas_dashboard(db=None, usuario_id=1, filtros=schemas.FiltrosDashboard())
    
    # Apenas o alerta do limiar deve ser gerado
    assert len(alertas) == 1
    assert "ATENÇÃO" in alertas[0]["mensagem"]
    assert "Alerta: Receita Total" in alertas[0]["titulo"]
