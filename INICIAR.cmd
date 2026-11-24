@echo off
setlocal
pushd "%~dp0"
title Sistema de Gestion Hospitalaria
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import flask, waitress" >nul 2>&1
    if not errorlevel 1 goto ejecutar
)
python -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=python"
    goto preparar
)
py -3 -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>&1
if not errorlevel 1 (
    set "PYTHON=py -3"
    goto preparar
)
echo Necesitas Python 3.10 o posterior para ejecutar el codigo fuente.
echo Para usarlo sin instalar Python, extrae Hospital_Portable.zip y abre Hospital.exe.
goto error

:preparar
echo Preparando el entorno. La primera vez necesita internet...
%PYTHON% -m venv .venv
if errorlevel 1 goto error
".venv\Scripts\python.exe" -m pip --disable-pip-version-check install -r requirements.txt
if errorlevel 1 goto error

:ejecutar
".venv\Scripts\python.exe" iniciar.py %*
if errorlevel 1 goto error
popd
exit /b 0

:error
echo.
echo No se pudo iniciar. Revisa el mensaje pasado.
pause
popd
exit /b 1
