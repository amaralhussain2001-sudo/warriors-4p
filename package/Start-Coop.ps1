# warriors-4p: online co-op TEST launcher for The Warriors (PS2, USA v1.03). Experimental.
# Double-click Start-Coop.bat (or run this script). The first run asks a few questions and saves the answers in
# my-settings.txt next to this script; edit that file or run with -Reset to change them.
# Nothing here changes your own PCSX2 installation: this package uses its own emulator and its own data folder.
param(
    [switch]$Reset,           # ask the questions again
    [string]$DataDir = "",    # default: <package>\data
    [int]$Port = 0,           # UDP port this PC listens on (default 41000)
    [int]$OtherPort = 0,      # UDP port of the other PC (default: same as Port)
    [string]$BotFile = "",    # developer tests only: scripted input instead of your controller
    [switch]$NoWait,          # developer tests only: do not wait for the game to close
    [string]$SettingsFile = ""   # default: <package>\my-settings.txt
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$settingsFile = $(if ($SettingsFile -ne "") { $SettingsFile } else { Join-Path $here "my-settings.txt" })
$utf8 = New-Object System.Text.UTF8Encoding $false   # UTF-8 without BOM for files PCSX2 reads
$isoMd5 = "56a021f03e5718aa3e4760eb0dc179cd"   # Redump: Warriors, The (USA) (En,Fr,De,Es,It), SLUS-21215 v1.03

function Read-Settings {
    $s = @{}
    if (Test-Path $settingsFile) {
        foreach ($line in Get-Content $settingsFile) {
            $i = $line.IndexOf("=")
            if ($i -gt 0 -and -not $line.TrimStart().StartsWith("#")) { $s[$line.Substring(0, $i).Trim()] = $line.Substring($i + 1).Trim() }
        }
    }
    return $s
}

function Write-Settings($s) {
    $lines = @("# warriors-4p test settings (edit freely; run Start-Coop.bat again afterwards)",
        "# Player: 1 on one PC, 2 on the other. OtherIP: the other PC's address (see README).",
        "# Fps60 and Widescreen must be the SAME on both PCs. Quality: 1 (native) to 12 (sharpest).")
    foreach ($k in @("Player", "OtherIP", "Iso", "Bios", "Quality", "Fps60", "Widescreen", "Fullscreen", "InputDelay", "Renderer", "Adapter", "IsoChecked")) {
        if ($s.ContainsKey($k)) { $lines += "$k=$($s[$k])" }
    }
    [System.IO.File]::WriteAllText($settingsFile, (($lines -join "`r`n") + "`r`n"), $utf8)
}

function Ask($question, $default) {
    $a = Read-Host "$question [$default]"
    if ([string]::IsNullOrWhiteSpace($a)) { return $default }
    return $a.Trim()
}

function Pick-File($title, $filter) {
    Add-Type -AssemblyName System.Windows.Forms
    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Title = $title; $d.Filter = $filter
    if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $d.FileName }
    throw "Nothing selected."
}

function Default-Adapter {
    $names = @(Get-CimInstance Win32_VideoController | ForEach-Object { $_.Name })
    foreach ($n in $names) { if ($n -match "NVIDIA") { return $n } }
    foreach ($n in $names) { if ($n -match "Radeon RX|Arc") { return $n } }
    return ""
}

function Default-Quality($adapter) {
    if ($adapter -match "RTX 50|RTX 40|RX 7[0-9]{3}|RX 9[0-9]{3}") { return "8" }
    if ($adapter -match "RTX 30|RTX 20|RX 6[0-9]{3}") { return "6" }
    return "4"
}

Write-Host ""
Write-Host "warriors-4p online co-op TEST (experimental)" -ForegroundColor Cyan
Write-Host ""

