@echo off
setlocal
cd /d "%~dp0"
if exist .git\index.lock del /F /Q .git\index.lock 2>nul
git update-index --refresh 2>nul
if errorlevel 1 (
  if exist .git\index del /F /Q .git\index 2>nul
  git reset --mixed HEAD 2>nul
)
git config core.autocrlf input
git add pages\02_plan.py src\core\navbar.py
git commit -m "fix: normalize tipos legacy con sufijos + logo column ancho"
git pull --rebase origin main 2>nul
git push origin main
echo === HECHO. Cierra esta ventana.
pause
