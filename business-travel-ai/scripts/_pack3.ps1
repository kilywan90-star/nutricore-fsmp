$ErrorActionPreference = "Stop"
$tarball = "$env:TEMP\btai3-deploy.tar.gz"
Set-Location "e:\qoder"

if (Test-Path $tarball) { Remove-Item $tarball -Force }

& 'C:\Windows\System32\tar.exe' czf $tarball `
    --exclude='node_modules' `
    --exclude='data/*.db' `
    --exclude='data/*.db-shm' `
    --exclude='data/*.db-wal' `
    --exclude='.env' `
    --exclude='.env.local' `
    --exclude='.git' `
    --exclude='*.tsbuildinfo' `
    -C 'e:\qoder' 'business-travel-ai'

if ($LASTEXITCODE -ne 0) { throw "tar failed" }

$size = [math]::Round((Get-Item $tarball).Length / 1MB, 1)
Write-Host "Package: $tarball ($size MB)"
