# warriors-4p: online co-op TEST launcher for 2-4 players (The Warriors, PS2, USA v1.03). Experimental.
# Double-click Start-Coop.bat. The first start asks a few questions and keeps the answers in my-settings.txt next to
# this script (change them with "Settings" in the menu, or start with -Reset).
# Nothing here touches your own PCSX2 installation or its memory cards: this package has its own emulator, its own
# data folder (data\) and its own co-op save folder (coop-saves\).
# How it works: the connection helper net\w4p-net.exe makes the connections (join codes, docs/research/
# m5_connection_design.md); this launcher runs the lobby over the helper (or over the home network for "Join by IP"),
# writes the session settings and starts the emulator. Notes: docs/research/m5_package4.md.
param(
    [switch]$Reset,              # ask the setup questions again
    [string]$DataDir = "",       # default: <package>\data
    [string]$SettingsFile = "",  # default: <package>\my-settings.txt
    [string]$TestFile = ""       # developer self-test only (tests/m5/package4_selftest.py): JSON answers, no questions
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$utf8 = New-Object System.Text.UTF8Encoding $false   # UTF-8 without BOM for files PCSX2 reads
$Inv = [System.Globalization.CultureInfo]::InvariantCulture
$isoMd5 = "56a021f03e5718aa3e4760eb0dc179cd"         # Redump: Warriors, The (USA) (En,Fr,De,Es,It), SLUS-21215 v1.03
$Proto = "W4PL1"                                     # lobby messages between the launchers
$PadForSlot = @(0, 4, 1, 2)                          # emulated pad of players 1-4 (as in every M2/M5 test run)
# Patch groups of every session (2-4 players). 60 fps and widescreen are added when the host chooses them.
$BaseGroups = @("warriors-4p M1", "warriors-4p own view", "warriors-4p hud", "warriors-4p 4p", "warriors-4p 4p hud B1",
    "warriors-4p 4p hud B2", "warriors-4p 4p spawn", "warriors-4p 4p spawn leave", "warriors-4p 4p inventory",
    "warriors-4p 4p fx", "warriors-4p 4p markers", "warriors-4p session", "warriors-4p missions", "warriors-4p session call")
$script:clock = [System.Diagnostics.Stopwatch]::StartNew()

# ---------------------------------------------------------------- developer self-test answers (players: none)
$T = $null
if ($TestFile -ne "") { $T = [System.IO.File]::ReadAllText($TestFile) | ConvertFrom-Json }
$interactive = ($null -eq $T)
function TV([string]$name, $default) {
    if ($null -ne $T -and ($T.PSObject.Properties.Name -contains $name)) { return $T.$name }
    return $default
}

$settingsFile = $(if ($SettingsFile -ne "") { $SettingsFile } else { Join-Path $here "my-settings.txt" })
if ($DataDir -eq "") { $DataDir = Join-Path $here "data" }
$savesRoot = [string](TV "savesDir" (Join-Path $here "coop-saves"))
$logsRoot = [string](TV "logsDir" (Join-Path $here "logs"))
$netExe = Join-Path $here "net\w4p-net.exe"
$emuExe = Join-Path $here "emulator\pcsx2-qtx64.exe"
$pnachFile = Join-Path $here "game\w4p.pnach"
$profileFile = Join-Path $here "game\profile_PCSX2.ini"

# ---------------------------------------------------------------- small helpers
function NowMs { return $script:clock.Elapsed.TotalMilliseconds }
function NowUs { return [long]($script:clock.Elapsed.TotalMilliseconds * 1000.0) }
function IsYes($v) { return ("$v" -match "^(y|yes|1|true|on)$") }
function YesNo([bool]$b) { if ($b) { return "yes" } else { return "no" } }
function Mask([string]$tx) { return ($tx -replace 'W4P\d-[0-9A-Za-z][0-9A-Za-z-]*', '<code>') }
function Fmt1([double]$x) { return $x.ToString("0.0", $Inv) }

function Read-Settings {
    $s = @{}
    if (Test-Path -LiteralPath $settingsFile) {
        foreach ($line in [System.IO.File]::ReadAllLines($settingsFile)) {
            $i = $line.IndexOf("=")
            if ($i -gt 0 -and -not $line.TrimStart().StartsWith("#")) { $s[$line.Substring(0, $i).Trim()] = $line.Substring($i + 1).Trim() }
        }
    }
    return $s
}

function Write-Settings($s) {
    $lines = @("# warriors-4p co-op settings (edit freely, or use Settings in the menu of Start-Coop.bat).",
        "# Quality: 1 (native) to 12 (sharpest). Fps60 / Widescreen: what you choose when YOU host (the host decides for everybody).")
    foreach ($k in @("Iso", "Bios", "Quality", "Fullscreen", "Fps60", "Widescreen", "Group", "Renderer", "Adapter", "IsoChecked",
            "MinInputDelay", "EmuPort", "SlotPorts", "IcePort", "LanPort")) {
        if ($s.ContainsKey($k)) { $lines += "$k=$($s[$k])" }
    }
    [System.IO.File]::WriteAllText($settingsFile, (($lines -join "`r`n") + "`r`n"), $utf8)
}

function Ask($question, $default) {
    $a = Read-Host "$question [$default]"
    if ([string]::IsNullOrWhiteSpace($a)) { return "$default" }
    return $a.Trim()
}

function Pick-File($title, $filter) {
    Add-Type -AssemblyName System.Windows.Forms
    $d = New-Object System.Windows.Forms.OpenFileDialog
    $d.Title = $title; $d.Filter = $filter
    if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { return $d.FileName }
    throw "Nothing was selected."
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

function Copy-ToClipboard([string]$text) {
    if (-not $interactive) { return }   # self-tests never touch the clipboard
    try { Set-Clipboard -Value $text } catch { }
}

function Read-ClipboardText {
    if (-not $interactive) { return "" }
    try { return ((@(Get-Clipboard)) -join " ") } catch { return "" }
}

function Clean-Text([string]$tx) {
    $tx = $tx -replace '[^\x20-\x7E]', ' '
    $tx = $tx -replace '"', ' '
    $tx = ($tx -replace '\s+', ' ').Trim()
    if ($tx.Length -gt 2000) { $tx = $tx.Substring(0, 2000) }
    return $tx
}

function Get-PackageId {
    $vf = Join-Path $here "VERSION.txt"
    if (Test-Path -LiteralPath $vf) {
        foreach ($ln in [System.IO.File]::ReadAllLines($vf)) { if ($ln -match '^id=(\S+)') { return $Matches[1] } }
    }
    return "unknown"
}

# ---------------------------------------------------------------- co-op saves (BRIEF 4.6, M5 criterion 7)
# Co-op progress lives in coop-saves\<group name>\Mcd001.ps2 (+ Mcd002.ps2), never in your own PCSX2 memory cards.
function Valid-Group([string]$g) { return ($g -match '^[A-Za-z0-9][A-Za-z0-9 _-]{0,31}$' -and -not $g.EndsWith(" ")) }
function Save-Dir([string]$group) { return (Join-Path $savesRoot $group) }

function Get-DirSaveHash([string]$dir) {
    $parts = @()
    foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
        $p = Join-Path $dir $m
        if (Test-Path -LiteralPath $p) { $parts += ("{0}={1}" -f $m, (Get-FileHash -Algorithm SHA256 -LiteralPath $p).Hash.ToLower()) }
    }
    if ($parts.Count -eq 0) { return "new" }
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $h = $sha.ComputeHash([System.Text.Encoding]::ASCII.GetBytes(($parts -join ";")))
    return ([System.BitConverter]::ToString($h) -replace "-", "").ToLower()
}

function Get-SaveHash([string]$group) {
    if (-not (Valid-Group $group)) { return "?" }
    return (Get-DirSaveHash (Save-Dir $group))
}

function Save-Label([string]$hash) {
    if ($hash -eq "new") { return "new game, no save yet" }
    if ($hash.Length -lt 8) { return "?" }
    return ("check code " + $hash.Substring(0, 8).ToUpper())
}

function List-Groups {
    if (-not (Test-Path -LiteralPath $savesRoot)) { return @() }
    return @(Get-ChildItem -LiteralPath $savesRoot -Directory | ForEach-Object { $_.Name })
}

# ---------------------------------------------------------------- game file check
function Check-Iso($s) {
    $isoItem = Get-Item -LiteralPath $s["Iso"]
    $isoKey = "$($isoItem.FullName)|$($isoItem.Length)"
    if ($s["IsoChecked"] -eq $isoKey) { return $true }
    Write-Host "Checking your game file (only the first time, about half a minute)..."
    $md5 = (Get-FileHash -Algorithm MD5 -LiteralPath $isoItem.FullName).Hash.ToLower()
    if ($md5 -ne $isoMd5) {
        Write-Host "WARNING: this game file is not The Warriors (USA) v1.03 (MD5 $md5)." -ForegroundColor Yellow
        Write-Host "Online co-op only works with that exact version. Choose another file in Settings." -ForegroundColor Yellow
        return $false
    }
    Write-Host "Game file OK (USA v1.03)." -ForegroundColor Green
    $s["IsoChecked"] = $isoKey
    Write-Settings $s
    return $true
}

# ---------------------------------------------------------------- lobby state, log and messages
function New-Lobby($s, [string]$mode) {
    $stamp = (Get-Date).ToString("yyyyMMdd_HHmmss", $Inv)
    $logDir = Join-Path $logsRoot ("{0}_{1}" -f $stamp, $mode)
    New-Item -ItemType Directory -Force -Path $logDir | Out-Null
    $L = @{
        mode = $mode; code = ($mode -eq "host" -or $mode -eq "join"); isHost = ($mode -eq "host" -or $mode -eq "lanhost")
        stamp = $stamp; logDir = $logDir; logFile = (Join-Path $logDir "lobby-log.txt")
        slot = -1; players = 0; group = ""; saveHash = ""; saveAt = -1e9; fps60 = $true; wide = $true; delay = 2
        minDelay = [int](TV "minDelay" $(if ($s.ContainsKey("MinInputDelay")) { $s["MinInputDelay"] } else { 2 }))
        peers = @{}; occ = @(); msgs = (New-Object System.Collections.ArrayList); problemLog = @{}
        helper = $null; readTask = $null; helperEof = $false; helperError = ""; hostLeft = $false; ready = $false
        joinCode = ""; replyCode = ""; replyAt = -1; replyCopied = $false; lateHint = $false
        udp = $null; seq = 0; strangers = 0; nonce = ""; hostEp = $null; refused = ""; closed = $false
        started = $false; startInfo = $null; startAt = 0; starting = $false; go = $false; sid = ""; startT = 0
        lastStartSend = -1e9; startWarned = $false; lastScreen = ""; lastStatus = ""; t0 = (NowMs)
        emuPort = [int](TV "emuPort" $s["EmuPort"]); slotBase = [int](TV "slotPorts" $s["SlotPorts"])
        icePort = [int](TV "icePort" $s["IcePort"]); lanPort = [int](TV "lanPort" $s["LanPort"])
        lanBind = [string](TV "lanBind" "0.0.0.0"); maxRtt = 0.0; events = (New-Object System.Collections.ArrayList)
    }
    LLog $L ("warriors-4p co-op launcher, package {0}, mode {1}, pnach {2}" -f $pkgId, $mode, $pnachHash)
    return $L
}

function LLog($L, [string]$text) {
    $line = (Get-Date).ToString("HH:mm:ss", $Inv) + " " + (Fmt1 ((NowMs) / 1000.0)).PadLeft(8) + "  " + (Mask $text)
    try { [System.IO.File]::AppendAllText($L.logFile, $line + "`r`n", $utf8) } catch { }
    if (-not $interactive) { [Console]::Out.WriteLine($line) }
}

function Add-Msg($L, [string]$text) {
    [void]$L.msgs.Add($text)
    while ($L.msgs.Count -gt 6) { $L.msgs.RemoveAt(0) }
    LLog $L ("message: " + $text)
}

function Write-Status($L, [string]$phase, $extra) {
    $f = [string](TV "statusFile" "")
    $st = [ordered]@{ phase = $phase; mode = $L.mode; slot = $L.slot; players = $L.players; group = $L.group
        saveHash = $L.saveHash; delay = $L.delay; fps60 = $L.fps60; wide = $L.wide; logDir = $L.logDir; package = $pkgId
        sid = $(if ($L.isHost) { $L.sid } elseif ($null -ne $L.startInfo) { $L.startInfo["sid"] } else { "" })
        maxRttMs = $L.maxRtt; problems = $L.problemLog; helperError = $L.helperError; events = @($L.events) }
    if ($null -ne $extra) { foreach ($k in $extra.Keys) { $st[$k] = $extra[$k] } }
    $json = $st | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $L.logDir "launcher-status.json"), $json, $utf8)
    if ($f -ne "") { [System.IO.File]::WriteAllText($f, $json, $utf8) }
}

