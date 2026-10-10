# PCSX2 v2.9.115: capability research (Stage 1, read-only)

- **Author:** Claude (research subagent). **Date:** 2026-10-10. **Method:** I read the source text at the tag (fetched as raw text from GitHub) and the official docs. I did not download, install or run any binaries.
- **Target build:** PCSX2 **v2.9.115**, Qt, Windows x64.
- **Tag check (VERIFIED):** the tag `v2.9.115` exists and points to commit `cf3c372043ae4fe0f2561de80d223755b5d7bf94`, committed 2026-10-09T21:19:59Z. Evidence: https://api.github.com/repos/PCSX2/pcsx2/git/refs/tags/v2.9.115 (accessed 2026-10-10). The matching GitHub release is a **pre-release** ("nightly") published 2026-10-09T21:33:40Z. Its Windows asset is `pcsx2-v2.9.115-windows-x64-Qt.7z`. Evidence: https://api.github.com/repos/PCSX2/pcsx2/releases/tags/v2.9.115 (accessed 2026-10-10).
- **Labels:** I use the project's evidence standard (BRIEF.md §3).
  - **VERIFIED** here means "confirmed by reading the source or docs at this tag". **Nothing in this note has been runtime-tested.**
  - **HYPOTHESIS** means a plausible inference, with what would confirm it.
  - **BLOCKED** means investigation could not proceed.
- **Citation convention:** `[path Lx-Ly]` means `https://github.com/PCSX2/pcsx2/blob/v2.9.115/<path>#Lx-Ly`. All source citations are at tag v2.9.115 and were accessed 2026-10-10. Docs citations point to `https://github.com/PCSX2/pcsx2-net-www/blob/main/<path>` (main branch, accessed 2026-10-10). Those pages are not version-pinned, so where docs and source disagree, I treat the source as authoritative.

---

## 0. Summary table

| Feature | Exists in v2.9.115? | Label | Primary evidence (accessed 2026-10-10) |
|---|---|---|---|
| PINE IPC server (memory r/w, save/load state, info) | Yes, 16 opcodes. TCP on 127.0.0.1:`PINESlot` on Windows | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/PINE.cpp#L144-L163 |
| PINE reads/writes run on a separate "PINE Server" thread with no lock | Yes. They are asynchronous to emulation, so a read can land mid-frame | VERIFIED (source); not runtime-tested | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/PINE.cpp#L534-L629 |
| PINE save/load state | Queued to the CPU thread, then IPC_OK is returned immediately. Not frame-exact on demand | VERIFIED (source) | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/PINE.cpp#L641-L668 |
| PINE pause / frame-advance / pad-input commands | **No** | VERIFIED (absent from opcode enum) | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/PINE.cpp#L144-L163 |
| Input recording (.p2m2) | Yes, file version 1. **Only 2 pads (1A, 2A); no multitap slots** | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/Recording/InputRecordingFile.h#L20-L88 |
| Start input recording/playback from the command line | **No** CLI option | VERIFIED (absent from parser) | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2-qt/QtHost.cpp#L2179-L2383 |
| CLI: `-batch -nogui -portable -datapath -elf -gamecfg -disc -logfile -bios -fastboot -slowboot -state -statefile -fullscreen -earlyconsolelog -debugger -turbo -unlimited`… | Yes | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2-qt/QtHost.cpp#L2132-L2171 |
| `-settings <ini>` option | **No.** Use `-datapath <dir>` or a portable copy instead (each has its own `inis/PCSX2.ini`) | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/Pcsx2Config.cpp#L2203-L2299 |
| Single-instance lock | None found | VERIFIED (absence by grep of pcsx2/, pcsx2-qt/, common/) | (search, see §3) |
| Savestate = zip (.p2s) with named entries (eeMemory.bin, …) | Yes. Zstd by default | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/SaveState.cpp#L696-L711 |
| Multitap emulation, 8 pads | Yes. `[Pad] MultitapPort1/2`, `[Pad1]..[Pad8]` | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/SIO/Sio.cpp#L36-L54 |
| Pnach patches (place 0–3, EE/IOP, byte…bytes, extended RAW, dpatch) | Yes | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/Patch.h#L32-L80 |
| Qt debugger (breakpoints, memchecks, memory search, symbols) | Yes | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2-qt/Debugger/Docking/DockTables.cpp#L40-L56 |
| Built-in netplay / input sync / rollback | **No** (only an FAQ link to an external fork) | VERIFIED (absence by grep) | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/Docs/PCSX2_FAQ.md#L198-L199 |
| License | GPL-3.0+ headers; COPYING.GPLv3. 2 files are GPL-3.0-only and are compiled into the Windows build | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/COPYING.GPLv3 |
| Fixed-RTC option | Yes: `EmuCore/ManuallySetRealTimeClock`, `RtcYear`… The RTC is fixed to 2020-03-04 automatically while an input recording is active | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/CDVD/CDVD.cpp#L957-L1029 |
| MTVU enabled by default on ≥3-core PCs | Yes (hardware-dependent default) | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/pcsx2/VMManager.cpp#L3644-L3653 |
| GameDB entry for SLUS-21215 | Yes: compat 5, GS HW fixes only, no gamefixes/speedhack overrides | VERIFIED | https://github.com/PCSX2/pcsx2/blob/v2.9.115/bin/resources/GameIndex.yaml#L70975-L70983 |

---

## 1. PINE IPC

### 1.1 Transport, slot, settings

- **Default slot 28011.** VERIFIED. Source: `#define PINE_DEFAULT_SLOT 28011` [pcsx2/PINE.h L13]. The config default is `PINESlot = 28011;` [pcsx2/Pcsx2Config.cpp L1986].
- **Windows transport is TCP, loopback only, port = slot.** VERIFIED.
  - The source comment reads: "windows claim to have support for AF_UNIX sockets but that is a blatant lie … so we go on TCP sockets." [pcsx2/PINE.cpp L97-L99]
  - The bind calls are `socket(AF_INET, SOCK_STREAM, 0)`, `htonl(INADDR_LOOPBACK); // localhost only`, and `htons(slot)` [pcsx2/PINE.cpp L276-L287].
  - On Linux and macOS the transport is a Unix socket instead: `$XDG_RUNTIME_DIR/pcsx2.sock` (or `$TMPDIR` on macOS, else `/tmp`), with `.<slot>` appended when the slot is not the default [L297-L314].
  - **Consequence:** remote peers cannot connect directly. Each peer needs a local client or relay process.
