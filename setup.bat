@echo off
REM Install dependencies and prepare the project.
where uv >nul 2>nul
if errorlevel 1 (
    echo [ERROR] uv is not installed. Install it from https://docs.astral.sh/uv/
    exit /b 1
)
pushd "%~dp0"
uv sync
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
