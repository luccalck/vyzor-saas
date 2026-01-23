import os
import logging
import time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do ficheiro .env
load_dotenv()

# Obtém a URL da base de dados a partir das variáveis de ambiente
DATABASE_URL = os.getenv("DATABASE_URL")
READ_DATABASE_URL = os.getenv("READ_DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("A variável de ambiente DATABASE_URL não está definida no ficheiro .env")

# Configurações de pool e echo via ambiente
SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "false").lower() == "true"
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))  # 30 minutos
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_STATEMENT_TIMEOUT_MS = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "0"))  # 0 = desabilitado
SLOW_QUERY_MS = int(os.getenv("SLOW_QUERY_MS", "500"))

# Monta connect_args conforme o driver
connect_args = {}
if DATABASE_URL.startswith("postgres") or DATABASE_URL.startswith("postgresql"):
    # SSL e statement_timeout (se configurado)
    connect_args["sslmode"] = os.getenv("PG_SSLMODE", "require")
    if DB_STATEMENT_TIMEOUT_MS > 0:
        connect_args["options"] = f"-c statement_timeout={DB_STATEMENT_TIMEOUT_MS}"

# Cria a engine principal
engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=SQLALCHEMY_ECHO,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)

# Cria engine de leitura (read replica) se disponível; fallback para principal
read_engine = create_engine(
    READ_DATABASE_URL or DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,  # leitura normalmente não precisa de echo
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_recycle=DB_POOL_RECYCLE,
    pool_timeout=DB_POOL_TIMEOUT,
)

# Sessões
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
ReadSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=read_engine)

# Base de modelos
Base = declarative_base()

# ===============================
# DEPENDÊNCIAS DE SESSÃO
# ===============================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_read_db():
    db = ReadSessionLocal()
    try:
        yield db
    finally:
        db.close()

# ===============================
# LOG DE SLOW QUERY VIA EVENTOS
# ===============================
logger = logging.getLogger("sqlalchemy.slow")

@event.listens_for(engine, "before_cursor_execute")
def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.perf_counter()

@event.listens_for(engine, "after_cursor_execute")
def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    start = getattr(context, "_query_start_time", None)
    if start is None:
        return
    duration_ms = (time.perf_counter() - start) * 1000
    if duration_ms >= SLOW_QUERY_MS:
        try:
            rowcount = cursor.rowcount
        except Exception:
            rowcount = None
        logger.warning(
            f"Slow SQL ({duration_ms:.1f} ms, rows={rowcount}): {statement} | params={parameters}"
        )