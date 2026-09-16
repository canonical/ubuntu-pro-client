# First-boot configuration for the WSL test host.
#
# Runs once as SYSTEM through an Azure run command. Sets up everything that
# does not need a user session and registers a logon-triggered task
# (phase 2) that runs as the admin user after the reboot Terraform performs
# next. Phase 2 writes C:\wsl-host\READY once winget and WSL are usable.

param(
    [Parameter(Mandatory)] [string] $AdminUser,
    [Parameter(Mandatory)] [string] $AdminPasswordB64,
    [Parameter(Mandatory)] [string] $SshPublicKeyB64,
    [string] $WslMsiSpec = 'latest'
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$Root = 'C:\wsl-host'
$AdminPassword = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($AdminPasswordB64))
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

    if (-not (Get-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -ErrorAction SilentlyContinue)) {
        # Azure NICs land in the Public profile; without -Profile Any this
        # rule would only cover Private/Domain and silently drop inbound SSH.
        New-NetFirewallRule -Name 'OpenSSH-Server-In-TCP' -DisplayName 'OpenSSH Server (sshd)' `
            -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 -Profile Any | Out-Null
    }
    Start-Service sshd

    # --- WSL features ---------------------------------------------------------
    Write-Host '== Windows features'
    foreach ($feature in 'Microsoft-Windows-Subsystem-Linux', 'VirtualMachinePlatform') {
        Enable-WindowsOptionalFeature -Online -FeatureName $feature -All -NoRestart | Out-Null
    }

    # --- WSL package ----------------------------------------------------------
    # Installed from the GitHub release MSI so we control the version and do
    # not depend on the Microsoft Store.
    Write-Host '== WSL'
    $wslMsiUrl = switch ($WslMsiSpec) {
        'latest'     { Resolve-GitHubAsset -Repo 'microsoft/WSL' -Pattern '^wsl\..*x64\.msi$' -Prerelease $false }
        'prerelease' { Resolve-GitHubAsset -Repo 'microsoft/WSL' -Pattern '^wsl\..*x64\.msi$' -Prerelease $true }
        default      { $WslMsiSpec }
    }
    $wslMsi = Get-Download -Url $wslMsiUrl -Name 'wsl.msi'
    $msi = Start-Process msiexec.exe -Wait -PassThru -ArgumentList "/i `"$wslMsi`" /quiet /norestart"
    if ($msi.ExitCode -notin 0, 3010) { throw "WSL msiexec failed with $($msi.ExitCode)" }

    # --- winget ---------------------------------------------------------------
    # The Azure image ships without a usable App Installer. winget is only ever
    # needed inside the admin user's own session (both phase 2 here and later
    # test runs use it as that user over SSH), so install it there rather than
    # provisioning it as SYSTEM: a provisioned package is only picked up by
    # accounts that don't exist yet, not this already-created profile. Just
    # fetch the installer artifacts now; phase 2 installs them as the user.
    Write-Host '== winget (downloading for phase 2 to install)'
    $wingetRelease = Resolve-GitHubRelease -Repo 'microsoft/winget-cli' -Prerelease $false
    Write-Host "Using microsoft/winget-cli $($wingetRelease.tag_name)"
    function Get-WingetAsset {
        param([string]$Pattern)
        $asset = $wingetRelease.assets | Where-Object { $_.name -match $Pattern } | Select-Object -First 1
        if (-not $asset) { throw "No asset matching '$Pattern' in winget-cli $($wingetRelease.tag_name)" }
        return $asset.browser_download_url
    }

    Get-Download -Url (Get-WingetAsset '\.msixbundle$') -Name 'winget.msixbundle' | Out-Null
    $depsZip = Get-Download -Url (Get-WingetAsset '^DesktopAppInstaller_Dependencies\.zip$') -Name 'winget-deps.zip'

    $depsDir = "$Root\winget-deps"
    Remove-Item -Recurse -Force $depsDir -ErrorAction SilentlyContinue
    Expand-Archive -Path $depsZip -DestinationPath $depsDir -Force
    if (-not (Get-ChildItem -Path "$depsDir\x64" -Filter '*.appx' -Recurse)) {
        throw 'No x64 dependency packages found in DesktopAppInstaller_Dependencies.zip'
    }

    # --- Automatic logon ------------------------------------------------------
    # winget needs an interactive user session; the harness reaches it over
    # SSH as the same user, so keep that user logged on after every boot.
    Write-Host '== Automatic logon'
    $winlogon = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
    Set-ItemProperty -Path $winlogon -Name AutoAdminLogon -Value '1' -Type String
    Set-ItemProperty -Path $winlogon -Name DefaultUserName -Value $AdminUser -Type String
    Set-ItemProperty -Path $winlogon -Name DefaultPassword -Value $AdminPassword -Type String
    Set-ItemProperty -Path $winlogon -Name DefaultDomainName -Value $env:COMPUTERNAME -Type String

    # --- Phase 2: runs as the admin user after logon --------------------------
    Write-Host '== Phase 2 task'
    $phase2 = @'
$ErrorActionPreference = 'Stop'
$Root = 'C:\wsl-host'
Start-Transcript -Path "$Root\phase2.log" -Append
try {
    # Install as this user's own session, the same way any interactive user
    # would sideload the app -- this is the supported path for making a UWP
    # package usable by a specific, already-existing account.
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host 'Installing winget for this user'
        $deps = @(Get-ChildItem -Path "$Root\winget-deps\x64" -Filter '*.appx' -Recurse | ForEach-Object { $_.FullName })
        Add-AppxPackage -Path "$Root\winget.msixbundle" -DependencyPath $deps `
            -ForceApplicationShutdown -ForceUpdateFromAnyVersion
    }
    winget --version
    wsl --version
    Set-Content -Path "$Root\READY" -Value (Get-Date -Format o)
    Write-Host 'Host ready'
} finally {
    Stop-Transcript
}
'@
    Set-Content -Path "$Root\phase2.ps1" -Value $phase2 -Encoding ascii

    $action = New-ScheduledTaskAction -Execute 'powershell.exe' `
        -Argument "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File $Root\phase2.ps1"
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User $AdminUser
    $principal = New-ScheduledTaskPrincipal -UserId $AdminUser -LogonType Interactive -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    Register-ScheduledTask -TaskName 'wsl-host-phase2' -Action $action -Trigger $trigger `
        -Principal $principal -Settings $settings -Force | Out-Null

    Write-Host '== Bootstrap complete; reboot required'
    Stop-Transcript
    exit 0
} catch {
    Write-Host "BOOTSTRAP FAILED: $_"
    Write-Host $_.ScriptStackTrace
    Stop-Transcript
    exit 1
}
