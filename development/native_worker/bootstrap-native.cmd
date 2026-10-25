@echo off
setlocal EnableExtensions DisableDelayedExpansion
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" > NUL
if errorlevel 1 exit /b 70
cd /d "C:\Users\msemj\Documents\Codex\2026-10-25\podme-rozbehat-native-worker\unified-dev-worker-05\worker-native"
if errorlevel 1 exit /b 71
"C:\Users\msemj\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe" generate-lockfile --offline
if errorlevel 1 exit /b %errorlevel%
"C:\Users\msemj\.rustup\toolchains\stable-x86_64-pc-windows-msvc\bin\cargo.exe" build --locked --offline --jobs 2
exit /b %errorlevel%
