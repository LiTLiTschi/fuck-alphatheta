@echo off
setlocal EnableDelayedExpansion
title fuck-alphatheta :: BPM Tool Setup
color 0A

echo.
echo  ==========================================
echo   fuck-alphatheta - BPM Tool Setup
echo   Rekordbox Pixel-BPM Link v1.0
echo  ==========================================
echo.

:: -----------------------------------------------
:: 1. Check Python
:: -----------------------------------------------
echo [1/5] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation!
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
echo [OK] Python %PY_VER% found.
echo.

:: -----------------------------------------------
:: 2. Check Tesseract
:: -----------------------------------------------
echo [2/5] Checking Tesseract OCR...
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo [OK] Tesseract found at C:\Program Files\Tesseract-OCR\
) else (
    echo [WARN] Tesseract not found at default location.
    echo        Please install from: https://github.com/UB-Mannheim/tesseract/wiki
    echo        Install path must be: C:\Program Files\Tesseract-OCR\
    echo.
    set /p CONTINUE="Continue anyway? (y/n): "
    if /i "!CONTINUE!" neq "y" (
        echo Aborting setup.
        pause
        exit /b 1
    )
)
echo.

:: -----------------------------------------------
:: 3. Install Python dependencies
:: -----------------------------------------------
echo [3/5] Installing Python dependencies...
python -m pip install --upgrade pip --quiet
if errorlevel 1 (
    echo [ERROR] pip upgrade failed.
    pause
    exit /b 1
)

pip install pytesseract mss pillow numpy opencv-python pywin32 --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo [OK] All dependencies installed.
echo.

:: -----------------------------------------------
:: 4. Install PyInstaller
:: -----------------------------------------------
echo [4/5] Installing PyInstaller...
pip install pyinstaller --quiet
if errorlevel 1 (
    echo [ERROR] PyInstaller installation failed.
    pause
    exit /b 1
)
echo [OK] PyInstaller ready.
echo.

:: -----------------------------------------------
:: 5. Compile bpm_tool_v2.py to EXE
:: -----------------------------------------------
echo [5/5] Compiling bpm_tool_v2.py to standalone EXE...
echo       (This may take 30-60 seconds...)
echo.

set SCRIPT_DIR=%~dp0
set SCRIPT=%SCRIPT_DIR%bpm_tool_v2.py
set DIST_DIR=%SCRIPT_DIR%dist

if not exist "%SCRIPT%" (
    echo [ERROR] bpm_tool_v2.py not found in %SCRIPT_DIR%
    pause
    exit /b 1
)

pyinstaller --onefile --noconsole --name "BPM_Tool" --distpath "%DIST_DIR%" "%SCRIPT%" --clean --noconfirm >nul 2>&1
if errorlevel 1 (
    echo [WARN] EXE compilation failed - you can still run via Python directly:
    echo        python bpm_tool_v2.py
    echo.
    goto :DONE_NO_EXE
)

echo [OK] Compiled successfully!
echo.
echo  ==========================================
echo   EXE ready at:
echo   %DIST_DIR%\BPM_Tool.exe
echo  ==========================================
echo.
echo  Double-click BPM_Tool.exe to launch - no Python needed!
echo.

set /p OPEN_FOLDER="Open output folder now? (y/n): "
if /i "%OPEN_FOLDER%"=="y" explorer "%DIST_DIR%"

goto :DONE

:DONE_NO_EXE
echo  To run manually:
echo    cd %SCRIPT_DIR%
echo    python bpm_tool_v2.py

:DONE
echo.
echo  Setup complete. Press any key to exit.
pause >nul
endlocal
