param(
    [int]$Port = 8765,
    [string]$ImageName = "tinytool-uml-browser:local",
    [string]$ContainerName = "tinytool-uml-browser",
    [switch]$NoBuild
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path -LiteralPath (Join-Path $ScriptDir "..\..")).Path
$SavedRoot = Join-Path $RepoRoot "Saved\UmlBrowser"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Checked {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Command failed with exit code ${LASTEXITCODE}: $FilePath $($Arguments -join ' ')"
    }
}

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

Write-Host "Tiny Tool UML Browser Docker status window" -ForegroundColor Green
Write-Host "Repo: $RepoRoot"

Write-Step "Checking Docker"
Invoke-Checked docker @("info")

New-Item -ItemType Directory -Force -Path $SavedRoot | Out-Null

if (-not $NoBuild) {
    Write-Step "Building Docker image $ImageName"
    Invoke-Checked docker @("build", "--pull", "-t", $ImageName, $ScriptDir)
}

$HostPort = Find-FreePort -StartPort $Port
if ($HostPort -ne $Port) {
    Write-Host "Port $Port is busy. Using $HostPort instead." -ForegroundColor Yellow
}

Write-Step "Replacing old container if present"
$Existing = docker ps -aq --filter "name=^/$ContainerName$"
if ($Existing) {
    Invoke-Checked docker @("rm", "-f", $ContainerName)
} else {
    Write-Host "No previous $ContainerName container found."
}

Write-Step "Deploying and attaching logs"
Write-Host "URL: http://127.0.0.1:$HostPort"
Write-Host "Stop: press Ctrl+C in this window."
Write-Host ""

Invoke-Checked docker @(
    "run",
    "--rm",
    "--name", $ContainerName,
    "-p", "${HostPort}:8765",
    "-v", "${RepoRoot}:/workspace",
    $ImageName
)
