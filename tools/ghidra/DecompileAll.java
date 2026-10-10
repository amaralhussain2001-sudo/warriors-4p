// Decompile every function into a few large text files (grep-friendly).
// Each function starts with a line "//==== <name> @ <entry> size <bytes>".
// Output stays under local/ (it is derived from copyrighted code).
// Usage (headless): -postScript DecompileAll.java <out_dir> [threads]
// @category Warriors4P

import ghidra.app.decompiler.*;
import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import ghidra.util.task.TaskMonitor;
import java.io.*;
import java.util.*;
import java.util.concurrent.*;

public class DecompileAll extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        File outDir = new File(args[0]);
        int threads = args.length > 1 ? Integer.parseInt(args[1]) : 12;
        outDir.mkdirs();
        List<Function> funcs = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) funcs.add(f);
        println("functions: " + funcs.size());
        ConcurrentHashMap<Long, String> out = new ConcurrentHashMap<>();
        ExecutorService ex = Executors.newFixedThreadPool(threads);
        List<List<Function>> parts = new ArrayList<>();
        for (int t = 0; t < threads; t++) parts.add(new ArrayList<>());
        for (int i = 0; i < funcs.size(); i++) parts.get(i % threads).add(funcs.get(i));
        List<Future<?>> futs = new ArrayList<>();
        for (List<Function> part : parts) {
            futs.add(ex.submit(() -> {
                DecompInterface di = new DecompInterface();
                di.openProgram(currentProgram);
                for (Function f : part) {
                    DecompileResults r = di.decompileFunction(f, 60, TaskMonitor.DUMMY);
                    String head = "//==== " + f.getName() + " @ " + f.getEntryPoint() + " size " + f.getBody().getNumAddresses() + "\n";
                    String body = (r != null && r.decompileCompleted()) ? r.getDecompiledFunction().getC()
                            : "// decompile failed: " + (r == null ? "null" : r.getErrorMessage()) + "\n";
                    out.put(f.getEntryPoint().getOffset(), head + body);
                }
                di.dispose();
            }));
        }
        for (Future<?> f : futs) f.get();
        ex.shutdown();
        TreeMap<Long, String> sorted = new TreeMap<>(out);
        int chunk = 0, n = 0;
        PrintWriter pw = null;
        for (String s : sorted.values()) {
            if (n % 1500 == 0) {
                if (pw != null) pw.close();
                pw = new PrintWriter(new FileWriter(new File(outDir, String.format("all_%02d.c", chunk++))));
            }
            pw.println(s);
            n++;
        }
        if (pw != null) pw.close();
        println("wrote " + n + " functions in " + chunk + " files");
    }
}
