"""Append entries to the hash-chained registry. Sealed files stay in sealed/ (git-ignored) until resolution.

v2 (seq >= 15): each entry is a public CLAIM file plus an optional private METHOD file.
  python3 register.py <resolves_on YYYY-MM-DD> "<truth source>" <name> <claim_draft.json> [method_draft.json]
  - claim: target, point/interval or claim, kill condition. Revealed at resolution.
  - method: inputs, data sources, meter IDs. Revealed only if a result is disputed (its hash is public now).
  - Each sealed file gets a random 128-bit salt and made_utc, so hashes cannot be guessed and carry no local time zone.
v1 (seq 0-14): single forecast file; see registry."""
import json, hashlib, sys, datetime, secrets, os

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

def main():
    res, truth, name, claim = sys.argv[1:5]
    method = sys.argv[5] if len(sys.argv) > 5 else None
    lines = open("registry.jsonl").read().splitlines()
    last = json.loads(lines[-1])
    now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
    cf = f"{name}.claim.json"; cb = seal(claim, f"sealed/{cf}", now)
    e = {"v": 2, "seq": last["seq"] + 1, "file": cf, "file_sha256": sha(cb), "canonical_sha256": canon(json.loads(cb)),
         "registered_utc": now, "resolves_on": res, "truth_source": truth, "prev_hash": last["entry_hash"]}
    if method:
        mf = f"{name}.method.json"; mb = seal(method, f"sealed/{mf}", now)
        e.update({"method_file": mf, "method_sha256": sha(mb)})
    e["entry_hash"] = canon(e)
    with open("registry.jsonl", "a") as out: out.write(json.dumps(e, sort_keys=True) + "\n")
    print(e["seq"], cf, e.get("method_file", "-"), e["entry_hash"][:16])

if __name__ == "__main__": main()
