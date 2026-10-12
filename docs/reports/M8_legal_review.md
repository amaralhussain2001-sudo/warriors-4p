# M8 legal review of the package contents (2026-10-12)

Package reviewed: `dist/warriors-4p-coop.zip`, package id **e64016ce3a7b** (zip SHA-256
a5d4b2eb4aa5c0842c42296fef162d863b3d2fe8fa522d76675cc70dd4591c9d, 300 files, 57 MB), built by `tools/make_package4.py`
from fork commit b81b4cc (PCSX2 v2.9.115 + warriors-4p patches 0001-0020) and `mod/w4p_m1.pnach` (11733 addresses).
**This is an engineering review of what the package contains and which licence terms apply, not legal advice.** Where
something is a judgement call, it is listed as a decision for you with options and a recommendation. Nothing has been
published or uploaded; giving the package to friends is your decision (BRIEF section 11).

## Plain-English summary
- **No game, no BIOS, no extracted game files** are in the package (checked: the builder refuses ISO/BIN/ELF/IRX/
  memory-card/savestate/BIOS file types and `SLUS_`/`SCUS_` names; a second scan of the finished zip found none of
  them). Every player needs his own copy of the game and a BIOS dumped from his own PS2, and the README says so.
- **The emulator is PCSX2 (GPL-3.0), changed by us.** The GPL lets us give it to others, but whoever receives the program
  must also be able to get the **complete source code** of exactly that build. Today the package contains our 20 change
  files ("patches") plus the address of the unchanged PCSX2 version they apply to. That is a common practice, but the
  stronger and simpler way is to hand out the complete source as well: it is a 24.5 MB zip. **Recommendation: give
  friends a second zip with the full source together with the package (decision L1).**
- **Our game patch** (`game\w4p.pnach`) is our own code. To work at all it must name places in the game's program (memory
  addresses) and parts of the game's own scripts (function names, a few camera positions copied as numbers). Its comments
  also show, for 850 lines, the original 4-byte instruction we replace ("was 3C17005E"). These are tiny fragments needed
  for compatibility and documentation; they are not game assets. If you want the smallest possible footprint, the
  package can ship a copy without comments (decision L2; behaviour is identical).
- **Other parts:** libjuice (MPL-2.0, unmodified, licence and source address included), Microsoft's Visual C++ runtime
  DLLs (redistribution allowed by Microsoft's terms), our helper w4p-net (GPL-3.0-or-later, source included), Cloudflare's
  public STUN service for address lookup (described in the README, no account).
- **Names:** the package and README use "The Warriors" only to say which game it modifies; no logos, box art or game
  images are included (the 3P/4P radar labels are drawn at runtime from the player's own game data).
- **Recommendation for sharing:** private sharing with friends who own the game, the package zip plus the source zip, no
  public upload (a public release would be a separate decision with its own review).

## 1. What is in the package (from MANIFEST.txt, 299 hashed files)
| Part | Folder | Licence / basis | Notes |
|---|---|---|---|
| Launcher (Start-Coop.bat/.ps1), README, QUICK-START, VERSION | root | ours | test-only options exist but are not reachable from the menus |
| Game patch | `game\w4p.pnach` | ours | 11770 patch lines; our MIPS code, Lua rows, data; 850 comments quote the replaced original instruction word; Lua sources name game script functions and copy some numeric constants (camera positions, lane coordinates) |
| PCSX2 settings profile | `game\profile_PCSX2.ini` | ours | MTVU off, sandbox paths |
| Emulator | `emulator\` | GPL-3.0 (PCSX2), plus PCSX2's bundled third-party libraries (`emulator\docs\ThirdPartyLicenses.html`) | binaries as built from b81b4cc; Qt and other libraries as in an official PCSX2 build |
| Our emulator changes | `source\0001..0020-*.patch`, `source\SOURCE.txt` | GPL-3.0 | upstream tag v2.9.115 commit cf3c3720 named; build steps named |
| Connection helper | `net\w4p-net.exe`, `source\w4p-net\` | GPL-3.0-or-later (ours) + libjuice MPL-2.0 (unmodified) | libjuice licence in `licenses\libjuice-LICENSE.txt`, source archive URL and SHA-256 in SOURCE.txt |
| VC++ runtime | `emulator\`, `net\` (msvcp140, vcruntime140, vcruntime140_1) | Microsoft redistribution terms (Visual Studio redistributable files) | app-local copies |
| Licence texts | `COPYING.GPLv3`, `THIRD-PARTY-NOTICES.txt`, `licenses\` | - | present |
| Excluded | - | - | ISO/BIN/CHD/CSO, BIOS ROM/NVM/MEC, memory cards (.ps2/.mcd), savestates (.p2s), ELF/IRX, `SLUS_`/`SCUS_` files: none (builder check + zip scan 2026-10-12 21:45) |

## 2. Findings and decisions
| # | Topic | Finding | Risk | Options (recommendation first) |
|---|---|---|---|---|
| L1 | GPL-3.0 source for the modified PCSX2 | The package gives our patches + the upstream tag; GPL-3.0 section 6 asks that recipients of the binaries can get the complete Corresponding Source; relying on a third party (GitHub) to keep v2.9.115 available is allowed only if we make sure it stays available | low-medium (obligation, not a game-rights issue) | **A** give a second zip with the full fork source (git archive of b81b4cc, 24.5 MB, plus w4p-net source and build scripts) to everyone who gets the package; B put the source zip inside the package (zip about 80 MB); C keep patches + link only |
| L2 | Fragments of the game in our patch | Needed for interoperability: addresses, script names, a few constants; 850 comment fragments of original instruction words (4 bytes each) | low | **A** ship a comment-free `w4p.pnach` in the package (same behaviour; the full commented sources stay in the project); B ship as is (more transparent for anyone reading the patch) |
| L3 | Game and BIOS | none included; README requires own copies | - | no action |
| L4 | Names and marks | "The Warriors" used descriptively; no logos or art | low | keep it descriptive; do not call the package official |
| L5 | MPL-2.0 libjuice | unmodified, licence + source location provided | - | compliant as is (with L1 A the libjuice archive can be added too) |
| L6 | VC++ runtime | redistributable files | - | compliant |
| L7 | STUN / privacy | public STUN at Cloudflare for the address lookup; logs mask addresses except the LAN lobby log | low | README already explains; no action |
| L8 | Where the package goes | private sharing only so far | depends on audience | **A** friends who own the game, by direct transfer; B public download page (needs its own review and your explicit decision) |

## 3. Not checked / limits
- No lawyer reviewed this; country-specific rules (copyright exceptions for interoperability, consumer law) are not
  analysed. The game publisher's licence terms for the game itself were not available in the project.
- PCSX2's own bundled third-party components are taken as PCSX2 ships them (their notice file is included).
