"""Build the 2-4 player co-op test package in dist/warriors-4p-coop (and dist/warriors-4p-coop.zip).

Usage: python -I tools/make_package4.py [--reuse-emulator] [--pnach FILE] [--strip-comments]
  --strip-comments: ship the game patch without the "//" comments (legal review M8 L2: the comments quote
  replaced original instruction words); patch lines, group headers and descriptions are unchanged.
  --pnach FILE: the game patch to ship (default mod/w4p_m1.pnach), e.g. one generated from the current sources with
  `python -I mod/make_pnach.py > FILE` (check it with `python -I tools/note_patches.py check FILE`).
  --reuse-emulator: keep the emulator folder of the existing dist/warriors-4p-coop (the bin folder is copied only once;
  its origin - fork commit, patch list, exe hash - is kept in dist/warriors-4p-coop-emulator-origin.json) and rebuild
  everything else.
Contents: the launcher (package4/), our PCSX2 build (emulator/pcsx2/bin without debug files), the Visual C++ runtime
DLLs (app-local, next to the emulator and next to the helper), the connection helper w4p-net.exe (net/w4p-net/build)
with the libjuice licence and source pointer, the game patch, GPL/MPL notices, the fork patches and our sources, a
VERSION.txt with the package id the lobby compares, and a SHA-256 manifest. Never any game, ISO, BIOS, memory card,
savestate or extracted game file (BRIEF section 2.4): the build fails if such a file shows up (same rule as
tools/make_package.py, whose helpers are reused here; that script and dist/warriors-4p-test are not touched).
"""
import datetime
import glob
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import make_package  # noqa: E402  (2-player builder: FORBIDDEN list and the VC runtime lookup; not modified)

BIN = os.path.join(PROJ, "emulator", "pcsx2", "bin")
FORK = os.path.join(PROJ, "emulator", "pcsx2")
NET = os.path.join(PROJ, "net", "w4p-net")
SRC4 = os.path.join(PROJ, "package4")
NAME = "warriors-4p-coop"
DEST = os.path.join(PROJ, "dist", NAME)
ORIGIN = os.path.join(PROJ, "dist", NAME + "-emulator-origin.json")
CRT_DLLS = ("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll")
LIBJUICE = {"version": "1.7.4", "commit": "b89c792e3612faf2f12cf35bcc56857313a06be3",
            "url": "https://github.com/paullouisageneau/libjuice/archive/refs/tags/v1.7.4.tar.gz",
            "sha256": "95c088862aa1b88b73d62aa99577135010eb768fcafb252d13aa85a8515ef798"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    return subprocess.run(["git", "-C", FORK] + list(args), capture_output=True, text=True).stdout


def crlf(text):
    return text.replace("\r\n", "\n").replace("\n", "\r\n")


def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(crlf(text))


def stable_exe():
    """Wait until the emulator exe is not being rebuilt (same size and time for 5 s)."""
    exe = os.path.join(BIN, "pcsx2-qtx64.exe")
    for _ in range(60):
        a = os.stat(exe)
        time.sleep(5)
        b = os.stat(exe)
        if (a.st_size, a.st_mtime) == (b.st_size, b.st_mtime):
            return exe
    sys.exit("emulator exe keeps changing (a build is running?)")


def processes_in_package():
    """Processes whose program file lies inside the package folder (a test still running from it)."""
    cmd = ("Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -and $_.ExecutablePath.StartsWith('%s', "
           "[StringComparison]::OrdinalIgnoreCase) } | ForEach-Object { '{0} {1}' -f $_.ProcessId, $_.Name }") % DEST
    out = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if line.strip()]


def build_tag():
    """The W4P build tag compiled into the emulator (kBuildTag in the fork source)."""
    import re
    src = open(os.path.join(PROJ, "emulator", "pcsx2", "pcsx2", "W4P", "W4P.cpp"), encoding="utf-8", errors="replace").read()
    m = re.search(r'kBuildTag\[\] = "([^"]+)"', src)
    return m.group(1) if m else "unknown"


