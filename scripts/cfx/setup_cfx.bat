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
:: Capture full Python executable path for uv --python
for /f "delims=" %%p in ('python -c "import sys; print(sys.executable)"') do set PY_EXE=%%p
echo [OK] Python %PY_VER% at %PY_EXE%
echo.

:: -------------------------------------------------------
:: 2. Resolve package installer: prefer uv, fallback to pip
:: -------------------------------------------------------
echo [2/5] Installing Python dependencies...

:: Check if uv is available
uv --version >nul 2>&1
if not errorlevel 1 (
    echo [INFO] uv found.
    set USE_UV=1
    goto :INSTALL_DEPS
)

:: uv not found -- try to install via pip
echo [INFO] uv not found, trying pip install uv...
python -m pip --version >nul 2>&1
if not errorlevel 1 (
    python -m pip install uv --quiet
    uv --version >nul 2>&1
    if not errorlevel 1 (
        echo [OK] uv installed via pip.
        set USE_UV=1
        goto :INSTALL_DEPS
    )
)

:: pip unavailable -- install uv via official PowerShell installer
echo [INFO] pip unavailable. Installing uv via official installer...
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
uv --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] uv installed.
    set USE_UV=1
    goto :INSTALL_DEPS
)

echo [INFO] uv unavailable, falling back to plain pip.
set USE_UV=0

:INSTALL_DEPS
if "!USE_UV!"=="1" (
    :: Try --python <exe> first -- works in venvs and avoids "no system Python" error
    echo [INFO] Running: uv pip install --python "!PY_EXE!" ...
    uv pip install pynput pyautogui --python "!PY_EXE!"
    if errorlevel 1 (
        :: Fallback: --system (works when a system Python is registered)
        echo [INFO] Retrying with --system...
        uv pip install pynput pyautogui --system
    )
) else (
    python -m pip install pynput pyautogui --quiet --upgrade
)
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo         Try manually in your terminal:
    echo           uv pip install pynput pyautogui --python "%PY_EXE%"
    echo         or:  pip install pynput pyautogui
    pause & exit /b 1
)
echo [OK] pynput + pyautogui ready.
echo.

:: -------------------------------------------------------
:: 3. AutoHotkey silent install (if not present)
:: -------------------------------------------------------
echo [3/5] Checking AutoHotkey...
if exist "C:\Program Files\AutoHotkey\AutoHotkey.exe" (
    echo [OK] AutoHotkey already installed.
) else if exist "C:\Program Files\AutoHotkey\v2\AutoHotkey.exe" (
    echo [OK] AutoHotkey v2 already installed.
) else (
    echo [INFO] AutoHotkey not found -- downloading installer...
    set AHK_INSTALLER=%TEMP%\ahk_setup.exe
    curl -L -o "!AHK_INSTALLER!" "https://www.autohotkey.com/download/ahk-install.exe" --silent
    if errorlevel 1 (
        echo [ERROR] Download failed. Install manually: https://www.autohotkey.com
        pause & exit /b 1
    )
    echo [INFO] Running AutoHotkey installer (silent)...
    "!AHK_INSTALLER!" /S
    timeout /t 5 /nobreak >nul
    echo [OK] AutoHotkey installed.
)
echo.

:: -------------------------------------------------------
:: 4. Run Python calibration wizard
:: -------------------------------------------------------
echo [4/5] Launching calibration wizard...
echo       Follow the on-screen instructions to calibrate
echo       your Rekordbox layout.
echo.
python "%SCRIPT_DIR%setup_cfx.py"
if errorlevel 1 (
    echo [ERROR] Calibration failed or was cancelled.
    pause & exit /b 1
)
echo.

:: -------------------------------------------------------
:: 5. Compile RekordboxCFX.ahk -> RekordboxCFX.exe
:: -------------------------------------------------------
echo [5/5] Compiling AHK script to standalone EXE...

set AHK_SCRIPT=%SCRIPT_DIR%RekordboxCFX.ahk
set AHK_EXE_OUT=%SCRIPT_DIR%RekordboxCFX.exe

if not exist "%AHK_SCRIPT%" (
    echo [ERROR] RekordboxCFX.ahk not found -- calibration may have failed.
    pause & exit /b 1
)

set AHK2EXE="C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe"
if not exist %AHK2EXE% set AHK2EXE="C:\Program Files\AutoHotkey\v2\Ahk2Exe.exe"
if not exist %AHK2EXE% (
    echo [WARN] Ahk2Exe compiler not found.
    echo        You can still run:  double-click RekordboxCFX.ahk
    goto :DONE_NO_EXE
)

%AHK2EXE% /in "%AHK_SCRIPT%" /out "%AHK_EXE_OUT%" /compress 2
if errorlevel 1 (
    echo [WARN] Compile failed -- falling back to .ahk mode.
    goto :DONE_NO_EXE
)

echo.
echo  =====================================================
echo   SUCCESS!
echo   EXE ready:  %AHK_EXE_OUT%
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
set /p OPEN="Open folder? (y/n): "
if /i "%OPEN%"=="y" explorer "%SCRIPT_DIR%"
pause >nul
endlocal