- **Settings keys.** VERIFIED.
  - The keys live in section `[EmuCore]`: `EnablePINE` (bool, default false) and `PINESlot` (int, default 28011). Evidence: `SettingsWrapBitBool(EnablePINE)` and `SettingsWrapEntry(PINESlot)` inside `SettingsWrapSection("EmuCore")` [pcsx2/Pcsx2Config.cpp L1993-L2042]. The Qt UI binding is `"EmuCore", "EnablePINE", false` / `"EmuCore", "PINESlot", 28011` [pcsx2-qt/Settings/AdvancedSettingsWidget.cpp L66-L67].
  - The Big Picture UI limits the slot to 1024–65535 [pcsx2/ImGui/FullscreenUI_Settings.cpp L5873-L5876]. The server itself only rejects `slot > 65536` [PINE.cpp L277].
- **When the slot setting takes effect.** VERIFIED. `VMManager::ReloadPINE()` reinitializes the server only when the enabled flag or the slot differs from the running server [pcsx2/VMManager.cpp L3798-L3809]. It is called at CPU-thread init [L429] and on game change [L1174]. A slot changed mid-game therefore applies at the next game change or restart. (HYPOTHESIS: other UI paths may also reload it. I found only these two call sites by grep.)
- **Per-instance slot.** Each instance reads its own `PCSX2.ini` (see §3). Give each instance a distinct `[EmuCore] PINESlot`.
  - VERIFIED: if two instances use the same slot, the second fails `bind()`. It then logs "PINE: Error while binding to socket! Shutting down..." and the PINE server is disabled [PINE.cpp L289-L294].
- **PINE is disabled in RetroAchievements hardcore mode.** VERIFIED: `EmuConfig.EnablePINE = false;` [VMManager.cpp L3219].
- **One client at a time.** VERIFIED. `MainLoop` accepts a single client and runs `ClientLoop()` until that client disconnects. Only then does it accept the next client [PINE.cpp L415-L429]. The listen backlog is 4096 [L342].

### 1.2 Wire format (VERIFIED from [PINE.cpp L431-L481], [L511-L757])

- **Request:** `u32 total_len` (little-endian; **includes these 4 bytes**), followed by one or more commands back-to-back. Each command is `u8 opcode` + arguments. A request is a batch.
- **Reply:** `u32 total_len` (includes the 4-byte length and the result byte), then `u8 result` (`0x00` = IPC_OK, `0xFF` = IPC_FAIL), then the concatenated per-command reply payloads in order.
- **Failure behaviour:** if any command fails (no VM, an unknown opcode, or a size check), the whole reply is just `05 00 00 00 FF`. **Writes earlier in the same batch have already been applied and are not rolled back.** The code writes during parsing, then `goto error` returns `MakeFailIPC` [L586-L629, L749-L753].
- **Do not pipeline.** After each message, `ClientLoop` restarts with `receive_length = 0`. Any extra bytes read past `end_length` in the same `recv()` are discarded [L437-L479]. Send one request and wait for its reply. (The rule is VERIFIED from code. The data-loss consequence is a HYPOTHESIS until tested.)
- **Invalid length gets no reply.** If `total_len > 650000` or `< 4`, the server resets its state **without sending any reply** [L456-L462]. A client waiting for a reply would hang, so clients need timeouts.
- **Address semantics:** reads use `vtlb_ramRead<T>(addr)` and writes use `vtlb_ramWrite<T>(addr, v)`. The address is an **EE virtual address**, translated through the current vtlb map.
  - If the page is mapped to a hardware handler (I/O registers), the read returns 0 and the write is silently dropped. The PINE reply is still IPC_OK, because PINE ignores the `bool` result [pcsx2/vtlb.cpp L326-L353].

### 1.3 Full opcode table (VERIFIED, [pcsx2/PINE.cpp L144-L163] and handlers [L534-L748])

```
PINE opcodes, PCSX2 v2.9.115 (pcsx2/PINE.cpp). All integers little-endian.
Request framing:  u32 total_len (incl. itself) | cmd1 | cmd2 | ...
Reply framing:    u32 total_len (incl. itself) | u8 result (0x00 OK / 0xFF FAIL) | payload1 | payload2 | ...
"needs VM" = returns FAIL for the whole batch if VMManager::HasValidVM() is false.

Op    Name            Request args (after opcode)        Reply payload                       needs VM  Notes
0x00  MsgRead8        u32 addr                            u8 value                            yes       vtlb_ramRead<u8>, PINE thread
0x01  MsgRead16       u32 addr                            u16 value                           yes
0x02  MsgRead32       u32 addr                            u32 value                           yes
0x03  MsgRead64       u32 addr                            u64 value                           yes
0x04  MsgWrite8       u32 addr, u8 value                  (none)                              yes       vtlb_ramWrite<u8>, PINE thread
0x05  MsgWrite16      u32 addr, u16 value                 (none)                              yes
0x06  MsgWrite32      u32 addr, u32 value                 (none)                              yes
0x07  MsgWrite64      u32 addr, u64 value                 (none)                              yes
0x08  MsgVersion      -                                   u32 len, char[len] "PCSX2 <GitRev>\0"  no     len = strlen(GitRev)+7
0x09  MsgSaveState    u8 slot                             (none)                              yes       queued: Host::RunOnCPUThread -> VMManager::SaveStateToSlot(slot, zip_on_thread=true)
0x0A  MsgLoadState    u8 slot                             (none)                              yes       queued: Host::RunOnCPUThread -> VMManager::LoadStateFromSlot(slot, backup=false)
0x0B  MsgTitle        -                                   u32 len, char[len] (NUL-terminated) yes       VMManager::GetTitle(false)
0x0C  MsgID           -                                   u32 len, char[len]                  yes       VMManager::GetDiscSerial()  (e.g. serial string)
0x0D  MsgUUID         -                                   u32 len, char[len]                  yes       fmt "{:08x}" of VMManager::GetDiscCRC()
0x0E  MsgGameVersion  -                                   u32 len, char[len]                  yes       VMManager::GetDiscVersion()
0x0F  MsgStatus       -                                   u32 status                          no        0=Running, 1=Paused, 2=Shutdown (anything else)
0xFF  MsgUnimplemented (enum value only; any unknown opcode -> FAIL)

Size limits: MAX_IPC_SIZE = 650000 (whole request incl. 4-byte header)
             MAX_IPC_RETURN_SIZE = 450000 (reply must stay < this)
Max commands per batch (computed from those constants; not tested):
  Read8/Read16 ~129,999 | Read32 ~112,498 | Read64 ~56,249
  Write8 ~108,332 | Write16 ~92,856 | Write32 ~72,221 | Write64 ~49,999
  (source comments say "Equivalent to 50,000 Write64 requests" / "50,000 Read64 replies")
```

