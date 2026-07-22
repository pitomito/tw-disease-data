# One-time setup script: registers a Windows Task Scheduler task that runs
# refresh_local.ps1 every Monday at 08:00. Uses pwsh (PowerShell 7) as the
# executor; runs only when the user is logged on (no stored password needed,
# so git push can reuse the current user's gh/git credentials).
$ErrorActionPreference = "Stop"

$repo     = "C:\Users\cheng\claude_code\tw-disease-data"
$script   = Join-Path $repo "scripts\refresh_local.ps1"
$pwsh     = (Get-Command pwsh).Source
$taskName = "tw-disease-data-weekly-refresh"

if (Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue) {
    Write-Output "Task already exists; removing and recreating."
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action    = New-ScheduledTaskAction -Execute $pwsh `
    -Argument "-NoProfile -File `"$script`"" -WorkingDirectory $repo
$trigger   = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 8:00am
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -DontStopOnIdleEnd -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal `
    -Description "Weekly: fetch latest Taiwan CDC open data, update data/snapshot, push to trigger GitHub Actions rebuild+deploy." `
    | Out-Null

Write-Output "Task created: $taskName"
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State
Get-ScheduledTaskInfo -TaskName $taskName | Select-Object NextRunTime, LastTaskResult
