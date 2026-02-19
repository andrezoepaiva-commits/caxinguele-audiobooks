@echo off
REM Script de atalho para converter PDFs em audiobooks

echo ============================================================
echo     PDF2Audiobook - Conversor para Alexa
echo ============================================================
echo.

REM Verifica se foi passado um arquivo
if "%~1"=="" (
    echo ERRO: Arraste um arquivo PDF sobre este .bat
    echo.
    echo Ou use:
    echo   converter.bat "caminho\para\arquivo.pdf"
    echo.
    pause
    exit /b 1
)

REM Verifica se arquivo existe
if not exist "%~1" (
    echo ERRO: Arquivo nao encontrado: %~1
    echo.
    pause
    exit /b 1
)

echo Arquivo: %~1
echo.
echo Iniciando conversao...
echo (Isso pode demorar 30-60 minutos para livros grandes)
echo.

REM Executa conversão (sem upload por padrão, mais seguro)
python pipeline_mvp.py --pdf "%~1" --no-upload --verbose

echo.
echo ============================================================
echo.

if %ERRORLEVEL% EQU 0 (
    echo [OK] Conversao concluida!
    echo.
    echo Arquivos salvos em: audiobooks\
    echo.
    echo Para fazer upload no Google Drive, execute:
    echo   python pipeline_mvp.py --pdf "%~1"
) else (
    echo [ERRO] Conversao falhou!
    echo.
    echo Verifique os erros acima.
)

echo.
pause
