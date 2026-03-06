param(
    [string]$Version = ""
)

$ErrorActionPreference = "Stop"

if (-not $Version) {
    $Version = python -c "from _bootstrap import ensure_src_on_path; ensure_src_on_path(); from sap_role_updater.version import APP_VERSION; print(APP_VERSION)"
}

$distDir = Join-Path $PSScriptRoot "..\dist"
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$exePath = Join-Path $distDir "SAP Role Updater.exe"
$zipPath = Join-Path $distDir "SAP Role Updater v$Version.zip"
$stagingDir = Join-Path $distDir "_release_pack"

if (-not (Test-Path $exePath)) {
    throw "Missing build artifact: $exePath"
}

if (Test-Path $stagingDir) {
    Remove-Item -Recurse -Force $stagingDir
}
if (Test-Path $zipPath) {
    Remove-Item -Force $zipPath
}

New-Item -ItemType Directory -Force -Path $stagingDir | Out-Null
Copy-Item $exePath (Join-Path $stagingDir "SAP Role Updater.exe")
Copy-Item (Join-Path $repoRoot "templates\RULES_template.xlsx") (Join-Path $stagingDir "RULES_template.xlsx")
Copy-Item (Join-Path $repoRoot "README.md") (Join-Path $stagingDir "README.md")
Copy-Item (Join-Path $repoRoot "docs\user\HELP.md") (Join-Path $stagingDir "HELP.md")
Copy-Item (Join-Path $repoRoot "LICENSE") (Join-Path $stagingDir "LICENSE")

Compress-Archive -Path (Join-Path $stagingDir "*") -DestinationPath $zipPath -Force
Remove-Item -Recurse -Force $stagingDir

Write-Output $zipPath
