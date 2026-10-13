# Unit test of the co-op save list in the package launcher (package4/Start-Coop.ps1): List-Groups, Choose-Group (number,
# Enter, N, D with confirm, D cancelled, a typed name) and Menu-Saves delete. The launcher's function definitions are
# loaded from the script's syntax tree (its main code does not run); Read-Host is replaced by scripted answers; every
# file lives in a temporary folder under local/. Usage: powershell -NoProfile -ExecutionPolicy Bypass -File
# tests/m5/save_menu_test.ps1 [-Script package4/Start-Coop.ps1] [-Out evidence/M5/save_menu.json]
param([string]$Script = "", [string]$Out = "")
$ErrorActionPreference = "Stop"
$proj = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if ($Script -eq "") { $Script = Join-Path $proj "package4\Start-Coop.ps1" }
$work = Join-Path $proj ("local\m5\save_menu_" + (Get-Date).ToString("yyyyMMdd_HHmmss"))
New-Item -ItemType Directory -Force -Path $work | Out-Null

$tokens = $null; $errs = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile((Resolve-Path $Script), [ref]$tokens, [ref]$errs)
if ($errs.Count) { throw "the launcher does not parse" }
foreach ($f in $ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $false)) {
    . ([scriptblock]::Create($f.Extent.Text))
}

$Inv = [System.Globalization.CultureInfo]::InvariantCulture
$utf8 = New-Object System.Text.UTF8Encoding($false)
$savesRoot = Join-Path $work "coop-saves"
$settingsFile = Join-Path $work "my-settings.txt"
$script:answers = New-Object System.Collections.Queue
function Read-Host([string]$prompt) {
    if ($script:answers.Count -eq 0) { throw "test ran out of answers at: $prompt" }
    $a = $script:answers.Dequeue()
    Write-Output "" | Out-Null
    [Console]::WriteLine("    > " + $prompt + "  <- '" + $a + "'")
    return $a
}

function Make-Save([string]$g, [datetime]$t, [bool]$files) {
    $d = Join-Path $savesRoot $g
    New-Item -ItemType Directory -Force -Path $d | Out-Null
    if ($files) {
        foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
            $p = Join-Path $d $m
            [System.IO.File]::WriteAllBytes($p, [byte[]](1..64))
            (Get-Item -LiteralPath $p).LastWriteTime = $t
        }
    }
}
Make-Save "book" ([datetime]"2026-10-13 08:54") $true
Make-Save "friends" ([datetime]"2026-10-13 12:00") $true
Make-Save "zzz" ([datetime]"2026-01-01") $false
New-Item -ItemType Directory -Force -Path (Join-Path $savesRoot "_deleted") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $savesRoot "bad!name") | Out-Null

$results = [ordered]@{}
function Check([string]$name, [bool]$ok, $detail) {
    $results[$name] = [ordered]@{ ok = $ok; detail = "$detail" }
    Write-Host ("{0}  {1}  {2}" -f $(if ($ok) { "PASS" } else { "FAIL" }), $name, $detail)
}
function Run-Choose($s, [string[]]$ans) {
    $script:answers.Clear(); foreach ($a in $ans) { $script:answers.Enqueue($a) }
    $g = Choose-Group $s
    return @{ g = $g; left = $script:answers.Count }
}

$l = @(List-Groups)
Check "list order (newest first, invalid and _deleted hidden)" (($l -join ",") -eq "friends,book,zzz") ($l -join ",")
$s = @{}
$r = Run-Choose $s @("2")
Check "number 2 picks the 2nd save" ($r.g -eq "book" -and $s["Group"] -eq "book" -and $r.left -eq 0) $r.g
$r = Run-Choose $s @("")
Check "Enter picks the last used save" ($r.g -eq "book") $r.g
$r = Run-Choose $s @("N", "new one")
Check "N makes a new save name" ($r.g -eq "new one") $r.g
$r = Run-Choose $s @("N", "bad!", "ok2")
Check "N refuses a bad name and asks again" ($r.g -eq "ok2") $r.g
$r = Run-Choose $s @("D", "", "1")
Check "D then Enter cancels (nothing deleted)" ($r.g -eq "friends" -and (Test-Path -LiteralPath (Join-Path $savesRoot "friends"))) $r.g
$r = Run-Choose $s @("D", "1", "no", "1")
Check "D with 'no' keeps the save" ((Test-Path -LiteralPath (Join-Path $savesRoot "friends")) -and $r.g -eq "friends") $r.g
$r = Run-Choose $s @("D", "1", "yes", "1")
$moved = @(Get-ChildItem -LiteralPath (Join-Path $savesRoot "_deleted") -Directory | Where-Object { $_.Name -like "friends_*" })
Check "D + yes moves the save to _deleted (files kept), list moves up" (-not (Test-Path -LiteralPath (Join-Path $savesRoot "friends")) -and
    $moved.Count -eq 1 -and (Test-Path -LiteralPath (Join-Path $moved[0].FullName "Mcd001.ps2")) -and $r.g -eq "book") ("chose " + $r.g + ", moved " + $moved.Count)
$r = Run-Choose $s @("legacy")
Check "a typed name still works" ($r.g -eq "legacy") $r.g
$r = Run-Choose $s @("x", "1")
Check "a wrong answer asks again" ($r.g -eq "book") $r.g
$script:answers.Clear(); foreach ($a in @("D", "2", "yes", "")) { $script:answers.Enqueue($a) }
Menu-Saves
Check "Settings > co-op saves: delete" (-not (Test-Path -LiteralPath (Join-Path $savesRoot "zzz")) -and $script:answers.Count -eq 0) "zzz deleted"
Remove-Item -Recurse -Force -LiteralPath $savesRoot
$s2 = @{ Group = "book" }
$r = Run-Choose $s2 @("")
Check "no saves at all: asks for a name, Enter takes the last name" ($r.g -eq "book") $r.g
$settings = [System.IO.File]::ReadAllText($settingsFile)
Check "the choice is written to my-settings.txt" ($settings -match "(?m)^Group=book\r?$") "Group line"

$all = @($results.Values | Where-Object { -not $_.ok }).Count -eq 0
$summary = [ordered]@{ test = "save_menu"; environment = "SINGLE-PC, launcher functions with scripted answers, temporary folder"
    script = (Resolve-Path $Script).Path; pass = $all; results = $results }
if ($Out -ne "") { [System.IO.File]::WriteAllText((Join-Path $proj $Out), ($summary | ConvertTo-Json -Depth 5), $utf8) }
Write-Host ("ALL " + $(if ($all) { "PASS" } else { "FAIL" }))
if (-not $all) { exit 1 }
