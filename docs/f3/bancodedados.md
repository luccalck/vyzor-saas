Fase 3 — Infraestrutura e Base do Back-End

2 - Banco de dados - Próximos passos gerais
- Utilizar Supabase (PostgreSQL) como banco SQL padrão do projeto.
- Consolidar o modelo inicial em `backend/app/models.py` com relacionamentos principais e manter migrações via Alembic.
- Criar scripts básicos de seed para dados de teste em desenvolvimento (fixtures ou comandos dedicados).
- Garantir conexões seguras (`sslmode=require`) e otimizações iniciais (índices essenciais, parâmetros de pool).
- Não alterar o banco manualmente; sempre aplicar mudanças via código e Alembic.