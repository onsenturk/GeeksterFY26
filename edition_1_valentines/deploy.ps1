$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$zipPath = Join-Path $root "deploy.zip"

if (Test-Path $zipPath) {
  Remove-Item $zipPath -Force
}

$include = @(
  "app",
  "data",
  "requirements.txt",
  "README.md",
  "roadmap.md"
)

$staging = Join-Path $root ".deploy_staging"
if (Test-Path $staging) {
  Remove-Item $staging -Recurse -Force
}

New-Item -ItemType Directory -Path $staging | Out-Null

foreach ($item in $include) {
  $source = Join-Path $root $item
  if (Test-Path $source) {
    Copy-Item $source -Destination $staging -Recurse -Force
  }
}

Get-ChildItem -Path $staging -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -File -Filter "*.pyc" | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $staging -Recurse -File -Filter "valentines.db" | Remove-Item -Force -ErrorAction SilentlyContinue

Compress-Archive -Path (Join-Path $staging "*") -DestinationPath $zipPath
Remove-Item $staging -Recurse -Force

Write-Host "Created $zipPath"