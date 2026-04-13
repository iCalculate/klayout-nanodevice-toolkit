@echo off
REM Install/Update InterdigitatedFETLib to KLayout user salt directory
setlocal
set SALTDIR=%USERPROFILE%\KLayout\salt\interdigitated-fet-lib
set SOURCEDIR=%~dp0interdigitated-fet-lib

if not exist "%SOURCEDIR%" (
  echo Source directory not found: %SOURCEDIR%
  exit /b 1
)

if exist "%SALTDIR%" (
  echo Removing old library files from %SALTDIR%
  rmdir /S /Q "%SALTDIR%"
  if exist "%SALTDIR%" (
    echo Failed to remove existing target directory. Close KLayout and try again.
    exit /b 1
  )
)

mkdir "%SALTDIR%"
if errorlevel 1 (
  echo Failed to create target directory: %SALTDIR%
  exit /b 1
)

echo Copying new library files into %SALTDIR%
xcopy /E /Y /I "%SOURCEDIR%\*" "%SALTDIR%\"
if errorlevel 1 (
  echo File copy failed.
  exit /b 1
)

echo InterdigitatedFETLib has been fully synchronized to %SALTDIR%
echo Please restart KLayout and use InterdigitatedFETLib in the Library panel.
pause
