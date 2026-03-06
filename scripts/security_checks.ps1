param(
    [switch]$UpgradePip
)

$ErrorActionPreference = "Stop"

if ($UpgradePip) {
    python -m pip install --upgrade pip
}

Write-Host "[ruff] python -m ruff check ."
python -m ruff check .

Write-Host "[pytest] python -m pytest"
python -m pytest

Write-Host "[i18n-audit] python scripts\\i18n_audit.py"
python scripts\i18n_audit.py

if (Get-Command pip-audit -ErrorAction SilentlyContinue) {
    Write-Host "[pip-audit] pip-audit -r requirements.txt"
    pip-audit -r requirements.txt
    Write-Host "[pip-audit] pip-audit -r requirements-dev.txt"
    pip-audit -r requirements-dev.txt
}
else {
    Write-Host "[pip-audit] not installed. Install with: python -m pip install pip-audit"
}

if (Get-Command bandit -ErrorAction SilentlyContinue) {
    Write-Host "[bandit] bandit -r src scripts main.py -x build,dist,tests,scripts\\smoke_test.py"
    bandit -r src scripts main.py -x build,dist,tests,scripts\smoke_test.py
}
else {
    Write-Host "[bandit] not installed. Install with: python -m pip install bandit"
}
