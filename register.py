"""Append entries to the hash-chained registry. Sealed files stay in sealed/ (git-ignored) until resolution.

v2 (seq >= 15): each entry is a public CLAIM file plus an optional private METHOD file.
  python3 register.py <resolves_on YYYY-MM-DD> "<truth source>" <name> <claim_draft.json> [method_draft.json]
  - claim: target, point/interval or claim, kill condition. Revealed at resolution.
  - method: inputs, data sources, meter IDs. Revealed only if a result is disputed (its hash is public now).
  - Each sealed file gets a random 128-bit salt and made_utc, so hashes cannot be guessed and carry no local time zone.
v1 (seq 0-14): single forecast file; see registry.

v3 (seq >= 17): every entry names its forecast line (a folder under lines/, see lines.py).
  python3 register.py <line> <resolves_on YYYY-MM-DD> "<truth source>" <name> <claim_draft.json> [method_draft.json]
  The entry records "line" and "line_prev" (head of that line), so each line is a chain inside the global chain.
  python3 register.py --map      # bind lines/legacy_map.json and the current lines root (type "line_map")
After any registration run: python3 lines.py build."""
import json, hashlib, sys, datetime, secrets, os
import lines as L

def sha(b): return hashlib.sha256(b).hexdigest()
def canon(d): return sha(json.dumps(d, sort_keys=True).encode())

def seal(draft_path, out_path, now):
    d = json.load(open(draft_path))
    for k in list(d):
        if k in ("made", "salt", "made_utc"): d.pop(k)          # no local-time stamps, fresh salt
    d["salt"], d["made_utc"] = secrets.token_hex(16), now
    b = json.dumps(d, sort_keys=True).encode()
    if os.path.exists(out_path): sys.exit(f"refusing to overwrite {out_path}")
    open(out_path, "wb").write(b)
    return b

def append(e):
    e["entry_hash"] = canon(e)
    with open("registry.jsonl", "a") as out: out.write(json.dumps(e, sort_keys=True) + "\n")

def datalog_head():
    if os.path.exists("datalog.jsonl"):
        return json.loads(open("datalog.jsonl").read().splitlines()[-1])["entry_hash"]

def bind_map(last, now):
    _, idx = L.compute()
    e = {"v": 3, "seq": last["seq"] + 1, "type": "line_map", "file": "lines/legacy_map.json",
         "map_sha256": sha(open("lines/legacy_map.json", "rb").read()), "lines_root": idx["lines_root"],
         "n_lines": len(idx["lines"]), "registered_utc": now, "prev_hash": last["entry_hash"]}
    if datalog_head(): e["datalog_head"] = datalog_head()
    append(e); print(e["seq"], "line_map", e["lines_root"][:16], e["entry_hash"][:16])

def main():
    lines = open("registry.jsonl").read().splitlines()
    last = json.loads(lines[-1])
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    if sys.argv[1] == "--map": return bind_map(last, now)
    line, res, truth, name, claim = sys.argv[1:6]
    method = sys.argv[6] if len(sys.argv) > 6 else None
    if line not in L.defined_lines(): sys.exit(f"undefined line {line}: create lines/{line}/LINE.json first")
    cf = f"{name}.claim.json"; cb = seal(claim, f"sealed/{cf}", now)
    e = {"v": 3, "seq": last["seq"] + 1, "line": line, "line_prev": L.head(line), "file": cf, "file_sha256": sha(cb), "canonical_sha256": canon(json.loads(cb)),
         "registered_utc": now, "resolves_on": res, "truth_source": truth, "prev_hash": last["entry_hash"]}
    if datalog_head(): e["datalog_head"] = datalog_head()   # data vintage this forecast was made on
    if method:
        mf = f"{name}.method.json"; mb = seal(method, f"sealed/{mf}", now)
        e.update({"method_file": mf, "method_sha256": sha(mb)})
    append(e)
    print(e["seq"], line, cf, e.get("method_file", "-"), e["entry_hash"][:16])

if __name__ == "__main__": main()
