// Print the disassembly listing of functions containing the given addresses.
// Usage (headless): -postScript DumpListing.java <out_file> <hexaddr> [hexaddr...]
// @category Warriors4P

import ghidra.app.script.GhidraScript;
import ghidra.program.model.listing.*;
import java.io.*;

public class DumpListing extends GhidraScript {
    @Override
    public void run() throws Exception {
        String[] args = getScriptArgs();
        try (PrintWriter pw = new PrintWriter(new FileWriter(args[0]))) {
            for (int i = 1; i < args.length; i++) {
                Function f = currentProgram.getFunctionManager().getFunctionContaining(toAddr(Long.parseLong(args[i].replace("0x", ""), 16)));
                if (f == null) { pw.println("no function at " + args[i]); continue; }
                pw.println("== " + f.getName() + " @ " + f.getEntryPoint());
                InstructionIterator it = currentProgram.getListing().getInstructions(f.getBody(), true);
                while (it.hasNext()) {
                    Instruction ins = it.next();
                    StringBuilder hex = new StringBuilder();
                    for (byte b : ins.getBytes()) hex.append(String.format("%02x", b));
                    pw.printf("%s  %s  %s%n", ins.getAddress(), hex, ins.toString());
                }
            }
        }
    }
}
