@echo off
setlocal EnableExtensions
title PDC Analyzer - Installer Builder
set "BUILDROOT=C:\CIA_BUILD"
set "VENV=%BUILDROOT%\venv"

echo ============================================================
echo PDC ANALYZER - READY INSTALLER BUILD
echo ============================================================
echo This builds one normal Windows Setup EXE.
echo End users will NOT need Python.
echo.
where py >nul 2>nul || (echo ERROR: Python launcher py was not found.& echo Install Python 3.11 x64 from python.org, then retry.& pause& exit /b 1)
where winget >nul 2>nul || (echo ERROR: Windows Package Manager winget was not found.& echo Install Inno Setup manually from jrsoftware.org, then retry.& pause& exit /b 1)
if not exist "%BUILDROOT%" mkdir "%BUILDROOT%"
if exist "%VENV%" rmdir /s /q "%VENV%"
py -m venv "%VENV%" || goto :fail
call "%VENV%\Scripts\activate.bat" || goto :fail
python -m pip install --upgrade pip setuptools wheel --no-cache-dir || goto :fail
python -m pip install --no-cache-dir -r "%~dp0requirements.txt" || goto :fail
cd /d "%~dp0"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist installer_output rmdir /s /q installer_output
python -m PyInstaller --noconfirm --clean --windowed --name "PDC Analyzer" --icon "PDC_Analyzer_Icon.png" main.py || goto :fail
if not exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" (
  echo Installing Inno Setup...
  winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements || goto :fail
)
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo ERROR: Inno Setup compiler not found.& goto :fail)
"%ISCC%" "%~dp0installer.iss" || goto :fail

echo.
echo ============================================================
echo READY
 echo Final installer:
echo "%~dp0installer_output\CanineImpactionAnalyzer_Setup_v1.1.2.exe"
echo ============================================================
pause
exit /b 0
:fail
echo.
echo BUILD FAILED. Copy the error shown above.
pause
exit /b 1
