from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, case, text
from fastapi import HTTPException, status
from . import models, schemas
from .auth import get_password_hash
import pandas as pd
import io
import json
import logging
import math  # [!code ++] Adicionado para checar 'NaN'
from typing import Optional, List, Dict, Any
from . import cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# ===============================
# DEPARTAMENTOS
# ===============================
def get_departamento(db: Session, departamento_id: int):
    return db.query(models.Departamento).filter(models.Departamento.id == departamento_id).first()

def get_departamentos(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Departamento).offset(skip).limit(limit).all()

def create_departamento(db: Session, departamento: schemas.DepartamentoCreate, autor_id: int):
    db_departamento = models.Departamento(nome=departamento.nome)
    db.add(db_departamento)
    try:
        db.commit()
        db.refresh(db_departamento)
        log_activity(db, autor_id, "criação", "departamentos", db_departamento.id, dados_depois={"nome": departamento.nome})
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Um departamento com o nome '{departamento.nome}' já existe.")
    return db_departamento

def update_departamento(db: Session, departamento_id: int, departamento_update: schemas.DepartamentoUpdate, autor_id: int):
    db_departamento = get_departamento(db, departamento_id)
    if not db_departamento:
        return None

    dados_antes = {"nome": db_departamento.nome}
    if departamento_update.nome is not None:
        db_departamento.nome = departamento_update.nome
    try:
        db.commit()
        db.refresh(db_departamento)
        log_activity(db, autor_id, "atualização", "departamentos", departamento_id, dados_antes, {"nome": db_departamento.nome})
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Um departamento com o nome '{departamento_update.nome}' já existe.")
    return db_departamento

def delete_departamento(db: Session, departamento_id: int, autor_id: int):
    db_departamento = get_departamento(db, departamento_id)
    if not db_departamento:
        return None
    if db.query(models.Usuario).filter(models.Usuario.departamento_id == departamento_id).first():
        raise HTTPException(status_code=400, detail="Não é possível excluir um departamento com usuários associados.")

    dados_antes = {"nome": db_departamento.nome}
    db.delete(db_departamento)
    db.commit()
    log_activity(db, autor_id, "exclusão", "departamentos", departamento_id, dados_antes)
    return db_departamento

# ===============================
# USUÁRIOS
# ===============================
def get_usuario(db: Session, usuario_id: int):
    return db.query(models.Usuario).options(joinedload(models.Usuario.departamento)).filter(models.Usuario.id == usuario_id).first()

def get_usuarios(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Usuario).options(joinedload(models.Usuario.departamento)).offset(skip).limit(limit).all()

def create_usuario(db: Session, usuario: schemas.UsuarioCreate, autor_id: int):
    hashed_password = get_password_hash(usuario.password)
    db_usuario = models.Usuario(email=usuario.email, nome_completo=usuario.nome_completo, senha_hash=hashed_password, perfil=usuario.perfil)
    db.add(db_usuario)
    try:
        db.commit()
        db.refresh(db_usuario)
        log_activity(db, autor_id, "criação", "usuarios", db_usuario.id, None, usuario.model_dump(exclude={'password'}))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Um usuário com o email '{usuario.email}' já existe.")
    return db_usuario

def update_usuario(db: Session, usuario_id: int, usuario_update: schemas.UsuarioUpdate, autor_id: int):
    db_usuario = get_usuario(db, usuario_id)
    if not db_usuario: return None

    dados_antes = {"email": db_usuario.email, "nome_completo": db_usuario.nome_completo, "perfil": db_usuario.perfil}
    update_data = usuario_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_usuario, key, value)
    try:
        db.commit()
        db.refresh(db_usuario)
        log_activity(db, autor_id, "atualização", "usuarios", usuario_id, dados_antes, usuario_update.model_dump(exclude_unset=True))
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Um usuário com o email '{usuario_update.email}' já existe.")
    return db_usuario

def delete_usuario(db: Session, usuario_id: int, autor_id: int):
    db_usuario = get_usuario(db, usuario_id)
    if not db_usuario: return None

    dados_antes = {"email": db_usuario.email, "nome_completo": db_usuario.nome_completo}
    db.delete(db_usuario)
    db.commit()
    log_activity(db, autor_id, "exclusão", "usuarios", usuario_id, dados_antes)
    return db_usuario

def associar_departamento_a_usuario(db: Session, usuario_id: int, departamento_id: int, autor_id: int):
    db_usuario = get_usuario(db=db, usuario_id=usuario_id)
    if not db_usuario: raise HTTPException(status_code=404, detail="Usuário não encontrado")

    db_departamento = get_departamento(db=db, departamento_id=departamento_id)
    if not db_departamento: raise HTTPException(status_code=404, detail="Departamento não encontrado")

    dados_antes = {"usuario_id": usuario_id, "departamento_id_anterior": db_usuario.departamento_id}
    db_usuario.departamento_id = departamento_id
    db.commit()
    db.refresh(db_usuario)
    log_activity(db, autor_id, "associação", "usuarios_departamentos", db_usuario.id, dados_antes, {"departamento_id_novo": departamento_id})
    return db_usuario

# ===============================
# IMPORTAÇÕES
# ===============================
def get_importacao(db: Session, importacao_id: int):
    return db.query(models.Importacao).options(joinedload(models.Importacao.usuario)).filter(models.Importacao.id == importacao_id).first()

def create_importacao(db: Session, importacao: schemas.ImportacaoCreate):
    db_usuario = get_usuario(db, usuario_id=importacao.usuario_id)
    if not db_usuario: raise HTTPException(status_code=404, detail=f"Usuário com ID {importacao.usuario_id} não encontrado.")
    db_importacao = models.Importacao(**importacao.model_dump())
    db.add(db_importacao)
    db.commit()
    db.refresh(db_importacao)
    log_activity(db, importacao.usuario_id, "criação", "importacoes", db_importacao.id, dados_depois={"nome_arquivo": db_importacao.nome_arquivo})
    # Invalidação de cache dirigida após criação de importação
    try:
        from .cache_service import get_cache_service
        cache = get_cache_service()
        cache.invalidate_user_cache(usuario_id=db_usuario.id)
        if db_usuario.cliente_id:
            cache.invalidate_client_cache(cliente_id=db_usuario.cliente_id)
    except Exception:
        pass
    return db_importacao

def get_importacoes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Importacao).options(joinedload(models.Importacao.usuario)).order_by(models.Importacao.id.desc()).offset(skip).limit(limit).all()

def get_importacoes_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.Importacao).options(joinedload(models.Importacao.usuario)).filter(models.Importacao.usuario_id == usuario_id).order_by(models.Importacao.id.desc()).offset(skip).limit(limit).all()

def delete_importacao(db: Session, importacao_id: int, autor_id: int):
    db_importacao = get_importacao(db, importacao_id)
    if not db_importacao: return None
    # Captura usuario/cliente para invalidação
    db_usuario = get_usuario(db, usuario_id=db_importacao.usuario_id)
    dados_antes = {"importacao_id": importacao_id, "nome_arquivo": db_importacao.nome_arquivo}
    db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id == importacao_id).delete(synchronize_session=False)
    db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id == importacao_id).delete(synchronize_session=False)
    db.query(models.RegistroOperacional).filter(models.RegistroOperacional.importacao_id == importacao_id).delete(synchronize_session=False)
    # Removido: tabela legada registros_importados
    db.delete(db_importacao)
    db.commit()
    log_activity(db, autor_id, "exclusão", "importacoes", importacao_id, dados_antes)
    # Invalidação de cache dirigida após exclusão de importação
    try:
        from .cache_service import get_cache_service
        cache = get_cache_service()
        if db_usuario:
            cache.invalidate_user_cache(usuario_id=db_usuario.id)
            if db_usuario.cliente_id:
                cache.invalidate_client_cache(cliente_id=db_usuario.cliente_id)
    except Exception:
        pass
    return db_importacao

# ===============================
# LOG DE ATIVIDADES
# ===============================
def log_activity(db: Session, usuario_id: int, acao: str, tabela_afetada: Optional[str] = None, registro_id: Optional[int] = None, dados_antes: Optional[dict] = None, dados_depois: Optional[dict] = None):
    db_activity = models.AtividadeUsuario(usuario_id=usuario_id, acao=acao, tabela_afetada=tabela_afetada, registro_id=registro_id, dados_antes=dados_antes, dados_depois=dados_depois)
    db.add(db_activity)
    db.commit()

