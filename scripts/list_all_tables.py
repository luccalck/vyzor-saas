import os
import sys
import psycopg2
import configparser
from urllib.parse import urlparse

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    cfg = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'alembic.ini')
    if os.path.exists(ini_path):
        cfg.read(ini_path)
        DATABASE_URL = cfg.get('alembic', 'sqlalchemy.url', fallback=None)

if not DATABASE_URL:
    print('DATABASE_URL não definido e alembic.ini não encontrado ou sem URL.')
    sys.exit(1)

url = urlparse(DATABASE_URL)
conn_kwargs = {
    'host': url.hostname,
    'port': url.port or 5432,
    'database': url.path.lstrip('/'),
    'user': url.username,
    'password': url.password,
    'sslmode': 'require',
}

try:
    conn = psycopg2.connect(**conn_kwargs)
except Exception as e:
    print(f'Erro de conexão: {e}')
    sys.exit(1)

with conn, conn.cursor() as cur:
    cur.execute(
        """
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY tablename;
        """
    )
    tables = [r[0] for r in cur.fetchall()]

print('Tabelas presentes no schema public:')
for t in tables:
    print(f" - {t}")