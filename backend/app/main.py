from fastapi import FastAPI, Depends, HTTPException, status, File, UploadFile, Request, APIRouter, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from fastapi.middleware.cors import CORSMiddleware
from datetime import timedelta
import pandas as pd
from fastapi.responses import PlainTextResponse, Response
import io
import os

from . import models, schemas, crud, auth, ai_service, validation_utils
from .export_utils import markdown_to_pdf_bytes, gerar_excel_relatorio
# CORREÇÃO: Importa get_db e get_read_db
from .database import SessionLocal, engine, get_db, get_read_db # [!code ++]

from .database import Base
if os.getenv("CREATE_DB_SCHEMA_ON_START", "true").lower() == "true":
    Base.metadata.create_all(bind=engine)

# Utilitário: resolvesubquery de importações por cliente (multi-tenant) ou usuário
def _importacoes_por_contexto(db: Session, usuario: models.Usuario, cliente_id_param: Optional[int]):
    # Se admin e cliente_id fornecido, usa esse cliente
    if cliente_id_param is not None and usuario.perfil == "admin":
        return db.query(models.Importacao.id) \
            .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
            .filter(models.Usuario.cliente_id == cliente_id_param) \
            .subquery()
    # Se usuário pertence a um cliente, filtra por cliente
    if usuario.cliente_id is not None:
        return db.query(models.Importacao.id) \
            .join(models.Usuario, models.Importacao.usuario_id == models.Usuario.id) \
            .filter(models.Usuario.cliente_id == usuario.cliente_id) \
            .subquery()
    # Caso legado: sem cliente, filtra por usuário
    return db.query(models.Importacao.id).filter(models.Importacao.usuario_id == usuario.id).subquery()

import contextlib

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    from .scheduler_service import get_scheduler_service
    ENABLE_JOBS = os.getenv("ENABLE_JOBS", "true").lower() == "true"
    if ENABLE_JOBS:
        scheduler = get_scheduler_service()
        if not scheduler.is_running:
            scheduler.start()
    try:
        yield
    finally:
        if ENABLE_JOBS:
            scheduler = get_scheduler_service()
            if scheduler.is_running:
                scheduler.stop()

app = FastAPI(
    title="VYZOR API",
    description="API para gestão integrada e automação de processos via IA.",
    version="1.3.1",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

# ===============================
# ROTAS DE INTEGRAÇÕES (F5)
# ==============================
from .routes.integrations import router as integrations_router
app.include_router(integrations_router)

# ==============================
# AUTENTICAÇÃO E RAIZ
# ==============================
@app.post("/login", response_model=schemas.Token, tags=["Autenticação"])
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.get_usuario_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.senha_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos", headers={"WWW-Authenticate": "Bearer"})
    crud.log_activity(db, usuario_id=user.id, acao="login")
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Bem-vindo à VYZOR API! Acesse /docs para a documentação interativa."}

# ===============================
# ROTAS DE ADMINISTRADOR
# ===============================
admin_router = APIRouter(prefix="/admin", tags=["Administração"], dependencies=[Depends(auth.get_current_admin_user)])

@admin_router.get("/dashboard/kpis", response_model=schemas.AdminKpiResponse)
def ler_kpis_globais(db: Session = Depends(get_read_db)): # [!code ++]
    return {"kpis": crud.get_kpis_globais(db)}

@admin_router.get("/atividades", response_model=schemas.AdminAtividadeResponse)
def ler_atividades_globais(skip: int = 0, limit: int = 50, db: Session = Depends(get_read_db)): # [!code ++]
    return {"atividades": crud.get_atividades_gerais(db, skip=skip, limit=limit)}

# --- ROTAS DE CONTROLE DO SCHEDULER ---
@admin_router.get("/scheduler/status", response_model=schemas.SchedulerStatusSchema)
def get_status_scheduler(db: Session = Depends(get_read_db)): # [!code ++]
    return crud.get_scheduler_status(db)

@admin_router.post("/scheduler/start")
def start_scheduler_manual(db: Session = Depends(get_db)): # Escrita/Controle
    if crud.start_scheduler(db):
        return {"message": "Scheduler iniciado com sucesso."}
    raise HTTPException(status_code=500, detail="Não foi possível iniciar o scheduler.")

@admin_router.post("/scheduler/stop")
def stop_scheduler_manual(db: Session = Depends(get_db)): # Escrita/Controle
    if crud.stop_scheduler(db):
        return {"message": "Scheduler parado com sucesso."}
    raise HTTPException(status_code=500, detail="Não foi possível parar o scheduler.")

@admin_router.post("/scheduler/jobs", response_model=dict)
def add_new_job(job_request: schemas.CustomJobRequest, db: Session = Depends(get_db)): # Escrita/Controle
    if crud.add_custom_job(db, job_request):
        return {"success": True, "message": f"Tarefa '{job_request.name}' adicionada com sucesso."}
    raise HTTPException(status_code=400, detail="Não foi possível adicionar a tarefa customizada.")

@admin_router.delete("/scheduler/jobs/{job_id}")
def remove_existing_job(job_id: str, db: Session = Depends(get_db)): # Escrita/Controle
    if crud.remove_job(db, job_id):
        return {"message": f"Tarefa '{job_id}' removida com sucesso."}
    raise HTTPException(status_code=404, detail=f"Tarefa '{job_id}' não encontrada ou não pôde ser removida.")
# --- FIM DAS ROTAS DO SCHEDULER ---

@admin_router.get("/usuarios/", response_model=List[schemas.Usuario])
def ler_todos_usuarios(skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db)): # [!code ++]
    return crud.get_usuarios(db, skip=skip, limit=limit)

