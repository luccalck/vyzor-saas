import logging
from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Importa os componentes necessários da sua aplicação
from app.database import SessionLocal, engine
from app.models import (
    Base,
    Cliente,
    Usuario,
    Departamento,
    Importacao,
    RegistroFinanceiro,
    RegistroProduto,
    RegistroOperacional,
)
from app.auth import get_password_hash

# Configuração básica de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- DADOS DE TESTE ---

CLIENTE_NOME = "Cliente Padrão"
ADMIN_EMAIL = "admin@vyzor.com"
ADMIN_PASS = "admin123"
USER_EMAIL = "usuario@vyzor.com"
USER_PASS = "user123"
DEPARTAMENTOS = ["Vendas", "Marketing", "Suporte Técnico", "Financeiro"]

# ===============================
# FUNÇÕES AUXILIARES DE CRIAÇÃO
# ===============================

def criar_ou_obter_cliente(db: Session, nome: str) -> Cliente:
    """Cria um cliente se ele não existir, caso contrário, o retorna."""
    cliente = db.query(Cliente).filter(Cliente.nome == nome).first()
    if not cliente:
        logger.info(f"Criando cliente: {nome}")
        cliente = Cliente(nome=nome, ativo=True)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    return cliente

def criar_ou_obter_departamento(db: Session, nome: str) -> Departamento:
    """Cria um departamento se ele não existir."""
    departamento = db.query(Departamento).filter(Departamento.nome == nome).first()
    if not departamento:
        logger.info(f"Criando departamento: {nome}")
        departamento = Departamento(nome=nome)
        db.add(departamento)
        db.commit()
        db.refresh(departamento)
    return departamento

def criar_usuario_se_nao_existe(db: Session, nome_completo: str, email: str, password: str, perfil: str, cliente: Cliente, departamento: Departamento):
    """Cria um usuário se o email não estiver em uso."""
    usuario = db.query(Usuario).filter(Usuario.email == email).first()
    if not usuario:
        logger.info(f"Criando usuário ({perfil}): {email}")
        senha_hash = get_password_hash(password)
        novo_usuario = Usuario(
            nome_completo=nome_completo,
            email=email,
            senha_hash=senha_hash,
            perfil=perfil,
            cliente_id=cliente.id,
            departamento_id=departamento.id,
        )
        db.add(novo_usuario)
        db.commit()
        return novo_usuario
    return usuario

# ===============================
# FUNÇÃO PRINCIPAL DE SEEDING
# ===============================

def seed_database():
    logger.info("Iniciando o processo de seeding do banco de dados...")
    db: Session = SessionLocal()
    try:
        # 1. Criar Tabelas (se não existirem)
        logger.info("Verificando e criando tabelas do banco de dados...")
        Base.metadata.create_all(bind=engine)

        # 2. Criar Cliente Padrão
        cliente_padrao = criar_ou_obter_cliente(db, CLIENTE_NOME)

        # 3. Criar Departamentos
        deps = {nome: criar_ou_obter_departamento(db, nome) for nome in DEPARTAMENTOS}
        dep_vendas = deps["Vendas"]

        # 4. Criar Usuários (Admin e Comum)
        admin_user = criar_usuario_se_nao_existe(db, "Administrador Vyzor", ADMIN_EMAIL, ADMIN_PASS, "admin", cliente_padrao, dep_vendas)
        common_user = criar_usuario_se_nao_existe(db, "Usuário Comum", USER_EMAIL, USER_PASS, "usuario", cliente_padrao, dep_vendas)

        # 5. Criar uma Importação de Exemplo (se o usuário comum não tiver nenhuma)
        if common_user and not db.query(Importacao).filter(Importacao.usuario_id == common_user.id).count():
            logger.info(f"Criando importação de exemplo para o usuário {common_user.email}")
            importacao = Importacao(
                usuario_id=common_user.id,
                nome_arquivo="dados_de_exemplo.csv",
                tipo_arquivo="text/csv",
                status="concluído",
                total_registros=10,
                registros_validos=10,
                registros_invalidos=0
            )
            db.add(importacao)
            db.commit()
            db.refresh(importacao)

            # 6. Popular com dados de exemplo se a importação foi criada
            logger.info("Populando tabelas SaaS com dados de exemplo...")
            
            # Dados Financeiros
            db.add_all([
                RegistroFinanceiro(importacao_id=importacao.id, id_transacao=f"TXFIN{i}", data_transacao=date.today() - timedelta(days=i*10), receita=Decimal(150 + i*10), custo=Decimal(80 + i*5), lucro=Decimal(70 + i*5), categoria_financeira="Venda Online") for i in range(5)
            ])
            
            # Dados de Produtos
            db.add_all([
                RegistroProduto(importacao_id=importacao.id, id_venda=f"TXPROD{i}", sku_produto=f"SKU00{i}", nome_produto=f"Produto {i}", categoria_produto="Eletrônicos", quantidade_vendida=i+1, preco_unitario=Decimal(50.0), data_venda=date.today() - timedelta(days=i*10)) for i in range(5)
            ])
            
            # Dados Operacionais
            db.add_all([
                RegistroOperacional(importacao_id=importacao.id, id_evento=f"TXOP{i}", nome_colaborador="Colaborador Exemplo", departamento="Suporte Técnico", data_evento=date.today() - timedelta(days=i*10), tipo_evento="Atendimento", avaliacao_nps=10-i) for i in range(5)
            ])

            db.commit()
        else:
            logger.info("Usuário já possui importações. Nenhum dado novo foi adicionado.")

        logger.info("Seeding do banco de dados concluído com sucesso!")

    except IntegrityError as e:
        logger.warning(f"Erro de integridade durante o seeding (pode ser normal se os dados já existem): {e}")
        db.rollback()
    except Exception as e:
        logger.error(f"Ocorreu um erro durante o seeding do banco de dados: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
