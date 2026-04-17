@echo off
REM Install LabPDK technology files into the user's KLayout technology directory
setlocal

set "ROOT=%~dp0"
set "PDK_SRC=%ROOT%PDK"
set "TARGET=%USERPROFILE%\KLayout\tech\LabPDK"

if not exist "%PDK_SRC%" (
  echo PDK source directory not found: %PDK_SRC%
  exit /b 1
)

if exist "%TARGET%" (
  echo Removing old PDK installation from %TARGET%
  rmdir /S /Q "%TARGET%"
  if exist "%TARGET%" (
    echo Failed to remove existing PDK target directory. Close KLayout and try again.
    exit /b 1
  )
)

mkdir "%TARGET%"
if errorlevel 1 (
  echo Failed to create PDK target directory: %TARGET%
  exit /b 1
)

echo Copying LabPDK files...
xcopy /E /Y /I "%PDK_SRC%\*" "%TARGET%\"
if errorlevel 1 (
  echo PDK copy failed.
  exit /b 1
)

echo.
echo LabPDK has been installed to:
echo   %TARGET%
echo.
echo Installed content:
echo   - technology.lyt
echo   - layers\layer_map.lyp
echo   - macros\*.lym and init.py
echo   - examples\*
echo.
echo Please restart KLayout.
pause
