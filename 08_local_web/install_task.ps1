$ErrorActionPreference = 'Stop'
$OutputEncoding = [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$demoRoot = $PSScriptRoot
$demoTask = 'Microduck-Local-Web'
$demoIdentity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
$demoPython = Join-Path $demoRoot 'python\pythonw.exe'
$demoSupervisor = Join-Path $demoRoot 'supervise.py'
if (-not (Test-Path -LiteralPath $demoPython) -or -not (Test-Path -LiteralPath $demoSupervisor)) {
    throw 'Local runtime or supervisor is missing.'
}
$demoExisting = Get-ScheduledTask -TaskName $demoTask -ErrorAction SilentlyContinue
if ($demoExisting) {
    if ($demoExisting.Actions.Execute -ne $demoPython) {
        throw 'An unrelated task already uses this name; refusing to overwrite it.'
    }
}
$demoAction = New-ScheduledTaskAction -Execute $demoPython -Argument ('-B -u "{0}"' -f $demoSupervisor) -WorkingDirectory $demoRoot
$demoLogonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $demoIdentity.Name
$demoRecoveryTrigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddSeconds(10) -RepetitionInterval (New-TimeSpan -Minutes 1)
$demoPrincipal = New-ScheduledTaskPrincipal -UserId $demoIdentity.Name -LogonType Interactive -RunLevel Limited
$demoSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) -MultipleInstances IgnoreNew -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName $demoTask -Action $demoAction -Trigger @($demoLogonTrigger,$demoRecoveryTrigger) -Principal $demoPrincipal -Settings $demoSettings -Description 'Local Microduck demos: 127.0.0.1:8080 and 18080. Logon startup plus one-minute recovery trigger; no duplicate instances; simulated robot backend.' -Force | Select-Object TaskName,State
