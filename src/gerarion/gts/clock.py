# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Máquina de estados de confianza de reloj e incertidumbre (spec §6.3).

Separa ESTRUCTURALMENTE dos relojes que nunca deben confundirse:

- **Medición de intervalos**: reloj monotónico del SO
  (``time.monotonic_ns()`` / CLOCK_MONOTONIC): siempre avanza, no sirve
  para etiquetar el tiempo absoluto.
- **Tiempo absoluto**: fuente autenticada (CLOCK_TAI,GNSS, NTP autenticado,
  enlace firmado): aporta ``instant`` + ``nanos`` con una cota de error.

Estados de una lectura (nunca se emite un VERIFIED en silencio):

- ``VERIFIED``: la fuente autenticada está presente y su incertidumbre
  declarada cumple la cota de política (``uncertainty_ns <= max_uncertainty_ns``).
- ``HOLDOVER``: la fuente se perdió, pero existe un ancla previa de
  confianza dentro de la ventana ``max_holdover_s``; la extrapolación usa
  el delta monotónico y la incertidumbre CRECE con la deriva máxima
  declarada (``drift_ppm``).
- ``UNVERIFIED``: sin fuente confiable, incertidumbre desconocida o
  ventana de holdover agotada. Con política estricta se degrada a
  ``REJECTED``.
- ``REJECTED``: el reloj retrocedió respecto del último ancla persistido
  (rollback), o la política estricta exige rechazar lo no verificable.

Persistencia: `ClockAnchorStore` guarda el último ancla en JSON con
escritura atómica (temporal + os.replace + fsync) para sobrevivir
reinicios: un reinicio NO repara un retroceso de reloj.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from ..core.calendar import NANOS_MAX, validate_nanos

__all__ = [
    "ClockState",
    "ClockReading",
    "ClockPolicy",
    "TrustedClock",
    "ClockAnchorStore",
]


class ClockState(str, Enum):
    VERIFIED = "VERIFIED"
    HOLDOVER = "HOLDOVER"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


@dataclass(frozen=True)
class ClockReading:
    """Lectura de tiempo con estado de confianza explícito.

    `instant` son segundos GUS (int64) y `nanos` la fracción separada
    (0..999_999_999, validada estricta); `monotonic_ns` es la lectura del
    reloj monotónico del SO en el instante de la medición (nunca una
    etiqueta de tiempo absoluto). `authenticated` declara EXPLÍCITAMENTE
    que la lectura proviene de una fuente autenticada (adenda v3.1.1):
    el reloj de pared del SO y cualquier lectura sin adaptador verificado
    deben dejarlo en False.
    """

    instant: int
    nanos: int = 0
    state: ClockState = ClockState.UNVERIFIED
    source_id: str = ""
    uncertainty_ns: int = -1  # < 0: desconocida
    monotonic_ns: int = 0
    authenticated: bool = False

    def __post_init__(self):
        validate_nanos(self.nanos)
        if not isinstance(self.instant, int) or isinstance(self.instant, bool):
            raise ValueError(f"instant debe ser entero de segundos: {self.instant!r}")


@dataclass(frozen=True)
class ClockPolicy:
    """ Política declarada de la máquina de estados."""

    max_uncertainty_ns: int = 1_000_000  # 1 ms: cota para VERIFIED
    max_holdover_s: int = 3600           # ventana máxima de extrapolación
    drift_ppm: int = 500                 # deriva máxima declarada del reloj local
    strict: bool = False                 # True: sin fuente → REJECTED
    # Adenda v3.1.1: nadie asciende a VERIFIED sin autenticidad explícita.
    require_authenticated: bool = True   # VERIFIED exige reading.authenticated
    # Lista blanca opcional de fuentes: si no es None, `source_id` de la
    # lectura debe pertenecer a ella para poder ser VERIFIED.
    trusted_sources: Optional[frozenset] = None


