"""Noether Ledger — data-line log. Every captured data file is content-addressed, grouped by data line,
sealed into per-line Merkle roots, and chained into datalog.jsonl (public). Contents stay private.

Store layout (private, default ~/research/noether-data):
  objects/ab/abcdef...            content-addressed copies (sha256)
  leaves/pending.jsonl            leaves not yet sealed
  leaves/batch-<seq>.jsonl        leaves of each sealed batch (needed for inclusion proofs)
  lines.json                      private line registry {label: {name, source, cadence, salt}}
Public (in the repo): datalog.jsonl, proofs/datalog.jsonl.ots

Commands:
  python3 datalog.py ingest <LINE> <source-tag> <file-or-dir> [...]   copy + record leaves (skips secrets)
  python3 datalog.py gap <LINE> <reason>                               attest a missed capture (absence is logged too)
  python3 datalog.py seal                                              seal pending leaves into a chained entry
  python3 datalog.py prove <sha256>                                    inclusion proof for one object
  python3 datalog.py verify [<proof.json>]                             verify the chain (and a proof)
"""
import hashlib, json, os, sys, shutil, datetime, secrets, fnmatch, subprocess
STORE = os.environ.get("NOETHER_DATA", os.path.expanduser("~/research/noether-data"))
REPO = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(REPO, "datalog.jsonl")
SECRET_PATTERNS = ["*.key", ".key", "*.pem", "*id_ed25519*", ".env", "*secret*", "*token*", "*credential*"]
H = lambda b: hashlib.sha256(b).hexdigest()
now = lambda: datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
def canon(d): return json.dumps(d, sort_keys=True, separators=(",", ":"))

def merkle(leaves):
    """leaves: list of hex leaf hashes (sorted). Returns (root, levels). Odd node is promoted (not duplicated)."""
    if not leaves: return H(b""), [[]]
    level = [bytes.fromhex(x) for x in leaves]; levels = [level]
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            nxt.append(hashlib.sha256(b"\x01" + level[i] + level[i + 1]).digest() if i + 1 < len(level) else level[i])
        level = nxt; levels.append(level)
    return level[0].hex(), levels

def leaf_hash(rec): return H(b"\x00" + canon(rec).encode())

def lines():
    p = os.path.join(STORE, "lines.json")
    return json.load(open(p)) if os.path.exists(p) else {}

def ingest(line, tag, paths):
    L = lines()
    if line not in L: sys.exit(f"unknown line {line}; add it to {STORE}/lines.json first")
    os.makedirs(os.path.join(STORE, "leaves"), exist_ok=True)
    n = 0; skipped = 0
    with open(os.path.join(STORE, "leaves", "pending.jsonl"), "a") as out:
        for p in paths:
            files = [p] if os.path.isfile(p) else [os.path.join(r, f) for r, _, fs in os.walk(p) for f in fs]
            for f in sorted(files):
                base = os.path.basename(f)
                if any(fnmatch.fnmatch(base, pat) for pat in SECRET_PATTERNS) or os.path.islink(f):
                    skipped += 1; continue
                b = open(f, "rb").read(); h = H(b)
                dst = os.path.join(STORE, "objects", h[:2], h)
                if not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copyfile(f, dst)
                rec = {"line": line, "sha256": h, "bytes": len(b), "path": os.path.relpath(f, p) if os.path.isdir(p) else base,
                       "source": tag, "file_mtime_utc": datetime.datetime.fromtimestamp(os.path.getmtime(f), datetime.timezone.utc).replace(microsecond=0).isoformat(),
                       "ingested_utc": now(), "kind": "object"}
                out.write(canon(rec) + "\n"); n += 1
    print(f"{line}: {n} leaves pending, {skipped} skipped (secrets/links)")

def gap(line, reason):
    os.makedirs(os.path.join(STORE, "leaves"), exist_ok=True)
    rec = {"line": line, "kind": "gap", "reason": reason, "ingested_utc": now()}
    open(os.path.join(STORE, "leaves", "pending.jsonl"), "a").write(canon(rec) + "\n"); print("gap recorded")

def read_log():
    return [json.loads(l) for l in open(LOG)] if os.path.exists(LOG) else []

