"""
Sistema ALPR UNIPIAGET - Web Module
API REST com FastAPI para gerenciamento do sistema ALPR

Autor: Sistema ALPR
Instituição: Universidade Jean Piaget de Moçambique
Curso: Engenharia Electrónica e de Telecomunicações
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
import os
import sys
from pathlib import Path

# Adiciona diretório ao path para imports absolutos
current_dir = Path(__file__).resolve().parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

# Importa configuração do banco
from web_module.database import init_db, verificar_conexao

# Importa rotas
from web_module.routes import auth, veiculos, proprietarios, registros, dashboard, relatorios


# ============================================================================
# CONFIGURAÇÃO DA APLICAÇÃO
# ============================================================================

app = FastAPI(
    title="Sistema ALPR UNIPIAGET",
    description="API REST para Sistema de Reconhecimento Automático de Placas Veiculares",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# ============================================================================
# MIDDLEWARE - CORS
# ============================================================================

# Permitir requisições do módulo Desktop e frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://localhost:3000",
        "http://127.0.0.1:8000",
        "*"  # Em produção, especificar origens exatas
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# ARQUIVOS ESTÁTICOS E TEMPLATES
# ============================================================================

# Diretório base do módulo web
BASE_DIR = Path(__file__).resolve().parent

# Configurar arquivos estáticos (CSS, JS, imagens)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Configurar templates Jinja2
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ============================================================================
# ROTAS DA API (v1)
# ============================================================================

# Prefixo: /api/v1
API_V1_PREFIX = "/api/v1"

app.include_router(auth.router, prefix=API_V1_PREFIX, tags=["Autenticação"])
app.include_router(veiculos.router, prefix=API_V1_PREFIX, tags=["Veículos"])
app.include_router(proprietarios.router, prefix=API_V1_PREFIX, tags=["Proprietários"])
app.include_router(registros.router, prefix=API_V1_PREFIX, tags=["Registros de Acesso"])
app.include_router(dashboard.router, prefix=API_V1_PREFIX, tags=["Dashboard"])
app.include_router(relatorios.router, prefix=API_V1_PREFIX, tags=["Relatórios"])


# ============================================================================
# ROTAS WEB (HTML)
# ============================================================================

@app.get("/", response_class=HTMLResponse, tags=["Web"])
async def index(request: Request):
    """Página inicial do dashboard"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse, tags=["Web"])
async def login_page(request: Request):
    """Página de login"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/veiculos", response_class=HTMLResponse, tags=["Web"])
async def veiculos_page(request: Request):
    """Página de gestão de veículos"""
    return templates.TemplateResponse("veiculos.html", {"request": request})


@app.get("/proprietarios", response_class=HTMLResponse, tags=["Web"])
async def proprietarios_page(request: Request):
    """Página de gestão de proprietários"""
    return templates.TemplateResponse("proprietarios.html", {"request": request})


@app.get("/registros", response_class=HTMLResponse, tags=["Web"])
async def registros_page(request: Request):
    """Página de histórico de registros"""
    return templates.TemplateResponse("registros.html", {"request": request})


@app.get("/relatorios", response_class=HTMLResponse, tags=["Web"])
async def relatorios_page(request: Request):
    """Página de relatórios"""
    return templates.TemplateResponse("relatorios.html", {"request": request})


@app.get("/usuarios", response_class=HTMLResponse, tags=["Web"])
async def usuarios_page(request: Request):
    """Página de gestão de usuários (admin e gestor de sistema)"""
    return templates.TemplateResponse("usuarios.html", {"request": request})


# ============================================================================
# EVENTOS DO CICLO DE VIDA
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Executado quando a aplicação inicia
    - Verifica conexão com banco
    - Cria tabelas se não existirem
    """
    print("[INICIO] Iniciando Sistema ALPR UNIPIAGET...")

    # Verifica conexão com banco
    if verificar_conexao():
        print("[OK] Conexao com banco de dados estabelecida")
    else:
        print("[ERRO] Nao foi possivel conectar ao banco de dados")
        return

    # Inicializa banco (cria tabelas se não existirem)
    try:
        init_db(criar_dados_exemplo=True)
        print("[OK] Banco de dados inicializado")
    except Exception as e:
        print(f"[ERRO] Erro ao inicializar banco: {e}")

    print("[OK] Sistema ALPR pronto para uso!")
    print(f"[INFO] Documentacao API: http://localhost:8000/api/docs")
    print(f"[INFO] Dashboard Web: http://localhost:8000/")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a aplicação é encerrada"""
    print("[SHUTDOWN] Encerrando Sistema ALPR UNIPIAGET...")


# ============================================================================
# ROTA DE SAÚDE
# ============================================================================

@app.get("/health", tags=["Sistema"])
async def health_check():
    """
    Verifica saúde da aplicação

    Returns:
        Status da aplicação e conexão com banco
    """
    db_conectado = verificar_conexao()

    return {
        "status": "ok" if db_conectado else "degraded",
        "servico": "Sistema ALPR UNIPIAGET",
        "versao": "1.0.0",
        "banco_dados": "conectado" if db_conectado else "desconectado"
    }


@app.get("/api/info", tags=["Sistema"])
async def api_info():
    """
    Informações sobre a API

    Returns:
        Metadados da API
    """
    return {
        "nome": "Sistema ALPR UNIPIAGET",
        "versao": "1.0.0",
        "descricao": "API REST para Sistema de Reconhecimento Automático de Placas Veiculares",
        "instituicao": "Universidade Jean Piaget de Moçambique",
        "curso": "Engenharia Electrónica e de Telecomunicações",
        "endpoints": {
            "documentacao": "/api/docs",
            "documentacao_alternativa": "/api/redoc",
            "openapi": "/api/openapi.json",
            "saude": "/health"
        }
    }


# ============================================================================
# TRATAMENTO DE ERROS
# ============================================================================

@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handler para páginas não encontradas"""
    if request.url.path.startswith("/api/"):
        return {
            "erro": "Endpoint não encontrado",
            "path": request.url.path
        }
    else:
        return templates.TemplateResponse(
            "404.html",
            {"request": request},
            status_code=404
        )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handler para erros internos"""
    return {
        "erro": "Erro interno do servidor",
        "mensagem": "Ocorreu um erro inesperado. Contate o administrador."
    }


# ============================================================================
# EXECUÇÃO (para desenvolvimento)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    # Configurações de desenvolvimento
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Auto-reload em desenvolvimento
        log_level="info"
    )
