@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0track-shape-docker.ps1" %*
exit /b %ERRORLEVEL%
