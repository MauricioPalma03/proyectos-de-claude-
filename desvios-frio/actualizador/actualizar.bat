@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python instalado. Instalalo desde https://www.python.org/downloads/
    echo ^(marca la casilla "Add Python to PATH" durante la instalacion^) y vuelve a intentar.
    pause
    exit /b 1
)
python actualizar.py
