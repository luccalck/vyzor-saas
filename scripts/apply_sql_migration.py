import os
import sys
import pathlib
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError


def load_env(env_file: str = ".env") -> None:
    p = pathlib.Path(env_file)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            val = val.strip().strip('"').strip("'")
            os.environ.setdefault(key.strip(), val)


def get_engine():
    load_env()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL não encontrado no .env")
        sys.exit(1)
    # Cria a engine como no projeto
    engine = create_engine(
        db_url,
        connect_args={"sslmode": "require"},
        pool_pre_ping=True,
        echo=True,
    )
    return engine


def apply_sql(file_path: str) -> None:
    sql_path = pathlib.Path(file_path)
    if not sql_path.exists():
        print(f"Arquivo SQL não encontrado: {file_path}")
        sys.exit(1)
    sql = sql_path.read_text(encoding="utf-8")

    engine = get_engine()
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(sql)
        print(f"Migração aplicada com sucesso: {file_path}")
    except SQLAlchemyError as e:
        print("Falha ao aplicar migração SQL:", str(e))
        sys.exit(2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python scripts/apply_sql_migration.py <caminho_arquivo_sql>")
        sys.exit(1)
    apply_sql(sys.argv[1])