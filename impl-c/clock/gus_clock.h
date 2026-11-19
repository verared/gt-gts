/*
 * SPDX-License-Identifier: MIT OR Apache-2.0
 * SPDX-FileCopyrightText: 2026 verared contributors
 */

/*
 * gus_clock.h — Dominio GTS: máquina de estados de confianza de reloj
 * (spec §6.3). Depende únicamente de tipos estándar; sin malloc.
 */

#ifndef GUS_CLOCK_H
#define GUS_CLOCK_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* ---------------- máquina de estados de reloj (§6.3) ---------------- */

typedef enum {
    GUS_CLOCK_VERIFIED = 0,   /* fuente autenticada dentro de la cota */
    GUS_CLOCK_HOLDOVER = 1,   /* extrapolación con ancla previa válida */
    GUS_CLOCK_UNVERIFIED = 2, /* sin fuente confiable / incertidumbre unknown */
    GUS_CLOCK_REJECTED = 3    /* retroceso respecto del ancla persistida */
} GusClockState;

typedef struct {
    long long seconds;        /* lectura absoluta propuesta (int64) */
    uint32_t nanos;           /* 0..999999999 */
    GusClockState state;
    const char *source_id;    /* identificador de la fuente (estático) */
    long long uncertainty_ns; /* cota de error declarada, ns */
    long long monotonic_ns;   /*_CLOCK_MONOTONIC del sistema en la lectura */
    uint8_t authenticated;    /* adenda v3.1.1: fuente autenticada EXPLÍCITA */
} GusClockReading;

/* Parámetros de la máquina de estados (todos en unidades explícitas). */
typedef struct {
    long long max_uncertainty_ns; /* cota para considerarlo VERIFIED */
    long long max_holdover_s;     /* ventana máxima de extrapolación */
    long long drift_ppm;          /* deriva máxima declarada (ppm) */
    int strict;                   /* 1: sin fuente → REJECTED (no UNVERIFIED) */
    int require_authenticated;    /* 1 (por defecto): VERIFIED exige
                                   * reading->authenticated != 0 (adenda v3.1.1);
                                   * 0 solo en despliegues controlados. */
} GusClockPolicy;

/* Estabiliza una lectura contra el último ancla
 * (sec.monotonic + sec.nanos; -1 / UINT32_MAX si no hay). */
GusClockState gus_clock_classify(const GusClockReading *reading,
                                 const GusClockPolicy *policy,
                                 const GusClockReading *last_anchor);

#ifdef __cplusplus
}
#endif

#endif /* GUS_CLOCK_H */
