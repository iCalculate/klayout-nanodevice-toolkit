@echo off
REM Install backed-up KLayout user setup (theme, shortcuts, panels, and editor preferences)
setlocal EnableExtensions EnableDelayedExpansion

for /F %%A in ('echo prompt $E ^| cmd') do set "ESC=%%A"

set "ROOT=%~dp0"
set "SETUP_SRC=%ROOT%klayout_setup\klayoutrc"
set "KLAYOUT_HOME=%USERPROFILE%\KLayout"
set "TARGET=%KLAYOUT_HOME%\klayoutrc"
set "BACKUP=%KLAYOUT_HOME%\klayoutrc.before_nanodevice_backup"

set /A TOTAL_STEPS=5
set /A CURRENT_STEP=0

call :banner
call :info "Source" "%SETUP_SRC%"
call :info "Target" "%TARGET%"
echo.

if not exist "%SETUP_SRC%" (
  call :fail "Setup source not found: %SETUP_SRC%"
  goto :end_fail
)

call :step "Preparing KLayout user directory"
if not exist "%KLAYOUT_HOME%" (
  mkdir "%KLAYOUT_HOME%" >nul 2>nul
  if errorlevel 1 (
    call :fail "Failed to create %KLAYOUT_HOME%"
    goto :end_fail
  )
)
call :ok "KLayout user directory ready"

call :step "Backing up existing klayoutrc"
if exist "%TARGET%" (
  copy /Y "%TARGET%" "%BACKUP%" >nul
  if errorlevel 1 (
    call :fail "Failed to back up existing klayoutrc"
    goto :end_fail
  )
  call :ok "Existing config backed up to klayoutrc.before_nanodevice_backup"
) else (
  call :ok "No existing klayoutrc found, skipping backup"
)

call :step "Installing backed-up setup"
copy /Y "%SETUP_SRC%" "%TARGET%" >nul
if errorlevel 1 (
  call :fail "Failed to install klayoutrc"
  goto :end_fail
)
call :ok "klayoutrc installed"

call :step "Import summary"
call :headline "Imported settings"
call :bullet "Theme and colors: background, palette, grid, cursor, selection display"
call :bullet "Key bindings: custom shortcuts from the key-bindings block"
call :bullet "View layout: toolbar, layer panel, hierarchy panel, navigator, window geometry"
call :bullet "Editing preferences: default grids, ruler templates, text defaults, snapping behavior"
call :bullet "Technology and macros: initial technology, technology-data, custom macro paths"
echo.

call :step "Finalizing"
call :ok "KLayout setup restored successfully"
echo.
call :headline "Next step"
call :info "Action" "Restart KLayout to load the imported setup."
call :info "Backup" "%BACKUP%"
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
call :cecho 96 "  _  ___      _                        _      ____        _                 "
echo.
call :cecho 96 " | |/ / |    / \   _   _  ___  _   _| |_   / ___|  ___| |_ _   _ _ __    "
echo.
call :cecho 96 " | ' /| |   / _ \ | | | |/ _ \| | | | __|  \___ \ / _ \ __| | | | '_ \   "
echo.
call :cecho 96 " | . \| |__ / ___ \| |_| | (_) | |_| | |_    ___) |  __/ |_| |_| | |_) |  "
echo.
call :cecho 96 " |_|\_\_____/_/   \_\\__, |\___/ \__,_|\__|  |____/ \___|\__|\__,_| .__/   "
echo.
call :cecho 96 "                     |___/                                        |_|      "
echo.
call :cecho 90 " ------------------------------------------------------------------------- "
echo.
call :cecho 97 " KLayout Setup Installer"
echo.
call :cecho 90 " Restoring your saved theme, shortcuts, view layout, and editor preferences"
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
