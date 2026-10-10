"""Apply the warriors-4p hook edits to an upstream PCSX2 v2.9.115 checkout (idempotent).

New files (pcsx2/W4P/*) are added separately; this script only edits existing upstream files:
  pcsx2/R5900OpcodeImpl.cpp   SYSCALL: call W4P::OnGuestHook() for v1 == W4P::kHookMagic
  pcsx2/VMManager.cpp         OnVMStarted / OnVMShutdown / OnVsync
  pcsx2/GS/Renderers/Common/GSRenderer.cpp  presentation crop of the displayed frame
  pcsx2/pcsx2.vcxproj, pcsx2/CMakeLists.txt  build the new files
Usage: python -I apply_w4p_hooks.py <pcsx2 checkout dir>
"""
import os
import sys

root = sys.argv[1]


def edit(rel, old, new, marker):
    p = os.path.join(root, rel)
    s = open(p, encoding="utf-8").read()
    if marker in s:
        print("already applied:", rel, marker[:40])
        return
    if old not in s:
        raise SystemExit(f"anchor not found in {rel}: {old[:60]!r}")
    s = s.replace(old, new, 1)
    open(p, "w", encoding="utf-8", newline="").write(s)
    print("edited:", rel)


edit("pcsx2/R5900OpcodeImpl.cpp",
     "void SYSCALL()\n{\n\tu8 call;\n",
     "void SYSCALL()\n{\n\tu8 call;\n\n"
     "\t// warriors-4p: game-patch hook (not an upstream syscall). Needs proper testing.\n"
     "\tif (cpuRegs.GPR.n.v1.UL[0] == W4P::kHookMagic)\n\t{\n\t\tW4P::OnGuestHook();\n\t\treturn;\n\t}\n",
     "W4P::kHookMagic")
edit("pcsx2/R5900OpcodeImpl.cpp", '#include "R5900.h"\n', '#include "R5900.h"\n#include "W4P/W4P.h"\n', '#include "W4P/W4P.h"')

edit("pcsx2/VMManager.cpp",
     "\treturn VMBootResult::StartupSuccess;\n}",
     "\tW4P::OnVMStarted(); // warriors-4p\n\treturn VMBootResult::StartupSuccess;\n}",
     "W4P::OnVMStarted();")
edit("pcsx2/VMManager.cpp",
     "void VMManager::Shutdown(bool save_resume_state)\n{\n",
     "void VMManager::Shutdown(bool save_resume_state)\n{\n\tW4P::OnVMShutdown(); // warriors-4p\n\n",
     "W4P::OnVMShutdown();")
edit("pcsx2/VMManager.cpp",
     "\tHost::PumpMessagesOnCPUThread();\n\tInputManager::PollSources();\n",
     "\tHost::PumpMessagesOnCPUThread();\n\tInputManager::PollSources();\n\tW4P::OnVsync(); // warriors-4p\n",
     "W4P::OnVsync();")
edit("pcsx2/VMManager.cpp", '#include "VMManager.h"\n', '#include "VMManager.h"\n#include "W4P/W4P.h"\n', '#include "W4P/W4P.h"')

edit("pcsx2/GS/Renderers/Common/GSRenderer.cpp",
     "\tconst int bottom = size.y - static_cast<int>(static_cast<float>(GSConfig.Crop[3] * scale.y) * upscale);\n\treturn GSVector4i(left, top, right, bottom);",
     "\tconst int bottom = size.y - static_cast<int>(static_cast<float>(GSConfig.Crop[3] * scale.y) * upscale);\n"
     "\t// warriors-4p: show only the local player's view of the game's split screen (presentation only).\n"
     "\tfloat w4p[4];\n"
     "\tif (W4P::GetPresentationCrop(w4p))\n\t{\n"
     "\t\tconst float w = static_cast<float>(right - left), h = static_cast<float>(bottom - top);\n"
     "\t\treturn GSVector4i(left + static_cast<int>(w * w4p[0]), top + static_cast<int>(h * w4p[1]),\n"
     "\t\t\tleft + static_cast<int>(w * w4p[2]), top + static_cast<int>(h * w4p[3]));\n\t}\n"
     "\treturn GSVector4i(left, top, right, bottom);",
     "W4P::GetPresentationCrop")
edit("pcsx2/GS/Renderers/Common/GSRenderer.cpp", '#include "VMManager.h"\n', '#include "VMManager.h"\n#include "W4P/W4P.h"\n', '#include "W4P/W4P.h"')

edit("pcsx2/pcsx2.vcxproj", '    <ClCompile Include="PINE.cpp" />\n',
     '    <ClCompile Include="PINE.cpp" />\n    <ClCompile Include="W4P\\W4P.cpp" />\n    <ClCompile Include="W4P\\W4PTransport.cpp" />\n',
     'W4P\\W4P.cpp')
edit("pcsx2/pcsx2.vcxproj", '    <ClInclude Include="PINE.h" />\n',
     '    <ClInclude Include="PINE.h" />\n    <ClInclude Include="W4P\\W4P.h" />\n    <ClInclude Include="W4P\\W4PTransport.h" />\n',
     'W4P\\W4P.h')
edit("pcsx2/CMakeLists.txt", "\tPINE.cpp\n", "\tPINE.cpp\n\tW4P/W4P.cpp\n\tW4P/W4PTransport.cpp\n", "W4P/W4P.cpp")
edit("pcsx2/CMakeLists.txt", "\tPINE.h\n", "\tPINE.h\n\tW4P/W4P.h\n\tW4P/W4PTransport.h\n", "W4P/W4P.h")