$s = Read-Settings
if ($Reset -or -not $s.ContainsKey("Player")) {
    $s["Player"] = Ask "Are you player 1 or player 2? (one PC must be 1, the other 2)" "1"
    $s["OtherIP"] = Ask "The other PC's IP address (README explains how to find it)" "192.168.1.2"
    Write-Host "Choose your game file (The Warriors, USA, .iso)..."
    $s["Iso"] = Pick-File "Choose The Warriors (USA) ISO" "PS2 disc image (*.iso;*.bin;*.chd)|*.iso;*.bin;*.chd|All files|*.*"
    Write-Host "Choose your PS2 BIOS file (dumped from your own console)..."
    $s["Bios"] = Pick-File "Choose your PS2 BIOS file" "PS2 BIOS (*.bin;*.rom0;*.ROM0)|*.bin;*.rom0;*.ROM0|All files|*.*"
    $adapter = Default-Adapter
    $s["Adapter"] = $adapter
    $s["Quality"] = Ask "Picture quality 1-12 (higher = sharper, needs a stronger graphics card)" (Default-Quality $adapter)
    $s["Fps60"] = Ask "60 fps mode? yes/no (must be the same on both PCs)" "yes"
    $s["Widescreen"] = Ask "Widescreen 16:9? yes/no (must be the same on both PCs)" "no"
    $s["Fullscreen"] = Ask "Start in full screen? yes/no" "yes"
    if (-not $s.ContainsKey("InputDelay")) { $s["InputDelay"] = "2" }
    if (-not $s.ContainsKey("Renderer")) { $s["Renderer"] = "14" }
    Write-Settings $s
}

$player = [int]$s["Player"]
if ($player -ne 1 -and $player -ne 2) { throw "Player must be 1 or 2 (in my-settings.txt)." }
if (-not (Test-Path $s["Iso"])) { throw "Game file not found: $($s["Iso"])" }
if (-not (Test-Path $s["Bios"])) { throw "BIOS file not found: $($s["Bios"])" }

# Check the game version once (reads the whole file, about 10-30 seconds).
$isoItem = Get-Item $s["Iso"]
$isoKey = "$($isoItem.FullName)|$($isoItem.Length)"
if ($s["IsoChecked"] -ne $isoKey) {
    Write-Host "Checking your game file (only the first time)..."
    $md5 = (Get-FileHash -Algorithm MD5 -Path $isoItem.FullName).Hash.ToLower()
    if ($md5 -ne $isoMd5) {
        Write-Host "WARNING: this game file is not The Warriors (USA) v1.03 (MD5 $md5)." -ForegroundColor Yellow
        Write-Host "Online co-op only works with that exact version, so it will stay off." -ForegroundColor Yellow
    } else {
        Write-Host "Game file OK (USA v1.03)." -ForegroundColor Green
        $s["IsoChecked"] = $isoKey
        Write-Settings $s
    }
}

if ($DataDir -eq "") { $DataDir = Join-Path $here "data" }
if ($Port -eq 0) { $Port = 41000 }
if ($OtherPort -eq 0) { $OtherPort = $Port }
$root = Join-Path $DataDir "PCSX2"   # PCSX2 puts its files in <datapath>\PCSX2
foreach ($sub in @("inis", "memcards", "patches", "gamesettings", "logs", "cache", "snaps", "sstates", "cheats", "textures", "inputprofiles", "videos")) {
    New-Item -ItemType Directory -Force -Path (Join-Path $root $sub) | Out-Null
}

# Fresh, empty memory cards for every test session, so both PCs start identical. Old ones are kept as backups.
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
    $p = Join-Path $root "memcards\$m"
    if (Test-Path $p) {
        $bak = Join-Path $root "memcards\old"
        New-Item -ItemType Directory -Force -Path $bak | Out-Null
        Move-Item -Force $p (Join-Path $bak "$stamp`_$m")
    }
}

$fps60 = $s["Fps60"] -match "^(y|yes|1|true|on)$"
$wide = $s["Widescreen"] -match "^(y|yes|1|true|on)$"
$full = $s["Fullscreen"] -match "^(y|yes|1|true|on)$"

