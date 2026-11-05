# Waits for the WSL CLI and native distro catalog to become available after
# the reboot. Runs as SYSTEM through an Azure Run Command.

param(
    [int] $TimeoutMinutes = 25
)

$deadline = (Get-Date).AddMinutes($TimeoutMinutes)

while ((Get-Date) -lt $deadline) {
    wsl --version
    if ($LASTEXITCODE -eq 0) {
        wsl --list --online
        if ($LASTEXITCODE -eq 0) {
            Write-Host 'WSL host ready'
            exit 0
        }
    }
    Start-Sleep -Seconds 15
}

Write-Host "Host not ready after $TimeoutMinutes minutes."
exit 1
