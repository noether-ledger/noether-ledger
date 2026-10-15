# Noether Ledger

Dated forecasts of financial line items, built from conserved physical quantities.

Noether's theorem ties every conservation law to a symmetry. The method here is accounting with conservation laws: pipeline gas in → gallons out; carbon captured → carbon stored; physical units × public rules × contract terms → dollars on an earnings release. Each forecast names its target, its 80% interval and its kill condition before the number is published.

## How it works
- `registry.jsonl` — append-only, hash-chained. Each entry holds the SHA-256 of a forecast file, the hash of its canonical JSON, the registration time (UTC), the resolution date and the source of truth. `entry_hash = sha256(json.dumps(entry_without_entry_hash, sort_keys=True))`; each entry carries the previous entry's hash.
- `proofs/` — OpenTimestamps proofs. They anchor the registry and each forecast file to Bitcoin. Verify with `ots verify`.
- Commit-reveal: forecast files are published on or after their resolution date. Before that, the registry fixes their content by hash. Anyone can check a revealed file against the registry with `python3 verify.py <folder>`.

## Entry format v2 (seq 15 onward)
Each entry registers two hashes: a **claim** file (target, interval or probability, kill condition), revealed at resolution, and an optional **method** file (inputs, sources, meter IDs), revealed only if a result is disputed. Both files carry a random 128-bit salt and a UTC creation time. `python3 register.py <resolves_on> "<truth source>" <name> claim.json [method.json]`.

## Data-line log (datalog.jsonl)
Every data file the forecasts rest on is content-addressed (SHA-256), grouped into data lines (L001…), sealed into one Merkle root per line per batch, and chained in `datalog.jsonl`. Each batch records the forecast registry head; each new forecast records the datalog head. Each batch is OpenTimestamped: `proofs/datalog/seq<N>.ots` stamps `datalog.jsonl` as it stood after seal N (verify against its first N+1 lines). Daily captures (builder sitemaps, line L022, from seq 1) seal one batch per day; a missed or blocked source is sealed as a gap leaf, not skipped.
- Public: roots, counts, bytes per line, chain hashes, a salted commitment to the private line registry.
- Private: the files and leaf lists. Any single file can be proven to have existed in a batch (`python3 datalog.py prove <sha256>`, verified by `python3 datalog.py verify proof.json`) without revealing any other file.
- Missed captures are logged as gap leaves, so absence is attested too.
- Batch 0 (2026-10-13) is a genesis import: it proves these files existed on that date, not when each was first captured (file mtimes are self-reported). Earlier OpenTimestamps proofs on some research docs are included as objects.

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
| 15 | Homebuilder delivered price, locked theta (MHO, CCS, BZH) | 2026-11-15 |
| 16 | Line map: binds forecast lines (no forecast) | — |

`register.py` appends entries. `proofs/registry_head_seq7.jsonl.ots` stamps the first 8 lines of the registry; `proofs/registry.jsonl.ots` stamps the current file.

## Forecast lines
Forecasts are filed by line: one folder per recurring measured series, `lines/<domain>/<entity>/<metric>/`.

| Line | Seq |
|---|---|
| biofuels/gpre/45z-credit | 1, 2, 6, 7, 14 |
| biofuels/gpre/crush-margin | 3, 4 |
| biofuels/gpre/eps | 5 |
| biofuels/gevo/45z-credit | 0, 9 |
| biofuels/gevo/rng-volume | 8 |
| biofuels/rex/45z-credit | 10 |
| biofuels/dgd/45z-credit | 11 |
| biofuels/valero/rd-45z | 12 |
| trade/census/uco-imports-ex-na | 13 |
| homebuilders/panel/delivered-price | 15 |

Each folder holds `LINE.json` (target, unit, cadence, truth source, data inputs as opaque data-log line IDs) and `chain.jsonl` (a hash chain over that line's registry entries). `lines/INDEX.json` lists every line head and a Merkle root over all heads.

Seq 0-15 were made before lines existed. `lines/legacy_map.json` assigns them; registry seq 16 (type `line_map`) binds the map hash and the lines root, so the assignment cannot change silently. From seq 17, each registry entry carries `line` and `line_prev`, so every line is a chain inside the global chain. A track record can be checked per line, not only in total.

`python3 verify.py` checks the registry chain, then the lines (`lines.py verify`).
`proofs/registry_head_seq15.jsonl.ots` stamps the first 16 lines of the registry.

Not investment advice. Forecasts are research records, not recommendations.

## Verify signatures
Commits are SSH-signed. `git config gpg.ssh.allowedSignersFile allowed_signers && git log --show-signature`.
