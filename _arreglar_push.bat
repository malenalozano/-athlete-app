@echo off
setlocal
cd /d "%~dp0"
echo === Limpiando locks e index corrupto...
if exist .git\index.lock del /F /Q .git\index.lock 2>nul
if exist .git\index del /F /Q .git\index 2>nul
git reset --mixed HEAD 2>nul
echo === Estado:
git status --short
echo.
echo === Commit y push...
git config core.autocrlf input
git add src\core\styles.py src\core\navbar.py src\components\dnd_board_static\index.html pages\02_plan.py pages\01_dashboard.py src\core\zonas_ritmo.py
git commit -m "fix(ui): ancho completo, navbar responsive, plan-board scroll movil"
git pull --rebase origin main 2>nul
git push origin main
echo.
echo === HECHO. Pulsa una tecla para cerrar.
pause