def main():
    assert os.path.commonpath([DEST, PROJ]) == PROJ and os.path.basename(DEST) == NAME
    busy = processes_in_package()
    if busy:  # never move or delete files of a running test (a rebuild during a run broke one once)
        sys.exit(f"programs are running from {DEST}: {busy}; wait until they have ended")
    net_exe = os.path.join(NET, "build", "w4p-net.exe")
    if not os.path.exists(net_exe):
        sys.exit("net/w4p-net/build/w4p-net.exe missing: run powershell -File net\\w4p-net\\build.ps1")
    reuse = "--reuse-emulator" in sys.argv
    if reuse:
        origin = json.load(open(ORIGIN, encoding="utf-8"))
        keep = DEST + ".emulator-keep"
        if os.path.exists(keep):
            shutil.rmtree(keep)
        shutil.move(os.path.join(DEST, "emulator"), keep)
        shutil.rmtree(DEST)
        os.makedirs(DEST)
        shutil.move(keep, os.path.join(DEST, "emulator"))
        exe = os.path.join(DEST, "emulator", "pcsx2-qtx64.exe")
        if sha256(exe) != origin["exe_sha256"]:
            sys.exit("the kept emulator does not match its recorded origin")
    else:
        exe = stable_exe()
        if os.path.exists(DEST):
            shutil.rmtree(DEST)
        # emulator (no debug files), copied once per full build; its origin is recorded for --reuse-emulator
        shutil.copytree(BIN, os.path.join(DEST, "emulator"), ignore=shutil.ignore_patterns("*.pdb", "*.ilk", "*.exp", "*.lib"))
        origin = {"copied": datetime.datetime.now().isoformat(timespec="seconds"), "commit": git("rev-parse", "HEAD").strip(),
                  "uncommitted_diff": git("diff"), "exe_sha256": sha256(exe),
                  "exe_mtime": datetime.datetime.fromtimestamp(os.path.getmtime(exe)).isoformat(timespec="seconds"),
                  "w4p_cpp_mtime": datetime.datetime.fromtimestamp(os.path.getmtime(
                      os.path.join(FORK, "pcsx2", "W4P", "W4P.cpp"))).isoformat(timespec="seconds"),
                  "patches": [os.path.basename(p) for p in sorted(glob.glob(os.path.join(PROJ, "emulator", "patches", "*.patch")))]}
        json.dump(origin, open(ORIGIN, "w", encoding="utf-8"), indent=1)
    crt = make_package.vc_redist_dir()
    for sub in ("emulator", "net"):
        os.makedirs(os.path.join(DEST, sub), exist_ok=True)
        for dll in CRT_DLLS:
            shutil.copy2(os.path.join(crt, dll), os.path.join(DEST, sub, dll))
    shutil.copy2(net_exe, os.path.join(DEST, "net", "w4p-net.exe"))
    # game patch, profile, launcher, README
    os.makedirs(os.path.join(DEST, "game"))
    pnach = os.path.abspath(sys.argv[sys.argv.index("--pnach") + 1]) if "--pnach" in sys.argv else \
        os.path.join(PROJ, "mod", "w4p_m1.pnach")
    if "--strip-comments" in sys.argv:  # M8 legal review L2: no quoted original words in the shipped patch
        raw = open(pnach, "rb").read()
        nl = bytes([13, 13, 10]) if bytes([13, 13, 10]) in raw else (bytes([13, 10]) if bytes([13, 10]) in raw else bytes([10]))
        out = []
        for ln in raw.split(nl):
            t = ln.strip()
            if t.startswith(b"//"):
                continue
            if t.startswith(b"patch=") and b"//" in ln:
                ln = ln[:ln.index(b"//")].rstrip()
            out.append(ln)
        open(os.path.join(DEST, "game", "w4p.pnach"), "wb").write(nl.join(out))
    else:
        shutil.copy2(pnach, os.path.join(DEST, "game", "w4p.pnach"))
    shutil.copy2(os.path.join(SRC4, "profile_PCSX2.ini"), os.path.join(DEST, "game", "profile_PCSX2.ini"))
    for f in ("Start-Coop.ps1", "Start-Coop.bat", "README.txt", "QUICK-START.txt"):
        shutil.copy2(os.path.join(SRC4, f), os.path.join(DEST, f))
    # licences and sources
    shutil.copy2(os.path.join(FORK, "COPYING.GPLv3"), os.path.join(DEST, "COPYING.GPLv3"))
    os.makedirs(os.path.join(DEST, "licenses"))
    shutil.copy2(os.path.join(NET, "third_party", "libjuice", "LICENSE"), os.path.join(DEST, "licenses", "libjuice-LICENSE.txt"))
    src = os.path.join(DEST, "source")
    os.makedirs(src)
    patches = [os.path.join(PROJ, "emulator", "patches", n) for n in origin["patches"]]
    for p in patches:
        shutil.copy2(p, src)
    shutil.copy2(os.path.join(PROJ, "mod", "make_pnach.py"), src)
    commit = origin["commit"]
    diff = origin["uncommitted_diff"]
    if diff.strip():
        with open(os.path.join(src, "uncommitted-at-build.diff"), "w", encoding="utf-8", newline="") as f:
            f.write(diff)
    netsrc = os.path.join(src, "w4p-net")
    os.makedirs(netsrc)
    shutil.copytree(os.path.join(NET, "src"), os.path.join(netsrc, "src"))
    for f in ("CMakeLists.txt", "build.ps1", "README.md"):
        shutil.copy2(os.path.join(NET, f), os.path.join(netsrc, f))
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    exe_hash = sha256(exe)
    write_text(os.path.join(src, "SOURCE.txt"), "\n".join([
        "Emulator: PCSX2 v2.9.115 (https://github.com/PCSX2/pcsx2, tag v2.9.115, commit cf3c3720) with the warriors-4p",
        f"patches in this folder applied in order (git am 0001-*.patch .. {os.path.basename(patches[-1])[:4]}-*.patch).",
        f"Fork commit when the emulator was copied: {commit}",
        (f"Uncommitted changes in the fork when the emulator was copied: uncommitted-at-build.diff (W4P.cpp modified "
         f"{origin['w4p_cpp_mtime']}, emulator built {origin['exe_mtime']})." if diff.strip() else
         f"No uncommitted changes in the fork when the emulator was copied ({origin['copied']}; W4P.cpp modified "
         f"{origin['w4p_cpp_mtime']}, emulator built {origin['exe_mtime']})."),
        f"pcsx2-qtx64.exe SHA-256: {exe_hash}",
        "Build: Visual Studio Build Tools, PCSX2_qt.slnx, target pcsx2-qt, Release x64 (emulator/build.ps1 in the project).",
        "The game patch (game\\w4p.pnach) is generated by make_pnach.py from the project's mod/ sources",
        f"(packaged from {os.path.relpath(pnach, PROJ)}, SHA-256 {sha256(pnach)}).",
        "License: GPL-3.0 (COPYING.GPLv3).",
        "",
        "Connection helper net\\w4p-net.exe: our source in w4p-net\\ (GPL-3.0-or-later), built with w4p-net\\build.ps1",
        "(CMake + Ninja + MSVC). It links libjuice v1.7.4 unmodified (MPL-2.0, ..\\licenses\\libjuice-LICENSE.txt):",
        f"  source archive {LIBJUICE['url']}",
        f"  commit {LIBJUICE['commit']}, archive SHA-256 {LIBJUICE['sha256']}",
        f"w4p-net.exe SHA-256: {sha256(net_exe)}",
        ""]))
    write_text(os.path.join(DEST, "THIRD-PARTY-NOTICES.txt"), "\n".join([
        "warriors-4p co-op test package: third-party components",
        "",
        "1. PCSX2 (modified), folder emulator\\. GPL-3.0 (COPYING.GPLv3). Upstream: https://github.com/PCSX2/pcsx2 (v2.9.115).",
        "   Our changes: source\\*.patch, see source\\SOURCE.txt. PCSX2's own third-party libraries: emulator\\docs\\ThirdPartyLicenses.html.",
        "2. libjuice v1.7.4, built into net\\w4p-net.exe. Copyright (c) 2020-2022 Paul-Louis Ageneau.",
        "   Mozilla Public License 2.0 (licenses\\libjuice-LICENSE.txt). Not modified. Source code:",
        f"   {LIBJUICE['url']} (commit {LIBJUICE['commit']}).",
        "3. w4p-net (connection helper of this project), net\\w4p-net.exe. GPL-3.0-or-later. Source: source\\w4p-net\\.",
        "4. Microsoft Visual C++ runtime (msvcp140.dll, vcruntime140.dll, vcruntime140_1.dll) in emulator\\ and net\\,",
        "   included as allowed by Microsoft's redistribution terms for Visual Studio.",
        "5. Internet address lookup: w4p-net asks Cloudflare's public STUN server (stun.cloudflare.com, UDP port 3478) for this",
        "   PC's public internet address when you host or join with a code. No account; no game data is sent there.",
        ""]))
    # forbidden files (same rule as the 2-player package)
    bad = [os.path.relpath(os.path.join(d, f), DEST) for d, _, fs in os.walk(DEST) for f in fs
           if f.lower().endswith(make_package.FORBIDDEN) or f.upper().startswith(("SLUS_", "SCUS_"))]
    if bad:
        shutil.rmtree(DEST)
        sys.exit(f"refusing to package forbidden files: {bad}")
    # package id: hash over every file's hash and path (the lobby compares it between the PCs)
    entries = []
    for d, _, fs in os.walk(DEST):
        for f in sorted(fs):
            p = os.path.join(d, f)
            entries.append((os.path.relpath(p, DEST).replace("\\", "/"), sha256(p)))
    entries.sort()
    pid = hashlib.sha256("".join(f"{h}  {r}\n" for r, h in entries).encode()).hexdigest()[:12]
    write_text(os.path.join(DEST, "VERSION.txt"), "\n".join([
        f"id={pid}",
        f"warriors-4p co-op test package (2-4 players), built {stamp}",
        f"emulator build tag {build_tag()}, pcsx2-qtx64.exe SHA-256 {exe_hash}, fork commit {commit}"
        + (" + uncommitted changes" if diff.strip() else ""),
        f"w4p-net.exe SHA-256 {sha256(net_exe)}",
        f"game patch w4p.pnach SHA-256 {sha256(os.path.join(DEST, 'game', 'w4p.pnach'))}",
        "Every player must use exactly this package (the lobby compares the id above).", ""]))
    manifest = []
    for d, _, fs in os.walk(DEST):
        for f in sorted(fs):
            p = os.path.join(d, f)
            manifest.append(f"{sha256(p)}  {os.path.relpath(p, DEST)}")
    write_text(os.path.join(DEST, "MANIFEST.txt"), "\n".join(sorted(manifest, key=lambda l: l[66:])) + "\n")
    zpath = DEST + ".zip"
    if os.path.exists(zpath):
        os.remove(zpath)
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for d, _, fs in os.walk(DEST):
            for f in fs:
                p = os.path.join(d, f)
                z.write(p, os.path.join(NAME, os.path.relpath(p, DEST)))
    size = sum(os.path.getsize(os.path.join(d, f)) for d, _, fs in os.walk(DEST) for f in fs)
    print(f"package: {DEST} ({len(manifest) + 1} files, {size / 1e6:.0f} MB); zip {os.path.getsize(zpath) / 1e6:.0f} MB")
    print(f"package id {pid}; emulator {exe_hash[:16]}; fork commit {commit}{' + uncommitted diff' if diff.strip() else ''}")
    print(f"zip SHA-256 {sha256(zpath)}")


if __name__ == "__main__":
    main()
