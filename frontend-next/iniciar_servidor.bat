@echo off
setlocal enabledelayedexpansion
title Iniciando VYZOR Dashboard

echo ===================================
echo Iniciando o servidor VYZOR Dashboard
echo ===================================
echo.

REM Definir caminhos relativos ao diretorio do script
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%venv"
set "PYTHON_EXE=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXE=%VENV_DIR%\Scripts\pip.exe"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%requirements.txt"
set "APP_FILE=%SCRIPT_DIR%app.py"

echo [INFO] Verificando instalacao do Python...

REM Tentar diferentes formas de encontrar Python
set "PYTHON_CMD="
set "PYTHON_VERSION="

REM 1. Tentar py launcher (recomendado)
where py >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [INFO] Python launcher 'py' encontrado
    set "PYTHON_CMD=py -3"
    for /f "tokens=*" %%i in ('py -3 --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    goto :python_found
)

REM 2. Tentar python3
where python3 >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [INFO] Comando 'python3' encontrado
    set "PYTHON_CMD=python3"
    for /f "tokens=*" %%i in ('python3 --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    goto :python_found
)

REM 3. Tentar python
where python >nul 2>&1
if !ERRORLEVEL! EQU 0 (
    echo [INFO] Comando 'python' encontrado
    set "PYTHON_CMD=python"
    for /f "tokens=*" %%i in ('python --version 2^>^&1') do set "PYTHON_VERSION=%%i"
    goto :python_found
)

REM Python nao encontrado
echo [ERRO] Python nao foi encontrado no sistema!
echo.
echo Por favor, instale o Python 3.7+ de uma das seguintes formas:
echo 1. Baixe do site oficial: https://www.python.org/downloads/
echo 2. Instale via Microsoft Store (Windows 10/11)
echo 3. Use um gerenciador de pacotes como Chocolatey ou Scoop
echo.
echo Certifique-se de marcar "Add Python to PATH" durante a instalacao.
echo.
echo Pressione qualquer tecla para sair...
pause >nul
exit /b 1

:python_found
echo [INFO] !PYTHON_VERSION! detectado
echo.

REM Verificar se o ambiente virtual existe
if not exist "%VENV_DIR%" (
    echo [INFO] Ambiente virtual nao encontrado. Criando novo ambiente...
    !PYTHON_CMD! -m venv "%VENV_DIR%"
    if !ERRORLEVEL! NEQ 0 (
        echo [ERRO] Falha ao criar ambiente virtual!
        echo Verifique se o modulo venv esta disponivel.
        echo Pressione qualquer tecla para sair...
        pause >nul
        exit /b 1
    )
    echo [INFO] Ambiente virtual criado com sucesso!
) else (
    echo [INFO] Ambiente virtual encontrado em: %VENV_DIR%
)

REM Verificar se o Python do venv existe
if not exist "%PYTHON_EXE%" (
    echo [ERRO] Executavel do Python nao encontrado no ambiente virtual!
    echo Recriando ambiente virtual...
    rmdir /s /q "%VENV_DIR%" 2>nul
    !PYTHON_CMD! -m venv "%VENV_DIR%"
    if !ERRORLEVEL! NEQ 0 (
        echo [ERRO] Falha ao recriar ambiente virtual!
        echo Pressione qualquer tecla para sair...
        pause >nul
        exit /b 1
    )
)

REM Verificar se requirements.txt existe
if not exist "%REQUIREMENTS_FILE%" (
    echo [ERRO] Arquivo requirements.txt nao encontrado!
    echo Certifique-se de que o arquivo esta no mesmo diretorio do script.
    echo Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

REM Atualizar pip primeiro
echo [INFO] Atualizando pip...
"%PYTHON_EXE%" -m pip install --upgrade pip >nul 2>&1

REM Instalar/atualizar dependencias
echo [INFO] Instalando/atualizando dependencias...
"%PYTHON_EXE%" -m pip install -r "%REQUIREMENTS_FILE%"
if !ERRORLEVEL! NEQ 0 (
    echo [ERRO] Falha ao instalar dependencias!
    echo Verifique sua conexao com a internet e tente novamente.
    echo Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

REM Verificar se app.py existe
if not exist "%APP_FILE%" (
    echo [ERRO] Arquivo app.py nao encontrado!
    echo Certifique-se de que o arquivo esta no mesmo diretorio do script.
    echo Pressione qualquer tecla para sair...
    pause >nul
    exit /b 1
)

echo.
echo [INFO] Todas as dependencias foram instaladas com sucesso!
echo.
echo ===================================
echo Iniciando o servidor...
echo ===================================
echo.
echo IMPORTANTE: Acesse:
echo     http://localhost:5000?test=true    (Modo de teste automatico)
echo     http://localhost:5000              (Modo normal)
echo.
echo Para encerrar o servidor, pressione CTRL+C
echo.

REM Aguardar um pouco antes de abrir o navegador
timeout /t 2 /nobreak >nul

REM Abrir navegador automaticamente (modo normal)
start "" "http://localhost:5000/"

REM Iniciar o servidor Flask usando o ambiente virtual
echo [INFO] Executando aplicacao Flask...
"%PYTHON_EXE%" "%APP_FILE%"

REM Capturar codigo de saida
set "EXIT_CODE=!ERRORLEVEL!"
if !EXIT_CODE! NEQ 0 (
    echo.
    echo [ERRO] O servidor encerrou com codigo de erro: !EXIT_CODE!
    echo Verifique os logs acima para mais detalhes.
    echo.
)

echo.
echo Pressione qualquer tecla para sair...
pause >nul
exit /b !EXIT_CODE!