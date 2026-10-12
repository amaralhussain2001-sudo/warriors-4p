"""Build dist/warriors-4p-coop-source.zip: the complete Corresponding Source of the binaries in the co-op package
(legal review docs/reports/M8_legal_review.md, decision L1 option A). Contents:
  pcsx2-fork/           git archive of the fork commit the package's emulator was built from (emulator/pcsx2)
  w4p-net/              the connection helper's source with libjuice (net/w4p-net, as tracked in git; no build output)
  build/                emulator/build.ps1, net/w4p-net/build.ps1, the fork patches, mod/make_pnach.py and mod/m2 (the
                        game patch's sources)
  SOURCE-README.txt     what is where and how to build
Never any game, ISO, BIOS or extracted file (same FORBIDDEN rule as the package). Local only: giving it to anyone is
the user's decision.
Usage: python -I tools/make_source_zip.py  (the fork commit is read from dist/warriors-4p-coop-emulator-origin.json)"""
import io
import json
import os
import subprocess
import sys
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import make_package  # noqa: E402  (FORBIDDEN list)

OUT = os.path.join(PROJ, "dist", "warriors-4p-coop-source.zip")


def git(args, cwd):
    return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, check=True).stdout


def main():
    origin = json.load(open(os.path.join(PROJ, "dist", "warriors-4p-coop-emulator-origin.json")))
    commit = origin["commit"]
    fork = os.path.join(PROJ, "emulator", "pcsx2")
    fork_zip = zipfile.ZipFile(io.BytesIO(git(["archive", "--format=zip", commit], fork)))
    tracked = git(["ls-files", "net/w4p-net", "emulator/build.ps1", "emulator/patches", "mod/make_pnach.py", "mod/m2",
                   "tools/mips_asm.py"], PROJ).decode("utf-8").splitlines()
    bad = []
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for info in fork_zip.infolist():
            if info.is_dir():
                continue
            name = "pcsx2-fork/" + info.filename
            if info.filename.lower().endswith(make_package.FORBIDDEN):
                bad.append(name)
                continue
            z.writestr(name, fork_zip.read(info))
        for rel in tracked:
            if rel.startswith("net/w4p-net/build/"):
                continue
            if rel.lower().endswith(make_package.FORBIDDEN):
                bad.append(rel)
                continue
            dest = ("w4p-net/" + rel[len("net/w4p-net/"):]) if rel.startswith("net/w4p-net/") else "build/" + rel
            z.write(os.path.join(PROJ, rel), dest)
        z.writestr("SOURCE-README.txt", "\n".join([
            "warriors-4p co-op package: complete source of the programs in the package",
            f"pcsx2-fork/  PCSX2 v2.9.115 + warriors-4p changes, fork commit {commit} (GPL-3.0, see pcsx2-fork/COPYING.GPLv3).",
            "             Build on Windows with Visual Studio Build Tools: build/emulator/build.ps1 (expects the tree at",
            "             emulator/pcsx2 of the project layout), solution PCSX2_qt.slnx, target pcsx2-qt, Release x64.",
            "w4p-net/     connection helper (GPL-3.0-or-later) with libjuice v1.7.4 unmodified (MPL-2.0,",
            "             w4p-net/third_party/libjuice/LICENSE); build with w4p-net/build.ps1 (CMake + Ninja + MSVC).",
            "build/       the same changes as patch files (emulator/patches), and the sources of the game patch",
            "             (mod/m2/*.txt, generated into w4p.pnach by mod/make_pnach.py).",
            "No game, ISO, BIOS or game files are included.", ""]))
    if bad:
        print("skipped (forbidden types):", bad)
    print(OUT, os.path.getsize(OUT) // (1024 * 1024), "MB", "fork", commit)


if __name__ == "__main__":
    main()
