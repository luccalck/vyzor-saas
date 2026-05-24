-- WARNING: This schema is for context only and is not meant to be run.
-- Table order and constraints may not be valid for execution.

CREATE TABLE public.alembic_version (
  version_num character varying NOT NULL,
  CONSTRAINT alembic_version_pkey PRIMARY KEY (version_num)
);
CREATE TABLE public.atividades_usuarios (
  id integer NOT NULL DEFAULT nextval('atividades_usuarios_id_seq'::regclass),
  usuario_id integer,
  acao character varying NOT NULL,
  tabela_afetada character varying,
  registro_id integer,
  dados_antes json,
  dados_depois json,
  ip_address character varying,
  user_agent text,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT atividades_usuarios_pkey PRIMARY KEY (id),
  CONSTRAINT atividades_usuarios_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.clientes (
  id integer NOT NULL DEFAULT nextval('clientes_id_seq'::regclass),
  nome character varying NOT NULL UNIQUE,
  ativo boolean DEFAULT true,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT clientes_pkey PRIMARY KEY (id)
);
CREATE TABLE public.departamentos (
  id integer NOT NULL DEFAULT nextval('departamentos_id_seq'::regclass),
  nome character varying NOT NULL UNIQUE,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT departamentos_pkey PRIMARY KEY (id)
);
CREATE TABLE public.importacoes (
  id integer NOT NULL DEFAULT nextval('importacoes_id_seq'::regclass),
  usuario_id integer,
  nome_arquivo character varying NOT NULL,
  tipo_arquivo character varying NOT NULL,
  tamanho_bytes bigint,
  status character varying,
  total_registros integer,
  registros_validos integer,
  registros_invalidos integer,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT importacoes_pkey PRIMARY KEY (id),
  CONSTRAINT importacoes_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.indicadores_customizados (
  id integer NOT NULL DEFAULT nextval('indicadores_customizados_id_seq'::regclass),
  cliente_id integer NOT NULL,
  nome character varying NOT NULL,
  descricao text,
  unidade character varying,
  prefixo character varying,
  ativo boolean DEFAULT true,
  config_json jsonb NOT NULL,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT indicadores_customizados_pkey PRIMARY KEY (id),
  CONSTRAINT indicadores_customizados_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id)
);
CREATE TABLE public.integracoes_cliente (
  id integer NOT NULL DEFAULT nextval('integracoes_cliente_id_seq'::regclass),
  cliente_id integer NOT NULL,
  connector_key character varying NOT NULL,
  auth_type character varying,
  credentials json,
  enabled boolean,
  last_sync_ts timestamp with time zone,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT integracoes_cliente_pkey PRIMARY KEY (id),
  CONSTRAINT integracoes_cliente_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id)
);
CREATE TABLE public.integracoes_conectores (
  id integer NOT NULL DEFAULT nextval('integracoes_conectores_id_seq'::regclass),
  cliente_id integer NOT NULL,
  nome character varying NOT NULL,
  tipo_fonte character varying NOT NULL,
  tipo_conector character varying NOT NULL,
  configuracao json NOT NULL,
  credenciais_criptografadas text,
  ativo boolean,
  frequencia_sincronizacao character varying,
  ultima_sincronizacao timestamp with time zone,
  proxima_sincronizacao timestamp with time zone,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT integracoes_conectores_pkey PRIMARY KEY (id),
  CONSTRAINT integracoes_conectores_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id)
);
CREATE TABLE public.integracoes_execucoes (
  id integer NOT NULL DEFAULT nextval('integracoes_execucoes_id_seq'::regclass),
  conector_id integer NOT NULL,
  status character varying,
  tipo_operacao character varying NOT NULL,
  registros_processados integer,
  registros_inseridos integer,
  registros_atualizados integer,
  registros_erro integer,
  mensagem_erro text,
  detalhes_execucao json,
  iniciado_em timestamp with time zone DEFAULT now(),
  finalizado_em timestamp with time zone,
  duracao_segundos integer,
  CONSTRAINT integracoes_execucoes_pkey PRIMARY KEY (id),
  CONSTRAINT integracoes_execucoes_conector_id_fkey FOREIGN KEY (conector_id) REFERENCES public.integracoes_conectores(id)
);
CREATE TABLE public.integracoes_mapeamentos (
  id integer NOT NULL DEFAULT nextval('integracoes_mapeamentos_id_seq'::regclass),
  conector_id integer NOT NULL,
  tabela_destino character varying NOT NULL,
  mapeamento_campos json NOT NULL,
  filtros json,
  transformacoes json,
  ativo boolean,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT integracoes_mapeamentos_pkey PRIMARY KEY (id),
  CONSTRAINT integracoes_mapeamentos_conector_id_fkey FOREIGN KEY (conector_id) REFERENCES public.integracoes_conectores(id)
);
CREATE TABLE public.itens_pedido (
  id bigint NOT NULL DEFAULT nextval('itens_pedido_id_seq'::regclass),
  pedido_id bigint NOT NULL,
  produto_id bigint NOT NULL,
  quantidade integer NOT NULL DEFAULT 1,
  preco_unitario numeric NOT NULL,
  CONSTRAINT itens_pedido_pkey PRIMARY KEY (id),
  CONSTRAINT fk_pedido FOREIGN KEY (pedido_id) REFERENCES public.pedidos(id),
  CONSTRAINT fk_produto FOREIGN KEY (produto_id) REFERENCES public.saas_registros_produtos(id)
);
CREATE TABLE public.limiares_indicadores (
  id integer NOT NULL DEFAULT nextval('limiares_indicadores_id_seq'::regclass),
  cliente_id integer NOT NULL,
  nome character varying NOT NULL,
  operador character varying NOT NULL,
  valor_limite numeric NOT NULL,
  prioridade character varying DEFAULT 'normal'::character varying,
  canal character varying DEFAULT 'in_app'::character varying,
  ativo boolean DEFAULT true,
  mensagem character varying,
  config_json jsonb NOT NULL,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT limiares_indicadores_pkey PRIMARY KEY (id),
  CONSTRAINT limiares_indicadores_cliente_id_fkey FOREIGN KEY (cliente_id) REFERENCES public.clientes(id)
);
CREATE TABLE public.notificacoes (
  id integer NOT NULL DEFAULT nextval('notificacoes_id_seq'::regclass),
  usuario_id integer NOT NULL,
  titulo character varying NOT NULL,
  mensagem text NOT NULL,
  tipo character varying,
  canal character varying,
  prioridade character varying,
  url_acao character varying,
  lida boolean,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT notificacoes_pkey PRIMARY KEY (id),
  CONSTRAINT notificacoes_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.pedidos (
  id bigint NOT NULL DEFAULT nextval('pedidos_id_seq'::regclass),
  usuario_id bigint NOT NULL,
  status_pedido text DEFAULT 'pendente'::text,
  valor_total numeric NOT NULL,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT pedidos_pkey PRIMARY KEY (id),
  CONSTRAINT fk_usuario FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.preferencias_notificacao (
  id integer NOT NULL DEFAULT nextval('preferencias_notificacao_id_seq'::regclass),
  usuario_id integer NOT NULL UNIQUE,
  canal_in_app boolean,
  canal_email boolean,
  canal_web boolean,
  receber_alertas_financeiros boolean,
  receber_alertas_produto boolean,
  receber_alertas_operacional boolean,
  limiar_queda_receita_percentual numeric,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT preferencias_notificacao_pkey PRIMARY KEY (id),
  CONSTRAINT preferencias_notificacao_usuario_id_fkey FOREIGN KEY (usuario_id) REFERENCES public.usuarios(id)
);
CREATE TABLE public.saas_registros_financeiros (
  id integer NOT NULL DEFAULT nextval('saas_registros_financeiros_id_seq1'::regclass),
  importacao_id integer NOT NULL,
  id_transacao character varying NOT NULL,
  data_transacao date NOT NULL,
  receita numeric,
  custo numeric,
  lucro numeric,
  centro_custo character varying,
  categoria_financeira character varying,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT saas_registros_financeiros_pkey PRIMARY KEY (id),
  CONSTRAINT saas_registros_financeiros_importacao_id_fkey1 FOREIGN KEY (importacao_id) REFERENCES public.importacoes(id)
);
CREATE TABLE public.saas_registros_operacionais (
  id integer NOT NULL DEFAULT nextval('saas_registros_operacionais_id_seq'::regclass),
  importacao_id integer NOT NULL,
  id_evento character varying,
  id_colaborador character varying,
  nome_colaborador character varying,
  departamento character varying,
  data_evento date,
  tipo_evento character varying,
  duracao_minutos integer,
  avaliacao_nps integer,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT saas_registros_operacionais_pkey PRIMARY KEY (id),
  CONSTRAINT saas_registros_operacionais_importacao_id_fkey FOREIGN KEY (importacao_id) REFERENCES public.importacoes(id)
);
CREATE TABLE public.saas_registros_produtos (
  id integer NOT NULL DEFAULT nextval('saas_registros_produtos_id_seq'::regclass),
  importacao_id integer NOT NULL,
  id_venda character varying,
  sku_produto character varying,
  nome_produto character varying,
  categoria_produto character varying,
  quantidade_vendida integer,
  preco_unitario numeric,
  id_loja character varying,
  data_venda date,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT saas_registros_produtos_pkey PRIMARY KEY (id),
  CONSTRAINT saas_registros_produtos_importacao_id_fkey FOREIGN KEY (importacao_id) REFERENCES public.importacoes(id)
);
CREATE TABLE public.sua_tabela_financeira (
  id integer NOT NULL DEFAULT nextval('saas_registros_financeiros_id_seq'::regclass),
  importacao_id integer NOT NULL,
  id_transacao character varying NOT NULL,
  data_transacao date NOT NULL,
  sua_coluna_receita numeric,
  custo numeric,
  lucro numeric,
  centro_custo character varying,
  categoria_financeira character varying,
  criado_em timestamp with time zone DEFAULT now(),
  CONSTRAINT sua_tabela_financeira_pkey PRIMARY KEY (id),
  CONSTRAINT saas_registros_financeiros_importacao_id_fkey FOREIGN KEY (importacao_id) REFERENCES public.importacoes(id)
);
CREATE TABLE public.user_profiles (
  id uuid NOT NULL,
  email text UNIQUE,
  created_at timestamp with time zone DEFAULT now(),
  last_login_at timestamp with time zone,
  CONSTRAINT user_profiles_pkey PRIMARY KEY (id)
);
CREATE TABLE public.usuarios (
  id integer NOT NULL DEFAULT nextval('usuarios_id_seq'::regclass),
  nome_completo character varying NOT NULL,
  email character varying NOT NULL,
  senha_hash character varying NOT NULL,
  perfil character varying,
  departamento_id integer,
  criado_em timestamp with time zone DEFAULT now(),
  atualizado_em timestamp with time zone DEFAULT now(),
  cliente_id integer,
  CONSTRAINT usuarios_pkey PRIMARY KEY (id),
  CONSTRAINT usuarios_departamento_id_fkey FOREIGN KEY (departamento_id) REFERENCES public.departamentos(id),
  CONSTRAINT fk_usuarios_cliente FOREIGN KEY (cliente_id) REFERENCES public.clientes(id)
);