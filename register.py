"""Append forecast files to the hash-chained registry. Files stay in sealed/ (git-ignored) until resolution.
Usage: python3 register.py <resolves_on YYYY-MM-DD> "<truth source>" sealed/FILE.json [...]"""
import json, hashlib, sys, datetime
res, truth, files = sys.argv[1], sys.argv[2], sys.argv[3:]
lines = open("registry.jsonl").read().splitlines()
last = json.loads(lines[-1]); prev, seq = last["entry_hash"], last["seq"] + 1
now = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()
with open("registry.jsonl", "a") as out:
    for f in files:
        b = open(f, "rb").read()
        e = {"seq": seq, "file": f.split("/")[-1], "file_sha256": hashlib.sha256(b).hexdigest(),
             "canonical_sha256": hashlib.sha256(json.dumps(json.loads(b), sort_keys=True).encode()).hexdigest(),
             "registered_utc": now, "resolves_on": res, "truth_source": truth, "prev_hash": prev}
        e["entry_hash"] = hashlib.sha256(json.dumps(e, sort_keys=True).encode()).hexdigest()
        out.write(json.dumps(e, sort_keys=True) + "\n"); print(seq, e["file"], e["entry_hash"][:16])
        prev, seq = e["entry_hash"], seq + 1