def seal():
    pend = os.path.join(STORE, "leaves", "pending.jsonl")
    if not os.path.exists(pend) or os.path.getsize(pend) == 0: sys.exit("nothing pending")
    recs = [json.loads(l) for l in open(pend)]
    log = read_log(); seq = len(log); prev = log[-1]["entry_hash"] if log else "0" * 64
    by = {}
    for r in recs: by.setdefault(r["line"], []).append(r)
    per = {}
    for line, rs in sorted(by.items()):
        hs = sorted(leaf_hash(r) for r in rs)
        root, _ = merkle(hs)
        per[line] = {"root": root, "leaves": len(rs), "objects": sum(1 for r in rs if r["kind"] == "object"),
                     "gaps": sum(1 for r in rs if r["kind"] == "gap"), "bytes": sum(r.get("bytes", 0) for r in rs)}
    groot, _ = merkle(sorted(v["root"] for v in per.values()))
    L = lines()
    reg_commit = H(canon({k: {"name": v["name"], "salt": v["salt"]} for k, v in L.items()}).encode())
    try: commit = subprocess.run(["git", "-C", REPO, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except Exception: commit = None
    reg = os.path.join(REPO, "registry.jsonl")
    fhead = json.loads(open(reg).read().splitlines()[-1])["entry_hash"] if os.path.exists(reg) else None
    e = {"seq": seq, "sealed_utc": now(), "lines": per, "global_root": groot, "line_registry_commitment": reg_commit,
         "forecast_registry_head": fhead, "code_commit": commit, "prev_hash": prev}
    e["entry_hash"] = H(canon(e).encode())
    open(LOG, "a").write(canon(e) + "\n")
    shutil.move(pend, os.path.join(STORE, "leaves", f"batch-{seq}.jsonl"))
    print(f"sealed seq {seq}: {len(per)} lines, {len(recs)} leaves, global_root {groot[:16]}…, entry {e['entry_hash'][:16]}…")

def prove(sha):
    for e in read_log():
        bf = os.path.join(STORE, "leaves", f"batch-{e['seq']}.jsonl")
        if not os.path.exists(bf): continue
        recs = [json.loads(l) for l in open(bf)]
        hit = [r for r in recs if r.get("sha256") == sha]
        if not hit: continue
        r = hit[0]; line = r["line"]
        hs = sorted(leaf_hash(x) for x in recs if x["line"] == line)
        path = path_for(hs, leaf_hash(r))
        lroots = sorted(v["root"] for v in e["lines"].values())
        gpath = path_for(lroots, e["lines"][line]["root"])
        proof = {"leaf": r, "line_path": path, "global_path": gpath, "seq": e["seq"], "entry_hash": e["entry_hash"]}
        print(json.dumps(proof, indent=1)); return
    sys.exit("not found")

def path_for(hs, target):
    idx = hs.index(target); _, levels = merkle(hs); out = []
    for lvl in levels[:-1]:
        sib = idx ^ 1
        if sib < len(lvl): out.append({"side": "L" if sib < idx else "R", "h": lvl[sib].hex()})
        idx //= 2
    return out

def fold(h, path):
    x = bytes.fromhex(h)
    for s in path:
        o = bytes.fromhex(s["h"]); x = hashlib.sha256(b"\x01" + (o + x if s["side"] == "L" else x + o)).digest()
    return x.hex()

def verify(proof_file=None):
    prev = "0" * 64
    for e in read_log():
        eh = e.pop("entry_hash"); assert e["prev_hash"] == prev, f"chain break at {e['seq']}"
        assert H(canon(e).encode()) == eh, f"bad entry hash {e['seq']}"
        assert merkle(sorted(v["root"] for v in e["lines"].values()))[0] == e["global_root"], f"bad global root {e['seq']}"
        prev = eh
    print("datalog chain ok, head", prev)
    if proof_file:
        p = json.load(open(proof_file)); e = [x for x in read_log() if x["seq"] == p["seq"]][0]
        lr = fold(leaf_hash(p["leaf"]), p["line_path"]); assert lr == e["lines"][p["leaf"]["line"]]["root"], "line path fails"
        assert fold(lr, p["global_path"]) == e["global_root"], "global path fails"
        print("inclusion proof ok:", p["leaf"]["sha256"][:16], "in line", p["leaf"]["line"], "seq", p["seq"])

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    if c == "ingest": ingest(sys.argv[2], sys.argv[3], sys.argv[4:])
    elif c == "gap": gap(sys.argv[2], " ".join(sys.argv[3:]))
    elif c == "seal": seal()
    elif c == "prove": prove(sys.argv[2])
    elif c == "verify": verify(sys.argv[2] if len(sys.argv) > 2 else None)
    else: print(__doc__)