# ---------------------------------------------------------------- connection helper (w4p-net)
function Quote-Arg([string]$a) { if ($a -match '[\s"]') { return '"' + ($a -replace '"', '\"') + '"' } return $a }

function Start-Helper($L, [string[]]$argv) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $netExe
    $psi.Arguments = (($argv | ForEach-Object { Quote-Arg $_ }) -join " ")
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardInput = $true
    $psi.CreateNoWindow = $true
    $psi.WorkingDirectory = $L.logDir
    $L.helper = [System.Diagnostics.Process]::Start($psi)
    LLog $L ("connection helper started: w4p-net " + (Mask ($argv -join " ")))
}

function Helper-Send($L, [string]$line) {
    if ($null -eq $L.helper -or $L.helper.HasExited) { return }
    try { $L.helper.StandardInput.WriteLine($line); $L.helper.StandardInput.Flush() } catch { }
}

function Pump-Helper($L) {
    if ($null -eq $L.helper) { return }
    for ($i = 0; $i -lt 200; $i++) {
        if ($null -eq $L.readTask) {
            if ($L.helperEof) { return }
            $L.readTask = $L.helper.StandardOutput.ReadLineAsync()
        }
        if (-not $L.readTask.IsCompleted) { return }
        $line = $L.readTask.Result
        $L.readTask = $null
        if ($null -eq $line) { $L.helperEof = $true; LLog $L "connection helper output ended"; return }
        Handle-HelperLine $L $line
    }
}

function Handle-HelperLine($L, [string]$line) {
    if (-not $line.StartsWith("@")) {
        if ($line -match '^(Join code|If you are not connected)') { return }   # the launcher shows the codes itself
        # w4p-net prints a wrong (negative) connect time in this message (its timer is set later): show it without
        if ($line -match '^Player (\d) joined \(') { LLog $L ("helper: " + $line); Add-Msg $L ("Player {0} joined." -f $Matches[1]); return }
        Add-Msg $L $line
        return
    }
    $f = $line.Substring(1).Split(" ")
    if ($f[0] -ne "stats") { [void]$L.events.Add((Mask $line)) }
    switch ($f[0]) {
        "code" {
            if ($f[1] -eq "join") {
                $L.joinCode = $f[2]
                LLog $L "join code issued"
                Copy-ToClipboard $L.joinCode
                $cf = [string](TV "codeFile" "")
                if ($cf -ne "") { [System.IO.File]::WriteAllText($cf, $L.joinCode, $utf8) }
            } elseif ($f[1] -eq "reply") {
                $L.replyCode = $f[2]; $L.replyAt = NowMs
                LLog $L "reply code issued"
            }
        }
        "slot" { $L.slot = [int]$f[1]; LLog $L $line }
        "joined" { $pe = Get-Peer $L ([int]$f[1]); $pe.connected = $true; $pe.lastRx = -1e9; LLog $L $line }
        "left" {
            $p = [int]$f[1]
            if ($L.peers.ContainsKey($p)) { $L.peers.Remove($p) }
            LLog $L $line
        }
        "host_left" { $L.hostLeft = $true; LLog $L $line }
        "ready" { $L.ready = $true; LLog $L $line }
        "notready" { $L.ready = $false; LLog $L $line }
        "error" { $L.helperError = ($f[1..($f.Count - 1)] -join " "); LLog $L $line }
        "stats" { LLog $L "@stats (see connection-stats.json)" }
        default { LLog $L $line }
    }
}

function Stop-Helper($L) {
    if ($null -eq $L.helper) { return }
    Helper-Send $L "quit"
    $deadline = (NowMs) + 8000
    while (-not $L.helper.HasExited -and (NowMs) -lt $deadline) { Pump-Helper $L; Start-Sleep -Milliseconds 50 }
    Pump-Helper $L
    if (-not $L.helper.HasExited) { try { $L.helper.StandardInput.Close() } catch { }; Start-Sleep -Seconds 2 }
    if (-not $L.helper.HasExited) { try { $L.helper.Kill() } catch { } }   # our own child process only
    LLog $L ("connection helper stopped (exit code {0})" -f $(try { $L.helper.ExitCode } catch { "?" }))
}

# ---------------------------------------------------------------- lobby messages (UDP, text "W4PL1|TYPE|key=value|...")
function Open-Lobby($L, [string]$bindIp, [int]$port) {
    $u = New-Object System.Net.Sockets.UdpClient ([System.Net.Sockets.AddressFamily]::InterNetwork)
    try { $u.Client.Bind([System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse($bindIp), $port)) }
    catch { $u.Close(); throw "Cannot use UDP port $port on this PC (is another copy of Start-Coop or the game still open?)." }
    try { [void]$u.Client.IOControl(-1744830452, [byte[]](0, 0, 0, 0), $null) } catch { }   # ignore 'port unreachable'
    $L.udp = $u
    LLog $L "lobby socket on $bindIp`:$port"
}

function Close-Lobby($L) {
    if ($null -ne $L.udp) { try { $L.udp.Close() } catch { }; $L.udp = $null }
}

function Get-Peer($L, [int]$p) {
    if (-not $L.peers.ContainsKey($p)) {
        $L.peers[$p] = @{ slot = $p; lastRx = -1e9; hello = $null; rtt = (New-Object System.Collections.ArrayList); ep = $null
            connected = $false; ack = $null; pongs = 0 }
    }
    return $L.peers[$p]
}

function Send-Ep($L, $ep, [string]$body) {
    if ($null -eq $ep -or $null -eq $L.udp) { return }
    $b = [System.Text.Encoding]::ASCII.GetBytes($Proto + "|" + $body)
    try { [void]$L.udp.Send($b, $b.Length, $ep) } catch { }
}

function Slot-Endpoint($L, [int]$p) {
    if ($L.code) { return [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Loopback, $L.slotBase + $p) }
    if ($L.peers.ContainsKey($p)) { return $L.peers[$p].ep }
    return $null
}

function Send-Slot($L, [int]$p, [string]$body) { Send-Ep $L (Slot-Endpoint $L $p) $body }

function Parse-Msg([byte[]]$bytes) {
    $parts = [System.Text.Encoding]::ASCII.GetString($bytes).Split("|")
    if ($parts.Count -lt 2 -or $parts[0] -ne $Proto) { return $null }
    $m = @{ type = $parts[1] }
    for ($i = 2; $i -lt $parts.Count; $i++) {
        $k = $parts[$i].IndexOf("=")
        if ($k -gt 0) { $m[$parts[$i].Substring(0, $k)] = $parts[$i].Substring($k + 1) }
    }
    return $m
}

