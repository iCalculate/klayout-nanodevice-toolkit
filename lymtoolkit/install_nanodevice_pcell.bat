@echo off
REM Install/Update nanodevice-pcell to KLayout user salt directory (full sync)
setlocal
set SALTDIR=%USERPROFILE%\KLayout\salt\nanodevice-pcell
if exist "%SALTDIR%" rmdir /S /Q "%SALTDIR%"
mkdir "%SALTDIR%"
xcopy /E /Y /I "%~dp0nanodevice-pcell\*" "%SALTDIR%\"
echo nanodevice-pcell has been fully synchronized to %SALTDIR%
echo Please restart KLayout and use nanodevice-pcell in the Library panel.
pause 