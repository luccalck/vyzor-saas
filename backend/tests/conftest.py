import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import sys

# Garante que a pasta 'app' está no path para os testes encontrarem os módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.main import app
from app.database import Base, get_db
from app.models import Usuario, Departamento, Cliente
from app.auth import get_password_hash

# Configuração do banco de dados de teste em memória (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Cria as tabelas no banco de dados de teste ANTES de qualquer teste rodar
Base.metadata.create_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Fixture que cria uma nova sessão de banco de dados para cada teste.
    Usa transações para isolar os testes e faz rollback ao final.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Adiciona dados básicos que podem ser necessários em múltiplos testes
    # Cliente e Departamento são criados aqui para garantir que existam
    # antes da criação de usuários de teste.
    cliente_teste = Cliente(nome="Cliente Teste Fixture", ativo=True)
    dep_teste = Departamento(nome="Departamento Teste Fixture")
    session.add(cliente_teste)
    session.add(dep_teste)
    session.commit()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def test_client(db_session):
    """
    Fixture que cria um cliente de API (TestClient) para interagir
    com a aplicação nos testes, garantindo que ela use o banco de dados de teste.
    """
    
    def override_get_db():
        """Substitui a dependência get_db para usar a sessão de teste."""
        try:
            yield db_session
        finally:
            # Sessão é fechada pelo fixture db_session; não fechar aqui
            pass

    # Aplica a substituição da dependência na aplicação
    app.dependency_overrides[get_db] = override_get_db
    
    # Cria o cliente de teste
    with TestClient(app) as client:
        yield client

    # Limpa a substituição após o teste para não afetar outros
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(db_session):
    """Fixture para criar um usuário comum de teste no banco de dados."""
    cliente = db_session.query(Cliente).filter(Cliente.nome == "Cliente Teste Fixture").one()
    departamento = db_session.query(Departamento).filter(Departamento.nome == "Departamento Teste Fixture").one()
    
    user = Usuario(
        email="testuser@example.com",
        nome_completo="Test User",
        senha_hash=get_password_hash("testpassword"),
        perfil="usuario",
        cliente_id=cliente.id,
        departamento_id=departamento.id
    )
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture(scope="function")
def admin_user(db_session):
    """Fixture para criar um usuário administrador de teste no banco de dados."""
    cliente = db_session.query(Cliente).filter(Cliente.nome == "Cliente Teste Fixture").one()
    departamento = db_session.query(Departamento).filter(Departamento.nome == "Departamento Teste Fixture").one()

    user = Usuario(
        email="admin@example.com",
        nome_completo="Admin User",
        senha_hash=get_password_hash("adminpassword"),
        perfil="admin",
        cliente_id=cliente.id,
        departamento_id=departamento.id
    )
    db_session.add(user)
    db_session.commit()
    return user