Evidence for the limits: `#define MAX_IPC_SIZE 650000` and `#define MAX_IPC_RETURN_SIZE 450000` [PINE.cpp L113-L123]. `SafetyChecks` [L256-L260] requires `(reply_len + reply_size) < MAX_IPC_RETURN_SIZE`. The per-opcode counts are my arithmetic from these constants.

### 1.4 Threading and timing

- **Reads and writes are asynchronous to emulation and can land mid-frame.** VERIFIED (source); not runtime-tested.
  - The server runs on its own `std::thread` named "PINE Server" [PINE.cpp L355, L417].
  - The read and write cases call `vtlb_ramRead` / `vtlb_ramWrite` directly in `ParseCommand`, with no lock and no hand-off to the CPU thread [L534-L629]. `vtlb_ramRead` is a plain `memcpy` from host memory [vtlb.cpp L326-L342].
  - **Consequence:** a batch of reads is **not** an atomic snapshot. Values can come from different points within one emulated frame.
- **Save/load state via PINE is queued, not frame-exact on demand.** VERIFIED (source).
  - Both cases wrap the call in `Host::RunOnCPUThread([...]{ ... })` [PINE.cpp L647-L651, L661-L665]. On the Qt host this is `QMetaObject::invokeMethod(..., Qt::QueuedConnection ...)` with `block = false` [pcsx2-qt/QtHost.cpp L1243-L1254].
  - The PINE reply (`IPC_OK`) is sent **before** the save/load happens. A later failure is only shown in the on-screen display (OSD) via `SaveState_ReportSaveErrorOSD` / `SaveState_ReportLoadErrorOSD`.
  - While the VM is running, the CPU thread processes queued events in two places:
    - at the top of each `VMManager::Execute()` iteration [QtHost.cpp L404-L407];
    - inside `PollInputOnCPUThread()` → `Host::PumpMessagesOnCPUThread()` [VMManager.cpp L2968-L2971], which is called from `VSyncStart()` [pcsx2/Counters.cpp L489-L505].
  - **So a PINE save/load executes at the next vsync boundary after the message arrives.** Which frame that is depends on host timing. When the VM is paused, it runs immediately in the event loop [QtHost.cpp L401-L403].
  - HYPOTHESIS: to get a frame-exact save, pause first and then save. PINE has **no pause opcode**, so pausing would need a hotkey (`TogglePause`, `FrameAdvance` exist [pcsx2/Hotkeys.cpp L172-L180]) or a modified build.
- **PINE writes vs. recompiled code.** HYPOTHESIS (risk).
  - PCSX2 write-protects EE RAM pages that contain recompiled code. On a write fault, the fault handler calls `mmap_ClearCpuBlock()` → `Cpu->Clear(...)` [vtlb.cpp L1481-L1515].
  - A PINE `memcpy` into such a page would fault on the **PINE thread** and clear recompiler blocks from that thread while the EE thread runs. That is a possible race or crash.
  - Patching code (code caves) through PINE should therefore be treated as unsafe until tested. Pnach place-0 patches avoid this problem because the emulator clears all recompiler caches right after applying them (§6).
  - Confirm by stress-testing PINE writes into executing code pages with the recompiler enabled.

---

## 2. Input recording (.p2m2)

### 2.1 Exact file layout (VERIFIED from [pcsx2/Recording/InputRecordingFile.h L20-L88], [InputRecordingFile.cpp L164-L254], [pcsx2/Recording/PadData.cpp L64-L93])

```c
// .p2m2, file version 1, PCSX2 v2.9.115. Little-endian. Header written field-by-field with fwrite;
// all header fields are 1-byte-aligned, so there is no padding (sizeof(InputRecordingFileHeader) = 561).
// Offsets in hex.
struct P2M2Header {              // offset  size
    uint8_t  fileVersion;        // 0x000   1    must be 1; verifyRecordingFileHeader() rejects others
    char     emulatorVersion[50];// 0x001   50   "PCSX2-" + BuildVersion::GitRev (snprintf, NUL-terminated)
    char     author[255];        // 0x033   255  strncpy(.., 254)
    char     gameName[255];      // 0x132   255  VMManager::GetTitle(false) at creation time
};                               // = 561 bytes (0x231)
uint32_t totalFrames;            // 0x231   4    rewritten every recorded frame (setTotalFrames)
uint32_t undoCount;              // 0x235   4    "re-record" count (incrementUndoCount)
uint8_t  fromSavestate;          // 0x239   1    bool: 0 = power-on (VMManager::Reset()), 1 = starts from
                                 //              "<recording path>_SaveState.p2s" (e.g. foo.p2m2_SaveState.p2s)
// Frame data starts at 0x23A (= s_headerSize 569 + sizeof(bool) 1 = 570).
// Block for frame index f:  offset = 570 + f * 36
// Each block = 2 controller records x 18 bytes: [port 0 = pad 1A][port 1 = pad 2A]
// (s_controllerPortsSupported = 2; s_controllerInputBytes = 18; multitap slots are NOT stored)
struct P2M2PadRecord {           // 18 bytes, order exactly as written by writePadData()
    uint8_t buttonsHi;   // +0  ACTIVE-LOW (0 = pressed): b7 LEFT, b6 DOWN, b5 RIGHT, b4 UP,
                         //                               b3 START, b2 R3, b1 L3, b0 SELECT
    uint8_t buttonsLo;   // +1  ACTIVE-LOW: b7 SQUARE, b6 CROSS, b5 CIRCLE, b4 TRIANGLE,
                         //                 b3 R1, b2 L1, b1 R2, b0 L2
    uint8_t rightX;      // +2  0-255 (PadData neutral constant = 127)
    uint8_t rightY;      // +3
    uint8_t leftX;       // +4
    uint8_t leftY;       // +5
    uint8_t pRight;      // +6  pressure bytes 0-255
    uint8_t pLeft;       // +7
    uint8_t pUp;         // +8
    uint8_t pDown;       // +9
    uint8_t pTriangle;   // +10
    uint8_t pCircle;     // +11
    uint8_t pCross;      // +12
    uint8_t pSquare;     // +13
    uint8_t pL1;         // +14
    uint8_t pR1;         // +15
    uint8_t pL2;         // +16
    uint8_t pR2;         // +17
};
```

