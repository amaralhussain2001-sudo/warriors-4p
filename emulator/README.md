# warriors-4p PCSX2 build (fork of PCSX2 v2.9.115)

License: GPL-3.0 (PCSX2 is GPL-3.0+ with some GPL-3.0-only files compiled in on Windows; see
`docs/research/pcsx2_capabilities.md` §8.2). Anyone who receives a binary built from this must also be able to get
the complete source: upstream tag v2.9.115 + `patches/*.patch` + these build scripts.

Not affiliated with the PCSX2 project. Following PCSX2's `AGENTS.md`, none of this is to be submitted or posted to
PCSX2's GitHub by an AI agent; any upstream contribution would have to come from a human contributor who
understands the code and declares AI use.

## Reproduce the build (Windows)
1. `git clone --depth 1 --branch v2.9.115 --recurse-submodules --shallow-submodules https://github.com/PCSX2/pcsx2.git emulator/pcsx2`
   (upstream commit `cf3c3720`).
2. Download `pcsx2-windows-dependencies.7z` from the `latest-windows-dependencies` release of
   `PCSX2/pcsx2-windows-dependencies` (the copy used on 2026-10-10 has SHA-256
   `a3133c7841e8fbdab6f4d1d5ad8efec31fb1ecda95ffed39f4d1f36bb7eb0007`, Qt 6.12.0) and extract it into
   `emulator/pcsx2` so that `emulator/pcsx2/deps/` exists.
3. `cd emulator/pcsx2 && git am ../patches/*.patch`
4. `powershell -File emulator/build.ps1 -Config Release` (Visual Studio Build Tools with MSVC, Windows SDK).
   Output: `emulator/pcsx2/bin/pcsx2-qtx64.exe`.

## What the patch changes
- `pcsx2/W4P/*` (new): lockstep session, UDP transport with impairment, presentation crop.
- `pcsx2/R5900OpcodeImpl.cpp`: SYSCALL with v1 = 0x57345030 calls the W4P hook (used only by the warriors-4p game patch).
- `pcsx2/VMManager.cpp`: session start/stop and a per-vsync call.
- `pcsx2/GS/Renderers/Common/GSRenderer.cpp`: optional crop of the displayed frame (presentation only).
- Project files.

The W4P module does nothing unless the `W4P_CONFIG` environment variable names an INI file with `Enabled = true`
and the running disc is The Warriors (USA) v1.03 (CRC B99A75DE).