function Pump-Lobby($L) {
    for ($i = 0; $i -lt 500; $i++) {
        if ($null -eq $L.udp) { return }
        $n = 0
        try { $n = $L.udp.Available } catch { return }
        if ($n -le 0) { return }
        $rep = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Any, 0)
        $bytes = $null
        try { $bytes = $L.udp.Receive([ref]$rep) } catch { continue }
        $m = Parse-Msg $bytes
        if ($null -ne $m) { Handle-Msg $L $m $rep }
    }
}

function Targets($L) {
    $tg = @()
    if ($L.slot -lt 0) { return $tg }
    if ($L.isHost) {
        foreach ($p in @($L.peers.Keys)) { if ($L.peers[$p].connected) { $tg += [int]$p } }
    } else {
        $tg += 0
        foreach ($p in @($L.occ)) { if ($p -ne 0 -and $p -ne $L.slot) { $tg += [int]$p } }
    }
    return $tg
}

function Occupied($L) {
    $o = @(0)
    foreach ($p in @($L.peers.Keys | Sort-Object)) { if ($L.peers[$p].connected) { $o += [int]$p } }
    return $o
}

function Roster-String($L) {
    if ($L.code) { return "-" }
    $r = @()
    foreach ($p in @($L.peers.Keys | Sort-Object)) {
        $ep = $L.peers[$p].ep
        if ($null -ne $ep -and $p -ne 0) { $r += ("{0}@{1}:{2}" -f $p, $ep.Address, $ep.Port) }
    }
    return ($r -join ";")
}

function Source-Slot($L, $m, $rep) {
    if (-not $m.ContainsKey("slot")) { return -1 }
    $claimed = 0
    if (-not [int]::TryParse([string]$m["slot"], [ref]$claimed)) { return -1 }
    if ($claimed -lt 0 -or $claimed -gt 3 -or $claimed -eq $L.slot) { return -1 }
    if ($L.code) {
        if (-not [System.Net.IPAddress]::IsLoopback($rep.Address)) { return -1 }
        if ($rep.Port -ne $L.slotBase + $claimed) { return -1 }
        return $claimed
    }
    if ($L.peers.ContainsKey($claimed)) {
        $ep = $L.peers[$claimed].ep
        if ($null -ne $ep -and $ep.Address.Equals($rep.Address) -and $ep.Port -eq $rep.Port) { return $claimed }
    }
    return -1
}

function Handle-Msg($L, $m, $rep) {
    $type = [string]$m["type"]
    if ($type -eq "JOIN") { if ($L.mode -eq "lanhost") { Lan-HandleJoin $L $m $rep }; return }
    if ($type -eq "WELCOME" -or $type -eq "FULL") { if ($L.mode -eq "lanjoin") { Lan-HandleWelcome $L $m $rep }; return }
    $src = Source-Slot $L $m $rep
    if ($src -lt 0) { $L.strangers++; return }
    $pe = Get-Peer $L $src
    $pe.lastRx = NowMs
    switch ($type) {
        "HELLO" {
            $pe.hello = $m
            if ($src -eq 0 -and -not $L.isHost) { Apply-HostHello $L $m }
        }
        "PING" { Send-Slot $L $src ("PONG|slot={0}|to={1}|seq={2}|t={3}" -f $L.slot, $src, $m["seq"], $m["t"]) }
        "PONG" {
            if ([string]$m["to"] -eq [string]$L.slot) {
                $t0 = [long]0
                $pe.pongs++
                if ($pe.pongs -gt 2 -and [long]::TryParse([string]$m["t"], [ref]$t0)) {   # first 2 answers: warm-up
                    [void]$pe.rtt.Add(((NowUs) - $t0) / 1000.0)
                    while ($pe.rtt.Count -gt 20) { $pe.rtt.RemoveAt(0) }
                }
            }
        }
        "START" { if (-not $L.isHost -and $src -eq 0) { Handle-Start $L $m } }
        "ACK" { if ($L.isHost -and $L.starting -and [string]$m["sid"] -eq $L.sid) { $pe.ack = $m } }
        "BYE" {
            LLog $L ("player {0} left the lobby" -f ($src + 1))
            if ($L.mode -eq "lanhost") { $L.peers.Remove($src) } else { $pe.lastRx = -1e9; $pe.hello = $null }
            if ($src -eq 0) { $L.hostLeft = $true }
        }
    }
}

function Apply-HostHello($L, $m) {
    $L.players = [int]$m["players"]
    $g = [string]$m["group"]
    if ((Valid-Group $g) -and $g -ne $L.group) { $L.group = $g; $L.saveHash = Get-SaveHash $g; $L.saveAt = NowMs }
    $L.fps60 = ([string]$m["fps60"] -eq "1"); $L.wide = ([string]$m["wide"] -eq "1"); $L.delay = [int]$m["delay"]
    $o = @(); foreach ($x in ([string]$m["occ"] -split ",")) { if ($x -match '^\d$') { $o += [int]$x } }
    $L.occ = $o
    if (-not $L.code) { Apply-Roster $L ([string]$m["roster"]) }
}

function Apply-Roster($L, [string]$roster) {
    foreach ($e in ($roster -split ";")) {
        if ($e -match '^(\d)@([0-9.]+):(\d+)$') {
            $p = [int]$Matches[1]
            if ($p -eq $L.slot -or $p -eq 0) { continue }
            $pe = Get-Peer $L $p
            $pe.ep = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse($Matches[2]), [int]$Matches[3])
        }
    }
}

# ---- Join by IP (home network): the host gives out the slots itself
function Lan-HandleJoin($L, $m, $rep) {
    $nonce = [string]$m["nonce"]
    foreach ($p in @($L.peers.Keys)) {
        $ep = $L.peers[$p].ep
        if ($null -ne $ep -and $ep.Address.Equals($rep.Address) -and $ep.Port -eq $rep.Port) {
            Send-Ep $L $rep ("WELCOME|slot=0|you={0}|nonce={1}|players={2}" -f $p, $nonce, $L.players)
            return
        }
    }
    if ($L.closed) {
        Send-Ep $L $rep "FULL|slot=0|nonce=$nonce|why=started"
        LLog $L "late join refused (game already started)"
        return
    }
    $free = -1
    for ($p = 1; $p -lt $L.players; $p++) { if (-not $L.peers.ContainsKey($p)) { $free = $p; break } }
    if ($free -lt 0) { Send-Ep $L $rep "FULL|slot=0|nonce=$nonce|why=full"; return }
    $pe = Get-Peer $L $free
    $pe.ep = $rep; $pe.connected = $true; $pe.lastRx = NowMs
    Send-Ep $L $rep ("WELCOME|slot=0|you={0}|nonce={1}|players={2}" -f $free, $nonce, $L.players)
    [void]$L.events.Add("lan joined $free")
    Add-Msg $L ("Player {0} joined (from {1})." -f ($free + 1), $rep.Address)
}

function Lan-HandleWelcome($L, $m, $rep) {
    if ([string]$m["nonce"] -ne $L.nonce -or $L.slot -ge 0) { return }
    if ([string]$m["type"] -eq "FULL") {
        if ($L.refused -eq "") {
            $L.refused = [string]$m["why"]
            [void]$L.events.Add("lan refused " + $L.refused)
            if ($L.refused -eq "started") { Add-Msg $L "The host has already started the game. You can only join in the lobby: wait for the next game." }
            else { Add-Msg $L "This game is full." }
        }
        return
    }
    $L.slot = [int]$m["you"]; $L.players = [int]$m["players"]
    $P0 = Get-Peer $L 0
    $P0.ep = $rep; $P0.connected = $true
    [void]$L.events.Add("lan slot " + $L.slot)
    Add-Msg $L ("Connected to the host. You are Player {0}." -f ($L.slot + 1))
}

# ---- periodic: HELLO + PING to everybody; RTT; input delay
function Pct($list, [double]$q) {
    if ($null -eq $list -or $list.Count -eq 0) { return -1.0 }
    $a = @($list | Sort-Object)
    return [double]$a[[int][Math]::Floor($q * ($a.Count - 1))]
}

function Send-Hellos($L) {
    $now = NowMs
    $seen = @(); $rtt = @()
    foreach ($p in @($L.peers.Keys | Sort-Object)) {
        $pe = $L.peers[$p]
        if ($now - $pe.lastRx -lt 4000) { $seen += $p }
        $r = Pct $pe.rtt 0.9
        if ($r -ge 0) { $rtt += ("{0}:{1}" -f $p, [int][Math]::Round($r * 10)) }
    }
    $iso = $(if ($script:isoOk) { "ok" } else { "bad" })
    $msg = "HELLO|slot={0}|ver={1}|pnach={2}|iso={3}|save={4}|seen={5}|rtt={6}" -f $L.slot, $pkgId, $pnachHash, $iso, $L.saveHash,
        ($seen -join ","), ($rtt -join ",")
    if ($L.isHost) {
        $msg += "|players={0}|group={1}|fps60={2}|wide={3}|delay={4}|occ={5}|roster={6}" -f $L.players, $L.group, [int]$L.fps60,
            [int]$L.wide, $L.delay, ((Occupied $L) -join ","), (Roster-String $L)
    }
    $us = NowUs
    foreach ($p in @(Targets $L)) {
        Send-Slot $L $p $msg
        Send-Slot $L $p ("PING|slot={0}|seq={1}|t={2}" -f $L.slot, $L.seq, $us)
    }
    $L.seq++
}

function Compute-Delay($L) {
    $period = $(if ($L.fps60) { 1000.0 / 60.0 } else { 1000.0 / 30.0 })
    $max = 0.0
    foreach ($p in @($L.peers.Keys)) {
        $pe = $L.peers[$p]
        $r = Pct $pe.rtt 0.9
        if ($r -gt $max) { $max = $r }
        if ($null -ne $pe.hello -and $pe.hello.ContainsKey("rtt")) {
            foreach ($e in ([string]$pe.hello["rtt"] -split ",")) {
                if ($e -match '^\d:(\d+)$') { $v = [int]$Matches[1] / 10.0; if ($v -gt $max) { $max = $v } }
            }
        }
    }
    $L.maxRtt = $max
    # RTT budget of the lockstep: 2 x delay x poll period (m5_connection_design.md 2.1/2.4), 15 ms margin, at least 2
    $d = [int][Math]::Ceiling(($max + 15.0) / (2.0 * $period))
    return [Math]::Max($L.minDelay, [Math]::Min(12, $d))
}

