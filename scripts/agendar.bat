@echo off
REM ---------------------------------------------------------------------------
REM Cria as duas tarefas agendadas. Execute COMO ADMINISTRADOR.
REM As tarefas rodam com a conta conectada. Para rodar com o usuario
REM desconectado, ajuste depois no Agendador de Tarefas (precisa de senha).
REM ---------------------------------------------------------------------------
setlocal
set RAIZ=%~dp0..
for %%I in ("%RAIZ%") do set RAIZ=%%~fI

echo Tarefas que serao criadas:
echo   "docauto - processar"     a cada 10 minutos
echo   "docauto - enviar"        a cada 15 minutos
echo Raiz: %RAIZ%
echo.
choice /M "Confirma"
if errorlevel 2 exit /b 1

schtasks /Create /TN "docauto - processar" /TR "\"%RAIZ%\scripts\processar.bat\"" /SC MINUTE /MO 10 /F
schtasks /Create /TN "docauto - enviar"    /TR "\"%RAIZ%\scripts\enviar.bat\""    /SC MINUTE /MO 15 /F

echo.
echo Criadas. Confira em: taskschd.msc
echo IMPORTANTE: rode os dois .bat na mao com esta mesma conta antes de confiar
echo nas tarefas - o erro mais comum e a conta nao ter acesso ao \\SERVIDOR.
endlocal
