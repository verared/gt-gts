# Time synchronisation and clock quality

Part of the **Gerarion** reference suite (verared/gerarion `v3.2.0`,
Gerarion Universal Standard). This directory is an **export package**
ready to be published (or consumed) as the `verared/gt-gts` satellite
repository; it keeps the base repository's relative layout so modules
compose cleanly.

## The unique problem it solves

The clock trust state machine (VERIFIED → HOLDOVER → UNVERIFIED → REJECTED), persistent anti-rollback anchors, and the experimental Roughtime profile.

## Normative status

- **Estable (núcleo) / Experimental (Roughtime)** — baseline `v3.2.0` (frozen arithmetic and vectors:
  GUS v3.0.0).
- Included specification(s): `docs/specs/GTS.es.md`, `docs/specs/GTS.en.md`

## Dependencies

- `gt-core` (*verared/gt-core*): tipos base y servicios del núcleo.
Common base: `verared/gerarion` `3.2.0`.
- *Note:* the experimental Roughtime profile imports `gerarion.interop` (gt-interop) for the GUS-3339 profile.

## Contents

- `LICENSE`
- `NOTICE`
- `docs/specs/GTS.en.md`
- `docs/specs/GTS.es.md`
- `impl-c/clock/gus_clock.c`
- `impl-c/clock/gus_clock.h`
- `src/gerarion/gts/__init__.py`
- `src/gerarion/gts/clock.py`
- `src/gerarion/gts/roughtime.py`

## Offline usage

No network, accounts, package registries, or frameworks required:

```bash
python3 -c 'import sys; sys.path.insert(0, "src"); import gerarion'
```

## Verification

With Python ≥ 3.9 and `reuse` installed:

```bash
reuse lint                                    # licensing 100 %
# (las pruebas viven en la suite de verared/gerarion)
```

## Synchronisation contract with `verared/gerarion`

This package is **generated, never hand-edited**: it is regenerated
byte for byte from `verared/gerarion v3.2.0` with
`python3 tools/export_module.py --module gt-gts --out <dir>`. The
normative source of truth (specifications, CC0 vectors, reference
cores for the three platforms, and the full test suite) stays in
`verared/gerarion`; `verared/gt-gts` satellites consume it and never fork the
arithmetic. Updates flow by regenerating the export from a tag of the
base repository — never by editing exported files.
