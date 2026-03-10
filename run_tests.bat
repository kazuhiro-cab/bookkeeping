@echo off
setlocal

set VENV_DIR=.venv

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo [test] ERROR: virtual environment not found.
  echo [test] Please run setup.bat first.
  exit /b 1
)

echo [test] Running test suite ...
"%VENV_DIR%\Scripts\python.exe" -m unittest discover -s tests
if errorlevel 1 (
  echo [test] Tests failed.
  exit /b 1
)

echo [test] Completed successfully.
endlocal
