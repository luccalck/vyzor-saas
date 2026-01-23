-- Migration: Create clientes and indicadores_customizados, and add cliente_id to usuarios

BEGIN;

-- Clientes table
CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(150) NOT NULL UNIQUE,
    ativo BOOLEAN DEFAULT TRUE,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Add cliente_id to usuarios
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='usuarios' AND column_name='cliente_id'
    ) THEN
        ALTER TABLE usuarios ADD COLUMN cliente_id INTEGER;
        ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_cliente
            FOREIGN KEY (cliente_id) REFERENCES clientes(id);
    END IF;
END
$$;

-- Indicadores customizados table
CREATE TABLE IF NOT EXISTS indicadores_customizados (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    nome VARCHAR(150) NOT NULL,
    descricao TEXT,
    unidade VARCHAR(20),
    prefixo VARCHAR(10),
    ativo BOOLEAN DEFAULT TRUE,
    config_json JSONB NOT NULL,
    criado_em TIMESTAMPTZ DEFAULT NOW(),
    atualizado_em TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint per client
CREATE UNIQUE INDEX IF NOT EXISTS uq_indicadores_cliente_nome 
ON indicadores_customizados (cliente_id, nome);

COMMIT;