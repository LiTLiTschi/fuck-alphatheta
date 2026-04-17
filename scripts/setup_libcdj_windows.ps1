#requires -RunAsAdministrator
$ErrorActionPreference = 'Stop'

$RepoUrl = 'https://github.com/teknopaul/libcdj.git'
$Root = 'C:\libcdj-win'
$MsysRoot = 'C:\msys64'
$Installer = Join-Path $env:TEMP 'msys2-x86_64-latest.exe'
$MsysShell = Join-Path $MsysRoot 'msys2_shell.cmd'
$BashExe = Join-Path $MsysRoot 'usr\bin\bash.exe'

function Write-Step($msg) {
    Write-Host "`n=== $msg ===" -ForegroundColor Cyan
}

function Invoke-Msys($command) {
    & $BashExe -lc $command
    if ($LASTEXITCODE -ne 0) {
        throw "MSYS2 command failed: $command"
    }
}

Write-Step 'Checking winget'
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw 'winget is required for this script. Install App Installer from Microsoft first.'
}

Write-Step 'Installing MSYS2 if needed'
if (-not (Test-Path $MsysShell)) {
    winget install -e --id MSYS2.MSYS2 --accept-package-agreements --accept-source-agreements --disable-interactivity
    Start-Sleep -Seconds 5
}

if (-not (Test-Path $BashExe)) {
    throw 'MSYS2 installed but bash.exe was not found under C:\msys64\usr\bin\bash.exe'
}

Write-Step 'Updating MSYS2 core'
Invoke-Msys 'pacman -Sy --noconfirm'
Invoke-Msys 'pacman -Su --noconfirm'

Write-Step 'Installing build toolchain'
Invoke-Msys 'pacman -S --needed --noconfirm git make gcc base-devel mingw-w64-ucrt-x86_64-gcc'

Write-Step 'Preparing source tree'
New-Item -ItemType Directory -Force -Path $Root | Out-Null
if (-not (Test-Path (Join-Path $Root '.git'))) {
    git clone $RepoUrl $Root
} else {
    git -C $Root pull --ff-only
}

$MsysRepo = '/c/libcdj-win'

Write-Step 'Cleaning previous build'
Invoke-Msys "cd '$MsysRepo' && make clean || true"

Write-Step 'Building libcdj with a conservative single job'
Invoke-Msys "cd '$MsysRepo' && make -j1"

Write-Step 'Done'
Write-Host 'Built output should be under C:\libcdj-win\target' -ForegroundColor Green
Write-Host 'Open MSYS2 UCRT64 or use:' -ForegroundColor Yellow
Write-Host '  C:\msys64\usr\bin\bash.exe -lc "cd /c/libcdj-win/target && ./cdj-mon -h && ./vdj-mon -h"'
Write-Host ''
Write-Host 'Notes:' -ForegroundColor Yellow
Write-Host '- This is an unofficial Windows build path using MSYS2/MinGW, because upstream documents Linux/Ubuntu-style make builds.'
Write-Host '- The script uses make -j1 on purpose to avoid unnecessary CPU spikes / overheating.'
Write-Host '- If build errors mention POSIX or socket APIs, native Windows support may still need source patches.'
