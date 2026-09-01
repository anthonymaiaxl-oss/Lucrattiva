@echo off
REM ---------------------------------------------------------------------------
REM Envia a fila ao Express e concilia o que ja foi consumido.
REM Modo pasta_monitorada: agendar a cada 15 minutos.
REM Modo lote_manual:      agendar 1x por dia (ex.: 08h00) e avisar a equipe.
REM ---------------------------------------------------------------------------
set RAIZ=C:\CONTABIL\docauto
cd /d %RAIZ%
call .venv\Scripts\activate.bat
python -m docauto enviar       >> "%RAIZ%\data\registro\envio.log" 2>&1
python -m docauto envio-status >> "%RAIZ%\data\registro\envio.log" 2>&1
exit /b %ERRORLEVEL%
