"""Create isolated PCSX2 data directories for sandbox instances (BRIEF §2.2, §5.4).

All instances share the sandbox copy of the emulator binary in local/pcsx2/base
(never the user's original installation) and each gets its own -datapath
directory under local/pcsx2/inst<N>/ with its own settings, memory cards,
savestates, logs and PINE slot.

Usage:
    python -I tools/sandbox.py make <N> [--profile default|det] [--pad2] [--patch <file.pnach> "<group;group>"]
    python -I tools/sandbox.py cmd <N> [extra pcsx2 args]     # print the launch command
    python -I tools/sandbox.py launch <N> [extra pcsx2 args]  # start detached, record pid
    python -I tools/sandbox.py kill <N>                       # stop it (sandbox exe only)
"""
import configparser
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, ".."))
BASE = os.path.join(PROJ, "local", "pcsx2", "base")
EXE = os.environ.get("W4P_PCSX2_EXE") or os.path.join(BASE, "pcsx2-qt.exe")
FORK_EXE = os.path.join(PROJ, "emulator", "pcsx2", "bin", "pcsx2-qtx64.exe")
ISO = r"C:\Users\PC FORCE\Desktop\New folder\Warriors The (USA) (EnFrDeEsIt)\Warriors, The (USA) (En,Fr,De,Es,It).iso"
BIOS_DIR = os.path.join(BASE, "bios", "SCPH-90001_BIOS_V18_USA_230_(NTSC)")
PINE_BASE = 28100

PROFILES = {
    # Same emulation settings as the user's installation, plus sandbox plumbing.
    "default": {},
    # Candidate deterministic profile for E1 (see tests/experiments/E1).
    "det": {
        "EmuCore/Speedhacks": {"vuThread": "false", "fastCDVD": "false"},
        "EmuCore": {"CdvdPrecache": "true"},
    },
}


def inst_dir(n):
    return os.path.join(PROJ, "local", "pcsx2", f"inst{n}")


def data_root(n):
    # PCSX2 appends "PCSX2" to the -datapath argument (observed: emulog "DataRoot Directory").
    return os.path.join(inst_dir(n), "PCSX2")


def install_patch(n, pnach_path, enable_names):
    """Copy an experiment pnach into the instance and enable the named groups (per-game settings)."""
    d = data_root(n)
    shutil.copyfile(pnach_path, os.path.join(d, "patches", "SLUS-21215_B99A75DE.pnach"))
    body = "[Patches]\n" + "".join(f"Enable = {e}\n" for e in enable_names)
    for name in ("SLUS-21215_B99A75DE.ini", "B99A75DE.ini"):
        with open(os.path.join(d, "gamesettings", name), "w", encoding="utf-8") as fh:
            fh.write(body)


