$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

if (Test-Path (Join-Path $scriptDir ".venv312\Scripts\python.exe")) {
    & (Join-Path $scriptDir ".venv312\Scripts\python.exe") (Join-Path $scriptDir "app.py")
} elseif (Test-Path (Join-Path $scriptDir "venv\Scripts\python.exe")) {
    & (Join-Path $scriptDir "venv\Scripts\python.exe") (Join-Path $scriptDir "app.py")
} else {
    python (Join-Path $scriptDir "app.py")
}