# =================================================================
# FUNÇÕES DE DASHBOARD (NOVAS E DINÂMICAS)
# =================================================================
def get_kpis_dinamicos(db: Session, usuario_id: int) -> List[schemas.Kpi]:
    # Cache: tenta ler
    # [!code ++] ATENÇÃO: A chave de cache agora DEVE incluir o cliente_id
    # Primeiro, busca o cliente_id do usuário
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        # Fallback LEGADO: calcula KPIs com base nas importações do próprio usuário
        logger.warning(f"Usuário {usuario_id} sem cliente_id; calculando KPIs por usuario_id.")

        importacoes_usuario = db.query(models.Importacao.id).filter(models.Importacao.usuario_id == usuario_id).subquery()

        receita_total_raw = db.query(func.sum(models.RegistroFinanceiro.receita))\
            .filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_usuario)).scalar()
        lucro_total_raw = db.query(func.sum(models.RegistroFinanceiro.lucro))\
            .filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_usuario)).scalar()
        unidades_vendidas_raw = db.query(func.sum(models.RegistroProduto.quantidade_vendida))\
            .filter(models.RegistroProduto.importacao_id.in_(importacoes_usuario)).scalar()
        nps_medio_raw = db.query(func.avg(models.RegistroOperacional.avaliacao_nps))\
            .filter(models.RegistroOperacional.importacao_id.in_(importacoes_usuario))\
            .filter(models.RegistroOperacional.avaliacao_nps.isnot(None)).scalar()

        receita_total = receita_total_raw or 0
        lucro_total = lucro_total_raw or 0
        unidades_vendidas = unidades_vendidas_raw or 0
        nps_medio = float(nps_medio_raw) if nps_medio_raw is not None else 0

        return [
            schemas.Kpi(nome="Receita Total", valor=receita_total, prefixo="R$"),
            schemas.Kpi(nome="Lucro Total", valor=lucro_total, prefixo="R$"),
            schemas.Kpi(nome="Unidades Vendidas", valor=unidades_vendidas),
            schemas.Kpi(nome="NPS Médio", valor=round(nps_medio, 1)),
        ]
    
    cliente_id = usuario.cliente_id
    
    # [!code --] Chave antiga que está armazenando R$ 0,00
    # cache_key = cache.make_key("kpis_cliente", cliente_id)
    
    # [!code ++] CORREÇÃO: Alteramos o nome da chave para forçar o recálculo
    cache_key = cache.make_key("kpis_cliente_v2", cliente_id)
    
    cached = cache.get_json(cache_key)
    if cached is not None:
        return [schemas.Kpi(**item) for item in cached]

    # [!code --] Lógica antiga de subquery (baseada em usuario_id)
    # importacoes_usuario = db.query(models.Importacao.id).filter(models.Importacao.usuario_id == usuario_id).subquery()
    
    # [!code ++] Lógica NOVA de subquery (baseada em cliente_id, como nos gráficos)
    importacoes_cliente = db.query(models.Importacao.id) \
        .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
        .filter(models.Usuario.cliente_id == cliente_id) \
        .subquery()
    
    # [!code ++] Atualiza as queries para usar a nova subquery 'importacoes_cliente'
    receita_total_raw = db.query(func.sum(models.RegistroFinanceiro.receita)).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)).scalar()
    lucro_total_raw = db.query(func.sum(models.RegistroFinanceiro.lucro)).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)).scalar()
    unidades_vendidas_raw = db.query(func.sum(models.RegistroProduto.quantidade_vendida)).filter(models.RegistroProduto.importacao_id.in_(importacoes_cliente)).scalar()
    nps_medio_raw = db.query(func.avg(models.RegistroOperacional.avaliacao_nps)).filter(models.RegistroOperacional.importacao_id.in_(importacoes_cliente)).filter(models.RegistroOperacional.avaliacao_nps.isnot(None)).scalar()

    # CORREÇÃO: Trata None/NaN explicitamente antes de passar para o Pydantic
    # O 'or 0' falha porque math.nan é 'truthy' (nan or 0 == nan)
    receita_total = 0 if receita_total_raw is None or math.isnan(receita_total_raw) else receita_total_raw
    lucro_total = 0 if lucro_total_raw is None or math.isnan(lucro_total_raw) else lucro_total_raw
    unidades_vendidas = 0 if unidades_vendidas_raw is None or math.isnan(unidades_vendidas_raw) else unidades_vendidas_raw
    nps_medio = 0 if nps_medio_raw is None or math.isnan(nps_medio_raw) else nps_medio_raw
    
    kpis = [
        schemas.Kpi(nome="Receita Total", valor=receita_total, prefixo="R$"),
        schemas.Kpi(nome="Lucro Total", valor=lucro_total, prefixo="R$"),
        schemas.Kpi(nome="Unidades Vendidas", valor=unidades_vendidas),
        schemas.Kpi(nome="NPS Médio", valor=round(nps_medio, 1)), # [!code ++] Removido 'if nps_medio else 0' pois já foi tratado
    ]
    # --- Fim da Correção ---
    
    # Cache: grava
    cache.set_json(cache_key, [k.model_dump() for k in kpis], ttl_seconds=600)
    return kpis

def get_vendas_por_categoria(db: Session, usuario_id: int) -> List[schemas.VendasCategoria]:
    # [!code ++] CORREÇÃO DE LÓGICA: Esta função também deve usar cliente_id
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        logger.warning(f"Usuário {usuario_id} sem cliente_id, retornando vendas por categoria vazias.")
        return []
        
    cliente_id = usuario.cliente_id
    
    importacoes_cliente = db.query(models.Importacao.id) \
        .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
        .filter(models.Usuario.cliente_id == cliente_id) \
        .subquery()
        
    resultado = db.query(
        models.RegistroProduto.categoria_produto,
        func.sum(models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida).label('total_receita')
    ).filter(models.RegistroProduto.importacao_id.in_(importacoes_cliente)).group_by(models.RegistroProduto.categoria_produto).order_by(func.sum(models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida).desc()).all()
    return [schemas.VendasCategoria(categoria=cat if cat else "Não Categorizado", total_receita=total) for cat, total in resultado]

# =================================================================
# FUNÇÕES PARA RELATÓRIOS COM IA
# =================================================================
def formatar_dados_para_relatorio(db: Session, usuario_id: int, tipo_relatorio: str) -> str:
    """Prepara uma string JSON com dados agregados para enviar à IA."""
    dados_brutos = obter_dados_para_relatorio(db, usuario_id, tipo_relatorio)
    if not dados_brutos:
        return ""

    texto_formatado = f"## Dados para Relatório {tipo_relatorio.capitalize()}\n\n"
    texto_formatado += json.dumps(dados_brutos, indent=2, default=str)
    return texto_formatado


def obter_dados_para_relatorio(db: Session, usuario_id: int, tipo_relatorio: str) -> List[Dict[str, Any]]:
    """
    Retorna dados tabulares brutos para o tipo de relatório solicitado.
    CORREÇÃO DE SEGURANÇA: Usa queries parametrizadas para evitar SQL Injection.
    """
    # [!code ++] CORREÇÃO: Esta função DEVE usar cliente_id, não usuario_id
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        logger.warning(f"obter_dados_para_relatorio: Usuário {usuario_id} sem cliente_id.")
        return []
    
    params = {"cid": usuario.cliente_id} # [!code ++] Trocado de :uid para :cid
    
    if tipo_relatorio == "financeiro":
        query = text("""
            SELECT to_char(data_transacao, 'YYYY-MM') as mes,
                   SUM(receita) as receita_mensal,
                   SUM(lucro) as lucro_mensal,
                   AVG(lucro/NULLIF(receita, 0))*100 as margem_lucro_percentual
            FROM saas_registros_financeiros
            WHERE importacao_id IN (SELECT i.id FROM importacoes i JOIN usuarios u ON i.usuario_id = u.id WHERE u.cliente_id = :cid)
            GROUP BY mes ORDER BY mes;
        """) # [!code ++]
    elif tipo_relatorio == "produtos":
        query = text("""
            SELECT nome_produto, categoria_produto,
                   SUM(quantidade_vendida) as total_unidades,
                   SUM(quantidade_vendida * preco_unitario) as receita_total
            FROM saas_registros_produtos
            WHERE importacao_id IN (SELECT i.id FROM importacoes i JOIN usuarios u ON i.usuario_id = u.id WHERE u.cliente_id = :cid)
            GROUP BY nome_produto, categoria_produto ORDER BY receita_total DESC LIMIT 10;
        """) # [!code ++]
    elif tipo_relatorio == "operacional":
        query = text("""
            SELECT nome_colaborador, departamento,
                   COUNT(id_evento) as num_eventos,
                   AVG(avaliacao_nps) as nps_medio
            FROM saas_registros_operacionais
            WHERE importacao_id IN (SELECT i.id FROM importacoes i JOIN usuarios u ON i.usuario_id = u.id WHERE u.cliente_id = :cid)
            GROUP BY nome_colaborador, departamento ORDER BY num_eventos DESC;
        """) # [!code ++]
    else:
        return []

    dados = db.execute(query, params).mappings().all()
    return [dict(row) for row in dados]

# =================================================================
# FUNÇÕES PARA O DASHBOARD DO ADMINISTRADOR
# =================================================================
def get_kpis_globais(db: Session) -> List[schemas.AdminKpi]:
    total_usuarios = db.query(func.count(models.Usuario.id)).scalar() or 0
    total_importacoes = db.query(func.count(models.Importacao.id)).scalar() or 0
    receita_global = db.query(func.sum(models.RegistroFinanceiro.receita)).scalar() or 0
    registros_processados = db.query(func.sum(models.Importacao.total_registros)).scalar() or 0
    kpis = [
        schemas.AdminKpi(nome="Total de Usuários", valor=total_usuarios, descricao="Número total de usuários cadastrados na plataforma."),
        schemas.AdminKpi(nome="Total de Importações", valor=total_importacoes, descricao="Número total de arquivos importados por todos os usuários."),
        schemas.AdminKpi(nome="Receita Global Processada", valor=receita_global, descricao="Soma de toda a receita presente nos dados importados."),
        schemas.AdminKpi(nome="Linhas Processadas", valor=registros_processados, descricao="Total de linhas de dados em todos os arquivos."),
    ]
    return kpis

def get_atividades_gerais(db: Session, skip: int, limit: int) -> List[models.AtividadeUsuario]:
    return db.query(models.AtividadeUsuario).options(joinedload(models.AtividadeUsuario.usuario)).order_by(models.AtividadeUsuario.criado_em.desc()).offset(skip).limit(limit).all()

# =================================================================
# INSERÇÃO EM LOTE (CORRIGIDO PARA MAIOR RESILIÊNCIA)
# =================================================================
def inserir_dados_financeiros_em_lote(db: Session, registros: List[Dict[str, Any]], importacao_id: int) -> int:
    if not registros:
        return 0
    for r in registros:
        r['importacao_id'] = importacao_id

    try:
        # Tenta a inserção em lote primeiro (mais rápido)
        db.bulk_insert_mappings(models.RegistroFinanceiro, registros)
        db.commit()
        return len(registros)
    except IntegrityError:
        db.rollback()
        print("AVISO: Conflito de integridade detectado em lote financeiro. Tentando inserção individual...")
        registros_inseridos = 0
        for r_dict in registros:
            try:
                # Garante que id_transacao existe para a verificação
                if 'id_transacao' in r_dict:
                    existe = db.query(models.RegistroFinanceiro).filter_by(id_transacao=r_dict['id_transacao']).first()
                    if not existe:
                        db.execute(models.RegistroFinanceiro.__table__.insert(), r_dict)
                        db.commit()
                        registros_inseridos += 1
                else: # Se não houver id_transacao, insere mesmo assim
                    db.execute(models.RegistroFinanceiro.__table__.insert(), r_dict)
                    db.commit()
                    registros_inseridos += 1
            except Exception as e_individual:
                db.rollback()
                print(f"ERRO ao inserir registro individual financeiro: {r_dict}. Erro: {e_individual}")
        return registros_inseridos
    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO ao inserir dados financeiros em lote: {e}")
        raise HTTPException(status_code=500, detail=f"Erro crítico ao inserir dados financeiros: {e}")

