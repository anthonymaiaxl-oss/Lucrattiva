@echo off
REM ---------------------------------------------------------------------------
REM Processa a pasta de entrada. Agendar a cada 10 minutos no Windows.
REM Ajuste RAIZ para o caminho da instalacao.
REM ---------------------------------------------------------------------------
set RAIZ=C:\CONTABIL\docauto
cd /d %RAIZ%
call .venv\Scripts\activate.bat
python -m docauto processar >> "%RAIZ%\data\registro\processar.log" 2>&1
exit /b %ERRORLEVEL%
