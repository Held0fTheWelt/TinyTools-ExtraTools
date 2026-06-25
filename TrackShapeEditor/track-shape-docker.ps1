# Track Shape Editor — Docker helper (PowerShell wrapper → docker-up.py)
#Requires -Version 5.1
[CmdletBinding()]
param(
    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ErrorActionPreference = 'Stop'
$py = Get-Command python -ErrorAction SilentlyContinue
if (-not $py) {
    Write-Host 'Python not found. Install Python 3 and ensure it is on PATH.' -ForegroundColor Red
    exit 1
}
& python (Join-Path $PSScriptRoot 'docker-up.py') @Args
exit $LASTEXITCODE
