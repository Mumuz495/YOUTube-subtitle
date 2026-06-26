param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl,

    [string]$RemoteName = "origin",

    [string]$Branch = "main",

    [switch]$UpdateExistingRemote,

    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

Push-Location $ProjectRoot
try {
    if (-not $SkipPreflight) {
        Write-Host "Running preflight..." -ForegroundColor Cyan
        py scripts\preflight.py
    }

    $status = git status --short
    $nonIgnoredChanges = $status | Where-Object { $_ -notmatch '^!! ' }
    if ($nonIgnoredChanges) {
        Write-Host "Git working tree has uncommitted changes:" -ForegroundColor Yellow
        $nonIgnoredChanges | ForEach-Object { Write-Host $_ }
        throw "Commit or stash changes before publishing."
    }

    $existingUrl = git remote get-url $RemoteName 2>$null
    if ($LASTEXITCODE -eq 0 -and $existingUrl) {
        if (-not $UpdateExistingRemote) {
            Write-Host "Remote '$RemoteName' already exists: $existingUrl" -ForegroundColor Yellow
            Write-Host "Run again with -UpdateExistingRemote to replace it." -ForegroundColor Yellow
            exit 1
        }
        git remote set-url $RemoteName $RemoteUrl
    }
    else {
        git remote add $RemoteName $RemoteUrl
    }

    Write-Host "Pushing $Branch to $RemoteName..." -ForegroundColor Cyan
    git push -u $RemoteName $Branch

    Write-Host ""
    Write-Host "Published successfully." -ForegroundColor Green
    Write-Host "Next: open GitHub Actions and wait for CI to pass, then deploy with Render or Fly.io." -ForegroundColor Green
}
finally {
    Pop-Location
}
