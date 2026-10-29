[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$Spec = Join-Path $Root "packaging\resale_manager.spec"
$Dist = Join-Path $Root "dist"
$Work = Join-Path $Root "build"

if (-not (Test-Path -LiteralPath $Python)) {
    throw "Python virtual environment not found at $Python"
}

& $Python -c "import PyInstaller" 2>$null
if ($LASTEXITCODE -ne 0) {
    Push-Location $Root
    try {
        & $Python -m pip install "pyinstaller>=6.10"
        if ($LASTEXITCODE -ne 0) {
            throw "Could not install the packaging dependencies."
        }
    }
    finally {
        Pop-Location
    }
}

$Arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--distpath", $Dist,
    "--workpath", $Work
)
if ($Clean) {
    $Arguments += "--clean"
}
$Arguments += $Spec

& $Python @Arguments
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE."
}

$ApplicationDirectory = Join-Path $Dist "ResaleManager"
$BundleInternal = Join-Path $ApplicationDirectory "_internal"
if (Test-Path -LiteralPath $BundleInternal) {
    Get-ChildItem -LiteralPath $BundleInternal `
        -Recurse -Directory -Filter "__pycache__" `
        | Remove-Item -Recurse -Force
}
Copy-Item -LiteralPath (Join-Path $Root ".env.example") `
    -Destination (Join-Path $ApplicationDirectory ".env.example") `
    -Force
Copy-Item -LiteralPath (Join-Path $Root "README.md") `
    -Destination (Join-Path $ApplicationDirectory "README.md") `
    -Force

Write-Host "Built desktop executable:"
Write-Host "  $(Join-Path $ApplicationDirectory 'ResaleManager.exe')"
Write-Host "Application data will be stored in:"
Write-Host "  $(Join-Path $ApplicationDirectory 'data')"
