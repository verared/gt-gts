# Especificación GTS — Sincronización y calidad de reloj

- **Estado:** Estable el núcleo (§6.3); **Experimental** el perfil Roughtime ·
  **Versión:** 1.0.0 · **Línea base:** GUS v3.1.1
- **Edición consolidada:** [`../spec/gus-3.0.0.md`](../spec/gus-3.0.0.md) (§9.4, capas temporales) ·
  Perfil: [`../profiles/gus-roughtime-perfil.md`](../profiles/gus-roughtime-perfil.md)
- **Licencia:** CC-BY-4.0 · Mantenida por: verared contributors

## 1. Alcance

Cómo un dispositivo obtiene, evalúa y mantiene la **calidad de su tiempo**
antes de firmar o emitir nada: máquina de estados de confianza, incertidumbre,
anclas anti-rollback persistentes y el perfil opcional de sincronización
Roughtime. No cubre el formato de marca (GUS), la definición de TCJ ni el
sellado de eventos (GST).

## 2. Reglas normativas

1. **Separación estructural de relojes:** la medición de intervalos usa
   el reloj monotónico del SO (`time.monotonic_ns()` / `CLOCK_MONOTONIC`);
   el tiempo absoluto proviene de una fuente autenticada (CLOCK_TAI, GNSS,
   NTP autenticado, enlace firmado). Nunca se confunden.
2. **Máquina de estados** de cada lectura — nunca se emite un `VERIFIED`
   en silencio:
   - `VERIFIED`: fuente autenticada presente y `uncertainty_ns ≤
     max_uncertainty_ns`.
   - `HOLDOVER`: fuente perdida, pero existe un ancla previa confiable
     dentro de `max_holdover_s`; la extrapolación usa el delta monotónico
     y la incertidumbre crema según `drift_ppm`.
   - `UNVERIFIED`: sin fuente confiable, incertidumbre desconocida o
     ventana agotada (bajo política estricta degrada a `REJECTED`).
   - `REJECTED`: el reloj retrocedió respecto del último ancla persistido
     (rollback, comparación por la tupla `(instant, nanos)`), o la
     política estricta lo exige.
3. **Autenticidad de fuente explícita:** la lectura declara `authenticated`;
   una política con `require_authenticated` nunca eleva a `VERIFIED` una
   lectura sin fuente autenticada (o fuera de la lista blanca
   `trusted_sources`), aunque su cota sea cero.
4. **Persistencia anti-rollback:** el almacén de anclas guarda el último
   ancla con escritura atómica (temporal + rename + fsync). Un reinicio NO
   repara un retroceso: la comparación se hace también contra el ancla
   cargada de disco. Ante estado persistido corrupto, el comportamiento
   es *fail-closed*.
5. **Perfil Roughtime (experimental):** un testigo externo acota el
   instante declarado en `[midpoint − radius, midpoint + radius]` con
   nonce ligado al paquete. Nunca prueba la veracidad del instante; solo
   acota su existencia temporal.

## 3. Fuentes de verdad

| Plataforma | Implementación |
|---|---|
| Python | `src/gerarion/gts/clock.py`, `src/gerarion/gts/roughtime.py` |
| C11 | `impl-c/clock/gus_clock.c` (`GusClockState/Policy/Reading`) |
| JavaScript | el portal usa el núcleo y `zonas-tcj.mjs` para la vista; no hay máquina de estados JS autónoma |

## 4. Vectores aplicables

- `vectors/gus-normative-003.json` (conversiones que alimentan lecturas).
- La máquina de estados se verifica con pruebas dedicadas
  (`tests/test_clock_state.py`, categoría `check_clock_state` de la
  conformancia C) y con las pruebas adversarias de reloj/reloj invertido
  de `tests/test_adversarial_security.py`.

## 5. Madurez y límites

- Núcleo de la máquina de estados: **estable** (endurecido en v3.1.1:
  anti-rollback sub-segundo y autenticidad explícita).
- Perfil Roughtime: **experimental**; requiere red para la/providers, lo
  que lo excluye del modo estrictamente offline y de la garantía de
  conformancia del calendario.
- La precisión final y la disponibilidad de CLOCK_TAI dependen de la
  plataforma; el SDK nunca inventa una.

## 6. Referencias

- `docs/spec/threat-model.md` (sección de relojes), `docs/notary-runbook.md`.