function Get-Problems($L) {
    $res = @{}
    $now = NowMs
    for ($p = 1; $p -lt $L.players; $p++) {
        $msg = ""
        if (-not $L.peers.ContainsKey($p) -or -not $L.peers[$p].connected) { $msg = "waiting" }
        else {
            $pe = $L.peers[$p]; $h = $pe.hello
            if ($null -eq $h -or $now - $pe.lastRx -gt 4000 -or [string]$h["save"] -eq "" -or $pe.rtt.Count -lt 3) { $msg = "connecting" }
            elseif ([string]$h["ver"] -ne $pkgId) { $msg = "version" }
            elseif ([string]$h["pnach"] -ne $pnachHash) { $msg = "patch" }
            elseif ([string]$h["iso"] -ne "ok") { $msg = "iso" }
            elseif ([string]$h["save"] -ne $L.saveHash) { $msg = "save" }
            else {
                $seen = @(([string]$h["seen"] -split ",") | Where-Object { $_ -match '^\d$' } | ForEach-Object { [int]$_ })
                $missing = @()
                for ($q = 0; $q -lt $L.players; $q++) { if ($q -ne $p -and $seen -notcontains $q) { $missing += ($q + 1) } }
                if ($missing.Count -gt 0) { $msg = "reach:" + ($missing -join ",") }
            }
        }
        $res[$p] = $msg
        if ($msg -match '^(version|patch|iso|save)$') { $L.problemLog[[string]($p + 1)] = $msg }
    }
    return $res
}

function Problem-Text([string]$code) {
    switch -regex ($code) {
        '^waiting$' { return "waiting for a friend to join..." }
        '^connecting$' { return "connecting..." }
        '^version$' { return "PROBLEM: uses a different package version. Everybody must use the same zip file." }
        '^patch$' { return "PROBLEM: has a different game patch file. Everybody must use the same zip file." }
        '^iso$' { return "PROBLEM: the game file is not The Warriors (USA) v1.03." }
        '^save$' { return "PROBLEM: different co-op save. The host's save must be copied to this player's PC (README, step 9)." }
        '^reach:(.*)$' { return ("cannot reach Player {0} yet..." -f $Matches[1]) }
    }
    return "ready"
}

function Start-Blockers($L) {
    if (-not $script:isoOk) { return "Your own game file is not The Warriors (USA) v1.03 (see Settings)." }
    if ($L.code -and -not $L.ready) { return "Not everybody is connected yet." }
    $pr = Get-Problems $L
    for ($p = 1; $p -lt $L.players; $p++) {
        if ($pr[$p] -ne "") { return ("Player {0}: {1}" -f ($p + 1), (Problem-Text $pr[$p])) }
    }
    return ""
}

# ---- start: the host sends START until every player answers; then every PC starts the game
function Try-Start($L) {
    if ($L.starting) {
        if ($L.startWarned) { $L.go = $true; LLog $L "start: the host starts without every answer" }
        return
    }
    $why = Start-Blockers $L
    if ($why -ne "") { Add-Msg $L ("Cannot start yet. " + $why); return }
    $L.sid = ([guid]::NewGuid().ToString("N")).Substring(0, 12)
    $L.delay = Compute-Delay $L
    $L.starting = $true; $L.startT = NowMs; $L.lastStartSend = -1e9
    foreach ($p in @($L.peers.Keys)) { $L.peers[$p].ack = $null }
    if ($L.code) { Helper-Send $L "lock" } else { $L.closed = $true }   # nobody new can join from now on (M5 criterion 6)
    [void]$L.events.Add("start " + $L.sid)
    foreach ($p in @($L.peers.Keys | Sort-Object)) {
        $pe = $L.peers[$p]
        LLog $L ("ping to player {0}: median {1} ms, p90 {2} ms ({3} samples); reported by him: {4}" -f ($p + 1), (Fmt1 (Pct $pe.rtt 0.5)),
            (Fmt1 (Pct $pe.rtt 0.9)), $pe.rtt.Count, $(if ($null -ne $pe.hello) { [string]$pe.hello["rtt"] } else { "-" }))
    }
    LLog $L ("start: session {0}, {1} players, input delay {2}, co-op save '{3}' {4}, 60 fps {5}, widescreen {6}, slowest ping {7} ms" -f
        $L.sid, $L.players, $L.delay, $L.group, $L.saveHash, $L.fps60, $L.wide, (Fmt1 $L.maxRtt))
}

function Host-StartStep($L) {
    $now = NowMs
    if ($now - $L.lastStartSend -ge 200) {
        $L.lastStartSend = $now
        $msg = "START|slot=0|sid={0}|players={1}|group={2}|fps60={3}|wide={4}|delay={5}|save={6}|occ={7}|roster={8}" -f $L.sid,
            $L.players, $L.group, [int]$L.fps60, [int]$L.wide, $L.delay, $L.saveHash, ((Occupied $L) -join ","), (Roster-String $L)
        foreach ($p in @(Targets $L)) { Send-Slot $L $p $msg }
    }
    $all = $true; $refused = ""
    for ($p = 1; $p -lt $L.players; $p++) {
        $a = $(if ($L.peers.ContainsKey($p)) { $L.peers[$p].ack } else { $null })
        if ($null -eq $a) { $all = $false }
        elseif ([string]$a["ok"] -ne "1") { $refused = "Player {0}: {1}" -f ($p + 1), $a["why"] }
    }
    if ($refused -ne "") {
        Add-Msg $L ("Start cancelled. " + $refused + " New players cannot join any more: to let someone else in, quit and host again.")
        $L.starting = $false
        return
    }
    if ($all) { $L.go = $true; LLog $L "start: every player answered"; return }
    if ($now - $L.startT -gt 20000) {
        if (-not $interactive) { $L.go = $true; LLog $L "start: not every player answered within 20 s; starting anyway" }
        elseif (-not $L.startWarned) {
            $L.startWarned = $true
            Add-Msg $L "Not every player answered the start. Press S again to start anyway, or Q to stop."
        }
    }
}

function Handle-Start($L, $m) {
    if ($L.started) {
        if ([string]$m["sid"] -eq [string]$L.startInfo["sid"]) { Send-Slot $L 0 ("ACK|slot={0}|sid={1}|ok=1" -f $L.slot, $m["sid"]) }
        return
    }
    $g = [string]$m["group"]
    $why = ""
    $mine = "?"
    if (-not (Valid-Group $g)) { $why = "bad co-op save name" }
    else {
        $mine = Get-SaveHash $g
        if ($mine -ne [string]$m["save"]) { $why = "different co-op save" }
        elseif (-not $script:isoOk) { $why = "game file is not The Warriors (USA) v1.03" }
    }
    if ($why -ne "") {
        Send-Slot $L 0 ("ACK|slot={0}|sid={1}|ok=0|why={2}" -f $L.slot, $m["sid"], $why)
        if ($L.lastRefuse -ne [string]$m["sid"]) { $L.lastRefuse = [string]$m["sid"]; Add-Msg $L ("The host wants to start, but: " + $why + ".") }
        return
    }
    $L.started = $true; $L.startInfo = $m; $L.startAt = NowMs
    $L.group = $g; $L.saveHash = $mine; $L.players = [int]$m["players"]; $L.delay = [int]$m["delay"]
    $L.fps60 = ([string]$m["fps60"] -eq "1"); $L.wide = ([string]$m["wide"] -eq "1")
    if (-not $L.code) { Apply-Roster $L ([string]$m["roster"]) }
    Send-Slot $L 0 ("ACK|slot={0}|sid={1}|ok=1" -f $L.slot, $m["sid"])
    [void]$L.events.Add("start " + $m["sid"])
    LLog $L ("start received: session {0}, {1} players, input delay {2}, co-op save '{3}' {4}" -f $m["sid"], $L.players, $L.delay, $g, $mine)
    Add-Msg $L "The host started the game. Starting..."
}