# Settings profile
$prof = Get-Content (Join-Path $here "game\profile_PCSX2.ini") -Raw
$biosItem = Get-Item $s["Bios"]
$prof = $prof.Replace("{FULLSCREEN}", $(if ($full) { "true" } else { "false" }))
$prof = $prof.Replace("{BIOS_DIR}", $biosItem.DirectoryName).Replace("{BIOS_FILE}", $biosItem.Name)
$prof = $prof.Replace("{EE_CYCLE_RATE}", $(if ($fps60) { "2" } else { "0" }))
$prof = $prof.Replace("{RENDERER}", $s["Renderer"]).Replace("{ADAPTER}", $s["Adapter"]).Replace("{UPSCALE}", $s["Quality"])
[System.IO.File]::WriteAllText((Join-Path $root "inis\PCSX2.ini"), $prof, $utf8)

# Game patch and the groups to enable
$pnach = Join-Path $here "game\w4p.pnach"
Copy-Item -Force $pnach (Join-Path $root "patches\SLUS-21215_B99A75DE.pnach")
$groups = @("warriors-4p M1", "warriors-4p own view", "warriors-4p hud")
if ($fps60) { $groups += "warriors-4p 60fps" }
if ($wide) { $groups += "warriors-4p widescreen" }
$gs = "[Patches]`r`n" + (($groups | ForEach-Object { "Enable = $_" }) -join "`r`n") + "`r`n"
foreach ($n in @("SLUS-21215_B99A75DE.ini", "B99A75DE.ini")) { [System.IO.File]::WriteAllText((Join-Path $root "gamesettings\$n"), $gs, $utf8) }
$patchSet = (Get-FileHash -Algorithm SHA256 -Path $pnach).Hash + "|" + ($groups -join ";")

# Online session settings
$logDir = Join-Path $here ("logs\{0}_player{1}" -f $stamp, $player)
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$slot = $player - 1
$other = 1 - $slot
$w4p = @("[W4P]", "Enabled = true", "Players = 2", "LocalSlot = $slot", "PadForSlot0 = 0", "PadForSlot1 = 4",
    "ListenPort = $Port", "BindAddress = 0.0.0.0", "Peer$other = $($s["OtherIP"]):$OtherPort",
    "InputDelay = $($s["InputDelay"])", "HashInterval = 30", "LogFile = $logDir\w4p.log", "DumpDir = $logDir",
    "Crop = true", "PatchSet = $patchSet")
if ($BotFile -ne "") { $w4p += "BotInput = $BotFile" }
$w4pIni = Join-Path $logDir "w4p.ini"
[System.IO.File]::WriteAllText($w4pIni, (($w4p -join "`r`n") + "`r`n"), $utf8)
Copy-Item -Force (Join-Path $root "inis\PCSX2.ini") (Join-Path $logDir "PCSX2.ini")

Write-Host ""
Write-Host "You are player $player. Waiting for player $($other + 1) at $($s["OtherIP"]):$OtherPort." -ForegroundColor Cyan
Write-Host "60 fps: $fps60   Widescreen: $wide   Quality: $($s["Quality"])x"
Write-Host "Tab (keyboard) or the touchpad/share button (controller) switches between your view and all views."
Write-Host "Logs: $logDir"
Write-Host ""

$exe = Join-Path $here "emulator\pcsx2-qtx64.exe"
$env:W4P_CONFIG = $w4pIni
$q = { param($x) '"' + $x + '"' }
$argList = @("-batch", "-datapath", (& $q $DataDir), "-logfile", (& $q (Join-Path $logDir "emulog.txt")))
if ($full) { $argList += "-fullscreen" }
$argList += @("--", (& $q $isoItem.FullName))
$proc = Start-Process -FilePath $exe -ArgumentList $argList -PassThru
Set-Content -Path (Join-Path $logDir "pid.txt") -Value $proc.Id -Encoding ASCII
if ($NoWait) { return }
$proc.WaitForExit()
Write-Host ""
Write-Host "Game closed. Your logs are in:" -ForegroundColor Cyan
Write-Host "  $logDir"
Write-Host "Please send that whole folder (from BOTH PCs) back for checking."
Read-Host "Press Enter to close this window"
