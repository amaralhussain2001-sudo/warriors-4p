// Decompile functions and their callees up to a depth, one .c file per function,
// plus callgraph.tsv (caller, callee). Skips functions larger than a size cap
// unless they are roots.
// Lines in addr_file: "<hex address> [label]".
// Usage (headless): -postScript DecompileTree.java <addr_file> <out_dir> <depth> [maxBytes]
// @category Warriors4P

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import java.io.*;
import java.nio.file.*;
import java.util.*;

public class DecompileTree extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        List<String> lines = Files.readAllLines(Paths.get(args[0]));
        File outDir = new File(args[1]);
        int depth = Integer.parseInt(args[2]);
        long maxBytes = args.length > 3 ? Long.parseLong(args[3]) : 6000;
        outDir.mkdirs();
        DecompInterface di = new DecompInterface();
        di.openProgram(currentProgram);
        FunctionManager fm = currentProgram.getFunctionManager();
        Map<Function, String> labels = new LinkedHashMap<>();
        Deque<Object[]> q = new ArrayDeque<>();
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty() || line.startsWith("#")) continue;
            String[] p = line.split("\\s+", 2);
            Function f = fm.getFunctionContaining(toAddr(Long.parseLong(p[0].replace("0x", ""), 16)));
            if (f == null) continue;
            labels.put(f, p.length > 1 ? p[1] : "");
            q.add(new Object[]{f, 0});
        }
        Set<Function> done = new HashSet<>();
        PrintWriter cg = new PrintWriter(new FileWriter(new File(outDir, "callgraph.tsv"), true));
        while (!q.isEmpty() && !monitor.isCancelled()) {
            Object[] e = q.poll();
            Function f = (Function) e[0];
            int d = (Integer) e[1];
            if (!done.add(f)) continue;
            boolean root = d == 0;
            if (!root && f.getBody().getNumAddresses() > maxBytes) continue;
            String label = labels.getOrDefault(f, "").replaceAll("[^A-Za-z0-9_]", "_");
            File out = new File(outDir, f.getEntryPoint().toString() + (label.isEmpty() ? "" : "_" + label) + ".c");
            if (!out.exists()) {
                DecompileResults res = di.decompileFunction(f, 120, monitor);
                try (PrintWriter pw = new PrintWriter(new FileWriter(out))) {
                    pw.println("// " + f.getName() + " @ " + f.getEntryPoint() + " size " + f.getBody().getNumAddresses() + " depth " + d);
                    pw.println(res != null && res.decompileCompleted() ? res.getDecompiledFunction().getC() : "// decompile failed");
                }
            }
            for (Function c : f.getCalledFunctions(monitor)) {
                cg.printf("%s\t%s%n", f.getEntryPoint(), c.getEntryPoint());
                if (d + 1 <= depth) q.add(new Object[]{c, d + 1});
            }
        }
        cg.close();
        di.dispose();
        println("wrote " + done.size() + " functions");
    }
}