Supporting quotes:
- `static constexpr size_t s_controllerPortsSupported = 2;` and `s_controllerInputBytes = 18;` [InputRecordingFile.h L78-L80]
- `return s_headerSize + sizeof(bool) + frame * s_inputBytesPerFrame;` [InputRecordingFile.cpp L251-L254]
- `// TODO - multi-tap support with new file format, for now just controller 0 and 1` [pcsx2/Recording/InputRecording.cpp L167]

### 2.2 Which pads are recorded

- **Only pad index 0 (1A) and pad index 1 (2A) are recorded. Multitap slots B–D are not stored or replayed.** VERIFIED.
  - `handleControllerDataUpdate()` loops `for (int i = 0; i < 2; i++)` and uses `PadData frameData(i, 0)` (port i, slot 0) [InputRecording.cpp L165-L190].
  - `readPadData()` ignores its `slot` argument: `// TODO - slot unused` [InputRecordingFile.cpp L142].
- **Consequence for a 4-player multitap setup:** built-in .p2m2 cannot capture or replay players 1B/1C/1D or 2B/2C/2D in this version.

### 2.3 Playback and recording behaviour

- **Start point.** VERIFIED [InputRecording.cpp L37-L129].
  - Power-on recordings call `VMManager::Reset()`. The source has a TODO: "should this be an explicit [full] boot instead of a reset?"
  - Savestate recordings save or load `"{}_SaveState.p2s"` next to the recording.
  - If the title differs at playback, playback only logs a warning ("possibly constructed for a different game").
- **Frame clock.** VERIFIED. Per-frame work happens in `VMManager::Internal::PollInputOnCPUThread()`, called from `VSyncStart()` [VMManager.cpp L2968-L2989; Counters.cpp L489-L505].
  - Order of operations: process queues, then `incFrameCounter()`, then `handleExceededFrameCounter()`, then `handleControllerDataUpdate()` (write or override the pads for that frame).
  - Input is therefore applied at the emulated vsync, not on a host timer. This is gated by `EmuCore/EnableRecordingTools` (default **true** [Pcsx2Config.cpp L1966]) and is forced off in hardcore mode [VMManager.cpp L3218].
- **Frame-accuracy.** HYPOTHESIS. Design-wise, playback is frame-locked: one 36-byte block per emulated vsync, overriding pad state through `PadData::OverrideActualController()` [PadData.cpp L95-L118]. Whether a replay is actually *deterministic* also depends on the settings in §9. Confirm by recording and replaying twice, then comparing RAM hashes per frame.
- **Frame 0 block is likely never written.** HYPOTHESIS.
  - The counter is set to 0 at start, then incremented **before** the first write (`m_frame_counter++` and then `writePadData(m_frame_counter, …)`) [InputRecording.cpp L225-L264, L192-L199, L385-L390].
  - If so, block 0 stays zero-filled and file size = 570 + 36 × (totalFrames + 1). Confirm with a short real recording.
- **Read-failure quirk.** VERIFIED code; consequence is a HYPOTHESIS.
  - `readPadData` tests `fread(&data, 1, 18, f) != 1`, so it returns a `PadData` both on success (fread returns 18) and on a failed read (zero-filled data) [InputRecordingFile.cpp L144-L149].
  - Because the button bits are active-low, a zero-filled record would mean "all buttons pressed". Normal playback avoids reading past the end: at `totalFrames` it pauses and then switches to record mode [InputRecording.cpp L244-L249, L281-L288].
- **RTC is forced during recording.** VERIFIED. When an input recording is active and manual RTC is off, the emulated RTC is set to the fixed date 2020-03-04 00:00:00 ("Changing this will ruin compat with old input recordings (RNG seeding)") [pcsx2/CDVD/CDVD.cpp L985-L1006].
- **Command line.** VERIFIED: **no CLI option** starts recording or playback. The full option list in `ParseCommandLineOptions` has none [pcsx2-qt/QtHost.cpp L2179-L2383].
  - Recording and playback are started only from the Qt menu: `NewInputRecordingDlg` → `g_InputRecording.create(...)`, and a file dialog filtered to `*.p2m2` → `g_InputRecording.play(...)` [pcsx2-qt/MainWindow.cpp L2400-L2490].

---

## 3. Command-line options (pcsx2-qt)

VERIFIED. The full list from `PrintCommandLineHelp` [pcsx2-qt/QtHost.cpp L2132-L2171] matches the parser [L2179-L2383] and the docs (https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/advanced/cli.md):

`-help`, `-version`, `-batch`, `-nogui` (implies batch), `-portable`, `-datapath <path>`, `-elf <file>`, `-gameargs <string>`, `-gamecfg <file>`, `-disc <path>` (host DVD drive), `-logfile <path>`, `-bios`, `-fastboot`, `-slowboot`, `-state <index>`, `-statefile <filename>`, `-fullscreen`, `-nofullscreen`, `-bigpicture`, `-earlyconsolelog`, `-testconfig`, `-setupwizard`, `-debugger`, `-turbo`, `-unlimited`, `-raintegration` (only if built with RAIntegration), `--`. There is also an undocumented `-updatecleanup` [L2315-L2319].

