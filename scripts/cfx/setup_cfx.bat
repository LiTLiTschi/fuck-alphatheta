@echo off
setlocal EnableDelayedExpansion
title Rekordbox CFX Selector :: Setup
color 0B

echo.
echo  =====================================================
echo   Rekordbox CFX Selector  --  Full Setup
echo   Maps CFX dropdown to MIDI via AHK hotkeys
echo  =====================================================
echo.

set SCRIPT_DIR=%~dp0

:: -------------------------------------------------------
:: 1. Python check
:: -------------------------------------------------------
echo [1/5] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found.
    echo         Download: https://www.python.org/downloads/
    echo         IMPORTANT: Check "Add Python to PATH" during install!
    pause & exit /b 1
)
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PY_VER=%%v
for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)"') do set PY_EXE=%%p
echo [OK] Python %PY_VER% at %PY_EXE%
echo.

:: -------------------------------------------------------
:: 2. Install deps via uv (preferred) or pip
:: -------------------------------------------------------
echo [2/5] Installing Python dependencies...

uv --version >nul 2>&1
if not errorlevel 1 goto :UV_FOUND

echo [INFO] uv not found, trying pip install uv...
python -m pip install uv --quiet >nul 2>&1
uv --version >nul 2>&1
if not errorlevel 1 goto :UV_FOUND

echo [INFO] pip unavailable. Installing uv via PowerShell...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
uv --version >nul 2>&1
if not errorlevel 1 goto :UV_FOUND

echo [INFO] uv unavailable, using plain pip.
goto :PIP_INSTALL

:UV_FOUND
echo [INFO] uv found. Installing with --python "%PY_EXE%"...
uv pip install pynput pyautogui --python "%PY_EXE%"
if not errorlevel 1 goto :DEPS_OK
echo [INFO] --python failed, retrying --system...
uv pip install pynput pyautogui --system
if not errorlevel 1 goto :DEPS_OK
goto :DEPS_FAIL

:PIP_INSTALL
python -m pip install pynput pyautogui --quiet --upgrade
if not errorlevel 1 goto :DEPS_OK

:DEPS_FAIL
echo [ERROR] Dependency installation failed.
echo         Try manually:  uv pip install pynput pyautogui --python "%PY_EXE%"
pause & exit /b 1

:DEPS_OK
echo [OK] pynput + pyautogui ready.
echo.

:: -------------------------------------------------------
:: 3. AutoHotkey check / silent install
:: -------------------------------------------------------
echo [3/5] Checking AutoHotkey...

set AHK_OK=0
if exist "C:\Program Files\AutoHotkey\AutoHotkey.exe"    set AHK_OK=1
if exist "C:\Program Files\AutoHotkey\v2\AutoHotkey.exe" set AHK_OK=1

if "%AHK_OK%"=="1" (
    echo [OK] AutoHotkey already installed.
    goto :AHK_READY
)

echo [INFO] AutoHotkey not found -- downloading installer...
set AHK_INSTALLER=%TEMP%\ahk_setup.exe
curl -L -o "%AHK_INSTALLER%" "https://www.autohotkey.com/download/ahk-install.exe" --silent
if errorlevel 1 (
    echo [ERROR] Download failed. Install manually: https://www.autohotkey.com
    pause & exit /b 1
)
echo [INFO] Running AutoHotkey installer (silent)...
"%AHK_INSTALLER%" /S
timeout /t 5 /nobreak >nul
echo [OK] AutoHotkey installed.

:AHK_READY
echo.

:: -------------------------------------------------------
:: 4. Python calibration wizard
:: -------------------------------------------------------
echo [4/5] Launching calibration wizard...
echo       Follow the on-screen instructions.
echo.
:: BAT wrapper help
if /i "%~1"=="--help" goto :BAT_HELP
if /i "%~1"=="-h" goto :BAT_HELP

:: If caller provided --json <path>, pass it to python as --json-path
if /i "%~1"=="--json" (
    if "%~2"=="" (
        echo [ERROR] --json requires a path argument.
        pause & exit /b 1
    )
    python "%SCRIPT_DIR%setup_cfx.py" --json-path "%~2"
) else if /i "%~1"=="--generate-from-json" (
    python "%SCRIPT_DIR%setup_cfx.py" --generate-from-json
) else (
    python "%SCRIPT_DIR%setup_cfx.py"
)

