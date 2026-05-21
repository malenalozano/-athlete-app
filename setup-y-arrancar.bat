@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "BACK=%ROOT%backend-fastapi"
set "FRONT=%ROOT%Figma"

echo.
echo === Proyecto Athlete - Arranque ===
echo.

REM Crear venv backend si no existe
if not exist "%BACK%\venv\Scripts\python.exe" (
    echo Creando entorno virtual backend...
    pushd "%BACK%"
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    popd
) else (
    echo Backend venv OK
)

REM Instalar dependencias frontend si falta node_modules
if not exist "%FRONT%\node_modules" (
    echo Instalando dependencias frontend... esto tarda 1-2 min
    pushd "%FRONT%"
    call npm install
    popd
) else (
    echo Frontend node_modules OK
)

echo.
echo Arrancando servidores...
echo.

start "Athlete Backend" cmd /k "cd /d %BACK% && venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
start "Athlete Frontend" cmd /k "cd /d %FRONT% && npm run dev"

echo.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo.
pause
