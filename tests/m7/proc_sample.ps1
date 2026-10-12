# M7 criterion 8: CPU and memory of every running pcsx2-qtx64 process, one row per process every -Every seconds.
# Read-only (Get-Process); never stops a process. Usage: proc_sample.ps1 -Out file.csv [-Seconds 3900] [-Every 60]
param([Parameter(Mandatory = $true)][string]$Out, [int]$Seconds = 3900, [int]$Every = 60)
$t0 = Get-Date
"time_s,pid,cpu_s,working_set_mb,private_mb,threads" | Out-File -FilePath $Out -Encoding ascii
while (((Get-Date) - $t0).TotalSeconds -lt $Seconds) {
    $t = [int]((Get-Date) - $t0).TotalSeconds
    foreach ($p in @(Get-Process -Name "pcsx2-qtx64" -ErrorAction SilentlyContinue)) {
        $cpu = $(if ($null -ne $p.CPU) { [Math]::Round($p.CPU, 1) } else { -1 })
        ("{0},{1},{2},{3},{4},{5}" -f $t, $p.Id, $cpu, [Math]::Round($p.WorkingSet64 / 1MB, 1),
            [Math]::Round($p.PrivateMemorySize64 / 1MB, 1), $p.Threads.Count) | Out-File -FilePath $Out -Append -Encoding ascii
    }
    Start-Sleep -Seconds $Every
}
