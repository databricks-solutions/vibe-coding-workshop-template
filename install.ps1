#Requires -RunAsAdministrator
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Info  { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Green }
function Write-Warn  { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Write-Err   { param($msg) Write-Host "[ERROR] $msg" -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------------------
# winget (Windows Package Manager)
# ---------------------------------------------------------------------------
if (Get-Command winget -ErrorAction SilentlyContinue) {
    Write-Info "winget already available"
} else {
    Write-Err "winget is not installed. Please update 'App Installer' from the Microsoft Store."
}

# ---------------------------------------------------------------------------
# Helper: install or upgrade a winget package
# ---------------------------------------------------------------------------
function Install-OrUpgrade {
    param (
        [string]$PackageId,
        [string]$DisplayName
    )
    $installed = winget list --id $PackageId 2>$null
    if ($LASTEXITCODE -eq 0 -and $installed -match $PackageId) {
        Write-Info "$DisplayName already installed — upgrading..."
        winget upgrade --id $PackageId --accept-source-agreements --accept-package-agreements --silent
    } else {
        Write-Info "Installing $DisplayName..."
        winget install --id $PackageId --accept-source-agreements --accept-package-agreements --silent
    }
}

# ---------------------------------------------------------------------------
# Core tools
# ---------------------------------------------------------------------------
Install-OrUpgrade -PackageId "Git.Git"                 -DisplayName "Git"
Install-OrUpgrade -PackageId "Python.Python.3.12"      -DisplayName "Python 3"
Install-OrUpgrade -PackageId "OpenJS.NodeJS.LTS"       -DisplayName "Node.js (LTS)"
Install-OrUpgrade -PackageId "Databricks.DatabricksCLI" -DisplayName "Databricks CLI"

# ---------------------------------------------------------------------------
# Refresh PATH so newly installed tools are visible
# ---------------------------------------------------------------------------
$env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
            [System.Environment]::GetEnvironmentVariable("Path", "User")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
Write-Host ""
Write-Info "Installation complete. Versions installed:"
try { Write-Host "  git        : $(git --version)" }         catch { Write-Warn "git not on PATH yet — restart terminal" }
try { Write-Host "  python     : $(python --version)" }      catch { Write-Warn "python not on PATH yet — restart terminal" }
try { Write-Host "  node       : $(node --version)" }        catch { Write-Warn "node not on PATH yet — restart terminal" }
try { Write-Host "  databricks : $(databricks --version)" }   catch { Write-Warn "databricks not on PATH yet — restart terminal" }

Write-Host ""
Write-Info "Done. You may need to restart your terminal for PATH changes to take effect."