# ---------------------------------------------------------------- lobby screen
function Lobby-Lines($L) {
    $o = New-Object System.Collections.ArrayList
    $now = NowMs
    if ($L.isHost) {
        [void]$o.Add("#warriors-4p online co-op (TEST) - you are the HOST (Player 1)")
        [void]$o.Add(("  {0} players   co-op save: `"{1}`" ({2})   60 fps: {3}   widescreen: {4}" -f $L.players, $L.group,
                (Save-Label $L.saveHash), (YesNo $L.fps60), (YesNo $L.wide)))
        [void]$o.Add("")
        if ($L.code) {
            if ($L.joinCode -ne "") {
                [void]$o.Add("#Join code (already copied - paste it into your group chat):")
                [void]$o.Add("  " + $L.joinCode)
                [void]$o.Add("  Your friends choose 'Join a game' and paste it.")
            } else { [void]$o.Add("  Preparing the join code (a few seconds)...") }
        } else {
            [void]$o.Add("#Your friends choose 'Join by IP address' and type one of these addresses:")
            foreach ($a in @(Get-LanAddresses)) { [void]$o.Add("  " + $a) }
            if ($L.lanPort -ne 41000) { [void]$o.Add("  (port $($L.lanPort))") }
        }
        [void]$o.Add("")
        $pr = Get-Problems $L
        [void]$o.Add("  Player 1   you (host)")
        for ($p = 1; $p -lt $L.players; $p++) {
            $txt = Problem-Text $pr[$p]
            $ping = ""
            if ($L.peers.ContainsKey($p)) { $r = Pct $L.peers[$p].rtt 0.5; if ($r -ge 0) { $ping = "ping {0,4} ms   " -f [int][Math]::Round($r) } }
            $line = ("  Player {0}   {1}{2}" -f ($p + 1), $ping, $txt)
            if ($pr[$p] -ne "" -and $pr[$p] -ne "waiting" -and $pr[$p] -ne "connecting") { $line = "!" + $line }
            [void]$o.Add($line)
        }
        [void]$o.Add("")
        $ms = [int][Math]::Round($L.delay * $(if ($L.fps60) { 1000.0 / 60 } else { 1000.0 / 30 }))
        [void]$o.Add(("  Input delay: {0} frames ({1} ms), from the slowest connection ({2} ms)." -f $L.delay, $ms, [int][Math]::Round($L.maxRtt)))
        if ($L.code -and -not $L.ready -and $pr.Values -notcontains "waiting") { [void]$o.Add("  Connecting the players to each other...") }
        if ($L.starting) { [void]$o.Add("#Starting: waiting for every player to answer...") }
    } else {
        [void]$o.Add("#warriors-4p online co-op (TEST) - you JOINED a game")
        $hostOk = $L.peers.ContainsKey(0) -and $null -ne $L.peers[0].hello -and $now - $L.peers[0].lastRx -lt 4000
        if ($L.slot -ge 0 -and $hostOk) { [void]$o.Add(("  Connected. You are Player {0}." -f ($L.slot + 1))) }
        elseif ($L.slot -ge 0) { [void]$o.Add(("  You are Player {0}. Talking to the host..." -f ($L.slot + 1))) }
        else { [void]$o.Add("  Connecting to the host...") }
        if ($L.code -and $L.replyCode -ne "" -and -not $hostOk) {
            [void]$o.Add("")
            [void]$o.Add("#Reply code (send it to the host ONLY if you are not connected within 10 seconds):")
            [void]$o.Add("  " + $L.replyCode)
            if ($L.replyCopied) { [void]$o.Add("  (already copied - paste it into the chat for the host; the host presses R)") }
        }
        if ($hostOk) {
            [void]$o.Add("")
            [void]$o.Add(("  The host chose: {0} players, co-op save `"{1}`", 60 fps: {2}, widescreen: {3}, input delay {4} frames." -f
                    $L.players, $L.group, (YesNo $L.fps60), (YesNo $L.wide), $L.delay))
            $hh = [string]$L.peers[0].hello["save"]
            if ($hh -eq $L.saveHash) { [void]$o.Add(("  Your co-op save matches the host's ({0})." -f (Save-Label $L.saveHash))) }
            else {
                [void]$o.Add(("!  Your co-op save is DIFFERENT: yours {0}, the host's {1}." -f (Save-Label $L.saveHash), (Save-Label $hh)))
                [void]$o.Add("!  Copy the host's save folder to this PC (README, step 9). The game cannot start until they match.")
            }
            if ([string]$L.peers[0].hello["ver"] -ne $pkgId) { [void]$o.Add("!  The host uses a different package version. Everybody must use the same zip file.") }
            [void]$o.Add("")
            for ($p = 0; $p -lt $L.players; $p++) {
                if ($p -eq $L.slot) { [void]$o.Add(("  Player {0}   you" -f ($p + 1))); continue }
                $st = "waiting..."
                if ($L.peers.ContainsKey($p) -and $now - $L.peers[$p].lastRx -lt 4000) {
                    $r = Pct $L.peers[$p].rtt 0.5
                    $st = $(if ($r -ge 0) { "connected   ping {0,4} ms" -f [int][Math]::Round($r) } else { "connected" })
                }
                [void]$o.Add(("  Player {0}   {1}{2}" -f ($p + 1), $(if ($p -eq 0) { "(host)   " } else { "" }), $st))
            }
            [void]$o.Add("")
            [void]$o.Add("  Waiting for the host to start the game...")
        }
        if ($L.slot -lt 0 -and $now - $L.t0 -gt 30000) {
            [void]$o.Add("")
            [void]$o.Add("!  Still not connected. If the host has already started the game, you cannot join it now:")
            [void]$o.Add("!  players can only join in the lobby. Wait for the next game (the host will send a new code).")
        }
    }
    if ($L.msgs.Count -gt 0) {
        [void]$o.Add("")
        [void]$o.Add("  Messages:")
        foreach ($mt in $L.msgs) { [void]$o.Add("    " + $mt) }
    }
    [void]$o.Add("")
    if ($L.isHost) {
        if ($L.code) { [void]$o.Add("#Keys:  S = start the game   R = paste a reply code (copy it first)   Q = quit") }
        else { [void]$o.Add("#Keys:  S = start the game   Q = quit") }
    } else {
        if ($L.code) { [void]$o.Add("#Keys:  Q = leave   C = copy the reply code again") } else { [void]$o.Add("#Keys:  Q = leave") }
    }
    [void]$o.Add("  Only the players in this lobby play. Someone who comes later must wait for the next game.")
    return $o
}

function Show-Lobby($L) {
    $lines = Lobby-Lines $L
    $text = ($lines -join "`n")
    if ($interactive) {
        if ($text -eq $L.lastScreen) { return }
        $L.lastScreen = $text
        Clear-Host
        foreach ($ln in $lines) {
            if ($ln.StartsWith("#")) { Write-Host $ln.Substring(1) -ForegroundColor Cyan }
            elseif ($ln.StartsWith("!")) { Write-Host $ln.Substring(1) -ForegroundColor Yellow }
            else { Write-Host $ln }
        }
    } else {
        # self-test: the screen a player would see, codes masked (lobby-screens.txt keeps every different screen)
        $masked = Mask $text
        if ($masked -ne $L.lastScreen) {
            $L.lastScreen = $masked
            $plain = (($lines | ForEach-Object { if ($_.StartsWith("#") -or $_.StartsWith("!")) { $_.Substring(1) } else { $_ } }) -join "`r`n")
            $plain = Mask $plain
            try {
                [System.IO.File]::WriteAllText((Join-Path $L.logDir "lobby-screen.txt"), $plain + "`r`n", $utf8)
                [System.IO.File]::AppendAllText((Join-Path $L.logDir "lobby-screens.txt"),
                    ("---- {0} s`r`n{1}`r`n" -f (Fmt1 (((NowMs) - $L.t0) / 1000.0)), $plain), $utf8)
            } catch { }
        }
        $pr = $(if ($L.isHost) { Get-Problems $L } else { @{} })
        if (-not $L.isHost -and $L.peers.ContainsKey(0) -and $null -ne $L.peers[0].hello) {
            $own = $(if ([string]$L.peers[0].hello["save"] -eq $L.saveHash) { "same" } else { "DIFFERENT" })
            if ($own -eq "DIFFERENT") { $L.problemLog["own-save"] = "different from the host's" }
            $pr = @{ -1 = "own save $own" }
        }
        $st = "lobby: slot {0}, players {1}, helper ready {2}, peers [{3}], problems [{4}], delay {5}" -f $L.slot, $L.players, $L.ready,
            ((@($L.peers.Keys | Sort-Object) | ForEach-Object { "{0}:{1}" -f $_, $(if ((NowMs) - $L.peers[$_].lastRx -lt 4000) { "up" } else { "-" }) }) -join " "),
            ((@($pr.Keys | Sort-Object) | ForEach-Object { "{0}={1}" -f ($_ + 1), $pr[$_] }) -join " "), $L.delay
        if ($st -ne $L.lastStatus) { $L.lastStatus = $st; LLog $L $st }
    }
}

function Get-LanAddresses {
    $r = @()
    foreach ($ni in [System.Net.NetworkInformation.NetworkInterface]::GetAllNetworkInterfaces()) {
        if ($ni.OperationalStatus -ne "Up" -or $ni.NetworkInterfaceType -eq "Loopback") { continue }
        $props = $ni.GetIPProperties()
        $gw = @($props.GatewayAddresses | Where-Object { $_.Address.AddressFamily -eq "InterNetwork" -and $_.Address.ToString() -ne "0.0.0.0" }).Count -gt 0
        foreach ($ua in $props.UnicastAddresses) {
            $a = $ua.Address
            if ($a.AddressFamily -ne "InterNetwork" -or $a.ToString().StartsWith("169.254.")) { continue }
            $r += ("{0,-16} ({1}{2})" -f $a.ToString(), $ni.Name, $(if ($gw) { ", home network" } else { "" }))
        }
    }
    if ($r.Count -eq 0) { $r += "(no network address found - is this PC connected to the router?)" }
    return $r
}

