param(
    [int]$Port = 8000
)

Set-Location $PSScriptRoot\backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port $Port