if errorlevel 1 (
    echo [ERROR] Calibration failed or was cancelled.
    pause & exit /b 1
)
echo.

goto :COMPILE

:BAT_HELP
echo Usage: setup_cfx.bat [--help] [--json path] [--generate-from-json]
echo.
echo  --help                 Show this help
echo  --json path            Generate AHK from specified calibration JSON (for python --json-path)
echo  --generate-from-json   Use cfx_calibration.json in script dir
pause >nul
exit /b 0

:: -------------------------------------------------------
:: 5. Compile AHK -> EXE
:: -------------------------------------------------------
:COMPILE

echo [5/5] Compiling AHK script to standalone EXE...

set AHK_SCRIPT=%SCRIPT_DIR%RekordboxCFX.ahk
set AHK_EXE_OUT=%SCRIPT_DIR%RekordboxCFX.exe

if not exist "%AHK_SCRIPT%" (
    echo [ERROR] RekordboxCFX.ahk not found.
    pause & exit /b 1
)

set AHK2EXE=

:: Check common locations for Ahk2Exe.exe (quoted to handle spaces)
if exist "%SCRIPT_DIR%..\..\Ahk2Exe.exe" (
    set "AHK2EXE=%SCRIPT_DIR%..\..\Ahk2Exe.exe"
) 
if exist "%SCRIPT_DIR%..\Ahk2Exe.exe" (
    set "AHK2EXE=%SCRIPT_DIR%..\Ahk2Exe.exe"
)
if exist "%SCRIPT_DIR%Ahk2Exe.exe" (
    set "AHK2EXE=%SCRIPT_DIR%Ahk2Exe.exe"
)
if exist "C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe" (
    set "AHK2EXE=C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe"
)
if exist "C:\Program Files\AutoHotkey\v2\Ahk2Exe.exe" (
    set "AHK2EXE=C:\Program Files\AutoHotkey\v2\Ahk2Exe.exe"
)

if "%AHK2EXE%"=="" (
    echo [WARN] Ahk2Exe not found in candidate locations:
    echo    %SCRIPT_DIR%..\..\Ahk2Exe.exe
    echo    %SCRIPT_DIR%..\Ahk2Exe.exe
    echo    %SCRIPT_DIR%Ahk2Exe.exe
    echo    C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe
    echo    C:\Program Files\AutoHotkey\v2\Ahk2Exe.exe
    goto :DONE_NO_EXE
)

echo [INFO] Found Ahk2Exe at: %AHK2EXE%
:AHK2EXE_FOUND

echo [5/5] Starting Ahk2Exe compilation...
echo [INFO] Command: "%AHK2EXE%" /in "%AHK_SCRIPT%" /out "%AHK_EXE_OUT%" /compress 2
echo [INFO] Compilation may take several seconds; showing start/end times when done.
set "COMP_START=%TIME%"
"%AHK2EXE%" /in "%AHK_SCRIPT%" /out "%AHK_EXE_OUT%" /compress 2
set "COMP_END=%TIME%"
if errorlevel 1 (
    echo [WARN] Compile failed -- run RekordboxCFX.ahk manually.
    echo [INFO] Compilation started at %COMP_START% and ended at %COMP_END%
    goto :DONE_NO_EXE
)

echo [INFO] Compilation finished. Started: %COMP_START% Ended: %COMP_END%

echo.
echo  =====================================================
echo   SUCCESS!
echo   EXE: %AHK_EXE_OUT%
echo   --> Double-click RekordboxCFX.exe to activate.
echo   Hotkeys:  Ch1 Ctrl+Alt+1..9  Ch2 Ctrl+Shift+1..9
echo             Ch3 Alt+Shift+1..9  Ch4 Ctrl+Alt+Shift+1..9
echo  =====================================================
echo.
goto :DONE

:DONE_NO_EXE
echo.
echo  =====================================================
echo   DONE (script mode) -- run RekordboxCFX.ahk
echo  =====================================================
echo.

:DONE
set /p OPEN="Open output folder? (y/n): "
if /i "%OPEN%"=="y" explorer "%SCRIPT_DIR%"
pause >nul
endlocal
