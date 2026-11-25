# Upstream1.3.0 rebase, 25 Nov 2026

Base upstream tag v1.3.0 is87f3fb3a86313d481ae18507cddf7fcd569fff0c.
Fork main was23a015d; released home was2c319ff(v1.1.3).
Reconstructed atop upstream rather than replaying stale pre-refactor files.

## Carried behavior
- X3600H sound fallback tokens: Dolby Surround -> DOLBY DIGITAL, Neural:X -> DTS SURROUND, Multi In + DSur -> M CH IN+DSUR.
- Surround(SUA) None option, with availability retained after selecting None; front sizes unchanged.
- Read volume raw/100, set level*100 rounded to half steps, receiver limit caps sending. New control service owns conversion.

These three behaviors were NOT already in upstream1.3.0. Old fork also has
older tuner/IMAX/button/standby/power-on/logging commits; broad feature
parity for those was not established by this focused request. Do not claim
all historical fork extras survived; this PR preserves the explicitly
requested X3600H/volume behaviors and keeps upstream1.3.0 otherwise.

## Tests/review
Six focused cases failed5/pass1 before port, then6/6pass. Full suite282pass.
Only four golden command values change: main0.5 -> MV50 on both fixtures,
zone2 0.5 -> Z250 on both. Limits still cap high requests to MV60 in test.
Own adversarial review traced media-player read and control-service send,
profile token consumer, speaker-select options/current value/availability.
No real receiver or installed Home Assistant acceptance performed.

## Workflow boundary
Existing fork sync-upstream.yml retained byte-identical; upstream adds its
read-only tests.yaml and requirements_test.txt. No custom workflow edits,
credential, database or crypto edits. Manifest1.3.1 is release-preparing only.
No merge, release, tag or HA deployment authorized.

## Fork-main mergeability repair
Merged fork main23a015d into this PR branch to reconcile ancestry. Conflict
resolution keeps the upstream1.3.0 refactor and requested home patch behavior.
Older fork-main Bolt cache/dispatch/resync optimizations are not restored on
top of a different architecture. Their old test_parser.py belongs to the
pre-refactor parser; upstream's current characterization suite is retained.
CodeQL found an upstream warning logging MAC/serial-derived entity IDs;
removed those values, kept the warning, added a failing-first AST regression.
No branch protection changes or PR merge.
