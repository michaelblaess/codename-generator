@echo off
REM Launch the codename generator. Args are forwarded to the CLI/TUI.
pushd "%~dp0"
uv run codename %*
set EXITCODE=%ERRORLEVEL%
popd
exit /b %EXITCODE%
