"""Verify the Noether Ledger registry: hash chain, and (once revealed) forecast files.
Usage: python3 verify.py            # chain only
       python3 verify.py sealed/    # chain + files in that folder"""
import json, hashlib, sys, os
prev = "0" * 64
d = sys.argv[1] if len(sys.argv) > 1 else None
for line in open("registry.jsonl"):
    e = json.loads(line); h = e.pop("entry_hash")
    assert e["prev_hash"] == prev, f"chain break at seq {e['seq']}"
    assert hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest() == h, f"bad entry hash seq {e['seq']}"
    status = "chain ok"
    if d and os.path.exists(os.path.join(d, e["file"])):
        b = open(os.path.join(d, e["file"]), "rb").read()
        assert hashlib.sha256(b).hexdigest() == e["file_sha256"], f"file mismatch seq {e['seq']}"
        assert hashlib.sha256(json.dumps(json.loads(b), sort_keys=True).encode()).hexdigest() == e["canonical_sha256"]
        status += ", file ok"
    print(e["seq"], e["file"], e["registered_utc"], status)
    prev = h
print("head", prev)
