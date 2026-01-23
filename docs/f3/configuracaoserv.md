# 1- Configuração do servidor

## 1) Definir provedor (AWS, Azure, etc.)
- Provedor definido: **Microsoft Azure**.
- Justificativa:
  - Integrações nativas com serviços gerenciados para banco de dados, segurança e observabilidade.
  - **Azure Database for PostgreSQL (Flexible Server)** para o `DATABASE_URL` com `sslmode=require`.
  - **Azure App Service** ou **Azure Container Apps** para hospedar a API FastAPI com deploy contínuo via GitHub Actions.
  - **Azure Key Vault** para gerenciar segredos (`JWT_SECRET`, `GOOGLE_API_KEY`, credenciais externas) em produção.
  - **Azure Monitor / Application Insights** para logs, métricas, traces e alertas.
  - **Azure Storage** para arquivos (por exemplo, dados importados, relatórios gerados) quando necessário.

## 2) Configurar ambiente (produção, desenvolvimento e testes)
- Desenvolvimento (Dev):
  - Execução local com `uvicorn` e arquivo `security.env` (não versionado).
  - Banco de dados local ou instância de desenvolvimento em Azure PostgreSQL.
  - Logs verbosos (`echo=True` em SQLAlchemy) e recarregamento automático (`--reload`).
- Testes (QA/Staging):
  - Ambiente espelhando produção com instâncias menores.
  - Integração de CI/CD (GitHub Actions) para rodar testes automatizados antes do deploy.
  - Segredos fornecidos via Key Vault/Secrets do ambiente e variáveis protegidas.
- Produção (Prod):
  - API implantada em **Azure App Service** ou **Azure Container Apps**.
  - Banco gerenciado em **Azure Database for PostgreSQL** com SSL habilitado.
  - Segredos centralizados em **Azure Key Vault**.
  - Observabilidade com **Azure Monitor** e políticas de alerta.
  - Backups automáticos do banco e políticas de retenção.

## 3) Ajustar variáveis de ambiente e segurança (chaves, tokens, certificados SSL)
- Variáveis utilizadas no código (mapeadas):
  - `DATABASE_URL` (backend/app/database.py, alembic/env.py)
  - `JWT_SECRET` (backend/app/auth.py)
  - `GOOGLE_API_KEY` (backend/app/ai_service.py)
- Boas práticas:
  - Manter arquivos `.env` apenas em desenvolvimento; em produção, usar **Azure Key Vault**.
  - Não versionar segredos; adicionar `security.env` ao `.gitignore`.
  - Certificados SSL gerenciados pelo provedor e `sslmode=require` para PostgreSQL.
- Arquivo único consolidado criado: `security.env` na raiz do projeto.
  - Contém as variáveis e credenciais solicitadas, incluindo Gmail e Instagram.
  - Em produção, valores devem ser fornecidos por Key Vault; o arquivo local serve para desenvolvimento.

## 4) Integração com GitHub Actions (já presente no repositório)
- Workflows em `.github/workflows/` podem ser ajustados para:
  - Publicar a imagem/container na Azure.
  - Injetar segredos via GitHub Secrets e Azure Key Vault.
  - Rodar migrações Alembic antes de iniciar a aplicação.