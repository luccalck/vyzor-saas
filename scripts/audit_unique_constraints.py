import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables from .env in project root
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL não definido no .env")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"sslmode": "require"},
    pool_pre_ping=True,
)

QUERIES = {
    "usuarios.email": "SELECT email, COUNT(*) AS cnt FROM usuarios GROUP BY email HAVING COUNT(*) > 1 ORDER BY cnt DESC, email",
    "saas_registros_financeiros.id_transacao": "SELECT id_transacao AS chave, COUNT(*) AS cnt FROM saas_registros_financeiros GROUP BY id_transacao HAVING COUNT(*) > 1 ORDER BY cnt DESC, chave",
    "saas_registros_operacionais.id_evento": "SELECT id_evento AS chave, COUNT(*) AS cnt FROM saas_registros_operacionais GROUP BY id_evento HAVING COUNT(*) > 1 ORDER BY cnt DESC, chave",
}

with engine.connect() as conn:
    print("\nAuditoria de duplicados em colunas que devem ser únicas:\n")
    any_duplicates = False
    for label, sql in QUERIES.items():
        print(f"- Verificando {label}...")
        result = conn.execute(text(sql)).fetchall()
        if result:
            any_duplicates = True
            print(f"  Encontrados {len(result)} valores duplicados:")
            for row in result[:50]:
                chave = row[0]
                cnt = row[1]
                print(f"    {chave!r} aparece {cnt} vezes")
            if len(result) > 50:
                print(f"    ... e mais {len(result) - 50} entradas")
        else:
            print("  Nenhum duplicado encontrado.")
        print()

    if not any_duplicates:
        print("Nenhum duplicado encontrado em nenhuma coluna auditada. Seguro para aplicar índices únicos.")
    else:
        print("ATENÇÃO: Existem duplicados. Corrija-os antes de aplicar índices únicos.")