@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /std:c++20 /EHsc /O2 /W4 /utf-8 /MD /Fe:"F:\Remaster Framework\orchestrator\capture-worker\capture_process_audio.exe" "F:\Remaster Framework\orchestrator\capture-worker\capture_process_audio.cpp" /link
exit /b %errorlevel%
