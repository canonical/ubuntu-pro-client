# Blocks until the post-logon task (phase 2 of bootstrap.ps1) has written the
# READY marker, so `terraform apply` only returns once the host is usable.
# Runs as SYSTEM through an Azure run command after the reboot.

param(
    [int] $TimeoutMinutes = 25
)

$Root = 'C:\wsl-host'
$deadline = (Get-Date).AddMinutes($TimeoutMinutes)

while (-not (Test-Path "$Root\READY")) {
    if ((Get-Date) -gt $deadline) {
        Write-Host "Host not ready after $TimeoutMinutes minutes. Tail of phase2.log:"
        Get-Content "$Root\phase2.log" -Tail 40 -ErrorAction SilentlyContinue
        exit 1
    }
    Start-Sleep -Seconds 15
}

Write-Host "READY at $(Get-Content "$Root\READY")"
wsl --version
exit 0
