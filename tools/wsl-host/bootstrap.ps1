# First-boot configuration for the WSL test host.
#
# This script runs as SYSTEM through Azure Run Command. It handles host-level
# setup: OpenSSH, Windows features required by WSL, and the WSL runtime package.

param(
    [Parameter(Mandatory)] [string] $SshPublicKeyB64,
    [string] $WslMsiSpec = 'latest'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = 'C:\wsl-host'
$SshPublicKey = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($SshPublicKeyB64)).Trim()

New-Item -ItemType Directory -Force -Path $Root | Out-Null
Start-Transcript -Path "$Root\bootstrap.log" -Append

function Resolve-GitHubRelease {
    param([string]$Repo, [bool]$Prerelease)
    $releases = Invoke-RestMethod "https://api.github.com/repos/$Repo/releases?per_page=20"
    $release = $releases | Where-Object { $_.prerelease -eq $Prerelease -and -not $_.draft } | Select-Object -First 1
    if (-not $release) { throw "No release found for $Repo (prerelease=$Prerelease)" }
    return $release
}

function Resolve-GitHubAsset {
    param([string]$Repo, [string]$Pattern, [bool]$Prerelease)
    $release = Resolve-GitHubRelease -Repo $Repo -Prerelease $Prerelease
    $asset = $release.assets | Where-Object { $_.name -match $Pattern } | Select-Object -First 1
    if (-not $asset) { throw "No asset matching '$Pattern' in $Repo $($release.tag_name)" }
    Write-Host "Using $Repo $($release.tag_name): $($asset.name)"
    return $asset.browser_download_url
}

function Get-Download {
    param([string]$Url, [string]$Name)
    $dest = "$Root\$Name"
    Write-Host "Downloading $Url -> $dest"
    Invoke-WebRequest -Uri $Url -OutFile $dest -UseBasicParsing
    return $dest
}

try {
    # --- OpenSSH Server -------------------------------------------------------
    Write-Host '== OpenSSH Server'
    $cap = Get-WindowsCapability -Online | Where-Object Name -like 'OpenSSH.Server*'
    if ($cap.State -ne 'Installed') {
        Add-WindowsCapability -Online -Name $cap.Name | Out-Null
    }
    # Start once so sshd generates its default config and host keys.
    Set-Service -Name sshd -StartupType Automatic
    Start-Service sshd
    Stop-Service sshd

    $sshDir = "$env:ProgramData\ssh"
    $sshdConfig = "$sshDir\sshd_config"
    $conf = Get-Content $sshdConfig -Raw
    $conf = $conf -replace '(?m)^#?\s*PasswordAuthentication\s+\w+', 'PasswordAuthentication no'
    $conf = $conf -replace '(?m)^#?\s*PubkeyAuthentication\s+\w+', 'PubkeyAuthentication yes'
    Set-Content -Path $sshdConfig -Value $conf -Encoding ascii

    # Members of Administrators authenticate against this file, not ~/.ssh.
    $authKeys = "$sshDir\administrators_authorized_keys"
    Set-Content -Path $authKeys -Value $SshPublicKey -Encoding ascii
    icacls $authKeys /inheritance:r /grant 'Administrators:F' /grant 'SYSTEM:F' | Out-Null

    # Allow SSH traffic
    if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' `
            -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Any | Out-Null
    }
    Set-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -Enabled True -Profile Any
    Start-Service sshd

    # --- WSL features ---------------------------------------------------------
    Write-Host '== Windows features'
    foreach ($feature in 'Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform') {
        Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
    }

    # --- WSL package ----------------------------------------------------------
    # Install the WSL package (not the WSL distros) that gives us the ``wsl`` CLI.
    # This could also be done with ``wsl --install --no-distribution``, but this
    # way we get to pin the version and avoid a dependency on the Microsoft Store.
    Write-Host '== WSL'
    $wslMsiUrl = switch ($WslMsiSpec) {
        'latest'     { Resolve-GitHubAsset -Repo 'microsoft/WSL' -Pattern '^wsl\..*x64\.msi$' -Prerelease $false }
        'prerelease' { Resolve-GitHubAsset -Repo 'microsoft/WSL' -Pattern '^wsl\..*x64\.msi$' -Prerelease $true }
        default      { $WslMsiSpec }
    }
    $wslMsi = Get-Download -Url $wslMsiUrl -Name 'wsl.msi'
    $msi = Start-Process msiexec.exe -Wait -PassThru -ArgumentList "/i `"$wslMsi`" /quiet /norestart"
    if ($msi.ExitCode -notin 0, 3010) { throw "WSL msiexec failed with $($msi.ExitCode)" }

    Write-Host '== Bootstrap complete; reboot required'
    Stop-Transcript
    exit 0
} catch {
    Write-Host "BOOTSTRAP FAILED: $_"
    Write-Host $_.ScriptStackTrace
    Stop-Transcript
    exit 1
}
