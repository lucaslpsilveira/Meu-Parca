@echo off
REM ============================================================
REM  Retoma um treino interrompido (queda de energia, reinício do
REM  Windows Update...) a partir do último checkpoint salvo.
REM  Não refaz preprocess/extract e não move a pasta do modelo.
REM  Uso:  continuar.bat <voz> [epocas] [batch]
REM  Use os MESMOS valores de epocas/batch do treino original.
REM ============================================================
setlocal

set VOZ=%~1
set EPOCAS=%~2
set BATCH=%~3
if "%VOZ%"=="" (
    echo Uso: continuar.bat ^<voz^> [epocas] [batch]
    exit /b 1
)
REM Configuração: config.env ao lado deste script (gerado pelo scripts/enviar.sh a partir do .env)
set APPLIO=C:\Applio
set SR=40000
set EPOCAS_PADRAO=300
set BATCH_PADRAO=4
set SALVAR=25
if exist "%~dp0config.env" for /f "usebackq eol=# tokens=1,* delims==" %%a in ("%~dp0config.env") do set "%%a=%%b"
set BASE=%~dp0
if "%BASE:~-1%"=="\" set BASE=%BASE:~0,-1%
if "%EPOCAS%"=="" set EPOCAS=%EPOCAS_PADRAO%
if "%BATCH%"=="" set BATCH=%BATCH_PADRAO%

set PY=%APPLIO%\env\python.exe
set LOG=%BASE%\logs\%VOZ%_treino.log

if not exist "%APPLIO%\logs\%VOZ%\sliced_audios" (
    echo Nao ha treino anterior de %VOZ% para continuar. Use treinar.bat %VOZ%
    exit /b 1
)

cd /d "%APPLIO%"
echo. >> "%LOG%"
echo ==== %DATE% %TIME% CONTINUANDO: voz=%VOZ% epocas=%EPOCAS% batch=%BATCH% ==== >> "%LOG%"

echo [3/4] Train (continuando do ultimo checkpoint) - acompanhe em %LOG%
"%PY%" core.py train --model-name %VOZ% --sample-rate %SR% --total-epoch %EPOCAS% --batch-size %BATCH% --save-every-epoch %SALVAR% --save-every-weights --gpu 0 --pretrained --vocoder HiFi-GAN --index-algorithm Auto >> "%LOG%" 2>&1 || goto :erro

echo [4/4] Index...
echo [4/4] Index >> "%LOG%"
"%PY%" core.py index --model-name %VOZ% --index-algorithm Auto >> "%LOG%" 2>&1 || goto :erro

echo ==== %DATE% %TIME% CONCLUIDO ==== >> "%LOG%"
echo Concluido. Modelo em %APPLIO%\logs\%VOZ%
exit /b 0

:erro
echo ==== %DATE% %TIME% ERRO (veja acima) ==== >> "%LOG%"
echo ERRO - veja %LOG%
exit /b 1