# ---------------------------------------------------------------- the lobby loop
function Run-Lobby($L) {
    $nextTick = 0.0
    $autoStart = [bool](TV "autoStart" $false)
    $startAfter = [double](TV "startAfterSec" 3) * 1000.0
    $timeout = [double](TV "lobbyTimeoutSec" 0) * 1000.0
    while ($true) {
        if ($L.code) { Pump-Helper $L }
        Pump-Lobby $L
        $now = NowMs
        if ($L.code -and ($L.helperEof -or ($null -ne $L.helper -and $L.helper.HasExited))) {
            Pump-Helper $L
            return "helper"
        }
        if (-not $L.isHost -and $L.started -and ($L.hostLeft -or $now - $L.startAt -gt 2000)) { return "start" }
        if ($L.hostLeft) { return "hostleft" }
        if ($L.isHost -and $L.starting) { Host-StartStep $L; if ($L.go) { return "start" } }
        if ($now -ge $nextTick) {
            $nextTick = $now + 1000.0
            if ($L.mode -eq "lanjoin" -and $L.slot -lt 0 -and $L.refused -eq "") {
                Send-Ep $L $L.hostEp ("JOIN|slot=-1|nonce={0}|ver={1}" -f $L.nonce, $pkgId)
            }
            if ($L.slot -ge 0) { Send-Hellos $L }
            if ($L.group -ne "" -and $now - $L.saveAt -gt 5000) { $L.saveHash = Get-SaveHash $L.group; $L.saveAt = $now }
            if ($L.isHost -and -not $L.starting) { $L.delay = Compute-Delay $L }
            if ($L.code -and -not $L.isHost -and $L.replyCode -ne "" -and -not $L.replyCopied -and $now - $L.t0 -gt 10000) {
                $hostOk = $L.peers.ContainsKey(0) -and $null -ne $L.peers[0].hello
                if (-not $hostOk) {
                    Copy-ToClipboard $L.replyCode
                    $L.replyCopied = $true
                    LLog $L "not connected after 10 s: reply code shown and copied"
                }
            }
            if (-not $L.isHost -and $L.slot -lt 0 -and -not $L.lateHint -and $now - $L.t0 -gt 30000) {
                $L.lateHint = $true
                [void]$L.events.Add("not connected after 30 s")
                LLog $L "not connected after 30 s (if the host already started, joining is not possible until the next game)"
            }
            if (-not $interactive -and $autoStart -and $L.isHost -and -not $L.starting -and $now - $L.t0 -gt $startAfter -and
                (Start-Blockers $L) -eq "") { Try-Start $L }
            Show-Lobby $L
        }
        $keys = $false
        if ($interactive) { try { $keys = [Console]::KeyAvailable } catch { $keys = $false } }
        if ($interactive) {
            while ($keys -and [Console]::KeyAvailable) {
                $k = [Console]::ReadKey($true)
                $c = [string]$k.KeyChar
                if ($c -match '^[qQ]$') {
                    foreach ($p in @(Targets $L)) { Send-Slot $L $p ("BYE|slot={0}" -f $L.slot) }
                    return "quit"
                }
                if ($L.isHost -and $c -match '^[sS]$') { Try-Start $L; $L.lastScreen = "" }
                if ($L.isHost -and $L.code -and $c -match '^[rR]$') { Paste-Reply $L }
                if (-not $L.isHost -and $L.code -and $c -match '^[cC]$' -and $L.replyCode -ne "") {
                    Copy-ToClipboard $L.replyCode; $L.replyCopied = $true; Add-Msg $L "Reply code copied."
                }
            }
        } else {
            if ($timeout -gt 0 -and $now - $L.t0 -gt $timeout -and -not $L.started -and -not $L.starting) { return "timeout" }
        }
        if ($null -ne $L.udp) {
            try { [void]$L.udp.Client.Poll(20000, [System.Net.Sockets.SelectMode]::SelectRead) } catch { Start-Sleep -Milliseconds 20 }
        } else { Start-Sleep -Milliseconds 20 }
    }
}

function Paste-Reply($L) {
    $clip = Read-ClipboardText
    if ($clip -notmatch 'W4P\d-') {
        Write-Host ""
        $clip = Read-Host "Paste the reply code here (right-click or Ctrl+V), then press Enter"
    }
    $clip = Clean-Text $clip
    if ($clip -match 'W4P\d-') { Helper-Send $L $clip; Add-Msg $L "Reply code passed to the connection helper." }
    else { Add-Msg $L "No reply code found. Copy the whole code (it starts with W4P1-) and press R again." }
    $L.lastScreen = ""
}

# ---------------------------------------------------------------- the game
function Copy-SaveIn($L, [string]$root) {
    $mc = Join-Path $root "memcards"
    $left = Join-Path $DataDir "memcard-leftovers"   # cards left by an earlier session that did not end normally
    foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
        $p = Join-Path $mc $m
        if (Test-Path -LiteralPath $p) {
            New-Item -ItemType Directory -Force -Path $left | Out-Null
            Move-Item -Force -LiteralPath $p -Destination (Join-Path $left ("{0}_{1}" -f $L.stamp, $m))
        }
    }
    if (Test-Path -LiteralPath $left) {
        Get-ChildItem -LiteralPath $left -File | Sort-Object LastWriteTime -Descending | Select-Object -Skip 6 | Remove-Item -Force
    }
    $src = Save-Dir $L.group
    foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
        $p = Join-Path $src $m
        if (Test-Path -LiteralPath $p) { Copy-Item -Force -LiteralPath $p -Destination (Join-Path $mc $m) }
    }
    return (Get-DirSaveHash $mc)
}

