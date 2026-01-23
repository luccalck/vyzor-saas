"""
Serviço de Alertas com Limiares por Cliente/Indicador
Integra preferências de notificação e configuração por indicador
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import json
from . import models, schemas
from .indicadores_service import get_indicador_service

logger = logging.getLogger(__name__)

# ===============================
# TIPOS DE ALERTA
# ===============================

class TipoAlerta:
    LIMIAR_VIOLADO = "limiar_violado"
    TENDENCIA_NEGATIVA = "tendencia_negativa"
    ANOMALIA_DETECTADA = "anomalia_detectada"
    META_ATINGIDA = "meta_atingida"
    INATIVIDADE_PROLONGADA = "inatividade_prolongada"

class PrioridadeAlerta:
    BAIXA = "baixa"
    MEDIA = "media"
    ALTA = "alta"
    CRITICA = "critica"

class CanalNotificacao:
    EMAIL = "email"
    SMS = "sms"
    SISTEMA = "sistema"
    WEBHOOK = "webhook"
    PUSH = "push"

# ===============================
# MODELOS DE ALERTA
# ===============================

class AlertaGerado:
    """Representa um alerta gerado pelo sistema."""
    
    def __init__(self, 
                 tipo: str,
                 titulo: str,
                 mensagem: str,
                 prioridade: str,
                 cliente_id: int,
                 usuario_id: Optional[int] = None,
                 dados_contexto: Optional[Dict[str, Any]] = None,
                 canais: Optional[List[str]] = None):
        self.tipo = tipo
        self.titulo = titulo
        self.mensagem = mensagem
        self.prioridade = prioridade
        self.cliente_id = cliente_id
        self.usuario_id = usuario_id
        self.dados_contexto = dados_contexto or {}
        self.canais = canais or [CanalNotificacao.SISTEMA]
        self.gerado_em = datetime.now()

# ===============================
# SERVIÇO DE ALERTAS
# ===============================

class AlertsService:
    """Serviço principal de alertas e notificações."""
    
    def __init__(self, db: Session):
        self.db = db
        self.indicador_service = get_indicador_service(db)
    
    def verificar_limiares_cliente(self, cliente_id: int) -> List[AlertaGerado]:
        """
        Verifica todos os limiares ativos de um cliente para todos os seus usuários.
        Esta é a correção principal: agora iteramos sobre os usuários do cliente.
        """
        alertas = []
        
        try:
            # Buscar limiares ativos do cliente
            limiares = self.db.query(models.LimiarIndicador).filter(
                models.LimiarIndicador.cliente_id == cliente_id,
                models.LimiarIndicador.ativo == True
            ).all()

            if not limiares:
                return []

            # Buscar todos os usuários ativos do cliente
            usuarios_do_cliente = self.db.query(models.Usuario).filter(
                models.Usuario.cliente_id == cliente_id,
                # models.Usuario.ativo == True # Descomentar se houver campo 'ativo' no modelo Usuario
            ).all()

            for usuario in usuarios_do_cliente:
                for limiar in limiares:
                    try:
                        # Avaliar limiar usando o serviço de indicadores com o contexto do usuário
                        resultado = self.indicador_service.avaliar_limiar(limiar.id, usuario.id)
                        
                        if resultado['violado']:
                            alerta = self._criar_alerta_limiar(limiar, resultado)
                            # Associa o alerta ao usuário específico
                            alerta.usuario_id = usuario.id
                            alertas.append(alerta)
                            
                            # Salvar notificação no banco para este usuário
                            self._salvar_notificacao(alerta)
                            
                    except Exception as e:
                        logger.error(f"Erro ao avaliar limiar {limiar.id} para o usuário {usuario.id}: {str(e)}")
                        continue
            
            return alertas
            
        except Exception as e:
            logger.error(f"Erro ao verificar limiares do cliente {cliente_id}: {str(e)}")
            return []
    
    def verificar_tendencias_negativas(self, cliente_id: int, dias: int = 7) -> List[AlertaGerado]:
        """Detecta tendências negativas nos últimos N dias."""
        alertas = []
        
        try:
            data_inicio = datetime.now() - timedelta(days=dias)
            
            # Verificar tendência de receitas
            receitas = self.db.query(models.RegistroFinanceiro).filter(
                and_(
                    models.RegistroFinanceiro.data_transacao >= data_inicio.date()
                )
            ).all() # Simplificado, precisa de contexto de cliente
            
            if self._detectar_tendencia_negativa(receitas, 'receita'):
                alerta = AlertaGerado(
                    tipo=TipoAlerta.TENDENCIA_NEGATIVA,
                    titulo="Tendência Negativa em Receitas",
                    mensagem=f"Detectada queda consistente nas receitas nos últimos {dias} dias",
                    prioridade=PrioridadeAlerta.ALTA,
                    cliente_id=cliente_id,
                    dados_contexto={"periodo": dias, "metrica": "receitas"}
                )
                alertas.append(alerta)
                self._salvar_notificacao(alerta)
            
            # Verificar tendência de vendas
            vendas = self.db.query(models.RegistroProduto).filter(
                models.RegistroProduto.data_venda >= data_inicio.date()
            ).all() # Simplificado, precisa de contexto de cliente
            
            if self._detectar_tendencia_negativa(vendas, 'quantidade_vendida'):
                alerta = AlertaGerado(
                    tipo=TipoAlerta.TENDENCIA_NEGATIVA,
                    titulo="Tendência Negativa em Vendas",
                    mensagem=f"Detectada queda consistente nas vendas nos últimos {dias} dias",
                    prioridade=PrioridadeAlerta.ALTA,
                    cliente_id=cliente_id,
                    dados_contexto={"periodo": dias, "metrica": "vendas"}
                )
                alertas.append(alerta)
                self._salvar_notificacao(alerta)
            
            return alertas
            
        except Exception as e:
            logger.error(f"Erro ao verificar tendências do cliente {cliente_id}: {str(e)}")
            return []
    
    def verificar_inatividade_usuarios(self, cliente_id: int, dias: int = 30) -> List[AlertaGerado]:
        """Detecta usuários inativos por muito tempo."""
        alertas = []
        
        try:
            data_limite = datetime.now() - timedelta(days=dias)
            
            # Buscar usuários do cliente
            usuarios = self.db.query(models.Usuario).filter(
                models.Usuario.cliente_id == cliente_id
                # models.Usuario.ativo == True
            ).all()
            
            for usuario in usuarios:
                # Verificar última atividade
                ultima_atividade = self.db.query(models.AtividadeUsuario).filter(
                    models.AtividadeUsuario.usuario_id == usuario.id
                ).order_by(models.AtividadeUsuario.criado_em.desc()).first()
                
                if not ultima_atividade or ultima_atividade.criado_em.replace(tzinfo=None) < data_limite:
                    alerta = AlertaGerado(
                        tipo=TipoAlerta.INATIVIDADE_PROLONGADA,
                        titulo=f"Usuário Inativo: {usuario.nome_completo}",
                        mensagem=f"Usuário {usuario.nome_completo} não acessa o sistema há mais de {dias} dias",
                        prioridade=PrioridadeAlerta.MEDIA,
                        cliente_id=cliente_id,
                        usuario_id=usuario.id,
                        dados_contexto={
                            "usuario_nome": usuario.nome_completo,
                            "dias_inativo": dias,
                            "ultima_atividade": ultima_atividade.criado_em.isoformat() if ultima_atividade else None
                        }
                    )
                    alertas.append(alerta)
                    self._salvar_notificacao(alerta)
            
            return alertas
            
        except Exception as e:
            logger.error(f"Erro ao verificar inatividade do cliente {cliente_id}: {str(e)}")
            return []
    
    def processar_alertas_cliente(self, cliente_id: int) -> Dict[str, Any]:
        """Processa todos os tipos de alertas para um cliente."""
        resultado = {
            "cliente_id": cliente_id,
            "processado_em": datetime.now(),
            "alertas_gerados": 0,
            "alertas_por_tipo": {},
            "alertas_por_prioridade": {}
        }
        
        try:
            todos_alertas = []
            
            # Verificar limiares
            alertas_limiares = self.verificar_limiares_cliente(cliente_id)
            todos_alertas.extend(alertas_limiares)
            
            # Verificar tendências
            alertas_tendencias = self.verificar_tendencias_negativas(cliente_id)
            todos_alertas.extend(alertas_tendencias)
            
            # Verificar inatividade
            alertas_inatividade = self.verificar_inatividade_usuarios(cliente_id)
            todos_alertas.extend(alertas_inatividade)
            
            # Compilar estatísticas
            resultado["alertas_gerados"] = len(todos_alertas)
            
            for alerta in todos_alertas:
                # Contar por tipo
                resultado["alertas_por_tipo"][alerta.tipo] = resultado["alertas_por_tipo"].get(alerta.tipo, 0) + 1
                
                # Contar por prioridade
                resultado["alertas_por_prioridade"][alerta.prioridade] = resultado["alertas_por_prioridade"].get(alerta.prioridade, 0) + 1
            
            return resultado
            
        except Exception as e:
            logger.error(f"Erro ao processar alertas do cliente {cliente_id}: {str(e)}")
            resultado["erro"] = str(e)
            return resultado
    
    def _criar_alerta_limiar(self, limiar: models.LimiarIndicador, resultado: Dict[str, Any]) -> AlertaGerado:
        """Cria um alerta baseado na violação de limiar."""
        canais = [limiar.canal] if limiar.canal else [CanalNotificacao.SISTEMA]
        
        return AlertaGerado(
            tipo=TipoAlerta.LIMIAR_VIOLADO,
            titulo=f"Limiar Violado: {limiar.nome}",
            mensagem=limiar.mensagem or f"Limiar {limiar.nome} foi violado",
            prioridade=limiar.prioridade,
            cliente_id=limiar.cliente_id,
            dados_contexto={
                "limiar_id": limiar.id,
                "limiar_nome": limiar.nome,
                "valor_atual": resultado['valor_atual'],
                "valor_limite": resultado['valor_limite'],
                "operador": resultado['operador']
            },
            canais=canais
        )
    
    def _detectar_tendencia_negativa(self, registros: List, campo: str, threshold: float = 0.15) -> bool:
        """Detecta se há uma tendência negativa consistente."""
        if len(registros) < 3:
            return False
        
        # Agrupar por data e somar valores
        valores_por_data = {}
        for registro in registros:
            data_campo = getattr(registro, 'data_transacao', getattr(registro, 'data_venda', None))
            if not data_campo: continue
            data_str = data_campo.isoformat()
            valor = getattr(registro, campo, 0)
            valores_por_data[data_str] = valores_por_data.get(data_str, 0) + float(valor or 0)
        
        # Ordenar por data
        datas_ordenadas = sorted(valores_por_data.keys())
        valores = [valores_por_data[data] for data in datas_ordenadas]
        
        if len(valores) < 3:
            return False
        
        # Calcular tendência (regressão linear simples)
        n = len(valores)
        x = list(range(n))
        
        sum_x = sum(x)
        sum_y = sum(valores)
        sum_xy = sum(x[i] * valores[i] for i in range(n))
        sum_x2 = sum(x[i] ** 2 for i in range(n))
        
        # Coeficiente angular (slope)
        if (n * sum_x2 - sum_x ** 2) == 0: return False
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        
        # Tendência negativa se slope < -threshold
        return slope < -threshold
    
    def _salvar_notificacao(self, alerta: AlertaGerado):
        """Salva uma notificação no banco de dados."""
        try:
            # Não salva notificação se não houver um usuário associado
            if not alerta.usuario_id:
                logger.warning(f"Tentativa de salvar notificação sem usuário: {alerta.titulo}")
                return

            notificacao = models.Notificacao(
                usuario_id=alerta.usuario_id,
                titulo=alerta.titulo,
                mensagem=alerta.mensagem,
                tipo=alerta.tipo,
                prioridade=alerta.prioridade,
                lida=False,
                dados_json=json.dumps(alerta.dados_contexto, default=str)
            )
            
            self.db.add(notificacao)
            self.db.commit()
            
        except Exception as e:
            logger.error(f"Erro ao salvar notificação: {str(e)}")
            self.db.rollback()
    
    def obter_preferencias_notificacao(self, usuario_id: int) -> Optional[models.PreferenciasNotificacao]:
        """Obtém as preferências de notificação de um usuário."""
        return self.db.query(models.PreferenciasNotificacao).filter(
            models.PreferenciasNotificacao.usuario_id == usuario_id
        ).first()
    
    def aplicar_preferencias_usuario(self, alerta: AlertaGerado, usuario_id: int) -> bool:
        """Verifica se o alerta deve ser enviado baseado nas preferências do usuário."""
        preferencias = self.obter_preferencias_notificacao(usuario_id)
        
        if not preferencias:
            return True  # Se não há preferências, enviar por padrão
        
        # Verificar se o tipo de alerta está habilitado
        config = json.loads(getattr(preferencias, 'configuracao_json', '{}') or '{}')
        
        tipos_habilitados = config.get('tipos_habilitados', [])
        if tipos_habilitados and alerta.tipo not in tipos_habilitados:
            return False
        
        # Verificar prioridade mínima
        prioridade_minima = config.get('prioridade_minima', PrioridadeAlerta.BAIXA)
        prioridades = [PrioridadeAlerta.BAIXA, PrioridadeAlerta.MEDIA, PrioridadeAlerta.ALTA, PrioridadeAlerta.CRITICA]
        
        if prioridades.index(alerta.prioridade) < prioridades.index(prioridade_minima):
            return False
        
        return True

# ===============================
# FUNÇÃO AUXILIAR
# ===============================

def get_alerts_service(db: Session) -> AlertsService:
    """Retorna uma instância do AlertsService."""
    return AlertsService(db)
