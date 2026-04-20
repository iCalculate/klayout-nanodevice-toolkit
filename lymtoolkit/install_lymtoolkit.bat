@echo off
REM Install unified NanoDevice toolkit and GUI macros into KLayout salt directory
setlocal EnableExtensions EnableDelayedExpansion

for /F %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"

set "ROOT=%~dp0"
set "TARGET=%USERPROFILE%\KLayout\salt\nanodevice-toolkit"
set "TOOLKIT_SRC=%ROOT%toolkit"
set "PROJECT_ROOT=%ROOT%.."
set "CONFIG_SRC=%PROJECT_ROOT%\config.py"
set "UTILS_SRC=%PROJECT_ROOT%\utils"
set "COMPONENTS_SRC=%PROJECT_ROOT%\components"
set "PDK_SRC=%ROOT%PDK"
set "ASSETS_SRC=%ROOT%assets"

set /A TOTAL_STEPS=6
set /A CURRENT_STEP=0

call :banner
call :info "Target" "%TARGET%"
echo.

if not exist "%TOOLKIT_SRC%" (
  call :fail "Toolkit source directory not found: %TOOLKIT_SRC%"
  goto :end_fail
)

if not exist "%CONFIG_SRC%" (
  call :fail "config.py not found: %CONFIG_SRC%"
  goto :end_fail
)

if not exist "%UTILS_SRC%" (
  call :fail "utils directory not found: %UTILS_SRC%"
  goto :end_fail
)

if not exist "%COMPONENTS_SRC%" (
  call :fail "components directory not found: %COMPONENTS_SRC%"
  goto :end_fail
)

if not exist "%PDK_SRC%" (
  call :fail "PDK directory not found: %PDK_SRC%"
  goto :end_fail
)

if not exist "%ASSETS_SRC%" (
  call :fail "Assets directory not found: %ASSETS_SRC%"
  goto :end_fail
)

call :step "Cleaning previous installation"
if exist "%TARGET%" (
  rmdir /S /Q "%TARGET%"
  if exist "%TARGET%" (
    call :fail "Failed to remove existing target directory. Close KLayout and try again."
    goto :end_fail
  )
)
call :ok "Previous installation cleared"

call :step "Creating target directory"
mkdir "%TARGET%" >nul 2>nul
if errorlevel 1 (
  call :fail "Failed to create target directory: %TARGET%"
  goto :end_fail
)
call :ok "Target directory ready"

call :step "Copying toolkit libraries and GUI files"
xcopy /E /Y /I "%TOOLKIT_SRC%\*" "%TARGET%\" >nul
if errorlevel 1 (
  call :fail "Toolkit copy failed."
  goto :end_fail
)
xcopy /E /Y /I "%ASSETS_SRC%" "%TARGET%\assets\" >nul
if errorlevel 1 (
  call :fail "Assets copy failed."
  goto :end_fail
)
call :ok "Toolkit files copied"

call :step "Copying runtime dependencies"
copy /Y "%CONFIG_SRC%" "%TARGET%\config.py" >nul
if errorlevel 1 (
  call :fail "Failed to copy config.py"
  goto :end_fail
)
xcopy /E /Y /I "%UTILS_SRC%" "%TARGET%\utils\" >nul
if errorlevel 1 (
  call :fail "Failed to copy utils directory."
  goto :end_fail
)
xcopy /E /Y /I "%COMPONENTS_SRC%" "%TARGET%\components\" >nul
if errorlevel 1 (
  call :fail "Failed to copy components directory."
  goto :end_fail
)
call :ok "Runtime dependencies copied"

call :step "Copying LabPDK runtime bundle"
xcopy /E /Y /I "%PDK_SRC%" "%TARGET%\pdk\" >nul
if errorlevel 1 (
  call :fail "Failed to copy PDK directory."
  goto :end_fail
)
call :ok "PDK files copied"

call :step "Finalizing installation"
call :ok "NanoDevice Toolkit installed successfully"
echo.
call :headline "Installed content"
call :bullet "NanoDeviceLib PCells"
call :bullet "NanoDeviceToolkitLib PCells"
call :bullet "Unified NanoDevice Toolkit GUI"
call :bullet "NanoRoutingLib PCells"
call :bullet "NanoRouting GUI and toolbar button"
call :bullet "NanoMark GUI for writefield marks and mark arrays"
call :bullet "config.py, utils, components, and PDK runtime files"
echo.
call :headline "Next step"
call :info "Action" "Restart KLayout to load the updated toolkit."
echo.
pause
exit /b 0

:end_fail
echo.
call :headline "Installation aborted"
pause
exit /b 1

:banner
echo.
call :cecho 96 "  _   _                   ____             _             "
echo.
call :cecho 96 " | \ | | __ _ _ __   ___ |  _ \  _____   _(_) ___ ___   "
echo.
call :cecho 96 " |  \| |/ _` | '_ \ / _ \| | | |/ _ \ \ / / |/ __/ _ \  "
echo.
call :cecho 96 " | |\  | (_| | | | | (_) | |_| |  __/\ V /| | (_|  __/  "
echo.
call :cecho 96 " |_| \_|\__,_|_| |_|\___/|____/ \___| \_/ |_|\___\___|  "
echo.
call :cecho 90 " ------------------------------------------------------- "
echo.
call :cecho 97 " NanoDevice Toolkit Installer"
echo.
call :cecho 90 " Deploying GUI, runtime modules, and bundled LabPDK"
echo.
exit /b 0

:step
set /A CURRENT_STEP+=1
set "STEP_LABEL=%~1"
call :progress %CURRENT_STEP% %TOTAL_STEPS% "%STEP_LABEL%"
exit /b 0

:progress
set /A __cur=%~1
set /A __tot=%~2
set "PROGRESS_LABEL=%~3"
set /A __pct=(__cur*100)/__tot
set /A __filled=(__cur*28)/__tot
set "BAR="
for /L %%I in (1,1,28) do (
  if %%I LEQ !__filled! (
    set "BAR=!BAR!#"
  ) else (
    set "BAR=!BAR!-"
  )
)
echo.
call :cecho 94 " [%__cur%/%__tot%] [!BAR!] %__pct%%% "
echo.
call :cecho 97 " %PROGRESS_LABEL%"
echo.
exit /b 0

:headline
call :cecho 93 "%~1"
echo.
exit /b 0

:bullet
call :cecho 90 "   - %~1"
echo.
exit /b 0

:info
call :cecho 90 " %~1: "
call :cecho_inline 97 "%~2"
echo.
exit /b 0

:ok
call :cecho 92 "   OK  %~1"
echo.
exit /b 0

:fail
call :cecho 91 "   ERROR  %~1"
echo.
exit /b 0


:cecho
if defined ESC (
  <nul set /p "=!ESC![%~1m%~2!ESC![0m"
) else (
  <nul set /p "=%~2"
)
exit /b 0

:cecho_inline
if defined ESC (
  <nul set /p "=!ESC![%~1m%~2!ESC![0m"
) else (
  <nul set /p "=%~2"
)
exit /b 0
