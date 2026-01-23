from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, List, Any, Dict
from decimal import Decimal
from datetime import date, datetime
from pydantic import field_validator, model_validator

# ===============================
# SCHEMAS DE AUTENTICAÇÃO E ESTRUTURA
# ===============================
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class DepartamentoBase(BaseModel):
    nome: str

class DepartamentoCreate(DepartamentoBase):
    pass

class DepartamentoUpdate(BaseModel):
    nome: Optional[str] = None

class UsuarioBase(BaseModel):
    email: str
    nome_completo: str
    perfil: Optional[str] = 'usuario'

class UsuarioCreate(UsuarioBase):
    password: str

class UsuarioUpdate(BaseModel):
    email: Optional[str] = None
    nome_completo: Optional[str] = None
    perfil: Optional[str] = None
    departamento_id: Optional[int] = None

# ===============================
# SCHEMAS DE RESPOSTA CORRIGIDOS (PARA EVITAR RECURSÃO)
# ===============================
class UsuarioSimples(UsuarioBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class DepartamentoSimples(DepartamentoBase):
    id: int
    model_config = ConfigDict(from_attributes=True)

class Usuario(UsuarioBase):
    id: int
    departamento: Optional[DepartamentoSimples] = None
    model_config = ConfigDict(from_attributes=True)

class Departamento(DepartamentoBase):
    id: int
    usuarios: List[UsuarioSimples] = []
    model_config = ConfigDict(from_attributes=True)

# ===============================
# SCHEMAS DE IMPORTAÇÃO
# ===============================
class ImportacaoBase(BaseModel):
    nome_arquivo: str
    tipo_arquivo: str

class ImportacaoCreate(ImportacaoBase):
    usuario_id: int

class Importacao(ImportacaoBase):
    id: int
    status: str
    tamanho_bytes: Optional[int] = None
    usuario: UsuarioSimples
    model_config = ConfigDict(from_attributes=True)

class InfoProcessamento(BaseModel):
    mensagem: str
    importacao_id: int
    total_registros: int
    registros_validos: int
    registros_invalidos: int

# =================================================================
# SCHEMAS PARA DASHBOARD DE USUÁRIO
# =================================================================
class Kpi(BaseModel):
    nome: str
    valor: Decimal
    prefixo: Optional[str] = None
    sufixo: Optional[str] = None

class KpiResponse(BaseModel):
    kpis: List[Kpi]

class VendasCategoria(BaseModel):
    categoria: str
    total_receita: Decimal

class VendasCategoriaResponse(BaseModel):
    dados_grafico: List[VendasCategoria]

# =================================================================
# SCHEMAS PARA DASHBOARD DE ADMINISTRADOR
# =================================================================
class AdminKpi(BaseModel):
    nome: str
    valor: Decimal
    descricao: str

class AdminKpiResponse(BaseModel):
    kpis: List[AdminKpi]

class AtividadeUsuario(BaseModel):
    id: int
    acao: str
    tabela_afetada: Optional[str] = None
    registro_id: Optional[int] = None
    ip_address: Optional[str] = None
    criado_em: datetime
    usuario: UsuarioSimples
    model_config = ConfigDict(from_attributes=True)

class AdminAtividadeResponse(BaseModel):
    atividades: List[AtividadeUsuario]

# =================================================================
# SCHEMAS PARA AS TABELAS PADRONIZADAS E RESPOSTA DA API
# =================================================================
class RegistroFinanceiroBase(BaseModel):
    id_transacao: str
    data_transacao: date
    receita: Optional[Decimal] = None
    custo: Optional[Decimal] = None
    lucro: Optional[Decimal] = None
    centro_custo: Optional[str] = None
    categoria_financeira: Optional[str] = None

    @field_validator("id_transacao", mode="before")
    def _trim_id_transacao(cls, v):
        if v is None:
            raise ValueError("id_transacao é obrigatório")
        v = str(v).strip()
        if not v:
            raise ValueError("id_transacao não pode ser vazio")
        if len(v) > 128:
            raise ValueError("id_transacao muito longo (máx 128)")
        return v

    @field_validator("receita", "custo", "lucro")
    def _non_negative_decimal(cls, v):
        if v is None:
            return v
        if Decimal(v) < 0:
            raise ValueError("valor deve ser >= 0")
        return v

    @field_validator("centro_custo", "categoria_financeira", mode="before")
    def _trim_optional_str(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @model_validator(mode="after")
    def _compute_lucro(self):
        if self.lucro is None and self.receita is not None and self.custo is not None:
            try:
                self.lucro = self.receita - self.custo
            except Exception:
                pass
        return self

class RegistroProdutoBase(BaseModel):
    id_venda: Optional[str] = None
    sku_produto: Optional[str] = None
    nome_produto: Optional[str] = None
    categoria_produto: Optional[str] = None
    quantidade_vendida: Optional[int] = None
    preco_unitario: Optional[Decimal] = None
    id_loja: Optional[str] = None
    data_venda: Optional[date] = None

    @field_validator("id_venda", "sku_produto", "nome_produto", "categoria_produto", "id_loja", mode="before")
    def _trim_optional(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @field_validator("quantidade_vendida")
    def _non_negative_int(cls, v):
        if v is None:
            return v
        if int(v) < 0:
            raise ValueError("quantidade_vendida deve ser >= 0")
        return int(v)

    @field_validator("preco_unitario")
    def _non_negative_price(cls, v):
        if v is None:
            return v
        if Decimal(v) < 0:
            raise ValueError("preco_unitario deve ser >= 0")
        return v

class RegistroOperacionalBase(BaseModel):
    id_evento: str
    id_colaborador: Optional[str] = None
    nome_colaborador: Optional[str] = None
    departamento: Optional[str] = None
    data_evento: Optional[date] = None
    tipo_evento: Optional[str] = None
    duracao_minutos: Optional[int] = None
    avaliacao_nps: Optional[int] = None

    @field_validator("id_evento", mode="before")
    def _trim_id_evento(cls, v):
        if v is None:
            raise ValueError("id_evento é obrigatório")
        v = str(v).strip()
        if not v:
            raise ValueError("id_evento não pode ser vazio")
        if len(v) > 128:
            raise ValueError("id_evento muito longo (máx 128)")
        return v

    @field_validator("id_colaborador", "nome_colaborador", "departamento", "tipo_evento", mode="before")
    def _trim_optional_str_oper(cls, v):
        if v is None:
            return None
        v = str(v).strip()
        return v or None

    @field_validator("duracao_minutos")
    def _non_negative_duration(cls, v):
        if v is None:
            return v
        if int(v) < 0:
            raise ValueError("duracao_minutos deve ser >= 0")
        return int(v)

    @field_validator("avaliacao_nps")
    def _nps_range(cls, v):
        if v is None:
            return v
        v = int(v)
        if v < 0 or v > 10:
            raise ValueError("avaliacao_nps deve estar entre 0 e 10")
        return v

class ResultadoMultiTransformacao(BaseModel):
    mensagem: str
    registros_financeiros_inseridos: int
    registros_produtos_inseridos: int
    registros_operacionais_inseridos: int
    relatorio_validacao: Optional[Dict[str, "ValidationReport"]] = None

class ValidationIssue(BaseModel):
    tabela: str
    index: int
    campo: str
    detalhe: str

class ValidationReport(BaseModel):
    tabela: str
    total: int
    validos: int
    invalidos: int
    erros: List[ValidationIssue] = []

# =================================================================
# SCHEMAS PARA DASHBOARDS INTERATIVOS AVANÇADOS
# =================================================================
class FiltrosDashboard(BaseModel):
    data_inicio: Optional[date] = None
    data_fim: Optional[date] = None
    categoria_produto: Optional[str] = None
    departamento: Optional[str] = None
    colaborador: Optional[str] = None
    valor_minimo: Optional[float] = None
    valor_maximo: Optional[float] = None

class ClienteBase(BaseModel):
    nome: str

class Cliente(ClienteBase):
    id: int
    criado_em: datetime
    ativo: bool

class IndicadorCustomizadoBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    unidade: Optional[str] = None
    prefixo: Optional[str] = None
    ativo: Optional[bool] = True
    config_json: Dict[str, Any]

class IndicadorCustomizadoCreate(IndicadorCustomizadoBase):
    pass

class IndicadorCustomizadoUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    unidade: Optional[str] = None
    prefixo: Optional[str] = None
    ativo: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None

class IndicadorCustomizado(IndicadorCustomizadoBase):
    id: int
    cliente_id: int
    criado_em: datetime
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

class ValorIndicadorResponse(BaseModel):
    nome: str
    valor: float
    detalhes: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class AvaliacaoIndicadorResponse(BaseModel):
    indicador_id: int
    nome: str
    resultados: List[Dict[str, Any]]
    executado_em: datetime

class AvaliacaoLimiarResponse(BaseModel):
    limiar_id: int
    nome: str
    violado: bool
    valor_atual: Optional[float]
    valor_limite: float
    operador: str
    mensagem: Optional[str]
    prioridade: str
    canal: str

# Schemas para Limiares de Indicadores
class LimiarIndicadorCreate(BaseModel):
    nome: str
    operador: str  # '>', '<', '>=', '<=', '==', '!='
    valor_limite: float
    prioridade: str = "media"  # 'baixa', 'media', 'alta', 'critica'
    canal: str = "sistema"  # 'email', 'sms', 'sistema', 'webhook'
    ativo: bool = True
    mensagem: Optional[str] = None
    config_json: dict

class LimiarIndicadorUpdate(BaseModel):
    nome: Optional[str] = None
    operador: Optional[str] = None
    valor_limite: Optional[float] = None
    prioridade: Optional[str] = None
    canal: Optional[str] = None
    ativo: Optional[bool] = None
    mensagem: Optional[str] = None
    config_json: Optional[dict] = None

class DadosGraficoLinha(BaseModel):
    labels: List[str]
    datasets: List[Dict[str, Any]]

# Schemas para automação e scheduler
class JobInfoSchema(BaseModel):
    id: str
    name: str
    next_run: Optional[str] = None
    trigger: str

class SchedulerStatusSchema(BaseModel):
    is_running: bool
    jobs: List[JobInfoSchema]
    total_jobs: int

class CustomJobRequest(BaseModel):
    job_id: str
    name: str
    trigger_type: str  # 'interval', 'cron'
    trigger_config: Dict  # Configuração específica do trigger
    function_name: str

class RelatorioSaudeSchema(BaseModel):
    timestamp: datetime
    clientes_ativos: int
    usuarios_ativos: int
    indicadores_customizados: int
    notificacoes_nao_lidas: int
    importacoes_hoje: int
    status_sistema: str

# Schemas para Cache e Materialização
class CacheStatsSchema(BaseModel):
    type: str
    total_keys: int
    memory_usage: Optional[str] = None
    connected_clients: Optional[int] = None
    used_memory: Optional[str] = None
    keyspace_hits: Optional[int] = None
    keyspace_misses: Optional[int] = None
    hit_ratio: Optional[float] = None

class CacheInvalidationRequest(BaseModel):
    pattern: Optional[str] = None
    metric_type: Optional[str] = None
    cliente_id: Optional[int] = None
    usuario_id: Optional[int] = None

class CacheInvalidationResponse(BaseModel):
    invalidated_keys: int
    message: str

class MaterializationRequest(BaseModel):
    metric_types: List[str]
    cliente_id: Optional[int] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    force_refresh: bool = False

class MaterializationResponse(BaseModel):
    processed_metrics: int
    cached_entries: int
    processing_time_seconds: float
    errors: List[str] = []

# Schemas para Alertas e Notificações
class AlertaGeradoSchema(BaseModel):
    tipo: str
    titulo: str
    mensagem: str
    prioridade: str
    cliente_id: int
    usuario_id: Optional[int] = None
    dados_contexto: Dict[str, Any] = {}
    canais: List[str] = []
    gerado_em: datetime

class ProcessamentoAlertasResponse(BaseModel):
    cliente_id: int
    processado_em: datetime
    alertas_gerados: int
    alertas_por_tipo: Dict[str, int]
    alertas_por_prioridade: Dict[str, int]
    erro: Optional[str] = None

class PreferenciasNotificacaoUpdate(BaseModel):
    email_habilitado: Optional[bool] = None
    sms_habilitado: Optional[bool] = None
    push_habilitado: Optional[bool] = None
    tipos_habilitados: Optional[List[str]] = None
    prioridade_minima: Optional[str] = None
    horario_silencioso_inicio: Optional[str] = None
    horario_silencioso_fim: Optional[str] = None

class ConfiguracaoAlertaRequest(BaseModel):
    cliente_id: int
    verificar_limiares: bool = True
    verificar_tendencias: bool = True
    verificar_inatividade: bool = True
    dias_tendencia: int = 7
    dias_inatividade: int = 30

class DadosGraficoBarra(BaseModel):
    labels: List[str]
    data: List[Decimal]
    backgroundColor: List[str]

class DadosGraficoPizza(BaseModel):
    labels: List[str]
    data: List[Decimal]
    backgroundColor: List[str]

class MetricaComparativa(BaseModel):
    nome: str
    valor_atual: Decimal
    valor_anterior: Decimal
    percentual_mudanca: Decimal
    tendencia: str

class DashboardInterativo(BaseModel):
    kpis: List[Kpi]
    metricas_comparativas: List[MetricaComparativa]
    grafico_receita_tempo: DadosGraficoLinha
    grafico_vendas_categoria: DadosGraficoPizza
    grafico_performance_colaboradores: DadosGraficoBarra
    top_produtos: List[Dict[str, Any]]
    alertas: List[Dict[str, str]]

class FiltrosDisponiveis(BaseModel):
    categorias_produto: List[str]
    departamentos: List[str]
    colaboradores: List[str]
    periodo_dados: Dict[str, str]

# ===============================
# SCHEMAS PARA CATÁLOGO DE INSIGHTS
# ===============================
class InsightItem(BaseModel):
    tipo: str  # "financeiro", "produto", "operacional"
    titulo: str
    resumo: str
    prioridade: str = "media"  # "baixa" | "media" | "alta"
    metadados: Dict[str, Any] = {}

class InsightCatalogoResponse(BaseModel):
    insights: List[InsightItem]

# =================================================================
# SCHEMAS PARA REQUEST BODIES (COM EXEMPLOS)
# =================================================================
class PredictReceitaRequest(BaseModel):
    periodicidade: str = Field("mensal", description="Agrupamento dos dados: 'mensal' ou 'semanal'.")
    horizonte: int = Field(3, description="Número de períodos futuros para prever.")
    data_inicio: Optional[str] = Field(None, description="Data de início (AAAA-MM-DD) para filtrar os dados históricos.")
    data_fim: Optional[str] = Field(None, description="Data de fim (AAAA-MM-DD) para filtrar os dados históricos.")

class NotificacaoCreateRequest(BaseModel):
    usuario_id: Optional[int] = Field(None, description="ID do usuário de destino (apenas admins). Se omitido, usa o usuário logado.")
    titulo: str = "Título da Notificação"
    mensagem: str = "Esta é uma mensagem de exemplo para a notificação."
    tipo: str = "info"
    canal: str = "in_app"
    prioridade: str = "normal"
    url_acao: Optional[str] = None

class PreferenciasUpdateRequest(BaseModel):
    canal_in_app: Optional[bool] = None
    canal_email: Optional[bool] = None
    canal_web: Optional[bool] = None
    receber_alertas_financeiros: Optional[bool] = None
    receber_alertas_produto: Optional[bool] = None
    receber_alertas_operacional: Optional[bool] = None
    limiar_queda_receita_percentual: Optional[float] = None

# =================================================================
# SCHEMAS PARA LIMIAR DE INDICADOR
# =================================================================
class LimiarIndicadorBase(BaseModel):
    nome: str
    operador: str
    valor_limite: Decimal
    prioridade: Optional[str] = "normal"
    canal: Optional[str] = "in_app"
    ativo: Optional[bool] = True
    mensagem: Optional[str] = None
    config_json: Dict[str, Any]

    @field_validator("operador")
    def operador_valido(cls, v):
        if v not in {"above", "below"}:
            raise ValueError("operador deve ser 'above' ou 'below'")
        return v

    @field_validator("valor_limite")
    def valor_nao_negativo(cls, v):
        if v is None:
            return v
        if Decimal(v) < Decimal(0):
            raise ValueError("valor_limite deve ser não negativo")
        return v

class LimiarIndicadorCreate(LimiarIndicadorBase):
    pass

class LimiarIndicadorUpdate(BaseModel):
    nome: Optional[str] = None
    operador: Optional[str] = None
    valor_limite: Optional[Decimal] = None
    prioridade: Optional[str] = None
    canal: Optional[str] = None
    ativo: Optional[bool] = None
    mensagem: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None

    @field_validator("operador")
    def operador_valido_update(cls, v):
        if v is None:
            return v
        if v not in {"above", "below"}:
            raise ValueError("operador deve ser 'above' ou 'below'")
        return v

    @field_validator("valor_limite")
    def valor_nao_negativo_update(cls, v):
        if v is None:
            return v
        if Decimal(v) < Decimal(0):
            raise ValueError("valor_limite deve ser não negativo")
        return v

class LimiarIndicador(LimiarIndicadorBase):
    id: int
    cliente_id: int
    criado_em: datetime
    atualizado_em: datetime
    model_config = ConfigDict(from_attributes=True)

# ===============================
# SCHEMAS DE INTEGRAÇÃO           # ADICIONADO
# ===============================
class IntegracaoConfigCreate(BaseModel):
    """Schema para criar ou atualizar as credenciais de uma integração."""
    credentials: Dict[str, Any] = Field(..., description="Credenciais (ex: host, user, pass, client_id, client_secret)")
    auth_type: str = "credentials" # Ex: credentials, oauth2
    enabled: bool = True

class IntegracaoConfig(BaseModel):
    """Schema para retornar dados de uma integração (sem credenciais sensíveis)."""
    id: int
    cliente_id: int
    connector_key: str
    enabled: bool
    last_sync_ts: Optional[datetime] = None
    # Nota: Não expomos 'credentials' na leitura por segurança

    model_config = ConfigDict(from_attributes=True)

class TestConnectionResponse(BaseModel):
    status: str # 'ok' | 'error' | 'not_configured'
    message: str

# [!code ++]
# --- CORREÇÃO: Schema Faltante ---
# Este schema estava faltando, causando o AttributeError na inicialização.
# Ele representa a resposta do endpoint GET /{connector_key}/config
class IntegracaoConfigState(BaseModel):
    exists: bool
    connector_key: str
    enabled: bool
    id: Optional[int] = None
    cliente_id: Optional[int] = None
    last_sync_ts: Optional[datetime] = None
# --- FIM DA CORREÇÃO ---

# [!code ++]
# --- CORREÇÃO 2: Adiciona schema para o body do Teste ---
class TestConnectionRequest(BaseModel):
    """Schema opcional para testar credenciais antes de salvar."""
    credentials: Optional[Dict[str, Any]] = None
# --- FIM DA CORREÇÃO 2 ---

