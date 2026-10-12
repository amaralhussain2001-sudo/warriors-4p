"""Read-only PINE survey for docs/research/m2_extra_model.md (test X0): the Sector Pool that holds streamed models,
the 32-entry model pin list, and what one more Warrior model would need. Reads only (Pine.read32).
Standalone: python -I <this file> <pine slot>     As a probe: survey_mem(p) returns a dict (nav_probe --probe)."""
import json
import os
import struct
import sys
import zlib

WARRIORS = [(5, "Swan", "warr_sw"), (11, "Ajax", "warr_aj"), (33, "Snow", "warr_sn"), (15, "Cochise", "warr_co"),
            (26, "Vermin", "warr_ve"), (21, "Fox", "warr_fo"), (30, "Rembrandt", "warr_re"), (1, "Cleon", "warr_cl"),
            (18, "Cowboy", "warr_cb")]
NAMES = {zlib.crc32(n.encode()) & 0xFFFFFFFF: n for _, _, b in WARRIORS for n in (b, b + "_a", b + "_fury")}
NAMES[zlib.crc32(b"warr_cl_gen") & 0xFFFFFFFF] = "warr_cl_gen"


def survey_mem(p):
    r32 = p.read32

    def r16(a):
        return (r32(a & ~3) >> (8 * (a & 2))) & 0xFFFF

    def block(n):                      # FUN_001848D0: max(32 KB, next power of two)
        b = 1
        while b < n:
            b <<= 1
        return max(b, 0x8000)

    def lookup(tree, key):             # FUN_004DE458/8D0/BE8 lower_bound (unsigned), header *(tree+4), root header+4
        head = r32(tree + 4)
        if not head:
            return 0
        node, best, n = r32(head + 4), head, 0
        while node and n < 64:
            if r32(node + 0x10) < key:
                node = r32(node + 0xC)
            else:
                best, node = node, r32(node + 8)
            n += 1
        return best if best != head and not key < r32(best + 0x10) else 0

    def walk(tree, cap=20000):         # in-order node list (left +8, right +0xC)
        head = r32(tree + 4)
        if not head:
            return []
        out, stack, node, seen = [], [], r32(head + 4), set()
        while (stack or node) and len(out) < cap:
            if node and node != head and node not in seen:
                seen.add(node)
                stack.append(node)
                node = r32(node + 8)
            elif stack:
                node = stack.pop()
                out.append(node)
                node = r32(node + 0xC)
            else:
                break
        return out

    def pool(ptr_addr):                # MemoryPoolHeap (vtable 0x00544428) over an mmalloc-style descriptor
        P = r32(ptr_addr)
        if not P:
            return None
        H = r32(P + 4)
        d = {"obj": hex(P), "vtable": hex(r32(P)), "base": hex(r32(P + 8)), "size": r32(P + 0xC)}
        if not H:
            return d
        cap, used, free_in = r32(H + 0x40), r32(H + 0x48), r32(H + 0x50)
        claimed = (r32(H + 0xB0) - r32(H + 0xA8)) & 0xFFFFFFFF
        info, limit = r32(H + 0x3C), r32(H + 0x38)
        big, adj, n, i, seen = 0, 0, 0, r32(info + 4) if info else 0, set()
        while i and i not in seen and n < 20000:   # free clusters: heapinfo[i] = {size blocks, next, prev}
            seen.add(i)
            size = r32(info + 12 * i)
            big = max(big, size)
            if i + size == limit:
                adj = size
            i, n = r32(info + 12 * i + 4), n + 1
        tail = max(cap - claimed, 0)
        d.update({"capacity": cap, "bytes_used": used, "bytes_free_in_heap": free_in, "chunks_used": r32(H + 0x44),
                  "chunks_free": r32(H + 0x4C), "claimed": claimed, "unclaimed_tail": tail, "free_clusters": n,
                  "largest_cluster": big * 1024, "largest_possible": max(big * 1024, adj * 1024 + tail),
                  "total_free": free_in + tail})
        return d

    out = {"clock_ms": r32(r32(0x0050B734) + 0x38) if r32(0x0050B734) else None,
           "sector_pool": pool(0x006EB9C8), "sector_pool_2": pool(0x006EB9CC), "level_pool": pool(0x006EB9B8)}
    L = r32(0x005E5340)
    if L:                              # FUN_00154A68: queued loader requests (deque of 84-byte items)
        m = lambda x: (x * 0x3CF3CF3D & 0xFFFFFFFF) >> 2  # noqa: E731
        out["loader_queue"] = ((((r32(L + 0x38) - r32(L + 0x28)) & 0xFFFFFFFF) >> 2) - 1) * 6 + \
            m((r32(L + 0x2C) - r32(L + 0x30)) & 0xFFFFFFFF) + m((r32(L + 0x24) - r32(L + 0x1C)) & 0xFFFFFFFF)
    D = r32(0x0050CD4C)
    if not D:
        out["dict"] = None
        return out
    count, ents = r32(D + 0x84), r32(D + 0x88)
    n = min(count, 4096)               # dictionary entries (32 bytes): name hash, anim/model/texture ids, sizes
    if hasattr(p, "dump") and n:
        blob = p.dump(ents, 32 * n)
        raw = [list(struct.unpack_from("<8I", blob, 32 * k)) for k in range(n)]
    else:
        raw = [[r32(ents + 32 * k + 4 * j) for j in range(8)] for k in range(n)]
    size_of = {"anim": {}, "model": {}, "tex": {}}
    for e in raw:
        size_of["anim"][e[1]] = e[4]
        size_of["model"][e[2]] = e[6] or e[5] + 0x2000
        size_of["tex"][e[3]] = e[7] + 0x70
    trees = {"model": D + 0x00, "tex": D + 0x30, "anim": D + 0x40}
    out["dict"] = {"addr": hex(D), "count": count, "pin_flag_1B4": r32(D + 0x1B4), "loads_pending_C6C": r32(D + 0xC6C),
                   "state_BBC": r32(D + 0xBBC), "human_request_BC4": hex(r32(D + 0xBC4)),
                   "request_priorities": [struct.unpack("<f", struct.pack("<I", r32(D + o)))[0]
                                          for o in (0xBCC, 0xBDC, 0xBEC, 0xBFC)],
                   "pins": [(i, r32(D + 0xB4 + 8 * i), hex(r32(D + 0xB8 + 8 * i))) for i in range(32)
                            if r32(D + 0xB4 + 8 * i) != 0xFFFFFFFF]}
    out["dict"]["pins"] = [{"slot": i, "model_index": mi, "instance": inst,
                            "name": NAMES.get(raw[mi][0], hex(raw[mi][0])) if mi < len(raw) else "?"}
                           for i, mi, inst in out["dict"]["pins"]]
    evict = {}
    for k, t in trees.items():         # unreferenced (refcount 0) character components: what eviction could free
        nodes = walk(t)
        zero = [nd for nd in nodes if r32(r32(nd + 0x14) + 4) == 0]
        evict[k] = {"nodes": len(nodes), "unreferenced": len(zero),
                    "unreferenced_bytes_known": sum(size_of[k].get(r32(nd + 0x10), 0) for nd in zero)}
    out["character_trees"] = evict
    out["other_trees_nodes"] = {hex(o): len(walk(D + o)) for o in (0x10, 0x20, 0x50, 0x60)}
    G = r32(0x0051489C)
    level = r32(G + 0x14D8 + r16(G + 0x56DC) * 0x84) if G else -1
    off = 0x114 if 0 <= level - 60 < 5 else 0x112
    out["level"], out["model_field"] = level, hex(off)
    sp = out["sector_pool"] or {}
    cands = {}
    for cid, name, base in WARRIORS:
        mi = r16(0x00684620 + cid * 0x1AC + off)
        if mi >= count:
            cands[name] = {"char": cid, "model_index": hex(mi), "status": "no model index"}
            continue
        e = raw[mi]
        comp = {"anim": (trees["anim"], e[1], e[4]), "model": (trees["model"], e[2], e[6] or e[5] + 0x2000),
                "tex": (trees["tex"], e[3], e[7] + 0x70)}
        need, need_blocks, parts = 0, [], {}
        for k, (t, key, size) in comp.items():
            nd = lookup(t, key)
            parts[k] = {"id": hex(key), "bytes": size, "resident": bool(nd),
                        "refs": r32(r32(nd + 0x14) + 4) if nd else None}
            if not nd:
                need += size
                need_blocks.append(block(size))
        fits = None
        if sp.get("capacity") is not None and need_blocks:
            fits = max(need_blocks) <= sp["largest_possible"] and sum(need_blocks) <= sp["total_free"]
        cands[name] = {"char": cid, "model_index": mi, "name": NAMES.get(e[0], hex(e[0])), "parts": parts,
                       "missing_bytes": need, "fit_test_blocks": sum(need_blocks),
                       "fits_without_eviction": fits}
    out["warriors"] = cands
    live = [h for h in (r32(0x006EBD38 + 8 * s) for s in range(60)) if h]
    out["humans"] = {"live": len(live), "without_model_instance_D8": sum(1 for h in live if not r32(h + 0xD8))}
    out["w4p"] = {"choose_result": r32(0x000E15F0), "choose_status": [r32(0x000E15C0 + 4 * i) for i in range(9)],
                  "pin": [r32(0x000E1C00 + 4 * i) for i in range(24)],  # slot 0, codes, config, slot 1 (m6_chooser.md)
                  "config": [r32(0x000E1C40 + 4 * i) for i in range(3)]}
    return out


if __name__ == "__main__":
    sys.path.insert(0, os.path.join(os.getcwd(), "tools"))
    from pine import Pine
    print(json.dumps(survey_mem(Pine(int(sys.argv[1]))), indent=1, default=str))