- Usage: `pcsx2-qt [parameters] [--] [boot filename]`. Any other `-xxx` produces an "Unknown parameter" error dialog [L2342-L2346].
- `-batch` / `-nogui` without a boot target is an error ("Cannot use batch mode, because no boot filename was specified.") [L2374-L2381].
- **No `-settings <ini>` option exists.** VERIFIED (absent from the parser). The ways to point an instance at a different settings file are:
  1. **`-datapath <dir>`**: sets `EmuConfig.CustomDataPath` [L2222-L2226]. The data root becomes `<dir>/PCSX2`, and settings are read from `<DataRoot>/inis/PCSX2.ini` [pcsx2/Pcsx2Config.cpp L2269-L2270, L2292-L2293; QtHost.cpp L1363].
     - This only applies when portable mode is **off**: "-portable … Overrides '-datapath'" [QtHost.cpp L2141], and "Portable mode has the absolute priority" [Pcsx2Config.cpp L2226-L2227].
  2. **Portable copies.** If `portable.ini` or `portable.txt` exists next to the exe (or `-portable` is passed), portable mode is on [Pcsx2Config.cpp L2203-L2214].
     - The data root is then `AppRoot/<contents of portable.txt, trimmed>`, i.e. the exe folder itself if the file is empty [L2216-L2222, L2287-L2288].
     - So each copied folder has its own `inis/PCSX2.ini`, memcards, savestates, and so on. Docs: https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/configuration/general.md (section "Portable Mode").
  3. **`-gamecfg <file.ini>`** replaces the *per-game* settings layer path [VMManager.cpp L1482-L1496, L820-L824]. HYPOTHESIS: this could carry a per-instance `[EmuCore] PINESlot`, because PINE is reloaded on game change after the game layer is applied [VMManager.cpp L1160-L1174]. Confirm by test.
- **Several instances at once.** No single-instance guard was found. VERIFIED (absence): a grep of pcsx2/, pcsx2-qt/ and common/ at the tag for `QLockFile|SingleInstance|single.instance|CreateMutex` returned nothing. HYPOTHESIS: several instances can run at once if each uses a separate data root (separate portable folders, or separate `-datapath`) and a distinct `PINESlot`. Confirm by launching 4 instances.

---

## 4. Savestates (.p2s)

- **Format is a zip archive.** VERIFIED (libzip calls `zip_open_from_source(... ZIP_CREATE | ZIP_TRUNCATE ...)` [pcsx2/SaveState.cpp L1036-L1046]).
  - Entries:
    - `PCSX2 Savestate Version.id`: `u32 save_version` + `char[32]` version string, stored uncompressed [L339, L963-L999, L342].
    - `Screenshot.png`: stored, 640 px wide [L340, L778-L838].
    - `PCSX2 Internal Structures.dat`: BIOS and internal CPU/HW structures [L341, L715-L735].
    - Then, in order [L696-L711]: `eeMemory.bin` (`Ps2MemSize::ExposedRam`, 32 MiB unless extra memory is enabled [L523-L525; pcsx2/MemoryTypes.h L9]), `iopMemory.bin` (2 MiB), `eeHwRegs.bin`, `iopHwRegs.bin`, `Scratchpad.bin` (16 KiB), `vu0Memory.bin` (4 KiB), `vu1Memory.bin` (16 KiB), `vu0MicroMem.bin` (4 KiB), `vu1MicroMem.bin` (16 KiB), `SPU2.bin`, `USB.bin`, `PAD.bin`, `GS.bin`, `Achievements.bin`. VU sizes are from [pcsx2/VUmicro.h L10-L13].
  - The CDVD state, including the RTC, is frozen inside the internal structures: `Freeze(cdvd)` [CDVD.cpp L1037-L1042]. The input-recording frame counter (`g_FrameCount`) is too [InputRecording.cpp L8-L17].
- **Version gate.** VERIFIED. `g_SaveVersion = (0x9A59 << 16) | 0x0000` [pcsx2/SaveState.h L29]. A state is rejected if `savever > g_SaveVersion` or the major (upper 16 bits) differs [SaveState.cpp L1084-L1121]. All peers should use identical builds.
- **Compression settings.** VERIFIED.
  - Keys: `[EmuCore] SavestateCompressionType` (0 = Uncompressed, 1 = Deflate, 2 = Zstandard; default Zstandard) and `SavestateCompressionRatio` (0 = Low, 1 = Medium, 2 = High, 3 = VeryHigh; default Medium) [Pcsx2Config.cpp L1696-L1702; pcsx2/Config.h L384-L397, L1339-L1346].
  - Mapped levels: zstd 1/3/10/22, deflate 1/5/7/9 [SaveState.cpp L927-L960].
- **Typical size.** HYPOTHESIS: about 40 MiB uncompressed. EE RAM alone is 32 MiB; a 64 MiB staging buffer is reserved [SaveState.cpp L716]. A zstd-Medium file is likely a few MiB to ~15 MiB. Confirm by measuring real states of The Warriors.
- **Synchronous or not.** VERIFIED (source).
  - **Save:** the snapshot is taken synchronously on the CPU thread (`SaveState_DownloadState` into memory). Compression and the write to disk happen on a background thread when `zip_on_thread` is true, which PINE and slot saves use [VMManager.cpp L1955-L2001; PINE.cpp L648]. `WaitForSaveStateFlush()` joins those threads [VMManager.cpp L2048-L2061].
  - **Load:** fully synchronous on the CPU thread. `PreLoadPrep()` waits for MTVU (`vu1Thread.WaitVU()`) and the GS thread (`MTGS::WaitGS`), resets block tracking and clears recompiler caches before unzipping [SaveState.cpp L51-L65, L1206-L1235].
  - Both are refused while the memory card is busy (`MemcardBusy::IsBusy()`) [VMManager.cpp L2085-L2152, L2167-L2194].
  - A failed `LoadState` (non-slot path) triggers `Reset()` [L2101-L2105].
- **Slot file naming.** VERIFIED. `<Savestates>/<SERIAL> (<CRC8>).<NN>.p2s` (and `.resume.p2s` for slot -1) [VMManager.cpp L1888-L1904]. The UI uses 10 slots (`NUM_SAVE_STATE_SLOTS = 10` [pcsx2/VMManager.h L73]). The PINE slot is a `u8`, and any value just produces that filename.

---

## 5. Multitap

