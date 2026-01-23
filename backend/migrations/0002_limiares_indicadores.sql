-- Migration: Create limiares_indicadores table

BEGIN;

CREATE TABLE IF NOT EXISTS limiares_indicadores (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome VARCHAR(150) NOT NULL,
    operador VARCHAR(10) NOT NULL,
    valor_limite NUMERIC(12,2) NOT NULL,
    prioridade VARCHAR(20) DEFAULT 'normal',
    canal VARCHAR(20) DEFAULT 'in_app',
    ativo BOOLEAN DEFAULT TRUE,
    mensagem VARCHAR(255),
    config_json JSONB NOT NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Optional unique per cliente + nome
CREATE UNIQUE INDEX IF NOT EXISTS uq_limiares_cliente_nome
ON limiares_indicadores (cliente_id, nome);

COMMIT;