def inserir_dados_produtos_em_lote(db: Session, registros: List[Dict[str, Any]], importacao_id: int) -> int:
    if not registros:
        return 0
    for r in registros:
        r['importacao_id'] = importacao_id

    try:
        db.bulk_insert_mappings(models.RegistroProduto, registros)
        db.commit()
        return len(registros)
    except IntegrityError: # Embora não haja unique key, trata outros erros de integridade
        db.rollback()
        print("AVISO: Conflito de integridade detectado em lote de produtos. Tentando inserção individual...")
        registros_inseridos = 0
        for r_dict in registros:
            try:
                db.execute(models.RegistroProduto.__table__.insert(), r_dict)
                db.commit()
                registros_inseridos += 1
            except Exception as e_individual:
                db.rollback()
                print(f"ERRO ao inserir registro individual de produto: {r_dict}. Erro: {e_individual}")
        return registros_inseridos
    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO ao inserir dados de produtos em lote: {e}")
        raise HTTPException(status_code=500, detail=f"Erro crítico ao inserir dados de produtos: {e}")

def inserir_dados_operacionais_em_lote(db: Session, registros: List[Dict[str, Any]], importacao_id: int) -> int:
    if not registros:
        return 0
    for r in registros:
        r['importacao_id'] = importacao_id

    try:
        db.bulk_insert_mappings(models.RegistroOperacional, registros)
        db.commit()
        return len(registros)
    except IntegrityError:
        db.rollback()
        print("AVISO: Conflito de integridade detectado em lote operacional. Tentando inserção individual...")
        registros_inseridos = 0
        for r_dict in registros:
            try:
                if 'id_evento' in r_dict:
                    existe = db.query(models.RegistroOperacional).filter_by(id_evento=r_dict['id_evento']).first()
                    if not existe:
                        db.execute(models.RegistroOperacional.__table__.insert(), r_dict)
                        db.commit()
                        registros_inseridos += 1
                else:
                    db.execute(models.RegistroOperacional.__table__.insert(), r_dict)
                    db.commit()
                    registros_inseridos += 1
            except Exception as e_individual:
                db.rollback()
                print(f"ERRO ao inserir registro individual operacional: {r_dict}. Erro: {e_individual}")
        return registros_inseridos
    except Exception as e:
        db.rollback()
        print(f"ERRO CRÍTICO ao inserir dados operacionais em lote: {e}")
        raise HTTPException(status_code=500, detail=f"Erro crítico ao inserir dados operacionais: {e}")


# =================================================================
# FUNÇÕES PARA DASHBOARDS INTERATIVOS AVANÇADOS
# =================================================================
def get_filtros_disponiveis(db: Session, usuario_id: int) -> schemas.FiltrosDisponiveis:
    """Retorna todos os filtros disponíveis baseados nos dados do usuário"""
    # Cache: tenta ler
    cache_key = cache.make_key("filtros", usuario_id)
    cached = cache.get_json(cache_key)
    if cached is not None:
        return schemas.FiltrosDisponiveis(**cached)

    # [!code ++] CORREÇÃO: Esta função DEVE usar cliente_id
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        logger.warning(f"get_filtros_disponiveis: Usuário {usuario_id} sem cliente_id.")
        return schemas.FiltrosDisponiveis(categorias_produto=[], departamentos=[], colaboradores=[], periodo_dados={})
        
    cliente_id = usuario.cliente_id
    
    importacoes_cliente = db.query(models.Importacao.id) \
        .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
        .filter(models.Usuario.cliente_id == cliente_id) \
        .subquery()

    categorias = db.query(models.RegistroProduto.categoria_produto).filter(models.RegistroProduto.importacao_id.in_(importacoes_cliente)).filter(models.RegistroProduto.categoria_produto.isnot(None)).distinct().all() # [!code ++]
    departamentos = db.query(models.RegistroOperacional.departamento).filter(models.RegistroOperacional.importacao_id.in_(importacoes_cliente)).filter(models.RegistroOperacional.departamento.isnot(None)).distinct().all() # [!code ++]
    colaboradores = db.query(models.RegistroOperacional.nome_colaborador).filter(models.RegistroOperacional.importacao_id.in_(importacoes_cliente)).filter(models.RegistroOperacional.nome_colaborador.isnot(None)).distinct().all() # [!code ++]

    data_min = db.query(func.min(models.RegistroFinanceiro.data_transacao)).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)).scalar() # [!code ++]
    data_max = db.query(func.max(models.RegistroFinanceiro.data_transacao)).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)).scalar() # [!code ++]

    filtros = schemas.FiltrosDisponiveis(
        categorias_produto=[cat[0] for cat in categorias],
        departamentos=[dep[0] for dep in departamentos],
        colaboradores=[col[0] for col in colaboradores],
        periodo_dados={"data_inicio": data_min.strftime("%Y-%m-%d") if data_min else "", "data_fim": data_max.strftime("%Y-%m-%d") if data_max else ""}
    )
    # Cache: grava
    cache.set_json(cache_key, filtros.model_dump(), ttl_seconds=1800)
    return filtros

def get_dashboard_interativo(db: Session, usuario_id: int, filtros: schemas.FiltrosDashboard) -> schemas.DashboardInterativo:
    """Retorna dados completos do dashboard interativo com filtros aplicados"""

    kpis = get_kpis_dinamicos_filtrados(db, usuario_id, filtros)
    metricas_comparativas = get_metricas_comparativas(db, usuario_id, filtros)

    # Construção de queries base para gráficos
    importacoes_usuario = db.query(models.Importacao.id).filter(models.Importacao.usuario_id == usuario_id).subquery()
    query_financeiro = db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_usuario)) # [!code --]
    query_produtos = db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id.in_(importacoes_usuario)) # [!code --]
    query_operacional = db.query(models.RegistroOperacional).filter(models.RegistroOperacional.importacao_id.in_(importacoes_usuario)) # [!code --]

    # Aplicar filtros comuns
    if filtros.data_inicio:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao >= filtros.data_inicio)
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda >= filtros.data_inicio)
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento >= filtros.data_inicio)
    if filtros.data_fim:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao <= filtros.data_fim)
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda <= filtros.data_fim)
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento <= filtros.data_fim)
    if filtros.categoria_produto:
        query_produtos = query_produtos.filter(models.RegistroProduto.categoria_produto == filtros.categoria_produto)
    if filtros.departamento:
        query_operacional = query_operacional.filter(models.RegistroOperacional.departamento == filtros.departamento)
    if filtros.colaborador:
        query_operacional = query_operacional.filter(models.RegistroOperacional.nome_colaborador == filtros.colaborador)

    grafico_receita = get_grafico_receita_tempo(db, query_financeiro)
    grafico_categoria = get_grafico_vendas_categoria(db, query_produtos)
    grafico_colaboradores = get_grafico_performance_colaboradores(db, query_operacional)
    top_produtos = get_top_produtos_filtrados(db, query_produtos)
    alertas = gerar_alertas_dashboard(db, usuario_id, filtros)

    return schemas.DashboardInterativo(
        kpis=kpis,
        metricas_comparativas=metricas_comparativas,
        grafico_receita_tempo=grafico_receita,
        grafico_vendas_categoria=grafico_categoria,
        grafico_performance_colaboradores=grafico_colaboradores,
        top_produtos=top_produtos,
        alertas=alertas
    )

def get_kpis_dinamicos_filtrados(db: Session, usuario_id: int, filtros: schemas.FiltrosDashboard) -> List[schemas.Kpi]:
    """KPIs com filtros aplicados"""
    # [!code ++] CORREÇÃO: Esta função DEVE usar cliente_id
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        logger.warning(f"get_kpis_dinamicos_filtrados: Usuário {usuario_id} sem cliente_id.")
        return []
    cliente_id = usuario.cliente_id

    importacoes_cliente = db.query(models.Importacao.id) \
        .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
        .filter(models.Usuario.cliente_id == cliente_id) \
        .subquery()

    query_financeiro = db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)) # [!code ++]
    query_produtos = db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id.in_(importacoes_cliente)) # [!code ++]
    query_operacional = db.query(models.RegistroOperacional).filter(models.RegistroOperacional.importacao_id.in_(importacoes_cliente)) # [!code ++]

    # Aplicar filtros
    if filtros.data_inicio:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao >= filtros.data_inicio)
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda >= filtros.data_inicio)
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento >= filtros.data_inicio)
    if filtros.data_fim:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao <= filtros.data_fim)
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda <= filtros.data_fim)
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento <= filtros.data_fim)
    if filtros.categoria_produto:
        query_produtos = query_produtos.filter(models.RegistroProduto.categoria_produto == filtros.categoria_produto)
    if filtros.departamento:
        query_operacional = query_operacional.filter(models.RegistroOperacional.departamento == filtros.departamento)
    if filtros.colaborador:
        query_operacional = query_operacional.filter(models.RegistroOperacional.nome_colaborador == filtros.colaborador)

    receita_total = query_financeiro.with_entities(func.sum(models.RegistroFinanceiro.receita)).scalar() or 0
    lucro_total = query_financeiro.with_entities(func.sum(models.RegistroFinanceiro.lucro)).scalar() or 0
    unidades_vendidas = query_produtos.with_entities(func.sum(models.RegistroProduto.quantidade_vendida)).scalar() or 0
    nps_medio = query_operacional.filter(models.RegistroOperacional.avaliacao_nps.isnot(None)).with_entities(func.avg(models.RegistroOperacional.avaliacao_nps)).scalar()

    return [
        schemas.Kpi(nome="Receita Total", valor=receita_total, prefixo="R$"),
        schemas.Kpi(nome="Lucro Total", valor=lucro_total, prefixo="R$"),
        schemas.Kpi(nome="Unidades Vendidas", valor=unidades_vendidas),
        schemas.Kpi(nome="NPS Médio", valor=round(nps_medio, 1) if nps_medio else 0),
    ]

