-- Migration 0003: Índices críticos para tabelas SaaS e entidades relacionadas
-- Banco: PostgreSQL

BEGIN;

-- Registros Financeiros
CREATE INDEX IF NOT EXISTS idx_srf_importacao_data
    ON saas_registros_financeiros (importacao_id, data_transacao);
CREATE INDEX IF NOT EXISTS idx_srf_categoria_importacao
    ON saas_registros_financeiros (categoria_financeira, importacao_id);
CREATE INDEX IF NOT EXISTS idx_srf_centro_importacao
    ON saas_registros_financeiros (centro_custo, importacao_id);

-- Registros de Produtos
CREATE INDEX IF NOT EXISTS idx_srp_importacao_data
    ON saas_registros_produtos (importacao_id, data_venda);
CREATE INDEX IF NOT EXISTS idx_srp_categoria_importacao
    ON saas_registros_produtos (categoria_produto, importacao_id);

-- Registros Operacionais
CREATE INDEX IF NOT EXISTS idx_sro_importacao_data
    ON saas_registros_operacionais (importacao_id, data_evento);
CREATE INDEX IF NOT EXISTS idx_sro_departamento_importacao
    ON saas_registros_operacionais (departamento, importacao_id);
CREATE INDEX IF NOT EXISTS idx_sro_colaborador_importacao
    ON saas_registros_operacionais (nome_colaborador, importacao_id);

-- Indicadores Customizados
CREATE INDEX IF NOT EXISTS idx_ic_cliente_ativo
    ON indicadores_customizados (cliente_id, ativo);

-- Limiares de Indicadores
CREATE INDEX IF NOT EXISTS idx_li_cliente_ativo
    ON limiares_indicadores (cliente_id, ativo);

-- Importações
CREATE INDEX IF NOT EXISTS idx_importacoes_usuario_criadoem
    ON importacoes (usuario_id, criado_em);

COMMIT;