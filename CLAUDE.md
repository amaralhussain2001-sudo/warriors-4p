# CLAUDE.md: Warriors 4P project

Read this file and `docs/STATE.md` before doing anything else in a session.
The authoritative specification is `docs/BRIEF.md` (verbatim copy of the user's brief).
Re-read the relevant brief sections before each milestone.

## Operating rules (condensed from BRIEF §0)
1. Two stages with a hard gate. Stage 1 = investigate, experiment, plan, then STOP.
   Stage 2 (implementation) starts only after an explicit message like "Approved, proceed with Stage 2".
   Questions, comments, partial feedback or silence are NOT approval.
2. Evidence, not assumption. Every technical claim gets one label: VERIFIED, HYPOTHESIS, BLOCKED, FAILED TEST.
   Never invent structures, function names, addresses, mission names/classifications, measurements, results.
3. Protect the originals (below).
4. No success without proof. Compiling, a patch applying, four characters spawning, or a lobby connecting is not success.
5. Ask first before anything outward-facing, costly, legal or irreversible (see "Stop and ask").
6. Don't shrink the problem. Hard parts stay in scope until solved, proven blocked, or the user agrees.

## Protected originals (BRIEF §2.2): never modify, move, rename or delete
- `..\Warriors The (USA) (EnFrDeEsIt)\` and its ISO (open read-only; extract only into `local/`).
- `..\pcsx2-v2.9.115-windows-x64-Qt\` including settings, memcards, caches and `bios\`.
  Do NOT launch the original PCSX2: it rewrites its settings/memcards. Run sandbox copies under `local/pcsx2/`.
- `..\ghidra_12.1.4_PUBLIC\`: keep Ghidra projects inside `local/ghidra/`.
- Before any write, confirm the target is inside `warriors-4p\` or a temp directory.
- Re-verify ISO and BIOS hashes (`python -I tools/hash_inputs.py`) in every milestone report; compare with `docs/HASHES.md`.

## Evidence standard (BRIEF §3)
- VERIFIED needs a pointer: file+offset, Ghidra address+function, runtime address+method, test ID+log path, or URL+access date.
  State the build/version it applies to. Addresses: say static or dynamic.
- Names we give functions/structures are OUR labels (the ELF is stripped). Say so.
- Label test environment: SINGLE-PC / LAN / INTERNET; humans or bots; impairment simulated or not.
- Negative results are reported as prominently as positive ones. Supersede findings, never delete them.

## Stop and ask the user before (BRIEF §11)
Starting Stage 2; changing approved architecture or a milestone premise; making a mission fallback final;
installing system-wide software/drivers/services or changing firewall/router/network settings;
creating accounts, accepting terms, spending money, paid services; publishing/uploading/sharing anything;
any action that could touch the originals; tests needing other computers or people;
going ahead despite legal/licensing uncertainty. Also stop as soon as a core requirement is shown impossible.
Always include a recommendation and trade-offs. The user prefers plain English, examples, lettered options.

## Never (BRIEF §12)
Invent facts; call anything "lag-free" or say it "works" without tests; commit/distribute the game, ISO, BIOS or
extracted assets; hide or soften failed tests; quietly reduce scope (no unapproved fallbacks, no shared/streamed
views except the all-players-close rule in §4.5); use Steam; treat a library/lobby/netplay build/streaming tool
as the whole solution.

## Where things are
- `docs/STATE.md`: current stage/milestone, done, in progress, next steps, questions for the user.
- `docs/FINDINGS.md`: findings register (ID, claim, label, evidence, build, date, superseded-by).
- `docs/DECISIONS.md`: decision log. `docs/RISKS.md`: risk register. `docs/MISSIONS.md`: mission inventory.
- `docs/HASHES.md`: SHA-256 of original inputs and generated artifacts.
- `docs/plan/STAGE1_PLAN.md`: the Stage 1 plan. `docs/research/`: research notes. `docs/reports/`: reports.
- `tools/`: scripts (hashing, WAD/Lua extraction, Ghidra, sandbox launch). `tests/experiments/`: Stage 1 experiments.
- `local/` (gitignored): extracted disc files, Ghidra project, sandbox PCSX2, savestates, dumps.

## Git hygiene
Never commit anything under `local/`, `build/`, `dist/`, or any ISO/BIOS/ELF/IRX/savestate/memcard/Ghidra DB.
Run `git status` before each commit. Commit often; tag milestone ends.
