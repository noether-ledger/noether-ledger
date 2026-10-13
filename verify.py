"""Verify the Noether Ledger registry: hash chain, and (once revealed) claim and method files.
Usage: python3 verify.py            # chain only
       python3 verify.py sealed/    # chain + any files present in that folder"""
import json, hashlib, sys, os
sha = lambda b: hashlib.sha256(b).hexdigest()
prev = "0" * 64
d = sys.argv[1] if len(sys.argv) > 1 else None
for line in open("registry.jsonl"):
    e = json.loads(line); h = e.pop("entry_hash")
    assert e["prev_hash"] == prev, f"chain break at seq {e['seq']}"
    assert sha(json.dumps(e, sort_keys=True).encode()) == h, f"bad entry hash seq {e['seq']}"
    status = ["chain ok"]
    if d:
        p = os.path.join(d, e["file"])
        if os.path.exists(p):
            b = open(p, "rb").read()
            assert sha(b) == e["file_sha256"], f"claim/file mismatch seq {e['seq']}"
            assert sha(json.dumps(json.loads(b), sort_keys=True).encode()) == e["canonical_sha256"]
            status.append("file ok")
        if "method_file" in e and os.path.exists(os.path.join(d, e["method_file"])):
            assert sha(open(os.path.join(d, e["method_file"]), "rb").read()) == e["method_sha256"], f"method mismatch seq {e['seq']}"
            status.append("method ok")
    print(e["seq"], e["file"], e["registered_utc"], ", ".join(status))
    prev = h
print("head", prev)
