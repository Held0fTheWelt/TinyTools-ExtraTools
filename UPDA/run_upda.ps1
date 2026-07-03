param(
    [int]$Port = 8776,
    [string]$HostName = "127.0.0.1",
    [string[]]$SourceRoot = @(),
    [string]$StateRoot = ""
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$WorkspaceRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..")).Path

function Test-PortFree {
    param([int]$Candidate)
    $Connection = Get-NetTCPConnection -LocalPort $Candidate -State Listen -ErrorAction SilentlyContinue
    return $null -eq $Connection
}

function Find-FreePort {
    param([int]$StartPort)
    $Candidate = $StartPort
    while (-not (Test-PortFree -Candidate $Candidate)) {
        $Candidate++
        if ($Candidate -gt 65535) {
            throw "No free TCP port found after $StartPort."
        }
    }
    return $Candidate
}

$HostPort = Find-FreePort -StartPort $Port
if ($HostPort -ne $Port) {
    Write-Host "Port $Port is busy. Using $HostPort instead." -ForegroundColor Yellow
}

$ArgsList = @(
    (Join-Path $ScriptDir "upda.py"),
    "--host", $HostName,
    "--port", "$HostPort"
)

if ($StateRoot) {
    $ArgsList += @("--state-root", $StateRoot)
}

foreach ($Root in $SourceRoot) {
    $ArgsList += @("--source-root", $Root)
}

Write-Host "Unreal Project Design Assistant" -ForegroundColor Green
Write-Host "Workspace: $WorkspaceRoot"
Write-Host "URL: http://${HostName}:$HostPort"
Write-Host "Stop: press Ctrl+C in this window."
Write-Host ""

Push-Location $WorkspaceRoot
try {
    python @ArgsList
} finally {
    Pop-Location
}
