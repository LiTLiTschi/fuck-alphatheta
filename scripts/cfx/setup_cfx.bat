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
echo [OK] Python %PY_VER%
echo.

:: -------------------------------------------------------
:: 2. Resolve package installer: prefer uv, fallback to pip
:: -------------------------------------------------------
echo [2/5] Installing Python dependencies...

:: Check if uv is available
uv --version >nul 2>&1
if not errorlevel 1 (
    echo [INFO] uv found, using uv pip.
    set USE_UV=1
    goto :INSTALL_DEPS
)

:: uv not found -- try to install it via pip first
echo [INFO] uv not found, attempting to install via pip...
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

:: pip not available either -- install uv via official standalone installer
echo [INFO] pip not available (venv without pip?). Installing uv via official installer...
curl -LsSf https://astral.sh/uv/install.sh >nul 2>&1
powershell -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex" >nul 2>&1
:: Refresh PATH for current session
set "PATH=%USERPROFILE%\.local\bin;%USERPROFILE%\.cargo\bin;%PATH%"
uv --version >nul 2>&1
if not errorlevel 1 (
    echo [OK] uv installed via official installer.
    set USE_UV=1
    goto :INSTALL_DEPS
)

:: Last resort: plain pip (might still work if module exists but --version fails)
echo [INFO] Falling back to plain pip install...
set USE_UV=0

:INSTALL_DEPS
if "!USE_UV!"=="1" (
    uv pip install pynput pyautogui --system
) else (
    python -m pip install pynput pyautogui --quiet --upgrade
)
if errorlevel 1 (
    echo [ERROR] Dependency installation failed.
    echo         Try running:  uv pip install pynput pyautogui --system
    echo         Or manually:  pip install pynput pyautogui
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
       your Rekordbox layout.
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

:: Try AHK v1 compiler location first, then v2
set AHK2EXE="C:\Program Files\AutoHotkey\Compiler\Ahk2Exe.exe"
if not exist %AHK2EXE% set AHK2EXE="C:\Program Files\AutoHotkey\v2\Ahk2Exe.exe"
if not exist %AHK2EXE% (
    echo [WARN] Ahk2Exe compiler not found.
    echo        You can still run:  double-click RekordboxCFX.ahk
    echo        (AutoHotkey must be installed on that machine)
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
echo.
echo   EXE ready:  %AHK_EXE_OUT%
echo.
echo   --> Double-click RekordboxCFX.exe to activate.
echo       No AHK installation needed on target machine.
echo.
echo   Hotkeys:
echo     Ch1  Ctrl+Alt+1..9
echo     Ch2  Ctrl+Shift+1..9
echo     Ch3  Alt+Shift+1..9
echo     Ch4  Ctrl+Alt+Shift+1..9
echo  =====================================================
echo.
goto :DONE

:DONE_NO_EXE
echo.
echo  =====================================================
echo   DONE (script mode)
echo   Run RekordboxCFX.ahk with AutoHotkey to activate.
echo  =====================================================
echo.

:DONE
set /p OPEN="Open folder? (y/n): "
if /i "%OPEN%"=="y" explorer "%SCRIPT_DIR%"
pause >nul
endlocal
