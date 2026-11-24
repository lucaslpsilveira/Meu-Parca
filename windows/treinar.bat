@echo off
REM ============================================================
REM  Treino de voz RVC (Applio) - projeto
REM  Uso:  treinar.bat <voz> [epocas] [batch]
REM  Ex.:  treinar.bat joao
REM        treinar.bat joao 400 4
REM  Dataset esperado em <pasta deste script>\dataset\<voz>\*.wav
REM ============================================================
setlocal

set VOZ=%~1
set EPOCAS=%~2
set BATCH=%~3
if "%VOZ%"=="" (
    echo Uso: treinar.bat ^<voz^> [epocas] [batch]
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
set DATASET=%BASE%\dataset\%VOZ%
set LOGDIR=%BASE%\logs
set LOG=%LOGDIR%\%VOZ%_treino.log

if not exist "%DATASET%" (
    echo Dataset nao encontrado: %DATASET%
    exit /b 1
)
if not exist "%LOGDIR%" mkdir "%LOGDIR%"

REM Guarda um treino anterior desta voz em vez de apagar
if exist "%APPLIO%\logs\%VOZ%" (
    set STAMP=%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%
    call :backup
)

cd /d "%APPLIO%"
echo ==== %DATE% %TIME% inicio: voz=%VOZ% epocas=%EPOCAS% batch=%BATCH% sr=%SR% ==== > "%LOG%"

echo [1/4] Preprocess...
echo [1/4] Preprocess >> "%LOG%"
"%PY%" core.py preprocess --model-name %VOZ% --dataset-path "%DATASET%" --sample-rate %SR% --cut-preprocess Automatic --normalization-mode post >> "%LOG%" 2>&1 || goto :erro

echo [2/4] Extract (rmvpe + contentvec)...
echo [2/4] Extract >> "%LOG%"
"%PY%" core.py extract --model-name %VOZ% --f0-method rmvpe --embedder-model contentvec --sample-rate %SR% --gpu 0 >> "%LOG%" 2>&1 || goto :erro

echo [3/4] Train (%EPOCAS% epocas, batch %BATCH%) - acompanhe em %LOG%
echo [3/4] Train >> "%LOG%"
"%PY%" core.py train --model-name %VOZ% --sample-rate %SR% --total-epoch %EPOCAS% --batch-size %BATCH% --save-every-epoch %SALVAR% --save-every-weights --gpu 0 --pretrained --vocoder HiFi-GAN --index-algorithm Auto >> "%LOG%" 2>&1 || goto :erro

echo [4/4] Index...
echo [4/4] Index >> "%LOG%"
"%PY%" core.py index --model-name %VOZ% --index-algorithm Auto >> "%LOG%" 2>&1 || goto :erro

echo ==== %DATE% %TIME% CONCLUIDO ==== >> "%LOG%"
echo Concluido. Modelo em %APPLIO%\logs\%VOZ%
exit /b 0

:backup
set STAMP=%STAMP: =0%
move "%APPLIO%\logs\%VOZ%" "%APPLIO%\logs\%VOZ%_backup_%STAMP%" >nul
echo Treino anterior movido para logs\%VOZ%_backup_%STAMP%
exit /b 0

:erro
echo ==== %DATE% %TIME% ERRO (veja acima) ==== >> "%LOG%"
echo ERRO - veja %LOG%
exit /b 1
