import os
import sys
import psycopg2
import configparser
from urllib.parse import urlparse

DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    # Fallback: ler do alembic.ini
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

tables = [
    'usuarios',
    'atividades_usuarios',
    'logs_importacoes',
    'registros_importados',
    'saas_registros_financeiros',
    'saas_registros_operacionais',
    'saas_registros_produtos',
]

with conn, conn.cursor() as cur:
    cur.execute(
        """
        SELECT i.relname AS indexname,
               t.relname AS tablename,
               ind.indisunique AS is_unique,
               array_to_string(array_agg(att.attname ORDER BY att.attname), ',') AS columns
        FROM pg_index ind
        JOIN pg_class i ON i.oid = ind.indexrelid
        JOIN pg_class t ON t.oid = ind.indrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN pg_attribute att ON att.attrelid = t.oid AND att.attnum = ANY(ind.indkey)
        WHERE t.relname = ANY(%s)
        GROUP BY indexname, tablename, ind.indisunique
        ORDER BY tablename, indexname;
        """,
        (tables,)
    )
    rows = cur.fetchall()

print('Índices existentes nas tabelas alvo:')
current_table = None
for indexname, tablename, is_unique, columns in rows:
    if tablename != current_table:
        current_table = tablename
        print(f"\nTabela: {tablename}")
    tipo = 'UNIQUE' if is_unique else 'INDEX'
    print(f" - {indexname} [{tipo}] ({columns})")

# Também listar constraints únicas
print("\nConstraints únicas nas tabelas alvo:")
with conn, conn.cursor() as cur:
    cur.execute(
        """
        SELECT
            c.conname AS constraint_name,
            t.relname AS tablename,
            array_to_string(array_agg(a.attname ORDER BY a.attname), ',') AS columns
        FROM pg_constraint c
        JOIN pg_class t ON t.oid = c.conrelid
        JOIN pg_namespace n ON n.oid = t.relnamespace
        JOIN unnest(c.conkey) AS cols(attnum) ON TRUE
        JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = cols.attnum
        WHERE c.contype = 'u' AND t.relname = ANY(%s)
        GROUP BY constraint_name, tablename
        ORDER BY tablename, constraint_name;
        """,
        (tables,)
    )
    cons = cur.fetchall()

current_table = None
for constraint_name, tablename, columns in cons:
    if tablename != current_table:
        current_table = tablename
        print(f"\nTabela: {tablename}")
    print(f" - {constraint_name} (UNIQUE) ({columns})")