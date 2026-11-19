# Sincronización y calidad de reloj

Parte de la suite de referencia **Gerarion** (verared/gerarion `v3.2.0`,
Gerarion Universal Standard). Este directorio es un **paquete de
exportación** listo para publicarse (o consumirse) como repositorio
satélite `verared/gt-gts`; conserva las rutas relativas del repositorio
base para componer módulos.

## El problema único que resuelve

La máquina de estados de confianza de reloj (VERIFIED → HOLDOVER → UNVERIFIED → REJECTED), las anclas anti-rollback persistentes y el perfil experimental de sincronización Roughtime.

## Estado normativo

- **Estable (núcleo) / Experimental (Roughtime)** — línea base `v3.2.0` (aritmética y vectores
  congelados: GUS v3.0.0).
- Especificación(es) incluida(s): `docs/specs/GTS.es.md`, `docs/specs/GTS.en.md`

## Dependencias

- `gt-core` (*verared/gt-core*): tipos base y servicios del núcleo.
Base común: `verared/gerarion` `v3.2.0`.
- *Nota:* el perfil Roughtime (experimental) importa `gerarion.interop` (gt-interop) para el perfil GUS-3339.

## Contenido

- `LICENSE`
- `NOTICE`
- `docs/specs/GTS.en.md`
- `docs/specs/GTS.es.md`
- `impl-c/clock/gus_clock.c`
- `impl-c/clock/gus_clock.h`
- `src/gerarion/gts/__init__.py`
- `src/gerarion/gts/clock.py`
- `src/gerarion/gts/roughtime.py`

## Uso offline

No requiere red, cuentas, registro de paquetes ni frameworks:

```bash
python3 -c 'import sys; sys.path.insert(0, "src"); import gerarion'
```

## Verificación

Con Python ≥ 3.9 y `reuse` instalado:

```bash
reuse lint                                    # licencias al 100 %
# (las pruebas viven en la suite de verared/gerarion)
```

## Contrato de sincronización con `verared/gerarion`

Este paquete es **generado, no editado a mano**: se regenera byte a
byte desde `verared/gerarion v3.2.0` con
`python3 tools/export_module.py --module gt-gts --out <dir>`. La fuente
de verdad normativa (especificaciones, vectores CC0, núcleos de
referencia de las tres plataformas y la batería completa) permanece en
`verared/gerarion`; los satélites `verared/gt-gts` la consumen y no forkean la
aritmética. Las actualizaciones fluyen regenerando la exportación desde
un tag del repositorio base; nunca editando los archivos exportados.
