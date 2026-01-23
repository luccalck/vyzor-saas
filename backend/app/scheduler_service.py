"""
Serviço de Automação Periódica
Implementa APScheduler para pré-cálculo de métricas e processamento de notificações
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from sqlalchemy import text

from . import crud, models, schemas
from .database import get_db
from .alerts_service import AlertsService
from .indicadores_service import IndicadorService

logger = logging.getLogger(__name__)

class SchedulerService:
    """Serviço de agendamento para automação de tarefas periódicas"""
    
    def __init__(self):
        self.scheduler = BackgroundScheduler(timezone="America/Sao_Paulo")
        self.is_running = False
        
    def start(self):
        """Inicia o scheduler e configura as tarefas periódicas"""
        if not self.is_running:
            self.scheduler.start()
            self.is_running = True
            self._configure_jobs()
            logger.info("Scheduler iniciado com sucesso")
    
    def stop(self):
        """Para o scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("Scheduler parado")
    
    def _configure_jobs(self):
        """Configura todas as tarefas periódicas"""
        
        # Processamento de alertas a cada 15 minutos
        self.scheduler.add_job(
            func=self._processar_alertas_periodico,
            trigger=IntervalTrigger(minutes=15),
            id='processar_alertas',
            name='Processamento de Alertas',
            replace_existing=True
        )
        
        # Pré-cálculo de métricas diárias às 6:00
        self.scheduler.add_job(
            func=self._precalcular_metricas_diarias,
            trigger=CronTrigger(hour=6, minute=0),
            id='precalculo_metricas',
            name='Pré-cálculo de Métricas Diárias',
            replace_existing=True
        )
        
        # Limpeza de notificações antigas às 2:00 (semanalmente, no domingo)
        self.scheduler.add_job(
            func=self._limpar_notificacoes_antigas,
            trigger=CronTrigger(day_of_week=0, hour=2, minute=0),
            id='limpeza_notificacoes',
            name='Limpeza de Notificações Antigas',
            replace_existing=True
        )
        
        # Relatório de saúde do sistema diário às 8:00
        self.scheduler.add_job(
            func=self._gerar_relatorio_saude,
            trigger=CronTrigger(hour=8, minute=0),
            id='relatorio_saude',
            name='Relatório de Saúde do Sistema',
            replace_existing=True
        )
    
    def _processar_alertas_periodico(self):
        """Processa alertas para todos os clientes ativos"""
        try:
            db = next(get_db())
            alerts_service = AlertsService(db)
            
            # Busca todos os clientes ativos
            clientes = db.query(models.Cliente).filter(models.Cliente.ativo == True).all()
            
            total_alertas = 0
            for cliente in clientes:
                try:
                    resultado = alerts_service.processar_alertas_cliente(cliente.id)
                    alertas_gerados = resultado.get("alertas_gerados", 0)
                    total_alertas += alertas_gerados
                    logger.info(f"Processados {alertas_gerados} alertas para cliente {cliente.nome}")
                except Exception as e:
                    logger.error(f"Erro ao processar alertas para cliente {cliente.id}: {str(e)}")
            
            logger.info(f"Processamento de alertas concluído. Total: {total_alertas} alertas")
            
        except Exception as e:
            logger.error(f"Erro no processamento periódico de alertas: {str(e)}")
        finally:
            db.close()
    
    def _precalcular_metricas_diarias(self):
        """Pré-calcula métricas para otimizar consultas futuras"""
        try:
            db = next(get_db())
            
            # Calcula métricas para os últimos 30 dias
            data_fim = datetime.now().date()
            data_inicio = data_fim - timedelta(days=30)
            
            clientes = db.query(models.Cliente).filter(models.Cliente.ativo == True).all()
            
            for cliente in clientes:
                try:
                    # Busca usuários do cliente para pré-calcular suas métricas
                    usuarios_cliente = db.query(models.Usuario).filter(models.Usuario.cliente_id == cliente.id).all()
                    for usuario in usuarios_cliente:
                        # Pré-calcula métricas principais para cada usuário
                        filtros = schemas.FiltrosDashboard(data_inicio=data_inicio, data_fim=data_fim)
                        crud.get_metricas_comparativas(
                            db=db,
                            usuario_id=usuario.id,
                            filtros=filtros
                        )
                    
                    # Salva no cache (implementação futura com Redis)
                    cache_key = f"metricas_diarias:{cliente.id}:{data_inicio}:{data_fim}"
                    logger.info(f"Métricas pré-calculadas para cliente {cliente.nome}")
                    
                except Exception as e:
                    logger.error(f"Erro ao pré-calcular métricas para cliente {cliente.id}: {str(e)}")
            
            logger.info("Pré-cálculo de métricas diárias concluído")
            
        except Exception as e:
            logger.error(f"Erro no pré-cálculo de métricas: {str(e)}")
        finally:
            db.close()
    
    def _limpar_notificacoes_antigas(self):
        """Remove notificações antigas para manter a base limpa"""
        try:
            db = next(get_db())
            
            # Remove notificações lidas com mais de 30 dias
            data_limite = datetime.now() - timedelta(days=30)
            
            result = db.execute(
                text("""
                DELETE FROM notificacoes 
                WHERE lida = true 
                AND criado_em < :data_limite
                """),
                {"data_limite": data_limite}
            )
            
            db.commit()
            logger.info(f"Removidas {result.rowcount} notificações antigas")
            
        except Exception as e:
            logger.error(f"Erro na limpeza de notificações: {str(e)}")
            db.rollback()
        finally:
            db.close()
    
    def _gerar_relatorio_saude(self):
        """Gera relatório de saúde do sistema"""
        try:
            db = next(get_db())
            
            # Coleta estatísticas do sistema
            stats = {
                'clientes_ativos': db.query(models.Cliente).filter(models.Cliente.ativo == True).count(),
                'usuarios_ativos': db.query(models.Usuario).filter(models.Usuario.ativo == True).count() if hasattr(models.Usuario, 'ativo') else db.query(models.Usuario).count(),
                'indicadores_customizados': db.query(models.IndicadorCustomizado).filter(
                    models.IndicadorCustomizado.ativo == True
                ).count(),
                'notificacoes_nao_lidas': db.query(models.Notificacao).filter(
                    models.Notificacao.lida == False
                ).count(),
                'importacoes_hoje': db.query(models.Importacao).filter(
                    models.Importacao.criado_em >= datetime.now().date()
                ).count()
            }
            
            logger.info(f"Relatório de saúde do sistema: {stats}")
            
            # Aqui poderia enviar o relatório por email ou salvar em arquivo
            
        except Exception as e:
            logger.error(f"Erro ao gerar relatório de saúde: {str(e)}")
        finally:
            db.close()
    
    def add_custom_job(self, func, trigger, job_id: str, name: str, **kwargs):
        """Adiciona uma tarefa customizada ao scheduler"""
        try:
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=True,
                **kwargs
            )
            logger.info(f"Tarefa customizada '{name}' adicionada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao adicionar tarefa customizada: {str(e)}")
    
    def remove_job(self, job_id: str):
        """Remove uma tarefa do scheduler"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Tarefa '{job_id}' removida com sucesso")
        except Exception as e:
            logger.error(f"Erro ao remover tarefa: {str(e)}")
    
    def get_jobs(self) -> List[Dict]:
        """Retorna lista de tarefas ativas"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

# Instância global do scheduler
scheduler_service = SchedulerService()

def get_scheduler_service() -> SchedulerService:
    """Retorna a instância do serviço de agendamento"""
    return scheduler_service

