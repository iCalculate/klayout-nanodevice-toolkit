@echo off
REM Install/Update NanoDevice library to KLayout user salt directory
setlocal
set SALTDIR=%USERPROFILE%\KLayout\salt\nanodevice
if not exist "%SALTDIR%" mkdir "%SALTDIR%"
xcopy /E /Y /I "%~dp0NanoDevice\*" "%SALTDIR%\"
echo NanoDevice library has been updated to %SALTDIR%
echo Please restart KLayout and use NanoDevice in the Library panel.
pause 