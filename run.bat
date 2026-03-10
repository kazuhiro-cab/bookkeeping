@echo off
setlocal

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [run] ERROR: virtual environment not found.
  echo [run] Please run setup.bat first.
  exit /b 1
)

echo [run] Launching GUI ...
"%VENV_DIR%\Scripts\python.exe" -m bookkeeping_app
if errorlevel 1 (
  echo [run] Application exited with an error.
  exit /b 1
)

endlocal
