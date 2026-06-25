@echo off
set SCRIPT_DIR=%~dp0
start "Tiny Tool UML Browser" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_uml_browser.ps1"