def get_metricas_comparativas(db: Session, usuario_id: int, filtros: schemas.FiltrosDashboard) -> List[schemas.MetricaComparativa]:
    """Compara métricas com período anterior"""
    from datetime import datetime, timedelta

    if not filtros.data_inicio or not filtros.data_fim:
        return []

    try:
        # As datas já chegam como objetos `date` do Pydantic
        data_inicio = filtros.data_inicio
        data_fim = filtros.data_fim
    except (ValueError, AttributeError):
        return [] # Retorna vazio se as datas estiverem em formato inválido

    periodo_dias = (data_fim - data_inicio).days
    data_inicio_anterior = data_inicio - timedelta(days=periodo_dias + 1)
    data_fim_anterior = data_inicio - timedelta(days=1)

    filtros_anterior = schemas.FiltrosDashboard(
        data_inicio=data_inicio_anterior,
        data_fim=data_fim_anterior,
        categoria_produto=filtros.categoria_produto,
        departamento=filtros.departamento,
        colaborador=filtros.colaborador
    )

    kpis_atual = get_kpis_dinamicos_filtrados(db, usuario_id, filtros)
    kpis_anterior = get_kpis_dinamicos_filtrados(db, usuario_id, filtros_anterior)

    metricas = []
    map_kpis_anterior = {kpi.nome: kpi for kpi in kpis_anterior}

    for kpi_atual in kpis_atual:
        kpi_anterior = map_kpis_anterior.get(kpi_atual.nome)
        if not kpi_anterior: continue

        valor_anterior = kpi_anterior.valor
        percentual_mudanca = ((kpi_atual.valor - valor_anterior) / valor_anterior * 100) if valor_anterior > 0 else (100 if kpi_atual.valor > 0 else 0)
        tendencia = "alta" if percentual_mudanca > 5 else "baixa" if percentual_mudanca < -5 else "estavel"

        metricas.append(schemas.MetricaComparativa(
            nome=kpi_atual.nome,
            valor_atual=kpi_atual.valor,
            valor_anterior=valor_anterior,
            percentual_mudanca=round(percentual_mudanca, 2),
            tendencia=tendencia
        ))
    return metricas

def get_grafico_receita_tempo(db: Session, query_financeiro) -> schemas.DadosGraficoLinha:
    """Gráfico de receita ao longo do tempo"""
    dados = query_financeiro.with_entities(func.date_trunc('month', models.RegistroFinanceiro.data_transacao).label('mes'), func.sum(models.RegistroFinanceiro.receita).label('receita'), func.sum(models.RegistroFinanceiro.lucro).label('lucro')).group_by(func.date_trunc('month', models.RegistroFinanceiro.data_transacao)).order_by('mes').all()

    labels = [row.mes.strftime("%Y-%m") for row in dados] if dados else []
    receitas = [float(row.receita) for row in dados] if dados else []
    lucros = [float(row.lucro) for row in dados] if dados else []

    return schemas.DadosGraficoLinha(datasets=[{"label": "Receita", "data": receitas, "borderColor": "rgb(75, 192, 192)", "backgroundColor": "rgba(75, 192, 192, 0.2)"}, {"label": "Lucro", "data": lucros, "borderColor": "rgb(255, 99, 132)", "backgroundColor": "rgba(255, 99, 132, 0.2)"}], labels=labels)

def get_grafico_vendas_categoria(db: Session, query_produtos) -> schemas.DadosGraficoPizza:
    """Gráfico de pizza para vendas por categoria"""
    dados = query_produtos.with_entities(models.RegistroProduto.categoria_produto, func.sum(models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida).label('total')).group_by(models.RegistroProduto.categoria_produto).order_by('total').all()

    labels = [row.categoria_produto or "Não Categorizado" for row in dados]
    values = [float(row.total) for row in dados]
    cores = ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#FF9F40", "#C9CBCF"]

    return schemas.DadosGraficoPizza(labels=labels, data=values, backgroundColor=cores[:len(labels)])

def get_grafico_performance_colaboradores(db: Session, query_operacional) -> schemas.DadosGraficoBarra:
    """Gráfico de barras para performance de colaboradores"""
    dados = query_operacional.with_entities(models.RegistroOperacional.nome_colaborador, func.avg(models.RegistroOperacional.avaliacao_nps).label('nps_medio')).filter(models.RegistroOperacional.avaliacao_nps.isnot(None)).group_by(models.RegistroOperacional.nome_colaborador).order_by('nps_medio').limit(10).all()

    labels = [row.nome_colaborador for row in dados]
    values = [float(row.nps_medio) if row.nps_medio else 0 for row in dados]
    cores = ["#F44336" if v < 6 else ("#FF9800" if v < 8 else "#4CAF50") for v in values]

    return schemas.DadosGraficoBarra(labels=labels, data=values, backgroundColor=cores)

def get_top_produtos_filtrados(db: Session, query_produtos) -> List[Dict[str, Any]]:
    """Top 10 produtos com filtros aplicados"""
    dados = query_produtos.with_entities(models.RegistroProduto.nome_produto, models.RegistroProduto.categoria_produto, func.sum(models.RegistroProduto.quantidade_vendida).label('total_unidades'), func.sum(models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida).label('receita_total')).group_by(models.RegistroProduto.nome_produto, models.RegistroProduto.categoria_produto).order_by(func.sum(models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida).desc()).limit(10).all()

    return [{"nome": row.nome_produto, "categoria": row.categoria_produto or "Não Categorizado", "unidades_vendidas": int(row.total_unidades or 0), "receita_total": float(row.receita_total or 0)} for row in dados]

# ===============================
# LIMIARES POR CLIENTE
# ===============================

def create_limiar_indicador(db: Session, cliente_id: int, payload: schemas.LimiarIndicadorCreate, autor_id: int) -> models.LimiarIndicador:
    cliente = get_cliente(db, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    limiar = models.LimiarIndicador(
        cliente_id=cliente_id,
        nome=payload.nome,
        operador=payload.operador,
        valor_limite=payload.valor_limite,
        prioridade=payload.prioridade or 'normal',
        canal=payload.canal or 'in_app',
        ativo=payload.ativo if payload.ativo is not None else True,
        mensagem=payload.mensagem,
        config_json=payload.config_json,
    )
    db.add(limiar)
    db.commit()
    db.refresh(limiar)
    log_activity(db, autor_id, "criação", "limiares_indicadores", limiar.id, None, {
        "cliente_id": cliente_id,
        "nome": payload.nome,
    })
    return limiar


def list_limiares_cliente(db: Session, cliente_id: int, skip: int = 0, limit: int = 100) -> List[models.LimiarIndicador]:
    return db.query(models.LimiarIndicador).options(
        selectinload(models.LimiarIndicador.cliente)
    ).filter(
        models.LimiarIndicador.cliente_id == cliente_id,
        models.LimiarIndicador.ativo == True
    ).order_by(models.LimiarIndicador.id.desc()).offset(skip).limit(limit).all()


def update_limiar_indicador(db: Session, cliente_id: int, limiar_id: int, payload: schemas.LimiarIndicadorUpdate, autor_id: int) -> models.LimiarIndicador:
    limiar = db.query(models.LimiarIndicador).filter(
        models.LimiarIndicador.id == limiar_id,
        models.LimiarIndicador.cliente_id == cliente_id
    ).first()
    if not limiar:
        raise HTTPException(status_code=404, detail="Limiar não encontrado")
    update_data = payload.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        if hasattr(limiar, k):
            setattr(limiar, k, v)
    db.commit()
    db.refresh(limiar)
    log_activity(db, autor_id, "atualização", "limiares_indicadores", limiar.id, None, update_data)
    # Invalida cache do cliente após alteração de limiar
    try:
        from .cache_service import get_cache_service
        cache = get_cache_service()
        cache.invalidate_client_cache(cliente_id=cliente_id)
    except Exception:
        pass
    return limiar


def delete_limiar_indicador(db: Session, cliente_id: int, limiar_id: int, autor_id: int) -> Dict[str, bool]:
    limiar = db.query(models.LimiarIndicador).filter(
        models.LimiarIndicador.id == limiar_id,
        models.LimiarIndicador.cliente_id == cliente_id
    ).first()
    if not limiar:
        raise HTTPException(status_code=404, detail="Limiar não encontrado")
    db.delete(limiar)
    db.commit()
    log_activity(db, autor_id, "remoção", "limiares_indicadores", limiar_id, None, {"cliente_id": cliente_id})
    # Invalida cache do cliente após remoção de limiar
    try:
        from .cache_service import get_cache_service
        cache = get_cache_service()
        cache.invalidate_client_cache(cliente_id=cliente_id)
    except Exception:
        pass
    return {"ok": True}


def gerar_alertas_dashboard(db: Session, usuario_id: int, filtros: schemas.FiltrosDashboard) -> List[Dict[str, str]]:
    """Gera alertas baseados nos dados do dashboard, considerando limiares por cliente.
    - Suporta db=None para cenários de teste com monkeypatch.
    - Limiar customizado substitui regra padrão da mesma métrica.
    """
    alertas: List[Dict[str, str]] = []
    metricas = get_metricas_comparativas(db, usuario_id, filtros)

    # Mapa rápido das métricas por nome
    mapa_metricas = {m.nome: m for m in metricas}

    # Descobrir cliente_id de forma segura (permitir db=None em testes)
    cliente_id = None
    try:
        if db is not None:
            usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
            cliente_id = usuario.cliente_id if usuario else None
    except Exception:
        cliente_id = None

    # Coleta limiares; se db=None (tests), ainda chamamos para permitir monkeypatch
    limiares = []
    try:
        if db is None or cliente_id is not None:
            limiares = list_limiares_cliente(db, cliente_id)
    except Exception:
        limiares = []

    nomes_com_limiar = {limiar.nome for limiar in limiares}

    # Regras padrão (fallback) apenas quando não há limiar configurado para a métrica
    if "Receita Total" in mapa_metricas and "Receita Total" not in nomes_com_limiar:
        m = mapa_metricas["Receita Total"]
        if m.percentual_mudanca < -10:
            alertas.append({
                "tipo": "warning",
                "titulo": "Queda na Receita",
                "mensagem": f"Receita caiu {abs(m.percentual_mudanca):.1f}% em relação ao período anterior"
            })
    if "NPS Médio" in mapa_metricas and "NPS Médio" not in nomes_com_limiar:
        m = mapa_metricas["NPS Médio"]
        if m.valor_atual < 6:
            alertas.append({
                "tipo": "danger",
                "titulo": "NPS Baixo",
                "mensagem": f"NPS médio está em {m.valor_atual}, abaixo do recomendado (6+)"
            })

    # Integração de limiares por cliente (substitui comportamento padrão)
    for limiar in limiares:
        nome = limiar.nome
        if nome not in mapa_metricas:
            continue
        metrica = mapa_metricas[nome]
        if nome == "Receita Total":
            valor = float(metrica.percentual_mudanca)
            limite = float(limiar.valor_limite)
            operador = getattr(limiar, "operador", "below")
            cond = (valor < -limite) if operador == 'below' else (valor > limite)
            if cond:
                alertas.append({
                    "tipo": "warning" if operador == 'below' else "info",
                    "titulo": f"Alerta: {nome}",
                    "mensagem": getattr(limiar, "mensagem", None) or f"Variação de receita {valor:.1f}% excede limiar ({operador} {limite}%)",
                })
        elif nome == "NPS Médio":
            valor = float(metrica.valor_atual)
            limite = float(limiar.valor_limite)
            operador = getattr(limiar, "operador", "below")
            cond = (valor < limite) if operador == 'below' else (valor > limite)
            if cond:
                alertas.append({
                    "tipo": "danger" if operador == 'below' else "info",
                    "titulo": f"Alerta: {nome}",
                    "mensagem": getattr(limiar, "mensagem", None) or f"NPS {valor:.1f} está {operador} do limite ({limite})",
                })

    return alertas


def create_cliente(db: Session, nome: str) -> models.Cliente:
    cliente = models.Cliente(nome=nome)
    db.add(cliente)
    try:
        db.commit()
        db.refresh(cliente)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Cliente com nome '{nome}' já existe.")
    return cliente


def get_cliente(db: Session, cliente_id: int) -> Optional[models.Cliente]:
    return db.query(models.Cliente).filter(models.Cliente.id == cliente_id).first()


def create_indicador_customizado(db: Session, payload: schemas.IndicadorCustomizadoCreate, cliente_id: int, autor_id: int) -> models.IndicadorCustomizado:
    if not get_cliente(db, cliente_id):
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    indicador = models.IndicadorCustomizado(
        cliente_id=cliente_id,
        nome=payload.nome,
        descricao=payload.descricao,
        unidade=payload.unidade,
        prefixo=payload.prefixo,
        ativo=payload.ativo if payload.ativo is not None else True,
        config_json=payload.config_json,
    )
    db.add(indicador)
    try:
        db.commit()
        db.refresh(indicador)
        log_activity(db, autor_id, "criação", "indicadores_customizados", indicador.id, None, {
            "cliente_id": cliente_id,
            "nome": payload.nome,
        })
        # Invalida cache do cliente relacionado a indicadores
        try:
            from .cache_service import get_cache_service
            cache = get_cache_service()
            cache.invalidate_client_cache(cliente_id=cliente_id)
        except Exception:
            pass
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail=f"Indicador '{payload.nome}' já existe para este cliente.")
    return indicador


