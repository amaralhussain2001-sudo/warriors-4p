# Run a Ghidra script headless, read-only, against the analysed game executable.
# Usage: powershell -File tools\ghidra\run_script.ps1 <ScriptName.java> [script args...]
param([Parameter(Mandatory = $true)][string]$Script, [Parameter(ValueFromRemainingArguments = $true)][string[]]$ScriptArgs)
$proj = Join-Path $PSScriptRoot "..\..\local\ghidra"
$ghidra = "C:\Users\PC FORCE\Desktop\New folder\ghidra_12.1.4_PUBLIC\support\analyzeHeadless.bat"
& $ghidra (Resolve-Path $proj) warriors -process SLUS_212.15 -noanalysis -readOnly -scriptPath $PSScriptRoot -postScript $Script @ScriptArgs 2>&1 |
    Where-Object { $_ -match "ERROR|Exception|wrote|SCRIPT|no function" } | ForEach-Object { "$_" }
