from sqlalchemy import (
    Column, Integer, String, TIMESTAMP, ForeignKey, BigInteger, JSON, Boolean, Numeric,
    TEXT, Date
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base

# ===============================
# ESTRUTURA BÁSICA E USUÁRIOS
# ===============================
class Departamento(Base):
    __tablename__ = "departamentos"
    id = Column(Integer, primary_key=True)
    nome = Column(String(100), nullable=False, unique=True)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    usuarios = relationship("Usuario", back_populates="departamento")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True)
    nome_completo = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True, index=True)
    senha_hash = Column(String, nullable=False)
    perfil = Column(String, default='usuario')
    departamento_id = Column(Integer, ForeignKey("departamentos.id"))
    departamento = relationship("Departamento", back_populates="usuarios")
    cliente_id = Column(Integer, ForeignKey("clientes.id"))
    cliente = relationship("Cliente", back_populates="usuarios")
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    atividades = relationship("AtividadeUsuario", back_populates="usuario")
    importacoes = relationship("Importacao", back_populates="usuario")
    notificacoes = relationship("Notificacao", back_populates="usuario")
    preferencias_notificacao = relationship("PreferenciasNotificacao", back_populates="usuario", uselist=False)

class AtividadeUsuario(Base):
    __tablename__ = "atividades_usuarios"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    acao = Column(String, nullable=False)
    tabela_afetada = Column(String)
    registro_id = Column(Integer)
    dados_antes = Column(JSON)
    dados_depois = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(TEXT)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    usuario = relationship("Usuario", back_populates="atividades")

# ===============================
# IMPORTAÇÕES E REGISTROS SaaS
# ===============================
class Importacao(Base):
    __tablename__ = "importacoes"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"))
    nome_arquivo = Column(String, nullable=False)
    tipo_arquivo = Column(String, nullable=False)
    tamanho_bytes = Column(BigInteger)
    status = Column(String, default='pendente')
    total_registros = Column(Integer, default=0)
    registros_validos = Column(Integer, default=0)
    registros_invalidos = Column(Integer, default=0)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    usuario = relationship("Usuario", back_populates="importacoes")

class RegistroFinanceiro(Base):
    __tablename__ = "saas_registros_financeiros"
    id = Column(Integer, primary_key=True)
    importacao_id = Column(Integer, ForeignKey("importacoes.id"), nullable=False)
    id_transacao = Column(String, unique=True, index=True, nullable=False)
    data_transacao = Column(Date, nullable=False)
    receita = Column(Numeric(12, 2))
    custo = Column(Numeric(12, 2))
    lucro = Column(Numeric(12, 2))
    centro_custo = Column(String)
    categoria_financeira = Column(String)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

class RegistroProduto(Base):
    __tablename__ = "saas_registros_produtos"
    id = Column(Integer, primary_key=True)
    importacao_id = Column(Integer, ForeignKey("importacoes.id"), nullable=False)
    id_venda = Column(String, index=True)
    sku_produto = Column(String, index=True)
    nome_produto = Column(String)
    categoria_produto = Column(String)
    quantidade_vendida = Column(Integer)
    preco_unitario = Column(Numeric(10, 2))
    id_loja = Column(String)
    data_venda = Column(Date)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

class RegistroOperacional(Base):
    __tablename__ = "saas_registros_operacionais"
    id = Column(Integer, primary_key=True)
    importacao_id = Column(Integer, ForeignKey("importacoes.id"), nullable=False)
    id_evento = Column(String, unique=True, index=True)
    id_colaborador = Column(String)
    nome_colaborador = Column(String)
    departamento = Column(String)
    data_evento = Column(Date)
    tipo_evento = Column(String)
    duracao_minutos = Column(Integer)
    avaliacao_nps = Column(Integer)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())

# ===============================
# ALERTAS E NOTIFICAÇÕES
# ===============================
class Notificacao(Base):
    __tablename__ = "notificacoes"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    titulo = Column(String(200), nullable=False)
    mensagem = Column(TEXT, nullable=False)
    tipo = Column(String(20), default="info")  # info, warning, danger
    canal = Column(String(20), default="in_app")  # in_app, email, web
    prioridade = Column(String(20), default="normal")  # baixa, normal, alta
    url_acao = Column(String)
    lida = Column(Boolean, default=False)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    usuario = relationship("Usuario", back_populates="notificacoes")

class PreferenciasNotificacao(Base):
    __tablename__ = "preferencias_notificacao"
    id = Column(Integer, primary_key=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), unique=True, nullable=False)
    canal_in_app = Column(Boolean, default=True)
    canal_email = Column(Boolean, default=False)
    canal_web = Column(Boolean, default=True)
    receber_alertas_financeiros = Column(Boolean, default=True)
    receber_alertas_produto = Column(Boolean, default=True)
    receber_alertas_operacional = Column(Boolean, default=True)
    limiar_queda_receita_percentual = Column(Numeric(5, 2), default=10.00)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    usuario = relationship("Usuario", back_populates="preferencias_notificacao")

# ===============================
# CLIENTES E INDICADORES CUSTOMIZADOS
# ===============================
class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True)
    nome = Column(String(150), nullable=False, unique=True)
    ativo = Column(Boolean, default=True)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    usuarios = relationship("Usuario", back_populates="cliente")
    indicadores = relationship("IndicadorCustomizado", back_populates="cliente")
    # Relacionamento reverso para as configurações de integração # ADICIONADO
    integracoes = relationship("IntegracaoCliente", back_populates="cliente")

class IndicadorCustomizado(Base):
    __tablename__ = "indicadores_customizados"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    descricao = Column(TEXT)
    unidade = Column(String(20))
    prefixo = Column(String(10))
    ativo = Column(Boolean, default=True)
    config_json = Column(JSON, nullable=False)
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    cliente = relationship("Cliente", back_populates="indicadores")

class LimiarIndicador(Base):
    __tablename__ = "limiares_indicadores"
    id = Column(Integer, primary_key=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    nome = Column(String(150), nullable=False)
    operador = Column(String(10), nullable=False)  # 'above' | 'below'
    valor_limite = Column(Numeric(12, 2), nullable=False)
    prioridade = Column(String(20), default='normal')  # baixa, normal, alta
    canal = Column(String(20), default='in_app')  # in_app, email, web
    ativo = Column(Boolean, default=True)
    mensagem = Column(String(255))
    config_json = Column(JSON, nullable=False)  # {tabela, agregacao, campo}
    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())
    cliente = relationship("Cliente")

# ===============================
# CONFIGURAÇÃO DE INTEGRAÇÕES     # ADICIONADO
# ===============================
class IntegracaoCliente(Base):
    __tablename__ = "integracoes_cliente"
    id = Column(Integer, primary_key=True)

    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    connector_key = Column(String(100), nullable=False) # Ex: 'hubspot', 'mysql_readonly'
    auth_type = Column(String(50), default="credentials") # Ex: credentials, oauth2
    credentials = Column(JSON) # Armazena credenciais (ex: host, user, pass, client_id, client_secret, tokens)
    enabled = Column(Boolean, default=False)
    last_sync_ts = Column(TIMESTAMP(timezone=True), nullable=True)

    criado_em = Column(TIMESTAMP(timezone=True), server_default=func.now())
    atualizado_em = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    cliente = relationship("Cliente", back_populates="integracoes")

