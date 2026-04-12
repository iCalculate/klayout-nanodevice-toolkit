@echo off
REM Install/Update InterdigitatedFETLib to KLayout user salt directory
setlocal
set SALTDIR=%USERPROFILE%\KLayout\salt\interdigitated-fet-lib
if exist "%SALTDIR%" rmdir /S /Q "%SALTDIR%"
mkdir "%SALTDIR%"
xcopy /E /Y /I "%~dp0interdigitated-fet-lib\*" "%SALTDIR%\"
echo InterdigitatedFETLib has been fully synchronized to %SALTDIR%
echo Please restart KLayout and use InterdigitatedFETLib in the Library panel.
pause