- **Keys.** VERIFIED. `[Pad] MultitapPort1` (physical port 1) and `[Pad] MultitapPort2`. The internal names are `MultitapPort0_Enabled` / `MultitapPort1_Enabled` [Pcsx2Config.cpp L1866-L1868; Config.h L1266-L1279]. Both default to false [pcsx2/SIO/Pad/Pad.cpp L174-L175].
- **8 pads.** VERIFIED. `PadOptions::NUM_PORTS = 8` [Config.h L1255] and `Pad::NUM_CONTROLLER_PORTS = Pcsx2Config::PadOptions::NUM_PORTS` [pcsx2/SIO/Pad/PadTypes.h L99]. Each pad has a config section `Pad{n+1}`, i.e. `[Pad1]..[Pad8]` [Pad.cpp L503-L506], with `Type = DualShock2 | None | …` [Pcsx2Config.cpp L1845-L1863]. Defaults: Pad1 = DualShock2, all others = None [Pad.cpp L154-L157].
- **Mapping.** VERIFIED from `sioConvertPadToPortAndSlot` / `sioConvertPortAndSlotToPad` [pcsx2/SIO/Sio.cpp L36-L54]:

| Pad index | ini section | port, slot | UI label |
|---|---|---|---|
| 0 | [Pad1] | 0, 0 | 1A |
| 1 | [Pad2] | 1, 0 | 2A |
| 2 | [Pad3] | 0, 1 | 1B |
| 3 | [Pad4] | 0, 2 | 1C |
| 4 | [Pad5] | 0, 3 | 1D |
| 5 | [Pad6] | 1, 1 | 2B |
| 6 | [Pad7] | 1, 2 | 2C |
| 7 | [Pad8] | 1, 3 | 2D |

- Slots B–D are forced to "Not Connected" when their port's multitap is off [Pad.cpp L108-L113].
- Docs: "enabling multitap in port 1 will add controllers 1-A through 1-D … Some games will ignore multitapped controllers if you do not multitap a specific port" (https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/configuration/controllers.md, section "Multitap").
- The same docs also say "PCSX2 currently does not support multitapped memory cards", although the source has `Multitap%u_Slot%u_*` memcard keys [Pcsx2Config.cpp L2090-L2092]. This conflict doesn't matter for this project.
- **Which port The Warriors expects its multitap on is unknown** (see Gaps).

---

## 6. Pnach patches and debugger

### 6.1 Pnach

- **Line format.** VERIFIED. `patch=<place>,<cpu>,<address>,<type>,<data>`, with exactly 5 comma-separated fields; address and data are hex with no prefix [pcsx2/Patch.cpp L885-L975].
  - **place**: 0 = once at boot (entry point), 1 = every vsync, 2 = both, 3 = at boot and when enabled in the GUI [pcsx2/Patch.h L32-L56].
  - **cpu**: `EE` | `IOP`.
  - **type**: `byte short word double extended beshort beword bedouble bytes` [Patch.h L64-L80]. `bytes` takes a hex string of arbitrary length [Patch.cpp L936-L948].
- **Other pnach keys.** VERIFIED. `gametitle=`, `[Group\Sub]` headers, `description=`, `author=`, `comment=`, `gsaspectratio=`, `gsinterlacemode=`, `dpatch=` [Patch.cpp L144-L148, L420-L545].
  - `dpatch` matches instruction patterns and patches when the block is recompiled (`Patch::ApplyDynamicPatches(pc)` from `pcsx2/x86/ix86-32/iR5900.cpp L1686`).
- **Extended (RAW) codes** are partially supported. Handlers exist for type nibbles 0,1,2,3(inc/dec),4,5,6,7,C/D/E (conditionals) [Patch.cpp L1209-L1460]. The docs give the full table (https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/advanced/writing-patches.md, "RAW Codes").
- **Where files load from.** VERIFIED.
  - Patches load from the `patches` folder and from `patches.zip` in resources. Cheats load from the `cheats` folder. GameDB patches come from `GameIndex.yaml` [Patch.h L6-L16; Patch.cpp L117, L336-L347].
  - Filename: `<SERIAL>_<CRC8>.pnach` (also `<CRC8>.pnach`) [Patch.cpp L320-L331].
  - Enable lists are kept in the `[Patches]` / `[Cheats]` sections with `Enable` / `Disable` keys [Patch.cpp L119-L122].
  - Cheats require `EnableCheats`, and patches require `EnablePatches` (default true [Pcsx2Config.cpp L1964]).
- **When patches are applied.** VERIFIED.
  - Boot patches (place 0, 2, 3) are applied in `EntryPointCompilingOnCPUThread()`. Immediately after, the emulator runs `mmap_ResetBlockTracking(); ClearCPUExecutionCaches();` ("Toss all the recs, we're going to be executing new code.") [VMManager.cpp L2913-L2943].
  - Vsync patches (place 1, 2) are applied each vsync in `VSyncOnCPUThread()` [L2945-L2949], on the CPU thread.
  - Writes go through the normal emulated write path: `IdempotentWrite32` → `EEMemoryInterface::Write32` → `memWrite32` [common/MemoryInterface.cpp L124-L132; pcsx2/Memory.cpp L1242-L1246].
- **Code caves.** HYPOTHESIS (strongly supported). Nothing restricts patch content to data: any word can be written to any EE address, including new MIPS code in unused RAM plus a jump hook.
  - Place-0 patches are the safest route for code, because the recompiler caches are flushed right after they apply (above).
  - The upstream docs show code patches via `dpatch` and patching "strictly code".
  - Confirm with a trivial cave on SLUS-21215.

### 6.2 Debugger (Qt)

VERIFIED.
- **Dock views:** Breakpoints, Disassembly, Functions, Globals, Locals, Memory Search, Memory, Modules, Parameters, Registers, Saved Addresses, Stack, Threads [pcsx2-qt/Debugger/Docking/DockTables.cpp L40-L56].
- **Breakpoints:** execute breakpoints with optional condition expressions. Memory checks have conditions `MEMCHECK_READ`, `MEMCHECK_WRITE`, `MEMCHECK_WRITE_ONCHANGE` and results `MEMCHECK_BREAK` / `MEMCHECK_BOTH` [pcsx2/DebugTools/Breakpoints.h L60-L76]. Targets are EE and IOP [pcsx2/DebugTools/DebugInterface.h L32-L37].
- **Memory search:** types Byte/Int16/Int32/Int64/Float/Double/String/Array. Comparisons: Equals, NotEquals, >, >=, <, <=, Increased(By), Decreased(By), Changed(By), NotChanged, UnknownValue [pcsx2-qt/Debugger/Memory/MemorySearchView.h L24-L75].
- **Other:** symbol import, function scanning and hashing, and expressions are documented at https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/advanced/debugger.md. A MIPS assembler exists in source (`pcsx2/DebugTools/MipsAssembler.cpp`).
- **Enabling it:** `-debugger` opens the debugger and breaks on the entry point [QtHost.cpp L2310-L2314]. The docs say to enable `Tools -> Show Advanced Settings` first.

