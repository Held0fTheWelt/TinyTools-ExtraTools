@echo off
setlocal
python "%~dp0docker-up.py" %*
exit /b %ERRORLEVEL%
