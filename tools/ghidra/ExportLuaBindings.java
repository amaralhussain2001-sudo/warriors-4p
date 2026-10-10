// Pair Lua global names with the C functions registered under them.
// Heuristic (documented in docs/research/static_analysis.md): for every
// instruction that references a NUL-terminated ASCII string, look at the
// neighbouring instructions (+-8) for a reference to a function entry point.
// Output: TSV  name \t string_addr \t func_addr \t register_site \t caller_func
// Usage (headless): -postScript ExportLuaBindings.java <out.tsv>
// @category Warriors4P

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.mem.*;
import java.io.*;
import java.util.*;

public class ExportLuaBindings extends GhidraScript {
    private String readCString(Address a) {
        try {
            StringBuilder sb = new StringBuilder();
            Memory m = currentProgram.getMemory();
            for (int i = 0; i < 80; i++) {
                byte b = m.getByte(a.add(i));
                if (b == 0) break;
                if (b < 0x20 || b > 0x7e) return null;
                sb.append((char) b);
            }
            return sb.length() >= 2 ? sb.toString() : null;
        } catch (Exception e) {
            return null;
        }
    }

    @Override
    public void run() throws Exception {
        String out = getScriptArgs().length > 0 ? getScriptArgs()[0] : "lua_bindings.tsv";
        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager rm = currentProgram.getReferenceManager();
        PrintWriter pw = new PrintWriter(new FileWriter(out));
        pw.println("name\tstring_addr\tfunc_addr\tsite\tcaller");
        InstructionIterator it = listing.getInstructions(true);
        int n = 0;
        while (it.hasNext() && !monitor.isCancelled()) {
            Instruction ins = it.next();
            for (Reference r : ins.getReferencesFrom()) {
                Address to = r.getToAddress();
                if (!to.isMemoryAddress()) continue;
                if (fm.getFunctionAt(to) != null) continue;
                String s = readCString(to);
                if (s == null || !s.matches("[A-Za-z_][A-Za-z0-9_]*")) continue;
                // look around for a function-pointer reference
                Instruction cur = ins;
                Function found = null;
                Address site = null;
                for (int dir = 0; dir < 2 && found == null; dir++) {
                    cur = ins;
                    for (int k = 0; k < 8 && cur != null && found == null; k++) {
                        cur = dir == 0 ? cur.getNext() : cur.getPrevious();
                        if (cur == null) break;
                        if (cur.getFlowType().isCall()) continue;
                        for (Reference r2 : cur.getReferencesFrom()) {
                            if (r2.getReferenceType().isCall() || r2.getReferenceType().isJump()) continue;
                            Function f = fm.getFunctionAt(r2.getToAddress());
                            if (f != null) { found = f; site = cur.getAddress(); break; }
                        }
                    }
                }
                if (found == null) continue;
                Function caller = fm.getFunctionContaining(ins.getAddress());
                pw.printf("%s\t%s\t%s\t%s\t%s%n", s, to, found.getEntryPoint(), ins.getAddress(),
                        caller == null ? "-" : caller.getEntryPoint().toString());
                n++;
            }
        }
        pw.close();
        println("wrote " + n + " rows to " + out);
    }
}