---

## 7. Netplay / input sync

- **None built in.** VERIFIED (absence).
  - A case-insensitive grep of all `.cpp/.h/.hpp/.inl/.ui` files under `pcsx2/`, `pcsx2-qt/` and `common/` at the tag for `netplay|ggpo|lockstep|rollback|InputSync` matched only the FAQ link "The latest Netplay fork of PCSX2" (forums "PCSX2 Online Plus") [pcsx2/Docs/PCSX2_FAQ.md L198-L199].
  - The `pcsx2/DEV9/` network-adapter emulation exists for PS2 titles with online modes. It is not an input-sync feature.
  - PINE has no pad-input opcode (§1.3).
- HYPOTHESIS: per-frame input sync would need one of these:
  - a modified build that injects pad state at `PollInputOnCPUThread()` (the same hook input recording uses);
  - writing the game's own pad buffers through PINE (racy, see §1.4) or through a code cave.

---

## 8. Building from source on Windows, and license

### 8.1 Toolchain (VERIFIED for what the files say; local build not attempted)

- **Official docs** (https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/advanced/building.md, "Building on Windows"):
  - Visual Studio Community 2022 **17.10 or later**, "Desktop development with C++" (MSVC v143, C++ ATL v143, Windows 10/11 SDK), plus Git.
  - Download the binaries from https://github.com/PCSX2/pcsx2-windows-dependencies/releases/ and extract them so a `deps` folder sits next to `PCSX2_qt.slnx`.
  - Open `PCSX2_qt.slnx` and set `pcsx2-qt` as the startup project.
  - Optionally put `patches.zip` (from PCSX2/pcsx2_patches releases) in `bin/resources`.
- **CI at the tag:**
  - Runner `windows-2025-vs2026` [.github/workflows/windows_build_qt.yml L15].
  - MSBuild configurations "Release", "Release AVX2", "Release Clang", "Release Clang AVX2" [.github/workflows/windows_build_matrix.yml]. Clang configurations use the `ClangCL` toolset; others use `$(DefaultPlatformToolset)` [pcsx2-qt/pcsx2-qt.vcxproj L12-L13].
- **The official v2.9.115 Windows release is built with CMake + Ninja + clang-cl:**
  - `cmakeFlags: -DCMAKE_C_COMPILER=clang-cl -DCMAKE_CXX_COMPILER=clang-cl` [.github/workflows/release_cut_new.yml L143-L157].
  - The configure line is `cmake . -B build ... -DQT_BUILD=ON -DCMAKE_BUILD_TYPE=Release -DCMAKE_INTERPROCEDURAL_OPTIMIZATION=ON -DDISABLE_ADVANCE_SIMD=ON -G Ninja`, run inside `vcvars64.bat` [windows_build_qt.yml L110-L148].
  - Requirements: CMake ≥ 3.16 [CMakeLists.txt L3] and C++20 [cmake/BuildParameters.cmake L147].
