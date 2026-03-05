param(
    [switch]$CollectAllQt
)

$ErrorActionPreference = "Stop"

if (Test-Path build) { Remove-Item -Recurse -Force build }
if (Test-Path dist) { Remove-Item -Recurse -Force dist }

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if ($CollectAllQt) {
    pyinstaller --noconsole --onefile --clean --name "SAP Role Updater" --collect-all PySide6 main.py
}
else {
    pyinstaller --clean SAP-Role-Updater.spec
}