function Copy-SaveOut($L, [string]$root) {
    $mc = Join-Path $root "memcards"
    $dst = Save-Dir $L.group
    New-Item -ItemType Directory -Force -Path $dst | Out-Null
    $old = @(foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) { $p = Join-Path $dst $m; if (Test-Path -LiteralPath $p) { $p } })
    if ($old.Count -gt 0) {
        $bk = Join-Path $dst ("backup\" + $L.stamp)
        New-Item -ItemType Directory -Force -Path $bk | Out-Null
        foreach ($p in $old) { Copy-Item -Force -LiteralPath $p -Destination $bk }
        Get-ChildItem -LiteralPath (Join-Path $dst "backup") -Directory | Sort-Object Name -Descending | Select-Object -Skip 5 |
            Remove-Item -Recurse -Force
    }
    foreach ($m in @("Mcd001.ps2", "Mcd002.ps2")) {
        $p = Join-Path $mc $m
        if (Test-Path -LiteralPath $p) { Copy-Item -Force -LiteralPath $p -Destination (Join-Path $dst $m) }
    }
    $h = Get-DirSaveHash $dst
    $info = @("warriors-4p co-op save `"$($L.group)`"", "saved: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss', $Inv))",
        "players: $($L.players), you were Player $($L.slot + 1)", "save check code: $(Save-Label $h)", "full hash: $h",
        "Every player of this group must have exactly these files before the next game (the host's files are the reference).")
    [System.IO.File]::WriteAllText((Join-Path $dst "save-info.txt"), (($info -join "`r`n") + "`r`n"), $utf8)
    return $h
}

function Analyze-W4PLog([string]$path) {
    $r = @{ started = $false; shutdown = $false; mismatches = -1; hostGone = $false; differs = $false; desync = $false }
    if (-not (Test-Path -LiteralPath $path)) { return $r }
    $txt = [System.IO.File]::ReadAllText($path)
    $r.started = $txt.Contains("session started at guest poll")
    $mm = [regex]::Matches($txt, 'shutdown: polls \d+[^\r\n]*?mismatches (\d+)')
    if ($mm.Count -gt 0) { $r.shutdown = $true; $r.mismatches = [int]$mm[$mm.Count - 1].Groups[1].Value }
    $r.hostGone = $txt.Contains("the host did not come back")
    $r.differs = $txt.Contains("ERROR: player")
    $r.desync = $txt.Contains("DESYNC")
    return $r
}

function Run-Game($s, $L) {
    $root = Join-Path $DataDir "PCSX2"   # PCSX2 puts its files in <datapath>\PCSX2
    foreach ($sub in @("inis", "memcards", "patches", "gamesettings", "logs", "cache", "snaps", "sstates", "cheats", "textures", "inputprofiles", "videos")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $root $sub) | Out-Null
    }
    $full = IsYes $s["Fullscreen"]
    $logDir = $L.logDir

    # Settings profile (MTVU stays off in the profile; EE cycle rate 180 % with 60 fps, 100 % without)
    $prof = [System.IO.File]::ReadAllText($profileFile)
    $biosItem = Get-Item -LiteralPath $s["Bios"]
    $prof = $prof.Replace("{FULLSCREEN}", $(if ($full) { "true" } else { "false" }))
    $prof = $prof.Replace("{BIOS_DIR}", $biosItem.DirectoryName).Replace("{BIOS_FILE}", $biosItem.Name)
    $prof = $prof.Replace("{EE_CYCLE_RATE}", $(if ($L.fps60) { "2" } else { "0" }))
    $prof = $prof.Replace("{RENDERER}", $s["Renderer"]).Replace("{ADAPTER}", $s["Adapter"]).Replace("{UPSCALE}", $s["Quality"])
    [System.IO.File]::WriteAllText((Join-Path $root "inis\PCSX2.ini"), $prof, $utf8)

    # Game patch and the groups to enable (identical on every PC: the host's choices)
    Copy-Item -Force -LiteralPath $pnachFile -Destination (Join-Path $root "patches\SLUS-21215_B99A75DE.pnach")
    $groups = @(TV "baseGroups" $BaseGroups)   # developer self-test only may replace the base list (isolation tests)
    if ($L.fps60) { $groups += "warriors-4p 60fps" }
    if ($L.wide) { $groups += "warriors-4p widescreen" }
    foreach ($g in @(TV "extraGroups" @())) { $groups += [string]$g }   # developer self-test only
    $gs = "[Patches]`r`n" + (($groups | ForEach-Object { "Enable = $_" }) -join "`r`n") + "`r`n"
    foreach ($n in @("SLUS-21215_B99A75DE.ini", "B99A75DE.ini")) { [System.IO.File]::WriteAllText((Join-Path $root "gamesettings\$n"), $gs, $utf8) }

    # Co-op save: copied into the emulator's own memory card folder; its hash goes into the handshake
    $cardHash = Copy-SaveIn $L $root
    if ($cardHash -ne $L.saveHash) { LLog $L "WARNING: memory card copy $cardHash differs from the agreed save $($L.saveHash)" }
    $patchSet = $pnachHash + "|" + ($groups -join ";") + "|" + $cardHash

    # Online session settings
    $w4p = @("[W4P]", "Enabled = true", "Players = $($L.players)", "LocalSlot = $($L.slot)")
    for ($p = 0; $p -lt 4; $p++) { $w4p += "PadForSlot$p = $($PadForSlot[$p])" }
    if ($L.code) {
        $w4p += @("ListenPort = $($L.emuPort)", "BindAddress = 127.0.0.1")
        for ($p = 0; $p -lt $L.players; $p++) { if ($p -ne $L.slot) { $w4p += "Peer$p = 127.0.0.1:$($L.slotBase + $p)" } }
    } else {
        $w4p += @("ListenPort = $($L.lanPort)", "BindAddress = $($L.lanBind)")
        for ($p = 0; $p -lt $L.players; $p++) {
            if ($p -ne $L.slot) { $ep = $L.peers[$p].ep; $w4p += ("Peer{0} = {1}:{2}" -f $p, $ep.Address, $ep.Port) }
        }
    }
    $w4p += @("InputDelay = $($L.delay)", "HashInterval = 30", "LogFile = $logDir\w4p.log", "DumpDir = $logDir", "Crop = true",
        "SessionPolicies = true", "DisconnectTimeoutS = 60", "LeaveCalls = 0:000E7100:P", "RestartCalls = 0:00160D78:GM+0x124",
        "RestartCallsP2 = 0:00419AC0:GM:0,2:00160D78:GM+0x124", "PatchSet = $patchSet")
    $bot = [string](TV "botFile" "")
    if ($bot -ne "") { $w4p += "BotInput = $bot" }                    # developer self-test only
    foreach ($e in @(TV "extraW4P" @())) { $w4p += [string]$e }       # developer self-test only
    $w4pIni = Join-Path $logDir "w4p.ini"
    [System.IO.File]::WriteAllText($w4pIni, (($w4p -join "`r`n") + "`r`n"), $utf8)
    Copy-Item -Force -LiteralPath (Join-Path $root "inis\PCSX2.ini") -Destination (Join-Path $logDir "PCSX2.ini")

    if ($interactive) {
        Clear-Host
        Write-Host ""
        Write-Host ("You are Player {0} of {1}. The game is starting..." -f ($L.slot + 1), $L.players) -ForegroundColor Cyan
        Write-Host ("60 fps: {0}   Widescreen: {1}   Input delay: {2} frames   Co-op save: `"{3}`"" -f (YesNo $L.fps60), (YesNo $L.wide), $L.delay, $L.group)
        Write-Host "Tab (keyboard) or the touchpad/share button (controller) switches between your view and all views."
        Write-Host "Esc or Start pauses the game for everybody. Keep this window open while you play."
        Write-Host "Logs: $logDir"
        Write-Host ""
    }
    LLog $L ("game starting: slot {0}, players {1}, delay {2}, patch set {3}" -f $L.slot, $L.players, $L.delay, $patchSet)

    $isoItem = Get-Item -LiteralPath $s["Iso"]
    $env:W4P_CONFIG = $w4pIni
    $q = { param($x) '"' + $x + '"' }
    $argList = @("-batch", "-datapath", (& $q $DataDir), "-logfile", (& $q (Join-Path $logDir "emulog.txt")))
    if ($full) { $argList += "-fullscreen" }
    $argList += @("--", (& $q $isoItem.FullName))
    $proc = Start-Process -FilePath $emuExe -ArgumentList $argList -PassThru
    $null = $proc.Handle   # keeps the exit code available
    [System.IO.File]::WriteAllText((Join-Path $logDir "pid.txt"), [string]$proc.Id)
    Write-Status $L "running" @{ emuPid = $proc.Id; cardHashStart = $cardHash }

    $runS = [double](TV "runSeconds" 0)
    $t0 = NowMs; $closing = $false; $closeT = 0.0; $lastClose = -1e9; $forced = $false
    while (-not $proc.HasExited) {
        if ($L.code) { Pump-Helper $L }
        if ($runS -gt 0 -and -not $closing -and (NowMs) - $t0 -gt $runS * 1000.0) {
            $closing = $true; $closeT = NowMs
            LLog $L "self-test: closing the game window after $runS s"
        }
        if ($closing) {
            if ((NowMs) - $lastClose -gt 30000) { $proc.Refresh(); [void]$proc.CloseMainWindow(); $lastClose = NowMs }
            if ((NowMs) - $closeT -gt 150000) {
                LLog $L "self-test: the game did not close within 150 s; stopping it"
                try { Stop-Process -Id $proc.Id -Force } catch { }
                $forced = $true
                break
            }
        }
        Start-Sleep -Milliseconds 200
    }
    $proc.WaitForExit()
    $exitCode = $(try { $proc.ExitCode } catch { -1 })
    if ($L.code) { Pump-Helper $L }
    $a = Analyze-W4PLog (Join-Path $logDir "w4p.log")
    LLog $L ("game closed: exit code {0}, session started {1}, shutdown line {2}, mismatches {3}, host gone {4}, differs {5}" -f
        $exitCode, $a.started, $a.shutdown, $a.mismatches, $a.hostGone, $a.differs)

    # Co-op progress is kept only when this game ended normally (in sync to the end, closed by the player)
    $why = ""
    if ($forced) { $why = "the game had to be stopped" }
    elseif ($exitCode -ne 0) { $why = "the game did not close normally (exit code $exitCode)" }
    elseif (-not $a.started) { $why = "the online game never started" }
    elseif (-not $a.shutdown) { $why = "the game log is incomplete" }
    elseif ($a.mismatches -ne 0 -or $a.desync) { $why = "the game went out of sync" }
    elseif ($a.differs) { $why = "the players' settings did not match" }
    elseif ($a.hostGone) { $why = "the host left during the game" }
    $saved = $false; $endHash = ""
    if ($why -eq "") {
        $endHash = Copy-SaveOut $L $root
        $saved = $true
        LLog $L ("co-op save stored in {0} ({1})" -f (Save-Dir $L.group), $endHash)
    } else { LLog $L ("co-op save NOT stored: " + $why) }
    Stop-Helper $L
    Write-Status $L "done" @{ emuPid = $proc.Id; exitCode = $exitCode; forcedClose = $forced; cardHashStart = $cardHash
        normalEnd = ($why -eq ""); notSavedReason = $why; savedBack = $saved; saveHashEnd = $endHash; w4p = $a }
    if ($interactive) {
        Write-Host ""
        Write-Host "The game has closed." -ForegroundColor Cyan
        if ($saved) { Write-Host ("Co-op progress saved in coop-saves\{0} ({1})." -f $L.group, (Save-Label $endHash)) -ForegroundColor Green }
        else {
            Write-Host ("Co-op progress was NOT saved: {0}." -f $why) -ForegroundColor Yellow
            Write-Host "Your co-op save stays as it was before this game. If another player's game ended normally, copy the host's save (README, step 9)."
        }
        Write-Host "Your logs are in:"
        Write-Host "  $logDir"
        Write-Host "Please send that whole folder from EVERY PC back for checking (README, step 10)."
        Read-Host "Press Enter to go back to the menu"
    }
}

# ---------------------------------------------------------------- one session: lobby, then the game
function Run-Session($s, [string]$mode, $opt) {
    $L = New-Lobby $s $mode
    $helperArgs = @(TV "helperArgs" @())
    $common = @("--emu-port", "$($L.emuPort)", "--slot-ports", "$($L.slotBase)", "--ice-port", "$($L.icePort)",
        "--log", (Join-Path $L.logDir "connection-log.txt"), "--stats", (Join-Path $L.logDir "connection-stats.json"))
    try {
        if ($L.isHost) {
            $L.slot = 0; $L.players = [int]$opt.players; $L.group = [string]$opt.group; $L.fps60 = [bool]$opt.fps60; $L.wide = [bool]$opt.wide
            $L.saveHash = Get-SaveHash $L.group; $L.saveAt = NowMs
            LLog $L ("host: {0} players, co-op save '{1}' {2}, 60 fps {3}, widescreen {4}" -f $L.players, $L.group, $L.saveHash, $L.fps60, $L.wide)
        }
        switch ($mode) {
            "host" {
                Start-Helper $L (@("host", "--players", "$($L.players)") + $common + $helperArgs)
                Open-Lobby $L "127.0.0.1" $L.emuPort
            }
            "join" {
                Start-Helper $L (@("join", (Clean-Text $opt.code)) + $common + $helperArgs)
                Open-Lobby $L "127.0.0.1" $L.emuPort
            }
            "lanhost" { Open-Lobby $L $L.lanBind $L.lanPort }
            "lanjoin" {
                $L.nonce = ([guid]::NewGuid().ToString("N")).Substring(0, 10)
                $L.hostEp = [System.Net.IPEndPoint]::new([System.Net.IPAddress]::Parse([string]$opt.hostIp), [int]$opt.hostPort)
                Open-Lobby $L $L.lanBind $L.lanPort
            }
        }
        $result = Run-Lobby $L
        LLog $L "lobby ended: $result"
        Close-Lobby $L
        if ($result -ne "start") {
            if ($result -eq "quit") { foreach ($p in @(Targets $L)) { Send-Slot $L $p ("BYE|slot={0}" -f $L.slot) } }
            Stop-Helper $L
            Write-Status $L ("lobby-" + $result) $null
            if ($interactive) {
                Write-Host ""
                switch ($result) {
                    "helper" { Write-Host ("The connection helper stopped. " + (@($L.msgs) -join " ")) -ForegroundColor Yellow }
                    "hostleft" { Write-Host "The host closed the game." -ForegroundColor Yellow }
                    default { Write-Host "Left the lobby." }
                }
                Read-Host "Press Enter to go back to the menu"
            }
            return
        }
        if ([bool](TV "stopBeforeGame" $false)) {   # developer self-test of the lobby only: no emulator
            Start-Sleep -Seconds 3
            Stop-Helper $L
            Write-Status $L "start-ok" $null
            return
        }
        Write-Status $L "starting" $null
        Run-Game $s $L
    } finally {
        Close-Lobby $L
        if ($null -ne $L.helper -and -not $L.helper.HasExited) { Stop-Helper $L }
    }
}