- **Dependency versions** built by `.github/workflows/scripts/windows/build-dependencies.bat` at the tag [L58-L89]: Qt 6.12.0 (+ QtApng 1.3.0), SDL3-3.4.18, FFmpeg 9.0.1, FreeType 2.14.3, HarfBuzz 14.2.0, libjpeg-turbo 3.2.0, libpng 1658, LZ4 1.10.0, WebP 1.6.0, zlib 1.3.2, zstd 1.5.7, KDDockWidgets 2.4.1, plutovg 1.3.3, plutosvg 0.0.8, shaderc 2026.2.
- **Prebuilt deps:** the rolling release `latest-windows-dependencies` was published 2026-10-07T21:33:59Z (https://api.github.com/repos/PCSX2/pcsx2-windows-dependencies/releases).
- **Approximate steps.** HYPOTHESIS, derived from the docs and CI:
  1. `git clone --recursive` and check out `v2.9.115`.
  2. Get `deps` (prebuilt 7z, or run `build-dependencies.bat`).
  3. Either open `PCSX2_qt.slnx` in VS and build "Release Clang AVX2" x64, or run the CMake + clang-cl command above in a VS x64 developer prompt.
  4. The output goes to `bin/`.

### 8.2 License

- VERIFIED. The repo root carries `COPYING.GPLv3` ("GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007"). Per-file SPDX headers in `pcsx2/`, `pcsx2-qt/`, `common/`:
  - 974 files are `GPL-3.0+`, 13 are `GPL-2.0+`, 12 are `GPL-3.0` (all arm64 or GS arm64 files), 3 are MIT, 1 is BSD-3-Clause.
  - 2 files are `GPL-3.0-only`: `pcsx2/USB/usb-pad/lg/lg_ff.cpp/.h`, and these **are compiled into the Windows build** [pcsx2/pcsx2.vcxproj L489, L948; pcsx2/CMakeLists.txt L398, L437].
  - Third-party notices ship in `bin/docs/ThirdPartyLicenses.html`.
- **Obligations if a modified build is distributed.** HYPOTHESIS: my reading of GPLv3, not legal advice.
  - License the whole modified program under GPLv3. In practice that means version 3, because GPL-3.0-only files are linked in.
  - Provide the complete corresponding source, including build scripts, with the binary or by a written offer.
  - Keep the copyright and license notices, and mark modified files with prominent notices and dates (§5a).
  - Add no further restrictions. Honour the third-party licenses: Qt is LGPLv3, so its notices and relinkability apply.
  - The game ISO and BIOS must never be distributed (BRIEF.md).

---

## 9. Determinism-relevant settings and known nondeterminism

All keys VERIFIED from [Pcsx2Config.cpp L398-L413, L1586-L1608, L1751-L1763, L1993-L2042] and Qt bindings [pcsx2-qt/Settings/EmulationSettingsWidget.cpp L42-L61; AdvancedSettingsWidget.cpp L30].

| Setting (section/key) | Default | Notes |
|---|---|---|
| `EmuCore/ManuallySetRealTimeClock` + `RtcYear` (years since 2000), `RtcMonth`, `RtcDay`, `RtcHour`, `RtcMinute`, `RtcSecond` | false; 0/1/1/0/0/0 | **VERIFIED.** Without manual RTC (and no input recording), the RTC is seeded from **host time** `std::time(nullptr)` at CDVD reset [CDVD.cpp L1007-L1018]. After that it advances by emulated vsync count (`cdvdVsync`) [CDVD.cpp L1636-L1660]. It is saved in savestates (`Freeze(cdvd)`). → Set manual RTC identically on all peers, or start all peers from one savestate. |
| `EmuCore/Speedhacks/EECycleRate` (-3..3), `EECycleSkip` (0..3) | 0, 0 | Change emulated timing [Config.h L1135-L1137]; must match on all peers. |
| `EmuCore/Speedhacks/vuThread` (MTVU) | **Hardware-dependent: set to true if the CPU has ≥3 cores** [VMManager.cpp L3644-L3653]. Binding default false [EmulationSettingsWidget.cpp L44] | HYPOTHESIS: **nondeterministic.** Under MTVU the EE reads `Get_vuCycles()`, an average of atomics written by the VU thread ("Used for vu cycle stealing hack") [pcsx2/MTVU.cpp L340-L349, L454]. The value depends on host thread progress. → Force `vuThread=false` for lockstep; confirm by A/B RAM-hash runs. |
| `EmuCore/Speedhacks/vu1Instant` | true [Pcsx2Config.cpp L386] | "Enable Instant VU1 (Without MTVU only)" [Config.h L1146]. Changes timing; must match. |
| `EmuCore/Speedhacks/fastCDVD` | false | Halves sector-ready and read interrupt delays (`eCycle *= 0.5f`) [CDVD.cpp L71-L91]. That is cycle-based, not host-based; must match. |
| `EmuCore/CdvdPrecache` | false | Loads the image into RAM before VM start [VMManager.cpp L1657-L1658]. HYPOTHESIS: affects host I/O only, not emulated timing. |
| `EmuCore/EnableFastBoot` | true | Skips the BIOS logo; must match (different boot path). |
| `EmuCore/Speedhacks/WaitLoop`, `IntcStat`, `vuFlagHack` | true, true, true | Speedhacks; must match. |
| `EmuCore/Gamefixes/*` | GameDB-driven | The SLUS-21215 GameDB entry sets **only** `gsHWFixes` (halfPixelOffset 4, autoFlush 2, nativeScaling 2), with no gamefixes [bin/resources/GameIndex.yaml L70975-L70983]. |
| `EmuCore/GS/HWDownloadMode` | 0 = Accurate | The UI itself labels option 3 **"Unsynchronized (Non-Deterministic)"** [pcsx2-qt/Settings/GraphicsAdvancedSettingsTab.ui L40-L66; Config.h L399-L406]. Keep Accurate. HYPOTHESIS: if The Warriors reads back GS memory, different GPUs, renderers or upscales could still diverge. Consider the identical renderer and resolution on all peers, or the software renderer. |
| `Framerate/NominalScalar`, `TurboScalar`, `SlomoScalar`; `-turbo`/`-unlimited` | 1.0 … | HYPOTHESIS: these affect host pacing only (`Throttle`), not emulated state. |
| `EmuCore/EnableRecordingTools` | true | Required for the built-in input recording hook. |

Other observations:
- Pad input is sampled once per emulated vsync. `InputManager::PollSources()` runs inside `PollInputOnCPUThread()` from `VSyncStart` [VMManager.cpp L2968-L2972; Counters.cpp L504-L505]. VERIFIED (source).
- Pad state is part of savestates (`PAD.bin`). VERIFIED.
- The only explicit "non-deterministic" wording I found in the source is the GS download mode label (grep for `determinis|nondetermin|non-determin`). The pcsx2.net docs contain no determinism guidance. VERIFIED (absence by grep of the downloaded docs pages).
- Memory-card contents are emulated state that a game may read at boot. HYPOTHESIS: peers need byte-identical memcards, or saves that are never read during a session.

---

## 10. Open gaps

1. **Runtime behaviour is untested.** Every behaviour here was read from source. In particular, none of these have been tested: PINE read timing mid-frame, batch limits, the "no reply on invalid length" hang, PINE save/load landing at the next vsync, and multiple simultaneous instances.
2. **Frame-0 block of .p2m2** (HYPOTHESIS §2.3): verify with a real recording (file size and block 0 contents).
3. **The Warriors and multitap:** whether SLUS-21215 supports more than 2 local players at all, and on which multitap port and slots. This is not in GameDB, and the docs say it is game-specific. BLOCKED on testing with the game; no game files were touched in this step.
4. **MTVU determinism:** HYPOTHESIS that `vuThread=true` is nondeterministic. Needs A/B replay hashing.
5. **GS readback divergence across GPUs:** unknown whether The Warriors performs GS→EE readbacks.
6. **PINE writes into recompiled code pages** (fault-handler path on a non-EE thread): risk unquantified; test or avoid.
7. **`-gamecfg` carrying a per-instance `PINESlot`:** untested HYPOTHESIS.
8. **Build at this tag:** whether VS 2022 17.10+ (per the docs) still builds this tag, since CI uses a `windows-2025-vs2026` image. Also whether the rolling `latest-windows-dependencies` (2026-10-07) exactly matches `build-dependencies.bat` at the tag. Not verified; a local build was out of scope (no installs).
9. **Docs vs. source:** the pcsx2.net docs are unversioned (main branch). Where they differ from source (e.g. the multitap memcard statement), source at the tag wins.
10. **PINE `MsgVersion` string:** the exact `BuildVersion::GitRev` value for the official binary (likely "v2.9.115") was not observed. HYPOTHESIS.
11. **Typical savestate size** for The Warriors: not measured.
12. **Legal reading** of the GPLv3 obligations is mine, not legal advice.
