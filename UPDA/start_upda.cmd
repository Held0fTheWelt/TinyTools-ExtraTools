@echo off
set SCRIPT_DIR=%~dp0
start "Unreal Project Design Assistant" powershell.exe -NoExit -ExecutionPolicy Bypass -File "%SCRIPT_DIR%run_upda.ps1"
