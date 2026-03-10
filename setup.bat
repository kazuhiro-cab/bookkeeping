@echo off
setlocal

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [setup] Creating virtual environment in %VENV_DIR% ...
  py -3 -m venv %VENV_DIR%
  if errorlevel 1 (
    echo [setup] ERROR: failed to create virtual environment.
    exit /b 1
  )
)

echo [setup] Upgrading pip ...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  echo [setup] ERROR: failed to upgrade pip.
  exit /b 1
)

echo [setup] Installing project in editable mode ...
"%VENV_DIR%\Scripts\python.exe" -m pip install -e .
if errorlevel 1 (
  echo [setup] ERROR: failed to install project.
  exit /b 1
)

echo [setup] Done.
endlocal