@admin_router.put("/usuarios/{usuario_id}", response_model=schemas.Usuario)
def editar_usuario(usuario_id: int, usuario: schemas.UsuarioUpdate, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    db_usuario = crud.update_usuario(db, usuario_id=usuario_id, usuario_update=usuario, autor_id=admin.id)
    if db_usuario is None: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return db_usuario

@admin_router.delete("/usuarios/{usuario_id}", response_model=schemas.Usuario)
def remover_usuario(usuario_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    db_usuario = crud.delete_usuario(db, usuario_id=usuario_id, autor_id=admin.id)
    if db_usuario is None: raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return db_usuario

@admin_router.get("/departamentos/", response_model=List[schemas.Departamento])
def ler_departamentos(skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db)): # [!code ++]
    return crud.get_departamentos(db, skip=skip, limit=limit)

@admin_router.post("/departamentos/", response_model=schemas.Departamento, status_code=201)
def criar_departamento(departamento: schemas.DepartamentoCreate, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    return crud.create_departamento(db, departamento=departamento, autor_id=admin.id)

@admin_router.put("/departamentos/{departamento_id}", response_model=schemas.Departamento)
def editar_departamento(departamento_id: int, departamento: schemas.DepartamentoUpdate, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    db_departamento = crud.update_departamento(db, departamento_id=departamento_id, departamento_update=departamento, autor_id=admin.id)
    if db_departamento is None: raise HTTPException(status_code=404, detail="Departamento não encontrado")
    return db_departamento

@admin_router.delete("/departamentos/{departamento_id}", response_model=schemas.Departamento)
def remover_departamento(departamento_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    db_departamento = crud.delete_departamento(db, departamento_id=departamento_id, autor_id=admin.id)
    if db_departamento is None: raise HTTPException(status_code=404, detail="Departamento não encontrado")
    return db_departamento

@admin_router.put("/usuarios/{usuario_id}/departamento/{departamento_id}", response_model=schemas.Usuario)
def associar_usuario_a_departamento(usuario_id: int, departamento_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    return crud.associar_departamento_a_usuario(db, usuario_id=usuario_id, departamento_id=departamento_id, autor_id=admin.id)

@admin_router.get("/importacoes/", response_model=List[schemas.Importacao])
def ler_todas_importacoes(skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db)): # [!code ++]
    return crud.get_importacoes(db, skip=skip, limit=limit)

@admin_router.delete("/importacoes/{importacao_id}", response_model=schemas.Importacao)
def remover_importacao(importacao_id: int, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    db_importacao = crud.get_importacao(db, importacao_id)
    if not db_importacao:
        raise HTTPException(status_code=404, detail="Importação não encontrada")
    deleted = crud.delete_importacao(db, importacao_id=importacao_id, autor_id=admin.id)
    # Invalida caches do usuário dono da importação
    try:
        from . import cache
        cache.invalidate_usuario(db_importacao.usuario_id)
    except Exception:
        pass
    return deleted

# --- ROTAS DE CACHE ADMIN ---
@admin_router.get("/cache/stats", response_model=schemas.CacheStatsSchema)
def admin_cache_stats(db: Session = Depends(get_read_db)): # [!code ++]
    return crud.get_cache_stats(db)

@admin_router.post("/cache/invalidate", response_model=schemas.CacheInvalidationResponse)
def admin_cache_invalidate(request: schemas.CacheInvalidationRequest, db: Session = Depends(get_db)): # Escrita/Controle
    return crud.invalidate_cache(db, request)
# --- FIM ROTAS DE CACHE ADMIN ---

app.include_router(admin_router)

# ===============================
# GESTÃO DE USUÁRIOS (ROTAS GERAIS)
# ===============================
@app.post("/usuarios/", response_model=schemas.Usuario, status_code=201, tags=["Usuários e Departamentos"])
def criar_usuario_publico(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db), admin: models.Usuario = Depends(auth.get_current_admin_user)): # Escrita
    return crud.create_usuario(db=db, usuario=usuario, autor_id=admin.id)

@app.get("/usuarios/me", response_model=schemas.Usuario, tags=["Usuários e Departamentos"])
def read_users_me(current_user: models.Usuario = Depends(auth.get_current_user), db: Session = Depends(get_read_db)): # [!code ++]
    # Retorna o usuário logado, é uma operação de leitura
    return current_user

# ===============================
# FLUXO DE IMPORTAÇÃO (ETL COM IA)
# ===============================
@app.get("/importacoes/usuario", response_model=List[schemas.Importacao], tags=["Importação e ETL com IA"])
def listar_importacoes_usuario(skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # Leitura
    return crud.get_importacoes_usuario(db, usuario_id=current_user.id, skip=skip, limit=limit)

@app.post("/importacoes/", response_model=schemas.Importacao, status_code=201, tags=["Importação e ETL com IA"])
def criar_registro_importacao(importacao: schemas.ImportacaoCreate, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)): # Escrita
    return crud.create_importacao(db=db, importacao=importacao)

@app.post("/ai/classificar-e-inserir/{importacao_id}", response_model=schemas.ResultadoMultiTransformacao, tags=["Importação e ETL com IA"])
async def classificar_e_inserir_com_ia(importacao_id: int, file: UploadFile, db: Session = Depends(get_db), current_user: models.Usuario = Depends(auth.get_current_user)): # Escrita
    db_importacao = crud.get_importacao(db, importacao_id=importacao_id)
    if not db_importacao or (current_user.perfil != 'admin' and db_importacao.usuario_id != current_user.id):
        raise HTTPException(status_code=404, detail="ID de Importação não encontrado ou não pertence ao usuário.")
    try:
        conteudo = await file.read()
        df = pd.read_csv(io.BytesIO(conteudo)) if file.filename.endswith('.csv') else pd.read_excel(io.BytesIO(conteudo))
    except Exception as e: raise HTTPException(status_code=400, detail=f"Erro ao ler o arquivo: {e}")
    
    dados_completos = df.where(pd.notna(df), None).to_dict('records')
    colunas = df.columns.tolist()
    
    esquemas = {"financeiro": list(schemas.RegistroFinanceiroBase.model_fields.keys()), "produtos": list(schemas.RegistroProdutoBase.model_fields.keys()), "operacional": list(schemas.RegistroOperacionalBase.model_fields.keys())}
    
    dados = ai_service.classificar_e_transformar_dados_com_ia(colunas, dados_completos, esquemas)

    # Validação robusta por tabela
    registros_fin_raw = dados.get("financeiro", [])
    registros_prod_raw = dados.get("produtos", [])
    registros_oper_raw = dados.get("operacional", [])

    registros_financeiros_validos, rep_fin = validation_utils.validar_financeiro(registros_fin_raw)
    registros_produtos_validos, rep_prod = validation_utils.validar_produtos(registros_prod_raw)
    registros_operacionais_validos, rep_oper = validation_utils.validar_operacional(registros_oper_raw)

    # Atualiza contadores na importação
    db_importacao.total_registros = len(df)
    db_importacao.registros_validos = len(registros_financeiros_validos) + len(registros_produtos_validos) + len(registros_operacionais_validos)
    db_importacao.registros_invalidos = (len(registros_fin_raw) + len(registros_prod_raw) + len(registros_oper_raw)) - db_importacao.registros_validos
    db.commit()
    
    resultado = {
        "mensagem": "Dados classificados, validados e inseridos com sucesso!",
        "registros_financeiros_inseridos": crud.inserir_dados_financeiros_em_lote(db, registros_financeiros_validos, importacao_id),
        "registros_produtos_inseridos": crud.inserir_dados_produtos_em_lote(db, registros_produtos_validos, importacao_id),
        "registros_operacionais_inseridos": crud.inserir_dados_operacionais_em_lote(db, registros_operacionais_validos, importacao_id),
        "relatorio_validacao": {
            "financeiro": rep_fin,
            "produtos": rep_prod,
            "operacional": rep_oper,
        },
    }
    # Invalida caches de métricas para o usuário desta importação
    try:
        from . import cache
        cache.invalidate_usuario(db_importacao.usuario_id)
    except Exception:
        pass
    return resultado

# ===============================
# DASHBOARDS E RELATÓRIOS
# ===============================
@app.get("/dashboard/kpis", response_model=schemas.KpiResponse, tags=["Dashboard e Relatórios"])
def ler_kpis_dinamicos(db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    # NOTA: Otimização #2 (cache de KPI) já está implementada dentro de crud.get_kpis_dinamicos
    # A mudança aqui é usar get_read_db para usar a réplica de leitura.
    return {"kpis": crud.get_kpis_dinamicos(db, usuario_id=current_user.id)}

@app.get("/dashboard/vendas-por-categoria", response_model=schemas.VendasCategoriaResponse, tags=["Dashboard e Relatórios"])
def ler_vendas_por_categoria(db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    return {"dados_grafico": crud.get_vendas_por_categoria(db, usuario_id=current_user.id)}

@app.post("/dashboard/gerar-relatorio-ia", tags=["Dashboard e Relatórios"], response_class=PlainTextResponse)
def gerar_relatorio_ia(tipo_relatorio: str, db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if tipo_relatorio not in ["financeiro", "produtos", "operacional"]: raise HTTPException(status_code=400, detail="Tipo de relatório inválido.")
    
    if not crud.obter_dados_para_relatorio(db, current_user.id, tipo_relatorio): 
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar este tipo de relatório.")

    dados_formatados = crud.formatar_dados_para_relatorio(db, current_user.id, tipo_relatorio)
    return ai_service.gerar_relatorio_com_ia(tipo_relatorio, dados_formatados)

@app.post("/dashboard/exportar-relatorio-pdf", tags=["Dashboard e Relatórios"])
def exportar_relatorio_pdf(tipo_relatorio: str, db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if tipo_relatorio not in ["financeiro", "produtos", "operacional"]:
        raise HTTPException(status_code=400, detail="Tipo de relatório inválido.")
    
    if not crud.obter_dados_para_relatorio(db, current_user.id, tipo_relatorio):
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar este tipo de relatório.")

    dados_formatados = crud.formatar_dados_para_relatorio(db, current_user.id, tipo_relatorio)
    md_relatorio = ai_service.gerar_relatorio_com_ia(tipo_relatorio, dados_formatados)
    pdf_bytes = markdown_to_pdf_bytes(md_relatorio)
    headers = {"Content-Disposition": f"attachment; filename=relatorio_{tipo_relatorio}.pdf"}
    crud.log_activity(db, current_user.id, "exportação", "relatorios", None, None, {"tipo": tipo_relatorio, "formato": "pdf"})
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)

@app.post("/dashboard/exportar-relatorio-excel", tags=["Dashboard e Relatórios"])
def exportar_relatorio_excel(tipo_relatorio: str, db: Session = Depends(get_read_db), current_user: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if tipo_relatorio not in ["financeiro", "produtos", "operacional"]:
        raise HTTPException(status_code=400, detail="Tipo de relatório inválido.")

    dados_brutos = crud.obter_dados_para_relatorio(db, current_user.id, tipo_relatorio)
    if not dados_brutos:
        raise HTTPException(status_code=404, detail="Não há dados suficientes para gerar este tipo de relatório.")

    dados_formatados = crud.formatar_dados_para_relatorio(db, current_user.id, tipo_relatorio)
    md_relatorio = ai_service.gerar_relatorio_com_ia(tipo_relatorio, dados_formatados)
    
    xlsx_bytes = gerar_excel_relatorio(md_relatorio, dados_brutos, nome_planilha_dados=f"Dados {tipo_relatorio.capitalize()}")
    headers = {"Content-Disposition": f"attachment; filename=relatorio_{tipo_relatorio}.xlsx"}
    crud.log_activity(db, current_user.id, "exportação", "relatorios", None, None, {"tipo": tipo_relatorio, "formato": "excel"})
    return Response(content=xlsx_bytes, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

# ===============================
# DASHBOARDS INTERATIVOS AVANÇADOS
# ===============================
@app.get("/dashboard/filtros-disponiveis", response_model=schemas.FiltrosDisponiveis, tags=["Dashboard Interativo"])
def obter_filtros_disponiveis(
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    return crud.get_filtros_disponiveis(db, usuario_id=current_user.id)

@app.post("/dashboard/interativo", response_model=schemas.DashboardInterativo, tags=["Dashboard Interativo"])
def obter_dashboard_interativo(
    filtros: schemas.FiltrosDashboard,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    return crud.get_dashboard_interativo(db, usuario_id=current_user.id, filtros=filtros)

@app.post("/dashboard/grafico-receita-tempo", response_model=schemas.DadosGraficoLinha, tags=["Dashboard Interativo"]) 
def grafico_receita_tempo(
    filtros: schemas.FiltrosDashboard,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    importacoes_ctx = _importacoes_por_contexto(db, current_user, cliente_id)
    query_financeiro = db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_ctx))
    if filtros.data_inicio:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao >= filtros.data_inicio)
    if filtros.data_fim:
        query_financeiro = query_financeiro.filter(models.RegistroFinanceiro.data_transacao <= filtros.data_fim)
    return crud.get_grafico_receita_tempo(db, query_financeiro)

@app.post("/dashboard/grafico-vendas-categoria", response_model=schemas.DadosGraficoPizza, tags=["Dashboard Interativo"]) 
def grafico_vendas_categoria(
    filtros: schemas.FiltrosDashboard,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    importacoes_ctx = _importacoes_por_contexto(db, current_user, cliente_id)
    query_produtos = db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id.in_(importacoes_ctx))
    if filtros.data_inicio:
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda >= filtros.data_inicio)
    if filtros.data_fim:
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda <= filtros.data_fim)
    
    if filtros.categoria_produto and filtros.categoria_produto.lower() != 'null':
        query_produtos = query_produtos.filter(models.RegistroProduto.categoria_produto == filtros.categoria_produto)
    
    return crud.get_grafico_vendas_categoria(db, query_produtos)

@app.post("/dashboard/grafico-performance-colaboradores", response_model=schemas.DadosGraficoBarra, tags=["Dashboard Interativo"]) 
def grafico_performance_colaboradores(
    filtros: schemas.FiltrosDashboard,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    importacoes_ctx = _importacoes_por_contexto(db, current_user, cliente_id)
    query_operacional = db.query(models.RegistroOperacional).filter(models.RegistroOperacional.importacao_id.in_(importacoes_ctx))
    if filtros.data_inicio:
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento >= filtros.data_inicio)
    if filtros.data_fim:
        query_operacional = query_operacional.filter(models.RegistroOperacional.data_evento <= filtros.data_fim)
    
    if filtros.departamento and filtros.departamento.lower() != 'null':
        query_operacional = query_operacional.filter(models.RegistroOperacional.departamento == filtros.departamento)
    if filtros.colaborador and filtros.colaborador.lower() != 'null':
        query_operacional = query_operacional.filter(models.RegistroOperacional.nome_colaborador == filtros.colaborador)
    
    return crud.get_grafico_performance_colaboradores(db, query_operacional)

@app.post("/dashboard/top-produtos", response_model=List[Dict[str, Any]], tags=["Dashboard Interativo"]) 
def top_produtos(
    filtros: schemas.FiltrosDashboard,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    importacoes_ctx = _importacoes_por_contexto(db, current_user, cliente_id)
    query_produtos = db.query(models.RegistroProduto).filter(models.RegistroProduto.importacao_id.in_(importacoes_ctx))
    if filtros.data_inicio:
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda >= filtros.data_inicio)
    if filtros.data_fim:
        query_produtos = query_produtos.filter(models.RegistroProduto.data_venda <= filtros.data_fim)
    
    if filtros.categoria_produto and filtros.categoria_produto.lower() != 'null':
        query_produtos = query_produtos.filter(models.RegistroProduto.categoria_produto == filtros.categoria_produto)
    
    return crud.get_top_produtos_filtrados(db, query_produtos)

# ===============================
# ALERTAS E NOTIFICAÇÕES
# ===============================
@app.get("/notificacoes", tags=["Alertas e Notificações"], response_model=List[Dict[str, Any]])
def listar_notificacoes(
    somente_nao_lidas: bool = False,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    q = db.query(models.Notificacao).filter(models.Notificacao.usuario_id == current_user.id)
    if somente_nao_lidas:
        q = q.filter(models.Notificacao.lida == False)
    itens = q.order_by(models.Notificacao.criado_em.desc()).all()
    return [
        {
            "id": n.id, "titulo": n.titulo, "mensagem": n.mensagem, "tipo": n.tipo,
            "canal": n.canal, "prioridade": n.prioridade, "url_acao": n.url_acao,
            "lida": n.lida, "criado_em": n.criado_em.isoformat(),
        } for n in itens
    ]

@app.post("/notificacoes", status_code=201, tags=["Alertas e Notificações"])
def criar_notificacao(
    payload: schemas.NotificacaoCreateRequest = Body(
        ..., 
        examples={
            "Exemplo": {
                "value": {
                    "titulo": "Alerta de Performance",
                    "mensagem": "A receita do produto X caiu 15% esta semana.",
                    "tipo": "warning",
                    "canal": "in_app",
                    "prioridade": "alta",
                    "url_acao": "/dashboard/produtos/X",
                    "usuario_id": 1
                }
            }
        }
    ),
    db: Session = Depends(get_db), # Escrita
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    target_usuario_id = payload.usuario_id if current_user.perfil == "admin" and payload.usuario_id else current_user.id
    if not target_usuario_id:
        target_usuario_id = current_user.id
    
    n = models.Notificacao(
        usuario_id=target_usuario_id,
        titulo=payload.titulo,
        mensagem=payload.mensagem,
        tipo=payload.tipo,
        canal=payload.canal,
        prioridade=payload.prioridade,
        url_acao=payload.url_acao,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n

@app.put("/notificacoes/{notificacao_id}/ler", tags=["Alertas e Notificações"])
def marcar_notificacao_como_lida(
    notificacao_id: int,
    db: Session = Depends(get_db), # Escrita
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    n = db.query(models.Notificacao).filter(
        models.Notificacao.id == notificacao_id,
        models.Notificacao.usuario_id == current_user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    n.lida = True
    db.commit()
    db.refresh(n)
    return n

@app.delete("/notificacoes/{notificacao_id}", status_code=204, tags=["Alertas e Notificações"])
def deletar_notificacao(
    notificacao_id: int,
    db: Session = Depends(get_db), # Escrita
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    n = db.query(models.Notificacao).filter(
        models.Notificacao.id == notificacao_id,
        models.Notificacao.usuario_id == current_user.id
    ).first()
    if not n:
        raise HTTPException(status_code=404, detail="Notificação não encontrada")
    db.delete(n)
    db.commit()
    return Response(status_code=204)

@app.get("/notificacoes/preferencias", tags=["Alertas e Notificações"])
def obter_preferencias_notificacao(
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    p = db.query(models.PreferenciasNotificacao).filter(models.PreferenciasNotificacao.usuario_id == current_user.id).first()
    if not p:
        p = models.PreferenciasNotificacao(usuario_id=current_user.id)
        db.add(p)
        db.commit()
        db.refresh(p)
    return p

@app.put("/notificacoes/preferencias", tags=["Alertas e Notificações"])
def atualizar_preferencias_notificacao(
    payload: schemas.PreferenciasUpdateRequest = Body(
        ..., 
        examples={
            "Exemplo": {
                "value": {
                    "canal_email": True,
                    "receber_alertas_financeiros": True,
                    "limiar_queda_receita_percentual": 15.5
                }
            }
        }
    ),
    db: Session = Depends(get_db), # Escrita
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    p = db.query(models.PreferenciasNotificacao).filter(models.PreferenciasNotificacao.usuario_id == current_user.id).first()
    if not p:
        p = models.PreferenciasNotificacao(usuario_id=current_user.id)
        db.add(p)
    
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(p, key):
            setattr(p, key, value)
            
    db.commit()
    db.refresh(p)
    return p

# ===============================
# ANÁLISE PREDITIVA
# ===============================
@app.get("/analise-preditiva/modelos", tags=["Análise Preditiva"]) 
def listar_modelos_preditivos():
    return {
        "alvos": ["receita_mensal", "demanda_produto"],
        "modelos": [
            {"nome": "tendencia_linear", "descricao": "Previsão baseada em agregações e tendência linear simples"}
        ],
        "periodicidades": ["mensal", "semanal"]
    }

@app.post("/predict/receita", tags=["Análise Preditiva"])
def prever_receita(
    payload: schemas.PredictReceitaRequest = Body(
        ...,
        examples={
            "Exemplo": {
                "value": {
                    "periodicidade": "mensal",
                    "horizonte": 6,
                    "data_inicio": "2024-01-01",
                    "data_fim": "2024-12-31"
                }
            }
        }
    ),
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    periodicidade = payload.periodicidade
    horizonte = payload.horizonte
    data_inicio = payload.data_inicio
    data_fim = payload.data_fim

    importacoes_ctx = _importacoes_por_contexto(db, current_user, cliente_id)
    query = db.query(models.RegistroFinanceiro).filter(models.RegistroFinanceiro.importacao_id.in_(importacoes_ctx))
    if data_inicio:
        query = query.filter(models.RegistroFinanceiro.data_transacao >= data_inicio)
    if data_fim:
        query = query.filter(models.RegistroFinanceiro.data_transacao <= data_fim)

    registros = query.with_entities(models.RegistroFinanceiro.data_transacao, models.RegistroFinanceiro.receita).all()
    registros_validos = [r for r in registros if r[0] is not None]
    if len(registros_validos) < 2:
        raise HTTPException(status_code=404, detail="Sem dados financeiros suficientes (mínimo 2 pontos) para previsão.")

    df = pd.DataFrame([{"data": r[0], "valor": float(r[1] or 0)} for r in registros_validos])
    df = df.sort_values("data")
    df.set_index(pd.to_datetime(df["data"]), inplace=True)

    if periodicidade == "semanal":
        serie = df["valor"].resample("W").sum()
        fmt_label = lambda idx: idx.strftime("%Y-%W")
        freq = "W"
    else:
        serie = df["valor"].resample("M").sum()
        fmt_label = lambda idx: idx.strftime("%Y-%m")
        freq = "M"

    historico = [{"label": fmt_label(i), "valor": float(v)} for i, v in serie.items()]
    
    valores = serie.values
    slope = (valores[-1] - valores[0]) / (len(valores) - 1) if len(valores) >= 2 else 0.0

    last_index = serie.index[-1]
    previsao = []
    last_val = float(valores[-1])
    for i in range(1, horizonte + 1):
        next_index = pd.date_range(last_index, periods=i+1, freq=freq)[-1]
        y = max(0.0, last_val + slope * i)
        previsao.append({"label": fmt_label(next_index), "valor": float(y)})

    resumo = "Previsão baseada em tendência linear simples. Valores negativos são truncados a zero."
    return {
        "periodicidade": periodicidade, "horizonte": horizonte,
        "historico": historico, "previsao": previsao, "resumo": resumo,
    }

# ===============================
# INDICADORES, LIMIARES E INSIGHTS
# ===============================
router_indicadores = APIRouter(prefix="/clientes/{cliente_id}/indicadores", tags=["Indicadores Customizados"])

@router_indicadores.post("/", response_model=schemas.IndicadorCustomizado)
def criar_indicador_customizado(cliente_id: int, payload: schemas.IndicadorCustomizadoCreate, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.get_current_user)): # Escrita
    return crud.create_indicador_customizado(db, cliente_id, payload, autor_id=usuario.id)

@router_indicadores.get("/", response_model=List[schemas.IndicadorCustomizado])
def listar_indicadores(cliente_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db), usuario: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.list_indicadores_cliente(db, cliente_id, skip=skip, limit=limit)

@router_indicadores.post("/{indicador_id}/calcular", response_model=schemas.ValorIndicadorResponse)
def calcular_indicador(cliente_id: int, indicador_id: int, filtros: Optional[schemas.FiltrosDashboard] = Body(None), db: Session = Depends(get_read_db), usuario: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.calcular_indicador_customizado(db, cliente_id, indicador_id, filtros)

router_limiares = APIRouter(prefix="/clientes/{cliente_id}/limiares", tags=["Alertas e Notificações"])

@router_limiares.post("/", response_model=schemas.LimiarIndicador)
def criar_limiar(cliente_id: int, payload: schemas.LimiarIndicadorCreate, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.get_current_user)): # Escrita
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.create_limiar_indicador(db, cliente_id, payload, autor_id=usuario.id)

@router_limiares.get("/", response_model=List[schemas.LimiarIndicador])
def listar_limiares(cliente_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_read_db), usuario: models.Usuario = Depends(auth.get_current_user)): # [!code ++]
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.list_limiares_cliente(db, cliente_id, skip=skip, limit=limit)

@router_limiares.put("/{limiar_id}", response_model=schemas.LimiarIndicador)
def atualizar_limiar(cliente_id: int, limiar_id: int, payload: schemas.LimiarIndicadorUpdate, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.get_current_user)): # Escrita
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.update_limiar_indicador(db, cliente_id, limiar_id, payload, autor_id=usuario.id)

@router_limiares.delete("/{limiar_id}")
def remover_limiar(cliente_id: int, limiar_id: int, db: Session = Depends(get_db), usuario: models.Usuario = Depends(auth.get_current_user)): # Escrita
    if usuario.cliente_id != cliente_id and usuario.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado ao cliente")
    return crud.delete_limiar_indicador(db, cliente_id, limiar_id, autor_id=usuario.id)

router_insights = APIRouter(prefix="/insights", tags=["Insights"]) 

# --- ENDPOINT DE INSIGHTS ATUALIZADO PARA USAR IA ---
@router_insights.post("/catalogo", response_model=schemas.InsightCatalogoResponse)
async def post_catalogo_insights(
    filtros: Optional[schemas.FiltrosDashboard] = Body(None),
    db: Session = Depends(get_read_db), # [!code ++]
    current_user: models.Usuario = Depends(auth.get_current_user)
):
    """
    Gera um catálogo de insights usando IA com base nos dados filtrados do usuário.
    """
    try:
        # 1. Coletar dados para a IA (reutilizando a formatação dos relatórios)
        # Vamos agregar dados de todas as áreas para dar um contexto completo
        dados_fin = crud.formatar_dados_para_relatorio(db, current_user.id, "financeiro")
        dados_prod = crud.formatar_dados_para_relatorio(db, current_user.id, "produtos")
        dados_oper = crud.formatar_dados_para_relatorio(db, current_user.id, "operacional")
        
        dados_completos = f"""
        --- DADOS FINANCEIROS ---
        {dados_fin}
        
        --- DADOS DE PRODUTOS ---
        {dados_prod}
        
        --- DADOS OPERACIONAIS ---
        {dados_oper}
        """

        # 2. Chamar o novo serviço de IA para gerar insights (agora com user_id)
        insights_lista = ai_service.gerar_insights_com_ia(dados_completos, current_user.id) # [!code ++]
        
        # 3. Retornar no formato esperado pelo frontend
        return schemas.InsightCatalogoResponse(insights=insights_lista)

    except Exception as e:
        # Em caso de erro, retorna um insight de erro
        return schemas.InsightCatalogoResponse(insights=[{
            "tipo": "operacional",
            "titulo": "Erro ao Processar Insights",
            "resumo": f"Não foi possível gerar insights: {str(e)}",
            "prioridade": "alta",
            "metadados": {}
        }])
# --- FIM DA ATUALIZAÇÃO ---


app.include_router(router_indicadores)
app.include_router(router_limiares)
app.include_router(router_insights)