class ClockAnchorStore:
    """Último ancla de confianza persistido (JSON atómico, sin dependencias).

    Guarda (instant, nanos, monotonic_ns, source_id, uncertainty_ns) del
    último estado VERIFIED aceptado. Cargar el archivo no eleva
    nunca la calidad de una lectura: solo habilita HOLDOVER y detecta
    rollback.
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path
        self._anchor: Optional[ClockReading] = None
        if path:
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if data.get("instant") is not None and data.get("state") == ClockState.VERIFIED.value:
                    self._anchor = ClockReading(
                        instant=int(data["instant"]),
                        nanos=int(data.get("nanos", 0)),
                        state=ClockState(data.get("state", "VERIFIED")),
                        source_id=str(data.get("source_id", "")),
                        uncertainty_ns=int(data.get("uncertainty_ns", -1)),
                        monotonic_ns=int(data.get("monotonic_ns", 0)),
                    )
            except (FileNotFoundError, ValueError):
                pass  # sin ancla previa: no hay estado heredado

    @property
    def anchor(self) -> Optional[ClockReading]:
        return self._anchor

    def update(self, reading: ClockReading) -> None:
        self._anchor = reading
        if not self.path:
            return
        data = {
            "instant": reading.instant,
            "nanos": reading.nanos,
            "state": reading.state.value,
            "source_id": reading.source_id,
            "uncertainty_ns": reading.uncertainty_ns,
            "monotonic_ns": reading.monotonic_ns,
        }
        tmp = f"{self.path}.tmp.{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)


def monotonic_ns() -> int:
    """Reloj monotónico del SO: SOLO para medir intervalos, nunca para
    etiquetar tiempo absoluto (spec §6.3)."""
    return time.monotonic_ns()


class TrustedClock:
    """Máquina de estados: clasifica lecturas de fuentes candidatas.

    `submit(reading_candidate)` evalúa una lectura del mundo (con su cota)
    contra la política y el último ancla persistido; el resultado es un
    ClockReading con estado explícito. Las duraciones se miden SIEMPRE con
    el monotónico (`elapsed_ns`), jamás restando etiquetas absolutas.
    """

    def __init__(self, policy: ClockPolicy = None, store: ClockAnchorStore = None):
        self.policy = policy or ClockPolicy()
        self.store = store or ClockAnchorStore()

    def classify(self, reading: ClockReading) -> ClockReading:
        anchor = self.store.anchor
        # 1) Anti-rollback sub-segundo (adenda v3.1.1): retroceso respecto
        #    del ancla persistido evaluado con la tupla completa
        #    (instant, nanos); un reloj que retrocede solo dentro del
        #    mismo segundo también se rechaza.
        if (
            anchor is not None
            and reading.monotonic_ns >= anchor.monotonic_ns > 0
            and (reading.instant, reading.nanos) < (anchor.instant, anchor.nanos)
        ):
            rejected = ClockReading(
                instant=reading.instant,
                nanos=reading.nanos,
                state=ClockState.REJECTED,
                source_id=reading.source_id,
                uncertainty_ns=reading.uncertainty_ns,
                monotonic_ns=reading.monotonic_ns,
                authenticated=reading.authenticated,
            )
            return rejected

        # 2) Fuente autenticada dentro de la cota: VERIFIED (y ancla nueva).
        #    SIN autenticidad explícita NO hay ascenso a VERIFIED nunca
        #    (adenda v3.1.1), ni siquiera con uncertainty_ns == 0: la
        #    lectura cae a UNVERIFIED (o REJECTED en estricta).
        source_allowed = (
            self.policy.trusted_sources is None
            or reading.source_id in self.policy.trusted_sources
        )
        authentic = reading.authenticated and source_allowed
        if (
            0 <= reading.uncertainty_ns <= self.policy.max_uncertainty_ns
            and (authentic or not self.policy.require_authenticated)
        ):
            verified = ClockReading(
                instant=reading.instant,
                nanos=reading.nanos,
                state=ClockState.VERIFIED,
                source_id=reading.source_id,
                uncertainty_ns=reading.uncertainty_ns,
                monotonic_ns=reading.monotonic_ns,
                authenticated=reading.authenticated,
            )
            self.store.update(verified)
            return verified

        # 3) Sin cota válida: HOLDOVER si hay ancla dentro de la ventana y
        # la lectura es coherente con el delta monotónico (± deriva máxima).
        if (
            anchor is not None
            and anchor.state is ClockState.VERIFIED
            and anchor.monotonic_ns > 0
            and reading.monotonic_ns >= anchor.monotonic_ns
            and self.policy.max_holdover_s > 0
        ):
            dt_ns = reading.monotonic_ns - anchor.monotonic_ns
            if dt_ns <= self.policy.max_holdover_s * 1_000_000_000:
                expected = anchor.instant + dt_ns // 1_000_000_000
                drift = abs(reading.instant - expected)
                max_drift_s = 2 + (
                    (dt_ns // 1_000_000_000) * self.policy.drift_ppm // 1_000_000
                    if self.policy.drift_ppm > 0
                    else 0
                )
                if drift <= max_drift_s:
                    grown_uncertainty = (
                        max(anchor.uncertainty_ns, 0)
                        + dt_ns * self.policy.drift_ppm // 1_000_000
                        + 1_000  # granularidad de la extrapolación
                    )
                    holddover = ClockReading(
                        instant=reading.instant,
                        nanos=reading.nanos,
                        state=ClockState.HOLDOVER,
                        source_id=f"{anchor.source_id}+holdover",
                        uncertainty_ns=grown_uncertainty,
                        monotonic_ns=reading.monotonic_ns,
                    )
                    return holddover

        # 4) Sin fuente confiable: UNVERIFIED (o REJECTED en estricta).
        state = (
            ClockState.REJECTED if self.policy.strict else ClockState.UNVERIFIED
        )
        return ClockReading(
            instant=reading.instant,
            nanos=reading.nanos,
            state=state,
            source_id=reading.source_id,
            uncertainty_ns=reading.uncertainty_ns,
            monotonic_ns=reading.monotonic_ns,
        )

    @staticmethod
    def now_reading(source_id: str, uncertainty_ns: int = -1) -> ClockReading:
        """Lectura candidata 'ahora' desde la fuente local del SO.

        OJO: el reloj de pared del SO NO es una fuente autenticada; con
        `uncertainty_ns` desconocido la máquina la clasificará
        UNVERIFIED/REJECTED, nunca VERIFIED.
        """
        return ClockReading(
            instant=int(time.time()),
            nanos=0,
            source_id=source_id,
            uncertainty_ns=uncertainty_ns,
            monotonic_ns=time.monotonic_ns(),
        )

    @staticmethod
    def elapsed_ns(start_monotonic_ns: int) -> int:
        """Duración medida con el reloj monotónico (nunca con etiquetas)."""
        return time.monotonic_ns() - start_monotonic_ns