def list_indicadores_cliente(db: Session, cliente_id: int, skip: int = 0, limit: int = 100) -> List[models.IndicadorCustomizado]:
    return db.query(models.IndicadorCustomizado).options(
        selectinload(models.IndicadorCustomizado.cliente)
    ).filter(
        models.IndicadorCustomizado.cliente_id == cliente_id,
        models.IndicadorCustomizado.ativo == True
    ).order_by(models.IndicadorCustomizado.id.desc()).offset(skip).limit(limit).all()


# Utilitário interno: aplicar filtros do dashboard às queries
from sqlalchemy import and_ as sql_and

def _aplicar_filtros_dashboard(query, tabela, filtros: Optional[schemas.FiltrosDashboard]):
    if not filtros:
        return query
    # Datas
    if hasattr(tabela, 'data_transacao') and filtros.data_inicio:
        query = query.filter(tabela.data_transacao >= filtros.data_inicio)
    if hasattr(tabela, 'data_transacao') and filtros.data_fim:
        query = query.filter(tabela.data_transacao <= filtros.data_fim)
    if hasattr(tabela, 'data_venda') and filtros.data_inicio:
        query = query.filter(tabela.data_venda >= filtros.data_inicio)
    if hasattr(tabela, 'data_venda') and filtros.data_fim:
        query = query.filter(tabela.data_venda <= filtros.data_fim)
    if hasattr(tabela, 'data_evento') and filtros.data_inicio:
        query = query.filter(tabela.data_evento >= filtros.data_inicio)
    if hasattr(tabela, 'data_evento') and filtros.data_fim:
        query = query.filter(tabela.data_evento <= filtros.data_fim)
    # Categoria produto
    if hasattr(tabela, 'categoria_produto') and filtros.categoria_produto:
        query = query.filter(tabela.categoria_produto == filtros.categoria_produto)
    # Departamento
    if hasattr(tabela, 'departamento') and filtros.departamento:
        query = query.filter(tabela.departamento == filtros.departamento)
    # Colaborador
    if hasattr(tabela, 'nome_colaborador') and filtros.colaborador:
        query = query.filter(tabela.nome_colaborador == filtros.colaborador)
    # Valor mínimo/máximo para preço ou receita
    if hasattr(tabela, 'preco_unitario') and filtros.valor_minimo is not None:
        query = query.filter(tabela.preco_unitario >= filtros.valor_minimo)
    if hasattr(tabela, 'preco_unitario') and filtros.valor_maximo is not None:
        query = query.filter(tabela.preco_unitario <= filtros.valor_maximo)
    return query


def calcular_indicador_customizado(db: Session, cliente_id: int, indicador_id: int, filtros: Optional[schemas.FiltrosDashboard]) -> schemas.ValorIndicadorResponse:
    ind = db.query(models.IndicadorCustomizado).filter(models.IndicadorCustomizado.id == indicador_id, models.IndicadorCustomizado.cliente_id == cliente_id, models.IndicadorCustomizado.ativo == True).first()
    if not ind:
        raise HTTPException(status_code=404, detail="Indicador não encontrado para o cliente")

    cfg = ind.config_json or {}
    tabela = cfg.get('tabela')  # 'financeiro' | 'produtos' | 'operacional'
    agregacao = cfg.get('agregacao')  # 'sum' | 'avg' | 'count'
    campo = cfg.get('campo')  # ex: 'receita', 'lucro', 'quantidade_vendida', 'avaliacao_nps'

    tables_map = {
        'financeiro': models.RegistroFinanceiro,
        'produtos': models.RegistroProduto,
        'operacional': models.RegistroOperacional,
    }
    allowed_fields = {
        'financeiro': {'receita': models.RegistroFinanceiro.receita, 'lucro': models.RegistroFinanceiro.lucro},
        'produtos': {
            'quantidade_vendida': models.RegistroProduto.quantidade_vendida,
            'preco_unitario': models.RegistroProduto.preco_unitario,
            'receita_total': (models.RegistroProduto.preco_unitario * models.RegistroProduto.quantidade_vendida),
        },
        'operacional': {'avaliacao_nps': models.RegistroOperacional.avaliacao_nps, 'id_evento': models.RegistroOperacional.id_evento},
    }
    if tabela not in tables_map:
        raise HTTPException(status_code=400, detail="Tabela inválida no config do indicador")

    Model = tables_map[tabela]

    # Subquery: importações de usuários do cliente
    importacoes_cliente = db.query(models.Importacao.id).join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id).filter(models.Usuario.cliente_id == cliente_id).subquery()

    query = db.query(Model).filter(Model.importacao_id.in_(importacoes_cliente)) # [!code --]
    # Aplicar filtros do dashboard
    query = _aplicar_filtros_dashboard(query, Model, filtros)

    # Selecionar agregação
    from sqlalchemy import func as sa_func
    if agregacao == 'sum':
        if campo not in allowed_fields[tabela]:
            raise HTTPException(status_code=400, detail="Campo inválido para soma")
        expr = allowed_fields[tabela][campo]
        valor = query.with_entities(sa_func.sum(expr)).scalar() or 0
    elif agregacao == 'avg':
        if campo not in allowed_fields[tabela]:
            raise HTTPException(status_code=400, detail="Campo inválido para média")
        expr = allowed_fields[tabela][campo]
        valor = query.with_entities(sa_func.avg(expr)).scalar() or 0
    elif agregacao == 'count':
        valor = query.count()
    else:
        raise HTTPException(status_code=400, detail="Agregação inválida")

    detalhes = {
        "tabela": tabela,
        "agregacao": agregacao,
        "campo": campo,
    }
    return schemas.ValorIndicadorResponse(nome=ind.nome, valor=valor, detalhes=detalhes)

# ===============================
# CATÁLOGO DE INSIGHTS (HEURÍSTICO)
# ===============================

