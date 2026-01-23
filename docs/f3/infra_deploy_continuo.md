Fase 3 — Infraestrutura e Base do Back-End

3 - Infraestrutura de deploy contínuo - Próximos passos gerais
- Configurar repositórios (Git/GitHub) com branches claras e proteção em `main`.
- Ajustar workflows de CI para build e testes básicos antes do deploy.
- Automatizar deploy para `dev` e `prod` via GitHub Actions com Azure Web Apps.
- Habilitar autenticação OIDC com Azure e gerenciar segredos via GitHub Secrets/Azure Key Vault.
- Validar build e saúde pós-deploy (health-check) no App Service.

Observações
- Estamos usando o Azure no momento (conta Lucca), integrações com GitHub já prontas.
- Ao fazer deploy para o GitHub, mudar o plano de assinatura do Azure para Standard v1 na conta hospedada (conta Lucca).
- Para não haver erros, falar com Lucca antes de fazer deploy.
- Deploy apenas para o GitHub para testar códigos entre colaboradores não precisa do Azure; se precisar do Azure para testar o servidor, será necessário.