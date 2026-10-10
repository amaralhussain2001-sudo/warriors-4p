// Decompile the functions containing each address listed in a text file.
// Lines: "<hex address> [optional label]". Output: one <addr>_<label>.c per function.
// Usage (headless): -postScript DecompileList.java <addr_file> <out_dir>
// @category Warriors4P

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class DecompileList extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        List<String> lines = Files.readAllLines(Paths.get(args[0]));
        File outDir = new File(args[1]);
        outDir.mkdirs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] parts = line.split("\\s+", 2);
            Address a = toAddr(Long.parseLong(parts[0].replace("0x", ""), 16));
            Function f = fm.getFunctionContaining(a);
            if (f == null) {
                println("no function at " + a);
                continue;
            }
            DecompileResults res = di.decompileFunction(f, 120, monitor);
            String label = parts.length > 1 ? parts[1].replaceAll("[^A-Za-z0-9_]", "_") : "";
            File out = new File(outDir, f.getEntryPoint().toString() + (label.isEmpty() ? "" : "_" + label) + ".c");
            try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
                pw.println("// function " + f.getName() + " @ " + f.getEntryPoint() + " (requested " + a + " " + label + ")");
                if (res != null && res.decompileCompleted()) {
                    pw.println(res.getDecompiledFunction().getC());
                } else {
                    pw.println("// decompile failed: " + (res == null ? "null" : res.getErrorMessage()));
                }
            }
        }
        di.dispose();
    }
}