def gerar_catalogo_insights(db: Session, usuario_id: int, filtros: Optional[schemas.FiltrosDashboard] = None) -> schemas.InsightCatalogoResponse:
    """Gera um catálogo de insights heurísticos com base nas métricas e gráficos existentes."""
    insights: List[schemas.InsightItem] = []

    # Métricas comparativas para detectar variações relevantes
    metricas = get_metricas_comparativas(db, usuario_id, filtros or schemas.FiltrosDashboard())
    mapa_metricas = {m.nome: m for m in metricas}

    # Insight: Queda de Receita
    if "Receita Total" in mapa_metricas:
        m = mapa_metricas["Receita Total"]
        if float(m.percentual_mudanca) <= -10.0:
            insights.append(schemas.InsightItem(
                tipo="financeiro",
                titulo="Queda relevante de receita",
                resumo=f"Receita variou {float(m.percentual_mudanca):.1f}% para baixo frente ao período anterior.",
                prioridade="alta",
                metadados={"valor_atual": float(m.valor_atual), "valor_anterior": float(m.valor_anterior)}
            ))

    # Insight: NPS baixo
    if "NPS Médio" in mapa_metricas:
        m = mapa_metricas["NPS Médio"]
        if float(m.valor_atual) < 6.0:
            insights.append(schemas.InsightItem(
                tipo="operacional",
                titulo="NPS médio abaixo do recomendado",
                resumo=f"NPS médio atual {float(m.valor_atual):.1f} está abaixo de 6.",
                prioridade="alta",
                metadados={"nps_atual": float(m.valor_atual)}
            ))

    # Construção de queries base para análises complementares
    # [!code ++] CORREÇÃO: Esta função DEVE usar cliente_id
    usuario = get_usuario(db, usuario_id)
    if not usuario or not usuario.cliente_id:
        logger.warning(f"gerar_catalogo_insights: Usuário {usuario_id} sem cliente_id.")
        return schemas.InsightCatalogoResponse(insights=[])
    cliente_id = usuario.cliente_id
    
    importacoes_cliente = db.query(models.Importacao.id) \
        .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
        .filter(models.Usuario.cliente_id == cliente_id) \
        .subquery()
        
    q_fin = db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_cliente)) # [!code ++]
    q_prod = db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id.in_(importacoes_cliente)) # [!code ++]
    q_oper = db.query(models.RegistroOperacional).filter(models.RegistroOperacional.importacao_id.in_(importacoes_cliente)) # [!code ++]

    if filtros:
        q_fin = _aplicar_filtros_dashboard(q_fin, models.RegistroFinanceiro, filtros)
        q_prod = _aplicar_filtros_dashboard(q_prod, models.RegistroProduto, filtros)
        q_oper = _aplicar_filtros_dashboard(q_oper, models.RegistroOperacional, filtros)

    # Insight: Categoria com maior receita
    try:
        graf_pizza = get_grafico_vendas_categoria(db, q_prod)
        if graf_pizza.labels:
            max_idx = max(range(len(graf_pizza.data)), key=lambda i: float(graf_pizza.data[i]) if graf_pizza.data[i] is not None else 0.0)
            cat = graf_pizza.labels[max_idx]
            val = float(graf_pizza.data[max_idx]) if graf_pizza.data[max_idx] is not None else 0.0
            insights.append(schemas.InsightItem(
                tipo="produto",
                titulo="Categoria destaque em vendas",
                resumo=f"Categoria '{cat}' lidera receita no período.",
                prioridade="media",
                metadados={"categoria": cat, "receita_total": val}
            ))
    except Exception:
        pass

    # Insight: Colaborador com NPS mais baixo
    try:
        graf_barra = get_grafico_performance_colaboradores(db, q_oper)
        if graf_barra.labels and graf_barra.data:
            min_idx = min(range(len(graf_barra.data)), key=lambda i: float(graf_barra.data[i]) if graf_barra.data[i] is not None else 0.0)
            nome = graf_barra.labels[min_idx]
            nps = float(graf_barra.data[min_idx]) if graf_barra.data[min_idx] is not None else 0.0
            insights.append(schemas.InsightItem(
                tipo="operacional",
                titulo="Colaborador com menor NPS",
                resumo=f"'{nome}' apresenta o menor NPS médio no período.",
                prioridade="media",
                metadados={"colaborador": nome, "nps_medio": nps}
            ))
    except Exception:
        pass

    # Insight: Top produto
    try:
        top_produtos = get_top_produtos_filtrados(db, q_prod)
        if top_produtos:
            p = top_produtos[0]
            insights.append(schemas.InsightItem(
                tipo="produto",
                titulo="Produto com maior destaque",
                resumo=f"'{p.get('nome', 'Produto')}' aparece como destaque em vendas.",
                prioridade="baixa",
                metadados=p
            ))
    except Exception:
        pass

    return schemas.InsightCatalogoResponse(insights=insights)

# ===============================
# INDICADORES CUSTOMIZADOS
# ===============================

# def create_indicador_customizado(db: Session, indicador: schemas.IndicadorCustomizadoCreate, cliente_id: int, autor_id: int):
#     """Cria um novo indicador customizado para um cliente."""
#     from .indicadores_service import IndicadorService

#     # Validar configuração antes de salvar
#     service = IndicadorService(db)
#     try:
#         service.validar_config_indicador(indicador.config_json)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Configuração inválida: {str(e)}")

#     db_indicador = models.IndicadorCustomizado(
#         cliente_id=cliente_id,
#         nome=indicador.nome,
#         descricao=indicador.descricao,
#         unidade=indicador.unidade,
#         prefixo=indicador.prefixo,
#         ativo=indicador.ativo,
#         config_json=indicador.config_json
#     )

#     try:
#         db.add(db_indicador)
#         db.commit()
#         db.refresh(db_indicador)

#         # Log da atividade
#         log_activity(db, autor_id, "CREATE", "indicadores_customizados", db_indicador.id,
#                     dados_depois={"nome": indicador.nome, "cliente_id": cliente_id})

#         return db_indicador
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=400, detail="Indicador com este nome já existe para o cliente")

def get_indicadores_customizados(db: Session, cliente_id: int, skip: int = 0, limit: int = 100):
    """Lista indicadores customizados de um cliente."""
    return db.query(models.IndicadorCustomizado).filter(
        models.IndicadorCustomizado.cliente_id == cliente_id
    ).offset(skip).limit(limit).all()

def get_indicador_customizado(db: Session, indicador_id: int, cliente_id: int):
    """Busca um indicador customizado específico."""
    return db.query(models.IndicadorCustomizado).filter(
        models.IndicadorCustomizado.id == indicador_id,
        models.IndicadorCustomizado.cliente_id == cliente_id
    ).first()

def update_indicador_customizado(db: Session, indicador_id: int, indicador_update: schemas.IndicadorCustomizadoUpdate, cliente_id: int, autor_id: int):
    """Atualiza um indicador customizado."""
    db_indicador = get_indicador_customizado(db, indicador_id, cliente_id)
    if not db_indicador:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")

    # Validar nova configuração se fornecida
    if indicador_update.config_json:
        from .indicadores_service import IndicadorService
        service = IndicadorService(db)
        try:
            service.validar_config_indicador(indicador_update.config_json)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Configuração inválida: {str(e)}")

    dados_antes = {
        "nome": db_indicador.nome,
        "descricao": db_indicador.descricao,
        "ativo": db_indicador.ativo
    }

    # Atualizar campos
    update_data = indicador_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_indicador, field, value)

    try:
        db.commit()
        db.refresh(db_indicador)

        # Log da atividade
        log_activity(db, autor_id, "UPDATE", "indicadores_customizados", indicador_id,
                    dados_antes=dados_antes, dados_depois=update_data)

        return db_indicador
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Nome do indicador já existe para o cliente")

def delete_indicador_customizado(db: Session, indicador_id: int, cliente_id: int, autor_id: int):
    """Remove um indicador customizado."""
    db_indicador = get_indicador_customizado(db, indicador_id, cliente_id)
    if not db_indicador:
        raise HTTPException(status_code=404, detail="Indicador não encontrado")

    dados_antes = {"nome": db_indicador.nome, "cliente_id": cliente_id}

    db.delete(db_indicador)
    db.commit()

    # Log da atividade
    log_activity(db, autor_id, "DELETE", "indicadores_customizados", indicador_id, dados_antes=dados_antes)

    return {"message": "Indicador removido com sucesso"}

def avaliar_indicador_customizado(db: Session, indicador_id: int, usuario_id: int):
    """Avalia um indicador customizado e retorna os resultados."""
    from .indicadores_service import get_indicador_service
    from datetime import datetime

    service = get_indicador_service(db)

    try:
        resultados = service.avaliar_indicador(indicador_id, usuario_id)

        # Buscar nome do indicador
        indicador = db.query(models.IndicadorCustomizado).filter(
            models.IndicadorCustomizado.id == indicador_id
        ).first()

        return schemas.AvaliacaoIndicadorResponse(
            indicador_id=indicador_id,
            nome=indicador.nome if indicador else f"Indicador {indicador_id}",
            resultados=resultados,
            executado_em=datetime.now()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ===============================
# LIMIARES DE INDICADORES
# ===============================

# def create_limiar_indicador(db: Session, limiar: schemas.LimiarIndicadorCreate, cliente_id: int, autor_id: int):
#     """Cria um novo limiar de indicador para um cliente."""
#     from .indicadores_service import IndicadorService

#     # Validar configuração antes de salvar
#     service = IndicadorService(db)
#     try:
#         service.validar_config_indicador(limiar.config_json)
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=f"Configuração inválida: {str(e)}")

#     db_limiar = models.LimiarIndicador(
#         cliente_id=cliente_id,
#         nome=limiar.nome,
#         operador=limiar.operador,
#         valor_limite=limiar.valor_limite,
#         prioridade=limiar.prioridade,
#         canal=limiar.canal,
#         ativo=limiar.ativo,
#         mensagem=limiar.mensagem,
#         config_json=limiar.config_json
#     )

#     try:
#         db.add(db_limiar)
#         db.commit()
#         db.refresh(db_limiar)

#         # Log da atividade
#         log_activity(db, autor_id, "CREATE", "limiares_indicadores", db_limiar.id,
#                     dados_depois={"nome": limiar.nome, "cliente_id": cliente_id})

#         return db_limiar
#     except IntegrityError:
#         db.rollback()
#         raise HTTPException(status_code=400, detail="Limiar com este nome já existe para o cliente")

def get_limiares_indicadores(db: Session, cliente_id: int, skip: int = 0, limit: int = 100):
    """Lista limiares de indicadores de um cliente."""
    return db.query(models.LimiarIndicador).filter(
        models.LimiarIndicador.cliente_id == cliente_id
    ).offset(skip).limit(limit).all()

def get_limiar_indicador(db: Session, limiar_id: int, cliente_id: int):
    """Busca um limiar de indicador específico."""
    return db.query(models.LimiarIndicador).filter(
        models.LimiarIndicador.id == limiar_id,
        models.LimiarIndicador.cliente_id == cliente_id
    ).first()

