@echo off
setlocal EnableExtensions
title Canine Impaction Analyzer - Windows Builder

echo ============================================================
echo CANINE IMPACTION ANALYZER - WINDOWS BUILD
echo ============================================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python launcher "py" was not found.
    echo Install Python 3.10 or 3.11 from python.org and check:
    echo "Add python.exe to PATH"
    echo.
    pause
    exit /b 1
)

REM ------------------------------------------------------------
REM Use a SHORT Windows path for the virtual environment.
REM This prevents PySide6 installation failures caused by MAX_PATH.
REM ------------------------------------------------------------
set "BUILDROOT=C:\CIA_BUILD"
set "VENV=%BUILDROOT%\venv"

echo Using short build environment:
echo %VENV%
echo.

if not exist "%BUILDROOT%" mkdir "%BUILDROOT%"

if exist "%VENV%" (
    echo Removing old build environment...
    rmdir /s /q "%VENV%"
)

echo Creating virtual environment...
py -m venv "%VENV%"
if errorlevel 1 goto :fail

call "%VENV%\Scripts\activate.bat"
if errorlevel 1 goto :fail

echo.
echo Updating pip...
python -m pip install --upgrade pip setuptools wheel --no-cache-dir
if errorlevel 1 goto :fail

echo.
echo Installing application requirements...
python -m pip install --no-cache-dir -r "%~dp0requirements.txt"
if errorlevel 1 goto :fail

echo.
echo Building Windows application...
cd /d "%~dp0"

if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

python -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name "Canine Impaction Analyzer" ^
  main.py

if errorlevel 1 goto :fail

echo.
echo ============================================================
echo BUILD COMPLETE
echo ============================================================
echo.
echo Your application is here:
echo "%~dp0dist\Canine Impaction Analyzer\Canine Impaction Analyzer.exe"
echo.
echo Keep the ENTIRE "Canine Impaction Analyzer" folder together
echo when sharing the Windows build.
echo.
pause
exit /b 0

:fail
echo.
echo ============================================================
echo BUILD FAILED
echo ============================================================
echo.
echo Please copy the ERROR lines above.
echo.
pause
exit /b 1
