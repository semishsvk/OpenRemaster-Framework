@echo off
call "C:\Program Files\Microsoft Visual Studio\2022\Enterprise\VC\Auxiliary\Build\vcvars64.bat" >nul
cl /nologo /std:c++20 /EHsc /O2 /W4 /utf-8 /MD /Fe:"F:\Remaster Framework\work\OpenRemaster\fidelity_fixture\synthetic_scummvm_oracle.exe" "F:\Remaster Framework\work\OpenRemaster\fidelity_fixture\synthetic_scummvm_oracle.cpp" /link /SUBSYSTEM:WINDOWS
exit /b %errorlevel%