def avaliar_limiar_indicador(db: Session, limiar_id: int, usuario_id: int):
    """Avalia um limiar de indicador e retorna se foi violado."""
    from .indicadores_service import get_indicador_service

    service = get_indicador_service(db)

    try:
        resultado = service.avaliar_limiar(limiar_id, usuario_id)

        # Buscar nome do limiar
        limiar = db.query(models.LimiarIndicador).filter(
            models.LimiarIndicador.id == limiar_id
        ).first()

        return schemas.AvaliacaoLimiarResponse(
            limiar_id=limiar_id,
            nome=limiar.nome if limiar else f"Limiar {limiar_id}",
            **resultado
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# def list_limiares_cliente(db: Session, cliente_id: int):
#     """Lista todos os limiares ativos de um cliente para verificação de alertas."""
#     return db.query(models.LimiarIndicador).filter(
#         models.LimiarIndicador.cliente_id == cliente_id,
#         models.LimiarIndicador.ativo == True
#     ).all()

# ===============================
# ALERTAS E NOTIFICAÇÕES
# ===============================

def processar_alertas_cliente(db: Session, config: schemas.ConfiguracaoAlertaRequest, usuario_id: int):
    """Processa alertas para um cliente específico."""
    from .alerts_service import get_alerts_service

    service = get_alerts_service(db)

    try:
        resultado = service.processar_alertas_cliente(config.cliente_id)

        # Log da atividade
        log_activity(db, usuario_id, "PROCESS", "alertas", config.cliente_id,
                    dados_depois={
                        "alertas_gerados": resultado["alertas_gerados"],
                        "cliente_id": config.cliente_id
                    })

        return schemas.ProcessamentoAlertasResponse(**resultado)

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao processar alertas: {str(e)}")

def verificar_limiares_cliente(db: Session, cliente_id: int, usuario_id: int):
    """Verifica apenas os limiares de um cliente."""
    from .alerts_service import get_alerts_service

    service = get_alerts_service(db)

    try:
        alertas = service.verificar_limiares_cliente(cliente_id)

        # Log da atividade
        log_activity(db, usuario_id, "CHECK", "limiares", cliente_id,
                    dados_depois={"alertas_gerados": len(alertas)})

        return [
            schemas.AlertaGeradoSchema(
                tipo=alerta.tipo,
                titulo=alerta.titulo,
                mensagem=alerta.mensagem,
                prioridade=alerta.prioridade,
                cliente_id=alerta.cliente_id,
                usuario_id=alerta.usuario_id,
                dados_contexto=alerta.dados_contexto,
                canais=alerta.canais,
                gerado_em=alerta.gerado_em
            ) for alerta in alertas
        ]

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao verificar limiares: {str(e)}")

def verificar_tendencias_cliente(db: Session, cliente_id: int, dias: int, usuario_id: int):
    """Verifica tendências negativas de um cliente."""
    from .alerts_service import get_alerts_service

    service = get_alerts_service(db)

    try:
        alertas = service.verificar_tendencias_negativas(cliente_id, dias)

        # Log da atividade
        log_activity(db, usuario_id, "CHECK", "tendencias", cliente_id,
                    dados_depois={"alertas_gerados": len(alertas), "periodo_dias": dias})

        return [
            schemas.AlertaGeradoSchema(
                tipo=alerta.tipo,
                titulo=alerta.titulo,
                mensagem=alerta.mensagem,
                prioridade=alerta.prioridade,
                cliente_id=alerta.cliente_id,
                usuario_id=alerta.usuario_id,
                dados_contexto=alerta.dados_contexto,
                canais=alerta.canais,
                gerado_em=alerta.gerado_em
            ) for alerta in alertas
        ]

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Erro ao verificar tendências: {str(e)}")

def atualizar_preferencias_notificacao(db: Session, usuario_id: int, preferencias: schemas.PreferenciasNotificacaoUpdate, autor_id: int):
    """Atualiza as preferências de notificação de um usuário."""
    import json

    # Buscar preferências existentes
    db_preferencias = db.query(models.PreferenciasNotificacao).filter(
        models.PreferenciasNotificacao.usuario_id == usuario_id
    ).first()

    # Preparar configuração JSON
    config = {}
    if preferencias.tipos_habilitados is not None:
        config['tipos_habilitados'] = preferencias.tipos_habilitados
    if preferencias.prioridade_minima is not None:
        config['prioridade_minima'] = preferencias.prioridade_minima
    if preferencias.horario_silencioso_inicio is not None:
        config['horario_silencioso_inicio'] = preferencias.horario_silencioso_inicio
    if preferencias.horario_silencioso_fim is not None:
        config['horario_silencioso_fim'] = preferencias.horario_silencioso_fim

    try:
        if db_preferencias:
            # Atualizar existente
            dados_antes = {
                "email_habilitado": db_preferencias.email_habilitado,
                "sms_habilitado": db_preferencias.sms_habilitado,
                "push_habilitado": db_preferencias.push_habilitado
            }

            # Mesclar configuração existente com nova
            config_existente = json.loads(db_preferencias.configuracao_json or '{}')
            config_existente.update(config)

            # Atualizar campos
            if preferencias.email_habilitado is not None:
                db_preferencias.email_habilitado = preferencias.email_habilitado
            if preferencias.sms_habilitado is not None:
                db_preferencias.sms_habilitado = preferencias.sms_habilitado
            if preferencias.push_habilitado is not None:
                db_preferencias.push_habilitado = preferencias.push_habilitado

            db_preferencias.configuracao_json = json.dumps(config_existente)

        else:
            # Criar nova
            dados_antes = None
            db_preferencias = models.PreferenciasNotificacao(
                usuario_id=usuario_id,
                email_habilitado=preferencias.email_habilitado or True,
                sms_habilitado=preferencias.sms_habilitado or False,
                push_habilitado=preferencias.push_habilitado or True,
                configuracao_json=json.dumps(config)
            )
            db.add(db_preferencias)

        db.commit()
        db.refresh(db_preferencias)

        # Log da atividade
        log_activity(db, autor_id, "UPDATE", "preferencias_notificacao", usuario_id,
                    dados_antes=dados_antes,
                    dados_depois=preferencias.model_dump(exclude_unset=True))

        return db_preferencias

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao atualizar preferências: {str(e)}")

def listar_notificacoes_usuario(db: Session, usuario_id: int, skip: int = 0, limit: int = 50, apenas_nao_lidas: bool = False):
    """Lista notificações de um usuário."""
    query = db.query(models.Notificacao).filter(
        models.Notificacao.usuario_id == usuario_id
    )

    if apenas_nao_lidas:
        query = query.filter(models.Notificacao.lida == False)

    return query.order_by(models.Notificacao.data_criacao.desc()).offset(skip).limit(limit).all()

def marcar_notificacao_lida(db: Session, notificacao_id: int, usuario_id: int, autor_id: int):
    """Marca uma notificação como lida."""
    notificacao = db.query(models.Notificacao).filter(
        models.Notificacao.id == notificacao_id,
        models.Notificacao.usuario_id == usuario_id
    ).first()

    if not notificacao:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")

    notificacao.lida = True
    notificacao.data_leitura = datetime.now()

    db.commit()

    # Log da atividade
    log_activity(db, autor_id, "READ", "notificacao", notificacao_id)

    return {"message": "Notificação marcada como lida"}

def marcar_todas_notificacoes_lidas(db: Session, usuario_id: int, autor_id: int):
    """Marca todas as notificações de um usuário como lidas."""
    notificacoes = db.query(models.Notificacao).filter(
        models.Notificacao.usuario_id == usuario_id,
        models.Notificacao.lida == False
    ).all()

    count = 0
    for notificacao in notificacoes:
        notificacao.lida = True
        notificacao.data_leitura = datetime.now()
        count += 1

    db.commit()

    # Log da atividade
    log_activity(db, autor_id, "READ_ALL", "notificacoes", usuario_id,
                dados_depois={"notificacoes_marcadas": count})

    return {"message": f"{count} notificações marcadas como lidas"}

# ==================== FUNÇÕES PARA AUTOMAÇÃO E SCHEDULER ====================

def get_scheduler_status(db: Session) -> schemas.SchedulerStatusSchema:
    """Retorna o status atual do scheduler"""
    try:
        from .scheduler_service import get_scheduler_service

        scheduler = get_scheduler_service()
        jobs = scheduler.get_jobs()

        return schemas.SchedulerStatusSchema(
            is_running=scheduler.is_running,
            jobs=[schemas.JobInfoSchema(**job) for job in jobs],
            total_jobs=len(jobs)
        )

    except Exception as e:
        logger.error(f"Erro ao obter status do scheduler: {str(e)}")
        return schemas.SchedulerStatusSchema(
            is_running=False,
            jobs=[],
            total_jobs=0
        )

def start_scheduler(db: Session) -> bool:
    """Inicia o scheduler"""
    try:
        from .scheduler_service import get_scheduler_service

        scheduler = get_scheduler_service()
        scheduler.start()

        logger.info("Scheduler iniciado via API")
        return True

    except Exception as e:
        logger.error(f"Erro ao iniciar scheduler: {str(e)}")
        return False

def stop_scheduler(db: Session) -> bool:
    """Para o scheduler"""
    try:
        from .scheduler_service import get_scheduler_service

        scheduler = get_scheduler_service()
        scheduler.stop()

        logger.info("Scheduler parado via API")
        return True

    except Exception as e:
        logger.error(f"Erro ao parar scheduler: {str(e)}")
        return False

def add_custom_job(db: Session, job_request: schemas.CustomJobRequest) -> bool:
    """Adiciona uma tarefa customizada ao scheduler"""
    try:
        from .scheduler_service import get_scheduler_service
        from apscheduler.triggers.interval import IntervalTrigger
        from apscheduler.triggers.cron import CronTrigger

        scheduler = get_scheduler_service()

        # Mapeia funções disponíveis
        available_functions = {
            'processar_alertas': scheduler._processar_alertas_periodico,
            'precalcular_metricas': scheduler._precalcular_metricas_diarias,
            'limpar_notificacoes': scheduler._limpar_notificacoes_antigas,
            'gerar_relatorio_saude': scheduler._gerar_relatorio_saude
        }

        if job_request.function_name not in available_functions:
            raise ValueError(f"Função '{job_request.function_name}' não disponível")

        # Cria o trigger baseado no tipo
        if job_request.trigger_type == 'interval':
            trigger = IntervalTrigger(**job_request.trigger_config)
        elif job_request.trigger_type == 'cron':
            trigger = CronTrigger(**job_request.trigger_config)
        else:
            raise ValueError(f"Tipo de trigger '{job_request.trigger_type}' não suportado")

        scheduler.add_custom_job(
            func=available_functions[job_request.function_name],
            trigger=trigger,
            job_id=job_request.job_id,
            name=job_request.name
        )

        logger.info(f"Tarefa customizada '{job_request.name}' adicionada com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao adicionar tarefa customizada: {str(e)}")
        return False

def remove_job(db: Session, job_id: str) -> bool:
    """Remove uma tarefa do scheduler"""
    try:
        from .scheduler_service import get_scheduler_service

        scheduler = get_scheduler_service()
        scheduler.remove_job(job_id)

        logger.info(f"Tarefa '{job_id}' removida com sucesso")
        return True

    except Exception as e:
        logger.error(f"Erro ao remover tarefa: {str(e)}")
        return False

def gerar_relatorio_saude_sistema(db: Session) -> schemas.RelatorioSaudeSchema:
    """Gera relatório de saúde do sistema"""
    try:
        # Coleta estatísticas do sistema
        clientes_ativos = db.query(models.Cliente).filter(models.Cliente.ativo == True).count()
        usuarios_ativos = db.query(models.Usuario).filter(models.Usuario.ativo == True).count()
        indicadores_customizados = db.query(models.IndicadorCustomizado).filter(
            models.IndicadorCustomizado.ativo == True
        ).count()
        notificacoes_nao_lidas = db.query(models.Notificacao).filter(
            models.Notificacao.lida == False
        ).count()
        importacoes_hoje = db.query(models.Importacao).filter(
            models.Importacao.criado_em >= datetime.now().date()
        ).count()

        # Determina status do sistema
        status_sistema = "saudável"
        if notificacoes_nao_lidas > 100:
            status_sistema = "atenção"
        if importacoes_hoje == 0:
            status_sistema = "alerta"

        return schemas.RelatorioSaudeSchema(
            timestamp=datetime.now(),
            clientes_ativos=clientes_ativos,
            usuarios_ativos=usuarios_ativos,
            indicadores_customizados=indicadores_customizados,
            notificacoes_nao_lidas=notificacoes_nao_lidas,
            importacoes_hoje=importacoes_hoje,
            status_sistema=status_sistema
        )

    except Exception as e:
        logger.error(f"Erro ao gerar relatório de saúde: {str(e)}")
        return schemas.RelatorioSaudeSchema(
            timestamp=datetime.now(),
            clientes_ativos=0,
            usuarios_ativos=0,
            indicadores_customizados=0,
            notificacoes_nao_lidas=0,
            importacoes_hoje=0,
            status_sistema="erro"
        )

# ==================== FUNÇÕES PARA CACHE E MATERIALIZAÇÃO ====================

def get_cache_stats(db: Session) -> schemas.CacheStatsSchema:
    """Retorna estatísticas do cache"""
    try:
        from .cache_service import get_cache_service

        cache = get_cache_service()
        stats = cache.get_cache_stats()

        # Calcula hit ratio se disponível
        if 'keyspace_hits' in stats and 'keyspace_misses' in stats:
            total_requests = stats['keyspace_hits'] + stats['keyspace_misses']
            if total_requests > 0:
                stats['hit_ratio'] = stats['keyspace_hits'] / total_requests

        return schemas.CacheStatsSchema(**stats)

    except Exception as e:
        logger.error(f"Erro ao obter estatísticas do cache: {str(e)}")
        return schemas.CacheStatsSchema(
            type="error",
            total_keys=0,
            memory_usage="0B"
        )

def invalidate_cache(db: Session, request: schemas.CacheInvalidationRequest) -> schemas.CacheInvalidationResponse:
    """Invalida entradas do cache baseado nos critérios fornecidos"""
    try:
        from .cache_service import get_cache_service

        cache = get_cache_service()
        invalidated_keys = 0

        if request.pattern:
            # Invalida por padrão específico
            invalidated_keys = cache.invalidate_pattern(request.pattern)
        elif request.metric_type:
            # Invalida por tipo de métrica
            invalidated_keys = cache.invalidate_pattern(request.metric_type)
        elif request.cliente_id:
            # Invalida por cliente
            invalidated_keys = cache.invalidate_pattern(f"*cliente_id:{request.cliente_id}*")
        elif request.usuario_id:
            # Invalida por usuário
            invalidated_keys = cache.invalidate_pattern(f"*usuario_id:{request.usuario_id}*")
        else:
            raise ValueError("Pelo menos um critério de invalidação deve ser fornecido")

        message = f"Invalidadas {invalidated_keys} entradas do cache"
        logger.info(message)

        return schemas.CacheInvalidationResponse(
            invalidated_keys=invalidated_keys,
            message=message
        )

    except Exception as e:
        logger.error(f"Erro ao invalidar cache: {str(e)}")
        return schemas.CacheInvalidationResponse(
            invalidated_keys=0,
            message=f"Erro: {str(e)}"
        )

def materialize_metrics(db: Session, request: schemas.MaterializationRequest) -> schemas.MaterializationResponse:
    """Pré-calcula e materializa métricas no cache"""
    import time
    from .cache_service import get_cached_metrics_service

    start_time = time.time()
    processed_metrics = 0
    cached_entries = 0
    errors = []

    try:
        cached_service = get_cached_metrics_service(db)

        # Define período padrão se não fornecido
        if not request.data_inicio:
            request.data_inicio = datetime.now() - timedelta(days=30)
        if not request.data_fim:
            request.data_fim = datetime.now()

        # Busca clientes para processar
        if request.cliente_id:
            clientes = [db.query(models.Cliente).filter(models.Cliente.id == request.cliente_id).first()]
        else:
            clientes = db.query(models.Cliente).filter(models.Cliente.ativo == True).all()

        for cliente in clientes:
            if not cliente:
                continue

            # Busca usuários do cliente
            usuarios = db.query(models.Usuario).filter(
                models.Usuario.cliente_id == cliente.id,
                # models.Usuario.ativo == True # Uncomment if User model has 'ativo'
            ).all()

            for usuario in usuarios:
                for metric_type in request.metric_types:
                    try:
                        if metric_type == 'metricas_comparativas':
                            filtros = schemas.FiltrosDashboard(
                                data_inicio=request.data_inicio.date() if isinstance(request.data_inicio, datetime) else request.data_inicio,
                                data_fim=request.data_fim.date() if isinstance(request.data_fim, datetime) else request.data_fim
                            )
                            cached_service.get_metricas_comparativas_cached(
                                usuario_id=usuario.id,
                                filtros=filtros
                            )
                            cached_entries += 1

                        elif metric_type == 'kpis_dinamicos':
                            cached_service.get_kpis_dinamicos_cached(usuario.id)
                            cached_entries += 1

                        elif metric_type == 'vendas_categoria':
                            cached_service.get_vendas_por_categoria_cached(usuario.id)
                            cached_entries += 1

                        processed_metrics += 1

                    except Exception as e:
                        error_msg = f"Erro ao processar {metric_type} para usuário {usuario.id}: {str(e)}"
                        errors.append(error_msg)
                        logger.error(error_msg)

        processing_time = time.time() - start_time

        logger.info(f"Materialização concluída: {processed_metrics} métricas processadas, "
                   f"{cached_entries} entradas em cache, {processing_time:.2f}s")

        return schemas.MaterializationResponse(
            processed_metrics=processed_metrics,
            cached_entries=cached_entries,
            processing_time_seconds=round(processing_time, 2),
            errors=errors
        )

    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Erro na materialização: {str(e)}"
        logger.error(error_msg)

        return schemas.MaterializationResponse(
            processed_metrics=processed_metrics,
            cached_entries=cached_entries,
            processing_time_seconds=round(processing_time, 2),
            errors=[error_msg]
        )

def get_metricas_comparativas_cached(
    db: Session,
    usuario_id: int,
    filtros: schemas.FiltrosDashboard
) -> List[schemas.MetricaComparativa]:
    """Versão com cache das métricas comparativas"""
    try:
        from .cache_service import get_cached_metrics_service

        cached_service = get_cached_metrics_service(db)
        return cached_service.get_metricas_comparativas_cached(
            usuario_id=usuario_id,
            filtros=filtros
        )

    except Exception as e:
        logger.error(f"Erro ao obter métricas comparativas com cache: {str(e)}")
        # Fallback para versão sem cache
        return get_metricas_comparativas(
            db=db,
            usuario_id=usuario_id,
            filtros=filtros
        )

def get_kpis_dinamicos_cached(db: Session, usuario_id: int) -> List[schemas.Kpi]:
    """Versão com cache dos KPIs dinâmicos"""
    try:
        from .cache_service import get_cached_metrics_service

        cached_service = get_cached_metrics_service(db)
        return cached_service.get_kpis_dinamicos_cached(usuario_id)

    except Exception as e:
        logger.error(f"Erro ao obter KPIs dinâmicos com cache: {str(e)}")
        # Fallback para versão sem cache
        return get_kpis_dinamicos(db=db, usuario_id=usuario_id)

def get_vendas_por_categoria_cached(db: Session, usuario_id: int) -> List[schemas.VendasCategoria]:
    """Versão com cache das vendas por categoria"""
    try:
        from .cache_service import get_cached_metrics_service

        cached_service = get_cached_metrics_service(db)
        return cached_service.get_vendas_por_categoria_cached(usuario_id)

    except Exception as e:
        logger.error(f"Erro ao obter vendas por categoria com cache: {str(e)}")
        # Fallback para versão sem cache
        return get_vendas_por_categoria(db=db, usuario_id=usuario_id)

# ===============================
# CRUD DE INTEGRAÇÕES
# ===============================

def get_integracao_config(db: Session, cliente_id: int, connector_key: str) -> Optional[models.IntegracaoCliente]:
    """Busca a configuração de uma integração específica para um cliente."""
    return db.query(models.IntegracaoCliente).filter(
        models.IntegracaoCliente.cliente_id == cliente_id,
        models.IntegracaoCliente.connector_key == connector_key
    ).first()

def get_integracoes_por_cliente(db: Session, cliente_id: int) -> List[models.IntegracaoCliente]:
    """Lista todas as configurações de integração de um cliente."""
    return db.query(models.IntegracaoCliente).filter(
        models.IntegracaoCliente.cliente_id == cliente_id
    ).all()

def create_or_update_integracao(
    db: Session,
    cliente_id: int,
    connector_key: str,
    config_in: schemas.IntegracaoConfigCreate
) -> models.IntegracaoCliente:
    """Cria uma nova configuração de integração ou atualiza uma existente."""

    db_config = get_integracao_config(db, cliente_id, connector_key)

    if db_config:
        # Atualiza a existente
        db_config.credentials = config_in.credentials
        db_config.enabled = config_in.enabled
        db_config.auth_type = config_in.auth_type
    else:
        # Cria uma nova
        db_config = models.IntegracaoCliente(
            cliente_id=cliente_id,
            connector_key=connector_key,
            credentials=config_in.credentials,
            enabled=config_in.enabled,
            auth_type=config_in.auth_type
        )
        db.add(db_config)

    try:
        db.commit()
        db.refresh(db_config)
        return db_config
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erro ao salvar configuração: {e}")