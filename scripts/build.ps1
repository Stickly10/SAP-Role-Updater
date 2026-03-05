param(
    [switch]$CollectAllQt,
    [switch]$Package
)

$ErrorActionPreference = "Stop"

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (-not (Test-Path dist)) { New-Item -ItemType Directory -Force dist | Out-Null }
Get-ChildItem dist -File -Filter "SAP Role Updater.exe" -ErrorAction SilentlyContinue | Remove-Item -Force
Get-ChildItem dist -File -Filter "SAP Role Updater v*.zip" -ErrorAction SilentlyContinue | Remove-Item -Force

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts\generate_rules_template.py

if ($CollectAllQt) {
    pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --icon "SAP-Role-Updater-Logo.ico" --add-data "SAP-Role-Updater-Logo.ico;." --add-data "templates\\RULES_template.xlsx;templates" --collect-all PySide6 main.py
}
else {
    pyinstaller --clean SAP-Role-Updater.spec
}

if ($Package) {
    & (Join-Path $PSScriptRoot "package_release.ps1")
}
