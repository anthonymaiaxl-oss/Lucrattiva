@echo off
REM ---------------------------------------------------------------------------
REM Instalacao no servidor. Rode UMA vez, com a conta que vai operar.
REM Nao apaga nada: se algo ja existe, e mantido.
REM ---------------------------------------------------------------------------
setlocal
set RAIZ=%~dp0..
cd /d "%RAIZ%"

echo [1/5] conferindo Python...
python --version || (echo Instale Python 3.11+ e marque "Add to PATH" & exit /b 1)

echo [2/5] criando ambiente virtual...
if not exist ".venv" python -m venv .venv
call .venv\Scripts\activate.bat

echo [3/5] instalando dependencias...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo [4/5] criando config, cadastro e pastas...
python -m docauto init

echo [5/5] verificando o ambiente...
python -m docauto doutor
set RESULTADO=%ERRORLEVEL%

echo.
echo ---------------------------------------------------------------------------
if %RESULTADO% NEQ 0 (
  echo Ainda ha erros acima. Edite config\config.yaml e rode:
  echo     .venv\Scripts\activate ^&^& python -m docauto doutor
) else (
  echo Ambiente pronto. Proximos passos:
  echo   1. preencher data\empresas.csv com seus clientes
  echo   2. python -m docauto validar
  echo   3. python -m docauto diagnosticar --entrada C:\amostras --texto C:\amostras\_texto
  echo   4. scripts\agendar.bat  ^(como administrador^)
)
echo ---------------------------------------------------------------------------
endlocal
exit /b %RESULTADO%
