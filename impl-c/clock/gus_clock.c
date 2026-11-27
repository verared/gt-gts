/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus_clock.c — Máquina de estados de reloj (§6.3).
 * Extraído sin cambios de gus.c (v3.1.1); véase clock/gus_clock.h.
 */
#include "gus_clock.h"

/* ------------------------------------------------------------------ */
/* Máquina de estados de reloj (§6.3): medir con reloj monotónico,     */
/* afirmar tiempo absoluto solo con estado explícito.                  */
/* ------------------------------------------------------------------ */

GusClockState gus_clock_classify(const GusClockReading *reading,
                                 const GusClockPolicy *policy,
                                 const GusClockReading *last_anchor)
{
    if (!reading || !policy) return GUS_CLOCK_REJECTED;

    /* Anti-rollback sub-segundo (adenda v3.1.1): retroceso evaluado con
     * la tupla completa (seconds, nanos) respecto del último ancla
     * persistido; un retroceso dentro del mismo segundo también se
     * rechaza. */
    if (last_anchor && last_anchor->monotonic_ns > 0 &&
        reading->monotonic_ns >= last_anchor->monotonic_ns &&
        (reading->seconds < last_anchor->seconds ||
         (reading->seconds == last_anchor->seconds &&
          reading->nanos < last_anchor->nanos)))
        return GUS_CLOCK_REJECTED;

    /* VERIFIED exige autenticidad EXPLÍCITA de la fuente (adenda v3.1.1):
     * ni uncertainty_ns == 0 ni ningún valor de la cota asciende una
     * lectura sin `authenticated`. `require_authenticated = 0` reproduce
     * el comportamiento legado solo en despliegues controlados. */
    if (reading->uncertainty_ns >= 0 &&
        reading->uncertainty_ns <= policy->max_uncertainty_ns &&
        (!policy->require_authenticated || reading->authenticated))
        return GUS_CLOCK_VERIFIED;

    /* Sin cota válida: solo hay HOLDOVER si existe un ancla previa dentro
     * de la ventana y la lectura es coherente con el delta monotónico. */
    if (last_anchor && last_anchor->state == GUS_CLOCK_VERIFIED && last_anchor->monotonic_ns > 0 &&
        reading->monotonic_ns >= last_anchor->monotonic_ns &&
        policy->max_holdover_s > 0) {
        long long dt_ns = reading->monotonic_ns - last_anchor->monotonic_ns;
        long long elapsed_s = dt_ns / 1000000000LL;
        if (elapsed_s < policy->max_holdover_s ||
            (elapsed_s == policy->max_holdover_s && dt_ns % 1000000000LL == 0)) {
            /* Coherencia: |lectura − (ancla + Δmono redondeado)| <= 2 s
             * (tolerancia de granularidad); si el reloj se desvía del
             * ancla más allá de la deriva máxima declarada, no hay
             * extrapolación Honesta: UNVERIFIED. */
            long long expected = last_anchor->seconds + dt_ns / 1000000000LL;
            long long drift = reading->seconds - expected;
            if (drift < 0) drift = -drift;
            long long max_drift_s = 2 + (policy->drift_ppm > 0
                                             ? (dt_ns / 1000000000LL) * policy->drift_ppm / 1000000LL
                                             : 0);
            if (drift <= max_drift_s) return GUS_CLOCK_HOLDOVER;
        }
    }

    /* Política estricta: REJECTED; normal: UNVERIFIED (incertidumbre
     * desconocida; JAMÁS un VERIFIED silencioso). */
    return policy->strict ? GUS_CLOCK_REJECTED : GUS_CLOCK_UNVERIFIED;
}
