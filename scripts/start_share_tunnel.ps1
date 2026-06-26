param(
    [int]$Port = 8765,
    [string]$Username = "friend",
    [string]$Password = "",
    [ValidateSet("auto", "quic", "http2")]
    [string]$Protocol = "auto",
    [switch]$SkipDownload
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$ToolsDir = Join-Path $ProjectRoot ".tools"
$CloudflaredPath = Join-Path $ToolsDir "cloudflared.exe"
$PythonLauncher = "py"

function Read-PlainPassword {
    $secure = Read-Host "Set a temporary website password" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Resolve-Cloudflared {
    $existing = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($existing) {
        return $existing.Source
    }

    if ($SkipDownload) {
        throw "cloudflared is not installed. Install it first or run without -SkipDownload."
    }

    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
    if (-not (Test-Path $CloudflaredPath)) {
        $downloadUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
        Write-Host "Downloading cloudflared..." -ForegroundColor Cyan
        Invoke-WebRequest -Uri $downloadUrl -OutFile $CloudflaredPath
    }
    return $CloudflaredPath
}

if (-not $Password) {
    $Password = Read-PlainPassword
}

if (-not $Password) {
    throw "A password is required before sharing this tool on the public Internet."
}

Push-Location $ProjectRoot
try {
    $cloudflared = Resolve-Cloudflared

    $env:HOST = "127.0.0.1"
    $env:PORT = [string]$Port
    $env:APP_USERNAME = $Username
    $env:APP_PASSWORD = $Password
    $env:PUBLIC_DEPLOYMENT = "1"
    $env:RATE_LIMIT_ENABLED = "1"
    $env:OUTPUT_RETENTION_HOURS = "24"

    Write-Host "Starting Subtitle Studio at http://127.0.0.1:$Port ..." -ForegroundColor Cyan
    $appProcess = Start-Process `
        -FilePath $PythonLauncher `
        -ArgumentList "app.py" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -PassThru

    Start-Sleep -Seconds 3

    try {
        Write-Host ""
        Write-Host "Share the trycloudflare.com URL printed below with your friends." -ForegroundColor Green
        Write-Host "Username: $Username" -ForegroundColor Green
        Write-Host "Password: the temporary password you just set" -ForegroundColor Green
        Write-Host ""
        $tunnelArgs = @("tunnel")
        if ($Protocol -ne "auto") {
            $tunnelArgs += @("--protocol", $Protocol)
        }
        $tunnelArgs += @("--url", "http://127.0.0.1:$Port")

        & $cloudflared @tunnelArgs
    }
    finally {
        if ($appProcess -and -not $appProcess.HasExited) {
            Stop-Process -Id $appProcess.Id -Force
        }
    }
}
finally {
    Pop-Location
}
