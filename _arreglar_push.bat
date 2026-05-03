@echo off
setlocal
cd /d "%~dp0"
echo === Limpiando locks e index corrupto...
if exist .git\index.lock del /F /Q .git\index.lock 2>nul
git update-index --refresh 2>nul
if errorlevel 1 (
  echo Index posiblemente corrupto. Reseteando...
  if exist .git\index del /F /Q .git\index 2>nul
  git reset --mixed HEAD 2>nul
)
echo === Estado:
git status --short
echo.
echo === Add + commit + push...
git config core.autocrlf input
git add src\core\navbar.py src\core\styles.py
git commit -m "fix(css): cargar GLOBAL_CSS desde navbar (subpaginas)"
git pull --rebase origin main 2>nul
git push origin main
echo.
echo === HECHO. Cierra esta ventana.
pause
