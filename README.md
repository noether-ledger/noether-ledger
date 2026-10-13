# Noether Ledger

Dated forecasts of financial line items, built from conserved physical quantities.

Noether's theorem ties every conservation law to a symmetry. The method here is accounting with conservation laws: pipeline gas in → gallons out; carbon captured → carbon stored; physical units × public rules × contract terms → dollars on an earnings release. Each forecast names its target, its 80% interval and its kill condition before the number is published.

## How it works
- `registry.jsonl` — append-only, hash-chained. Each entry holds the SHA-256 of a forecast file, the hash of its canonical JSON, the registration time (UTC), the resolution date and the source of truth. `entry_hash = sha256(json.dumps(entry_without_entry_hash, sort_keys=True))`; each entry carries the previous entry's hash.
- `proofs/` — OpenTimestamps proofs. They anchor the registry and each forecast file to Bitcoin. Verify with `ots verify`.
- Commit-reveal: forecast files are published on or after their resolution date. Before that, the registry fixes their content by hash. Anyone can check a revealed file against the registry with `python3 verify.py <folder>`.

## Entry format v2 (seq 15 onward)
Each entry registers two hashes: a **claim** file (target, interval or probability, kill condition), revealed at resolution, and an optional **method** file (inputs, sources, meter IDs), revealed only if a result is disputed. Both files carry a random 128-bit salt and a UTC creation time. `python3 register.py <resolves_on> "<truth source>" <name> claim.json [method.json]`.

## Scoring
Every interval is scored as hit or miss at resolution. Probabilities are scored by log score. Misses stay in the ledger. Amendments are new entries; nothing is edited or deleted.

## Open entries
| seq | Target | Resolves |
|---|---|---|
| 0 | Gevo Q3 2026 45Z credits (GevoND) | 2026-11-15 |
| 1 | Green Plains Q3 2026 45Z net value (H0) | 2026-11-15 |
| 2 | Green Plains Q3 2026 45Z net value (rebuilt, plant-split) | 2026-11-15 |
| 3 | Green Plains Q3 2026 crush margin | 2026-11-15 |
| 4 | Green Plains Q3 2026 crush margin ex-45Z | 2026-11-15 |
| 5 | Green Plains Q3 2026 adjusted EPS | 2026-11-15 |
| 6 | Green Plains Nebraska capture-ceiling claim | 2026-11-15 |
| 7 | Green Plains 2026 credit sale vs booked value | 2027-03-31 |
| 8 | Gevo Q3 2026 RNG production (pipeline meter) | 2026-11-15 |
| 9 | Gevo 2026 emissions-factor bucket | 2026-11-15 |
| 10 | REX fiscal Q3 2026 45Z per gallon | 2026-12-15 |
| 11 | Diamond Green Diesel Q3 2026 45Z per gallon (feedstock origin) | 2026-11-15 |
| 12 | Valero Q3 2026 renewable diesel 45Z | 2026-11-15 |
| 13 | Census Sep 2026 non-North-American UCO imports | 2026-11-06 |
| 14 | Amendment: disclosed defect in seq 1 (scored as sealed) | — |

`register.py` appends entries. `proofs/registry_head_seq7.jsonl.ots` stamps the first 8 lines of the registry; `proofs/registry.jsonl.ots` stamps the current file.

Not investment advice. Forecasts are research records, not recommendations.

## Verify signatures
Commits are SSH-signed. `git config gpg.ssh.allowedSignersFile allowed_signers && git log --show-signature`.
