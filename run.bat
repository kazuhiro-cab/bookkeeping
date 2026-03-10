@echo off
setlocal

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [run] ERROR: virtual environment not found.
  echo [run] Please run setup.bat first.
  exit /b 1
)

echo [run] Running test suite ...
"%VENV_DIR%\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
  echo [run] Tests failed.
  exit /b 1
)

echo [run] Completed successfully.
endlocal
