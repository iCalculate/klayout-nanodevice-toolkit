@echo off
REM Install unified NanoDevice toolkit and GUI macros into KLayout salt directory
setlocal

set "ROOT=%~dp0"
set "TARGET=%USERPROFILE%\KLayout\salt\nanodevice-toolkit"
set "TOOLKIT_SRC=%ROOT%toolkit"
set "PROJECT_ROOT=%ROOT%.."
set "CONFIG_SRC=%PROJECT_ROOT%\config.py"
set "UTILS_SRC=%PROJECT_ROOT%\utils"
set "COMPONENTS_SRC=%PROJECT_ROOT%\components"
set "PDK_SRC=%ROOT%pdk"

if not exist "%TOOLKIT_SRC%" (
  echo Toolkit source directory not found: %TOOLKIT_SRC%
  exit /b 1
)

if exist "%TARGET%" (
  echo Removing old installation from %TARGET%
  rmdir /S /Q "%TARGET%"
  if exist "%TARGET%" (
    echo Failed to remove existing target directory. Close KLayout and try again.
    exit /b 1
  )
)

mkdir "%TARGET%"
if errorlevel 1 (
  echo Failed to create target directory: %TARGET%
  exit /b 1
)

echo Copying toolkit libraries and GUI files...
xcopy /E /Y /I "%TOOLKIT_SRC%\*" "%TARGET%\"
if errorlevel 1 (
  echo Toolkit copy failed.
  exit /b 1
)

echo Copying runtime dependencies...
copy /Y "%CONFIG_SRC%" "%TARGET%\config.py" >nul
if errorlevel 1 (
  echo Failed to copy config.py
  exit /b 1
)

xcopy /E /Y /I "%UTILS_SRC%" "%TARGET%\utils\"
if errorlevel 1 (
  echo Failed to copy utils directory.
  exit /b 1
)

xcopy /E /Y /I "%COMPONENTS_SRC%" "%TARGET%\components\"
if errorlevel 1 (
  echo Failed to copy components directory.
  exit /b 1
)

xcopy /E /Y /I "%PDK_SRC%" "%TARGET%\pdk\"
if errorlevel 1 (
  echo Failed to copy pdk directory.
  exit /b 1
)

echo.
echo NanoDevice Toolkit has been installed to:
echo   %TARGET%
echo.
echo Installed content:
echo   - NanoDeviceLib PCells
echo   - NanoDeviceToolkitLib PCells
echo   - Unified NanoDevice Toolkit GUI
echo   - config.py, utils, components, pdk runtime files
echo.
echo Please restart KLayout.
pause