# ---------------------------------------------------------------- menus
function Choose-Group($s) {
    $groups = @(List-Groups)
    $last = $(if ($s.ContainsKey("Group") -and (Valid-Group $s["Group"])) { $s["Group"] } else { "main" })
    Write-Host ""
    Write-Host "Co-op save: each group of friends has its own save (a story played together)."
    if ($groups.Count -gt 0) { Write-Host ("Saves on this PC: " + ($groups -join ", ")) }
    while ($true) {
        $g = Ask "Which co-op save? Type a name (a new name starts the story from the beginning)" $last
        if (Valid-Group $g) { break }
        Write-Host "Use letters, digits, spaces, - or _ (at most 32 characters)." -ForegroundColor Yellow
    }
    $s["Group"] = $g
    Write-Settings $s
    return $g
}

function Menu-Host($s) {
    Write-Host ""
    $n = 0
    while ($n -lt 2 -or $n -gt 4) {
        $a = Ask "How many players, including you? 2, 3 or 4" "4"
        [void][int]::TryParse($a, [ref]$n)
    }
    Write-Host ""
    Write-Host "How will your friends connect?"
    Write-Host "  1  with a join code (over the internet, or in the same house) - recommended"
    Write-Host "  2  by IP address (same house / same router only, no codes)"
    $how = Ask "Choose 1 or 2" "1"
    $g = Choose-Group $s
    $fps = IsYes (Ask "60 fps for everybody? yes/no" (YesNo (IsYes $s["Fps60"])))
    $wide = IsYes (Ask "Widescreen 16:9 for everybody? yes/no" (YesNo (IsYes $s["Widescreen"])))
    $s["Fps60"] = YesNo $fps; $s["Widescreen"] = YesNo $wide
    Write-Settings $s
    $mode = $(if ($how -eq "2") { "lanhost" } else { "host" })
    Run-Session $s $mode @{ players = $n; group = $g; fps60 = $fps; wide = $wide }
}

function Menu-Join($s) {
    Write-Host ""
    $clip = Read-ClipboardText
    $code = ""
    if ($clip -match 'W4P\d-') {
        $short = [regex]::Match($clip, 'W4P\d-[0-9A-Za-z]{0,10}').Value
        if (IsYes (Ask "Found a join code in your clipboard ($short...). Use it? yes/no" "yes")) { $code = $clip }
    }
    if ($code -eq "") { $code = Read-Host "Paste the join code from the host here (right-click or Ctrl+V), then press Enter" }
    if ($code -notmatch 'W4P\d-') { Write-Host "That is not a join code (it starts with W4P1-)." -ForegroundColor Yellow; Start-Sleep -Seconds 2; return }
    Run-Session $s "join" @{ code = $code }
}

function Menu-JoinIp($s) {
    Write-Host ""
    Write-Host "The host's window shows the address to type (for example 192.168.1.23)."
    $ip = Ask "Host's IP address" ""
    $addr = $null
    if (-not [System.Net.IPAddress]::TryParse($ip.Trim(), [ref]$addr) -or $addr.AddressFamily -ne "InterNetwork") {
        Write-Host "That is not an IP address like 192.168.1.23." -ForegroundColor Yellow; Start-Sleep -Seconds 2; return
    }
    Run-Session $s "lanjoin" @{ hostIp = $addr.ToString(); hostPort = [int]$s["LanPort"] }
}

function Menu-Settings($s) {
    while ($true) {
        Write-Host ""
        Write-Host "Settings" -ForegroundColor Cyan
        Write-Host "  1  Game file:        $($s['Iso'])"
        Write-Host "  2  BIOS file:        $($s['Bios'])"
        Write-Host "  3  Picture quality:  $($s['Quality'])  (1 = native, up to 12 = sharpest)"
        Write-Host "  4  Full screen:      $($s['Fullscreen'])"
        Write-Host "  5  60 fps when you host:      $($s['Fps60'])"
        Write-Host "  6  Widescreen when you host:  $($s['Widescreen'])"
        Write-Host "  7  Open the co-op save folder"
        Write-Host "  8  Back"
        $c = Ask "Choose" "8"
        switch ($c) {
            "1" { $s["Iso"] = Pick-File "Choose The Warriors (USA) ISO" "PS2 disc image (*.iso;*.bin;*.chd)|*.iso;*.bin;*.chd|All files|*.*"; $s.Remove("IsoChecked"); Write-Settings $s; $script:isoOk = Check-Iso $s }
            "2" { $s["Bios"] = Pick-File "Choose your PS2 BIOS file" "PS2 BIOS (*.bin;*.rom0;*.ROM0)|*.bin;*.rom0;*.ROM0|All files|*.*"; Write-Settings $s }
            "3" { $s["Quality"] = Ask "Picture quality 1-12" $s["Quality"]; Write-Settings $s }
            "4" { $s["Fullscreen"] = YesNo (IsYes (Ask "Full screen? yes/no" $s["Fullscreen"])); Write-Settings $s }
            "5" { $s["Fps60"] = YesNo (IsYes (Ask "60 fps? yes/no" $s["Fps60"])); Write-Settings $s }
            "6" { $s["Widescreen"] = YesNo (IsYes (Ask "Widescreen? yes/no" $s["Widescreen"])); Write-Settings $s }
            "7" { New-Item -ItemType Directory -Force -Path $savesRoot | Out-Null; Start-Process explorer.exe -ArgumentList ('"' + $savesRoot + '"') }
            default { return }
        }
    }
}

function First-Setup($s) {
    Write-Host "First start: a few questions. Press Enter to take the suggestion in [brackets]." -ForegroundColor Cyan
    Write-Host "Choose your game file (The Warriors, USA, .iso)..."
    $s["Iso"] = Pick-File "Choose The Warriors (USA) ISO" "PS2 disc image (*.iso;*.bin;*.chd)|*.iso;*.bin;*.chd|All files|*.*"
    Write-Host "Choose your PS2 BIOS file (dumped from a PS2 you own)..."
    $s["Bios"] = Pick-File "Choose your PS2 BIOS file" "PS2 BIOS (*.bin;*.rom0;*.ROM0)|*.bin;*.rom0;*.ROM0|All files|*.*"
    $adapter = Default-Adapter
    $s["Adapter"] = $adapter
    $s["Quality"] = Ask "Picture quality 1-12 (higher = sharper, needs a stronger graphics card)" (Default-Quality $adapter)
    $s["Fullscreen"] = YesNo (IsYes (Ask "Start the game in full screen? yes/no" "yes"))
    if (-not $s.ContainsKey("Fps60")) { $s["Fps60"] = "yes" }
    if (-not $s.ContainsKey("Widescreen")) { $s["Widescreen"] = "yes" }
    if (-not $s.ContainsKey("Renderer")) { $s["Renderer"] = "14" }
    Write-Settings $s
}

# ---------------------------------------------------------------- main
try {
    $pkgId = Get-PackageId
    $pnachHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $pnachFile).Hash.ToLower()
    if ($interactive) {
        $Host.UI.RawUI.WindowTitle = "warriors-4p co-op"
        Write-Host ""
        Write-Host "warriors-4p online co-op for 2-4 players - TEST VERSION (experimental)" -ForegroundColor Cyan
        Write-Host ""
    }
    $s = Read-Settings
    if ($Reset -or -not $s.ContainsKey("Iso") -or -not $s.ContainsKey("Bios")) {
        if (-not $interactive) { throw "self-test settings file is incomplete" }
        First-Setup $s
    }
    foreach ($kv in @(@("EmuPort", "41000"), @("SlotPorts", "41100"), @("IcePort", "41500"), @("LanPort", "41000"))) {
        if (-not $s.ContainsKey($kv[0])) { $s[$kv[0]] = $kv[1] }
    }
    if (-not (Test-Path -LiteralPath $s["Iso"])) { throw "Game file not found: $($s['Iso']) (choose it again: start with -Reset)" }
    if (-not (Test-Path -LiteralPath $s["Bios"])) { throw "BIOS file not found: $($s['Bios']) (choose it again: start with -Reset)" }
    $script:isoOk = Check-Iso $s

    if (-not $interactive) {
        $mode = [string](TV "mode" "host")
        $opt = @{ players = [int](TV "players" 2); group = [string](TV "group" "selftest"); fps60 = [bool](TV "fps60" $true)
            wide = [bool](TV "wide" $true); hostIp = [string](TV "hostIp" "127.0.0.1"); hostPort = [int](TV "hostPort" 41000); code = "" }
        if ($mode -eq "join") {
            $cf = [string](TV "codeFile" "")
            $deadline = (NowMs) + 180000
            while ((NowMs) -lt $deadline -and -not (Test-Path -LiteralPath $cf)) { Start-Sleep -Milliseconds 200 }
            Start-Sleep -Milliseconds 300
            $opt.code = [System.IO.File]::ReadAllText($cf)
        }
        Run-Session $s $mode $opt
        exit 0
    }

    while ($true) {
        Write-Host ""
        Write-Host "What do you want to do?" -ForegroundColor Cyan
        Write-Host "  1  Host a game (2, 3 or 4 players)"
        Write-Host "  2  Join a game (paste the join code from the host)"
        Write-Host "  3  Join by IP address (same house / same router)"
        Write-Host "  4  Settings"
        Write-Host "  5  Quit"
        $c = Ask "Choose" "1"
        switch ($c) {
            "1" { Menu-Host $s }
            "2" { Menu-Join $s }
            "3" { Menu-JoinIp $s }
            "4" { Menu-Settings $s }
            "5" { exit 0 }
        }
    }
} catch {
    Write-Host ""
    Write-Host ("Something went wrong: " + $_.Exception.Message) -ForegroundColor Red
    if (-not $interactive) { [Console]::Out.WriteLine(($_ | Out-String)) }
    if ($interactive) { Read-Host "Press Enter to close" }
    exit 1
}
