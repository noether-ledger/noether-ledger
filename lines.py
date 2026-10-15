"""Forecast lines: the registry organized as folders, one folder per recurring measured series.

Layout (public):
  lines/<domain>/<entity>/<metric>/LINE.json   definition: target series, unit, cadence, truth source, data inputs
  lines/<domain>/<entity>/<metric>/chain.jsonl per-line hash chain over its registry entries (generated)
  lines/legacy_map.json                        line assignment for seq 0-15 (made before lines existed)
  lines/INDEX.json                             every line's head + Merkle root over all lines (generated)

Binding: a registry entry of type "line_map" records sha256(legacy_map.json) and the lines root.
From seq 17 on, every registry entry names its "line" and "line_prev" (previous entry hash in that line),
so each line is a chain inside the global chain. Method details stay sealed; LINE.json names data inputs
only by opaque data-log line IDs.

  python3 lines.py build    # regenerate chain.jsonl files and INDEX.json from registry.jsonl
  python3 lines.py verify   # recompute and compare; check the line_map binding and line_prev links"""
import json, hashlib, sys, os, glob
H = lambda b: hashlib.sha256(b).hexdigest()
canon = lambda d: json.dumps(d, sort_keys=True, separators=(",", ":"))
ROOT = "lines"

def merkle(leaves):
    if not leaves: return "0" * 64
    lv = [bytes.fromhex(x) for x in leaves]
    while len(lv) > 1:
        nx = [hashlib.sha256(b"\x01" + lv[i] + lv[i + 1]).digest() for i in range(0, len(lv) - 1, 2)]
        if len(lv) % 2: nx.append(lv[-1])
        lv = nx
    return lv[0].hex()

def defined_lines():
    out = {}
    for p in sorted(glob.glob(f"{ROOT}/*/*/*/LINE.json")):
        d = json.load(open(p)); lid = os.path.relpath(os.path.dirname(p), ROOT)
        assert d["id"] == lid, f"LINE.json id {d['id']} != folder {lid}"
        out[lid] = d
    return out

def registry(): return [json.loads(l) for l in open("registry.jsonl")]

def kind(e):
    if e.get("type"): return e["type"]
    if e["file"].startswith("AMEND_"): return "amendment"
    return "forecast"

def compute(upto=None):
    """Per-line chains from the registry. upto: only entries with seq < upto."""
    lines = defined_lines()
    lmap = json.load(open(f"{ROOT}/legacy_map.json"))["assign"]
    chains = {lid: [] for lid in lines}
    for e in registry():
        if upto is not None and e["seq"] >= upto: break
        if kind(e) == "line_map": continue
        lid = e.get("line") or lmap.get(str(e["seq"]))
        assert lid, f"seq {e['seq']} has no line"
        assert lid in lines, f"seq {e['seq']} names undefined line {lid}"
        c = chains[lid]
        r = {"line": lid, "n": len(c), "registry_seq": e["seq"], "registry_entry_hash": e["entry_hash"],
             "kind": kind(e), "file": e.get("file"), "resolves_on": e.get("resolves_on"),
             "line_prev": c[-1]["hash"] if c else "0" * 64}
        if "resolves_seq" in e: r["resolves_seq"] = e["resolves_seq"]
        if "line_prev" in e:
            assert e["line_prev"] == r["line_prev"], f"seq {e['seq']}: line_prev does not match head of {lid}"
        r["hash"] = H(canon(r).encode()); c.append(r)
    if upto is not None:   # historical root: only lines that had entries before seq `upto` (later-defined lines did not exist then)
        chains = {lid: c for lid, c in chains.items() if c}
    index = {}
    for lid, c in chains.items():
        res = {x["resolves_seq"] for x in c if x["kind"] == "resolution"}
        fc = [x for x in c if x["kind"] == "forecast"]
        index[lid] = {"head": c[-1]["hash"] if c else "0" * 64, "entries": len(c),
                      "forecasts": len(fc), "open": sum(x["registry_seq"] not in res for x in fc),
                      "resolved": len(res)}
    root = merkle([H(b"\x00" + canon({"line": k, "head": v["head"]}).encode()) for k, v in sorted(index.items())])
    return chains, {"lines": index, "lines_root": root,
                    "legacy_map_sha256": H(open(f"{ROOT}/legacy_map.json", "rb").read())}

def render(chains, idx):
    files = {f"{ROOT}/{lid}/chain.jsonl": "".join(canon(r) + "\n" for r in c) for lid, c in chains.items()}
    files[f"{ROOT}/INDEX.json"] = json.dumps(idx, indent=1, sort_keys=True) + "\n"
    return files

def build():
    for p, s in render(*compute()).items(): open(p, "w").write(s)
    print("built", len(defined_lines()), "lines")

def verify():
    for p, s in render(*compute()).items():
        assert os.path.exists(p) and open(p).read() == s, f"{p} does not match registry (run lines.py build)"
    maps = [e for e in registry() if kind(e) == "line_map"]
    assert maps, "no line_map entry in registry"
    for m in maps:
        _, idx = compute(upto=m["seq"])
        assert m["lines_root"] == idx["lines_root"], f"line_map seq {m['seq']}: lines root mismatch"
    last = maps[-1]
    assert last["map_sha256"] == H(open(f"{ROOT}/legacy_map.json", "rb").read()), "legacy_map.json changed after binding"
    for e in registry():
        if e["seq"] > last["seq"] and kind(e) != "line_map":
            assert "line" in e and "line_prev" in e, f"seq {e['seq']} registered without a line"
    _, idx = compute()
    for lid, v in sorted(idx["lines"].items()):
        print(f"{lid:42s} {v['forecasts']:2d} forecasts {v['open']:2d} open  head {v['head'][:12]}")
    print("lines ok, root", idx["lines_root"])

def head(lid):
    chains, _ = compute(); assert lid in chains, f"undefined line {lid}"
    return chains[lid][-1]["hash"] if chains[lid] else "0" * 64

if __name__ == "__main__":
    {"build": build, "verify": verify}[sys.argv[1]]()
