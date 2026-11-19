# GTS Specification — Time Synchronisation and Clock Quality

- **Status:** Core stable (§6.3); Roughtime profile **Experimental** ·
  **Version:** 1.0.0 · **Baseline:** GUS v3.1.1
- **Consolidated edition:** [`../en/gus-3.0.0.md`](../en/gus-3.0.0.md) (§9.4, time layers) ·
  Profile: [`../en/profiles/gus-roughtime-profile.md`](../en/profiles/gus-roughtime-profile.md)
- **License:** CC-BY-4.0 · Maintained by: verared contributors

## 1. Scope

How a device obtains, evaluates and maintains the **quality of its time**
before signing or emitting anything: the trust state machine, uncertainty,
persistent anti-rollback anchors, and the optional Roughtime
synchronisation profile. It does not cover the stamp format (GUS), the
TCJ definition, or event sealing (GST).

## 2. Normative rules

1. **Structural clock separation:** interval measurement uses the OS
   monotonic clock (`time.monotonic_ns()` / `CLOCK_MONOTONIC`); absolute
   time comes from an authenticated source (CLOCK_TAI, GNSS, authenticated
   NTP, signed links). They are never conflated.
2. **State machine** for every reading — a `VERIFIED` state is never
   emitted silently:
   - `VERIFIED`: authenticated source present and `uncertainty_ns ≤
     max_uncertainty_ns`.
   - `HOLDOVER`: source lost, but a prior trusted anchor exists within
     `max_holdover_s`; extrapolation uses the monotonic delta and
     uncertainty grows per `drift_ppm`.
   - `UNVERIFIED`: no trusted source, unknown uncertainty or expired
     window (strict policy degrades it to `REJECTED`).
   - `REJECTED`: the clock went backwards against the last persisted
     anchor (rollback, compared as the `(instant, nanos)` tuple), or
     strict policy demands it.
3. **Explicit source authenticity:** the reading declares
   `authenticated`; a policy with `require_authenticated` never promotes
   an unauthenticated reading (or one outside the `trusted_sources`
   allow-list) to `VERIFIED`, even with a zero uncertainty bound.
4. **Anti-rollback persistence:** the anchor store keeps the last anchor
   with atomic writes (temp + rename + fsync). A reboot does NOT repair
   a backwards step: comparison also runs against the on-disk anchor.
   Corrupt persisted state fails closed.
5. **Roughtime profile (experimental):** an external witness bounds the
   claimed instant within `[midpoint − radius, midpoint + radius]` with
   a nonce bound to the bundle. It never proves the truth of the
   instant; it only bounds its existence in time.

## 3. Sources of truth

| Platform | Implementation |
|---|---|
| Python | `src/gerarion/gts/clock.py`, `src/gerarion/gts/roughtime.py` |
| C11 | `impl-c/clock/gus_clock.c` (`GusClockState/Policy/Reading`) |
| JavaScript | the portal uses the core and `zonas-tcj.mjs` for its view; there is no standalone JS state machine |

## 4. Applicable vectors

- `vectors/gus-normative-003.json` (conversions feeding readings).
- The state machine is verified by dedicated tests
  (`tests/test_clock_state.py`, the `check_clock_state` C conformance
  category) and by the clock/rollback adversarial tests in
  `tests/test_adversarial_security.py`.

## 5. Maturity and limits

- State-machine core: **stable** (hardened in v3.1.1: sub-second
  anti-rollback and explicit authenticity).
- Roughtime profile: **experimental**; it needs the network for
  servers/ranges, which excludes it from strict offline mode and from
  the calendar conformance guarantee.
- Final precision and CLOCK_TAI availability depend on the platform;
  the SDK never invents one.

## 6. References

- `docs/en/threat-model.md` (clock sections), `docs/notary-runbook.md`.
