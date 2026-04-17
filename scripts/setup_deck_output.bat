@echo off
setlocal EnableDelayedExpansion
title Rekordbox Deck Output Setup
color 0A

echo.
echo ===============================================
echo   Rekordbox Deck Output Setup
echo ===============================================
echo.

set "SCRIPTDIR=%~dp0"
set "PYFILE=%SCRIPTDIR%rekordbox_deck_output.py"
set "DISTDIR=%SCRIPTDIR%dist"
set "EXEFILE=%DISTDIR%\RekordboxDeckOutput.exe"
set "CONFIGFILE=%SCRIPTDIR%deck_output_config.json"

echo -----------------------------------------------
echo 1. Check Python
echo -----------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python nicht gefunden.
    echo Installiere Python 3.10+ und aktiviere "Add Python to PATH".
    pause
    exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set "PYVER=%%v"
echo OK: Python !PYVER! gefunden.
echo.

echo -----------------------------------------------
echo 2. Check Tesseract
echo -----------------------------------------------
if exist "C:\Program Files\Tesseract-OCR\tesseract.exe" (
    echo OK: Tesseract gefunden.
) else (
    echo WARN: Tesseract nicht unter dem Standardpfad gefunden.
    echo Bitte von https://github.com/UB-Mannheim/tesseract/wiki installieren.
    echo Standardpfad: C:\Program Files\Tesseract-OCR\tesseract.exe
    set /p CONTINUE=Continue anyway? (y/n): 
    if /i not "!CONTINUE!"=="y" (
        echo Abbruch.
        pause
        exit /b 1
    )
)
echo.

echo -----------------------------------------------
echo 3. Install Python dependencies
echo -----------------------------------------------
python -m pip install --upgrade pip
if errorlevel 1 (
    echo ERROR: pip upgrade fehlgeschlagen.
    pause
    exit /b 1
)
pip install mss pillow numpy opencv-python pytesseract pywin32 python-rtmidi
if errorlevel 1 (
    echo ERROR: Dependency-Installation fehlgeschlagen.
    pause
    exit /b 1
)
echo OK: Dependencies installiert.
echo.

echo -----------------------------------------------
echo 4. Calibration wizard
echo -----------------------------------------------
if not exist "%PYFILE%" (
    echo ERROR: %PYFILE% nicht gefunden.
    pause
    exit /b 1
)
echo Rekordbox sichtbar machen, dann startet der Kalibrierungs-Wizard.
echo.
python "%PYFILE%" --setup --config "%CONFIGFILE%"
if errorlevel 1 (
    echo ERROR: Setup-Wizard fehlgeschlagen.
    pause
    exit /b 1
)
echo.

echo -----------------------------------------------
echo 5. Optional EXE build
echo -----------------------------------------------
set /p BUILD=Build standalone EXE? (y/n): 
if /i "!BUILD!"=="y" (
    pip install pyinstaller
    if errorlevel 1 (
        echo ERROR: PyInstaller fehlgeschlagen.
        pause
        exit /b 1
    )
    if not exist "%DISTDIR%" mkdir "%DISTDIR%"
    pyinstaller --onefile --noconsole --name RekordboxDeckOutput --distpath "%DISTDIR%" "%PYFILE%" --clean --noconfirm
    if errorlevel 1 (
        echo WARN: EXE Build fehlgeschlagen. Skript laeuft auch direkt via Python.
    ) else (
        echo OK: EXE erstellt: %EXEFILE%
    )
)
echo.

echo -----------------------------------------------
echo Done
echo -----------------------------------------------
echo Dateien:
echo   %PYFILE%
echo   %SCRIPTDIR%rekordbox_deck_output.ahk
echo   %CONFIGFILE%
echo   %SCRIPTDIR%deck_state.txt  (wird zur Laufzeit geschrieben)
echo.
echo MIDI: python rekordbox_deck_output.py --list-midi
echo       python rekordbox_deck_output.py --midi-port "loopMIDI" --debug
echo.
pause
endlocal