def make(n, profile="default", pad2=False):
    d = data_root(n)
    assert os.path.commonpath([d, PROJ]) == PROJ, "refusing to write outside the project"
    for sub in ("inis", "memcards", "sstates", "logs", "snaps", "cache", "cheats", "patches", "gamesettings", "inputprofiles", "videos", "covers", "textures"):
        os.makedirs(os.path.join(d, sub), exist_ok=True)
    cp = configparser.ConfigParser(interpolation=None, strict=False)
    cp.optionxform = str
    cp.read(os.path.join(PROJ, "local", "pcsx2", "template_PCSX2.ini"), encoding="utf-8")
    s = {
        "UI": {"ConfirmShutdown": "false", "PauseOnFocusLoss": "false", "StartFullscreen": "false",
               "SetupWizardIncomplete": "false"},
        "AutoUpdater": {"CheckAtStartup": "false"},
        "Folders": {"Bios": BIOS_DIR, "Snapshots": "snaps", "Savestates": "sstates", "MemoryCards": "memcards",
                    "Logs": "logs", "Cheats": "cheats", "Patches": "patches", "Cache": "cache",
                    "UserResources": os.path.join(BASE, "resources")},
        "EmuCore": {"EnablePINE": "true", "PINESlot": str(PINE_BASE + n), "SaveStateOnShutdown": "false",
                    "ManuallySetRealTimeClock": "true", "RtcYear": "5", "RtcMonth": "10", "RtcDay": "1",
                    "RtcHour": "12", "RtcMinute": "0", "RtcSecond": "0", "EnableRecordingTools": "true",
                    "EnableFastBoot": "true", "EnableDiscordPresence": "false"},
        "Achievements": {"Enabled": "false"},
        "Logging": {"EnableFileLogging": "true", "EnableEEConsole": "true", "EnableIOPConsole": "false"},
        "GameList": {"RecursivePaths": ""},
        # native resolution keeps several instances cheap; recorded in the profile file
        "EmuCore/GS": {"upscale_multiplier": "1", "OsdShowFPS": "true", "OsdShowFrameTimes": "false"},
    }
    for sec, kv in list(s.items()) + list(PROFILES[profile].items()):
        if not cp.has_section(sec):
            cp.add_section(sec)
        for k, v in kv.items():
            cp.set(sec, k, v)
    if pad2:
        cp.remove_section("Pad2")
        cp.add_section("Pad2")
        for k, v in {"Type": "DualShock2", "Up": "Keyboard/5", "Down": "Keyboard/6", "Left": "Keyboard/7",
                     "Right": "Keyboard/8", "Cross": "Keyboard/X", "Circle": "Keyboard/C", "Square": "Keyboard/Z",
                     "Triangle": "Keyboard/V", "Start": "Keyboard/P", "Select": "Keyboard/O", "R1": "Keyboard/R",
                     "L1": "Keyboard/U", "R2": "Keyboard/9", "L2": "Keyboard/0", "LUp": "Keyboard/Y",
                     "LDown": "Keyboard/N", "LLeft": "Keyboard/B", "LRight": "Keyboard/M"}.items():
            cp.set("Pad2", k, v)
    with open(os.path.join(d, "inis", "PCSX2.ini"), "w", encoding="utf-8") as fh:
        cp.write(fh, space_around_delimiters=True)
    with open(os.path.join(d, "PROFILE.txt"), "w") as fh:
        fh.write(f"profile={profile}\npine_slot={PINE_BASE + n}\npad2={pad2}\n")
    return d


def cmd(n, extra):
    return [EXE, "-batch", "-datapath", inst_dir(n), "-logfile", os.path.join(data_root(n), "logs", "emulog.txt")] + extra + ["--", ISO]


def main():
    if sys.argv[1] == "make":
        n = int(sys.argv[2])
        prof = sys.argv[sys.argv.index("--profile") + 1] if "--profile" in sys.argv else "default"
        print(make(n, prof, "--pad2" in sys.argv))
        if "--patch" in sys.argv:
            i = sys.argv.index("--patch")
            install_patch(n, sys.argv[i + 1], sys.argv[i + 2].split(";"))
    elif sys.argv[1] == "cmd":
        print(cmd(int(sys.argv[2]), sys.argv[3:]))
    elif sys.argv[1] == "launch":
        n = int(sys.argv[2])
        proc = subprocess.Popen(cmd(n, sys.argv[3:]), creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
        with open(os.path.join(inst_dir(n), "pid.txt"), "w") as fh:
            fh.write(str(proc.pid))
        print(proc.pid)
    elif sys.argv[1] == "kill":
        n = int(sys.argv[2])
        pid = int(open(os.path.join(inst_dir(n), "pid.txt")).read())
        # only ever kill a process whose image is the sandbox copy
        out = subprocess.run(["powershell", "-NoProfile", "-Command", f"(Get-Process -Id {pid}).Path"], capture_output=True, text=True).stdout.strip()
        if os.path.normcase(out) in (os.path.normcase(EXE), os.path.normcase(FORK_EXE), os.path.normcase(os.path.join(BASE, "pcsx2-qt.exe"))):
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
            print("killed", pid)
        else:
            print("not killing", pid, out)


if __name__ == "__main__":
    main()
