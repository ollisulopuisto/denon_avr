# Upstream 1.3.0 rebase, 25 Nov 2026

Base upstream tag v1.3.0: 87f3fb3a86313d481ae18507cddf7fcd569fff0c.
Fork main: 23a015d. Released home: 2c319ff (v1.1.3).
The branch merges fork-main ancestry for a conflict-free PR, while porting behavior to upstream's split protocol/service architecture.

## Home behavior
- X3600H fallback tokens: Dolby Surround -> DOLBY DIGITAL, Neural:X -> DTS SURROUND, Multi In + DSur -> M CH IN+DSUR.
- Surround (SUA) None option and availability after selecting None; front sizes unchanged.
- Read volume raw/100, set level*100 rounded to half steps. The receiver limit still caps sends.

None of these three behaviors was already present upstream.

## Bolt optimization ledger
All 12 historical optimization commits are ported. None is discarded as not applicable or claimed already upstream.

| Old commit | Optimization | Status and new owner |
| --- | --- | --- |
| 858f785 | Bucket Telnet matchers; compile sound-mode regex | Ported: protocol/telnet_parser.py, longest-prefix order preserved within buckets |
| e832409 | Index XML feature blocks | Ported: protocol/deviceinfo.py shared first-block index |
| 3555203 | Consolidate XML scans; set-based fallback source deduplication | Ported: protocol/deviceinfo.py |
| 6508a11 | Precompute refresh trigger tuples | Ported: services/sync.py; retains new changed-state/refresh behavior |
| 014b07b | UPnP local-tag fast path and early exit after five fields | Ported: protocol/upnp.py |
| b12bb21 | Cache speaker grammar | Ported, adapted to new presence/size/count grammar rather than old double-token model |
| 5d21846 | Index controls by scope/group/feature | Ported: protocol/profile.py; accessors return fresh lists |
| b18b6fe | Single-pass Deviceinfo tree indexing | Ported: protocol/deviceinfo.py, including new QuickSelect and SubwooferLevel consumers |
| d54a5cf | Volume Param iterator; one-strip labels | Ported: protocol/deviceinfo.py |
| ed31229 | Two-character dispatch gates; cache level reference/terminator | Ported: protocol/telnet_parser.py; new upstream prefix precedence retained |
| d6d8c9a | Cache static resync queries; set-based deduplication | Ported: protocol/commands.py and services/sync.py. Preserve upstream's zone-before-readonly order; dynamic zones/features remain live |
| 23a015d | Source/channel lookup indexes | Ported: avr/models.py; parser rename explicitly invalidates; list append/replacement rebuilds. Derived caches stay out of dataclass serialization |

## Tests and review
- Ten focused Bolt cases: six fail on pre-port 37ac1eb, all ten pass after port.
- Full suite: 293 passed with Python 3.13, `python -m pytest -p no:anyio`.
- Existing characterization and catalogue goldens unchanged by the optimization port. Earlier home-volume port changed only four command values (MV50/Z250 for the two 0.5 test requests).
- Added checks for index reuse, serialization boundaries, first-match lookup semantics, source rename/visibility/append/replacement, channel replacement, profile-copy safety, prefix bucket order, dynamic resync state, all XML consumers, one full Deviceinfo scan and UPnP early exit.
- Traced discovery service list replacement, fallback source assignment, parser source upsert, media/player/select consumers and StateSync notification fingerprints. No runtime profile mutation in production call sites found. Source/channel descriptors changed externally in place require explicit invalidation, as on the original fork.
- CodeQL upstream warning logged MAC/serial-derived entity IDs. Removed identifier arguments and retained the warning; failing-first AST guard retained.

## Local microbenchmarks
Same Python 3.13 environment, recorded AVR-X3600H fixture, seven repetitions per case, median microseconds per operation. Before is 37ac1eb; after is this port. These are local measurements, not receiver latency or CI guarantees.

| Operation | Before us | After us |
| --- | ---: | ---: |
| Deviceinfo parse | 1610.745 | 1097.798 |
| UPnP parse | 90.555 | 91.613 |
| Core-profile lookup | 2.598 | 0.093 |
| Resync query construction | 34.965 | 16.083 |
| 240-line Telnet replay | 419.091 | 368.034 |
| Source lookup | 0.387 | 0.106 |

UPnP shows no measurable benefit on this small fixture (about 1% slower in this sample); early-exit correctness and reduced traversal on trailing nodes are tested. No unsupported speedup claim.

## Limits and boundaries
No installed Home Assistant or real receiver acceptance. Other historical nonperformance tuner/IMAX/button/standby/power-on changes are not asserted equivalent by this focused rebase.
Existing fork sync-upstream.yml remains byte-identical; upstream tests.yaml was imported unchanged and previously flagged. No custom workflow, credential, database or crypto edits. Manifest 1.3.1 is preparation only.
No merge, release, tag or HA deployment.
