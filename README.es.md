# Sincronización y calidad de reloj

Parte de la suite de referencia **Gerarion** (verared/gerarion `v3.3.0`,
Gerarion Universal Standard). Este directorio es un **paquete de
exportación** listo para publicarse (o consumirse) como repositorio
satélite `verared/gt-gts`; conserva las rutas relativas del repositorio
base para componer módulos.

## El problema único que resuelve

La máquina de estados de confianza de reloj (VERIFIED → HOLDOVER → UNVERIFIED → REJECTED), las anclas anti-rollback persistentes y el perfil experimental de sincronización Roughtime.

## Estado normativo

- **Estable (núcleo) / Experimental (Roughtime)** (`maturity: stable-core/experimental-roughtime`) — línea base `v3.3.0` (aritmética y vectores
  congelados: GUS v3.0.0).
- Especificación(es) incluida(s): `docs/specs/GTS.es.md`, `docs/specs/GTS.en.md`
- Manifiesto de integridad verificable: [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json)
- Matriz oficial de compatibilidad: [`COMPATIBILITY.md`](https://github.com/verared/gerarion/blob/v3.3.0/COMPATIBILITY.md)

## Las 5 Garantías de Distribución

| # | Garantía | Mecanismo verificable |
|---|---|---|
| 1 | **Integridad SHA-256** | Mapa `files` en [`EXPORT-MANIFEST.json`](EXPORT-MANIFEST.json) verificado con `--verify-existing`. |
| 2 | **Procedencia declarada** | Campos `source_repo`, `source_tag` (`v3.3.0`) y `source_commit` (SHA-1 de 40 caracteres). |
| 3 | **Autenticidad de publicación** | Firma Ed25519 separada `EXPORT-MANIFEST.json.sig` verificable con `--trusted-pub-key` (sin autorreferencia). |
| 4 | **Reproducibilidad** | Re-exportación determinista bit a bit desde el mismo `--source-commit`. |
| 5 | **Conformidad funcional** | Suite de vectores normativos CC0 e integración cruzada en C11, Python y JavaScript. |

## Dependencias

- `gt-core` (*verared/gt-core*): tipos base y servicios del núcleo.
Base común: `verared/gerarion` `v3.3.0`.
- *Nota:* el perfil Roughtime (experimental) importa `gerarion.interop` (gt-interop) para el perfil GUS-3339.

## Contenido

- `EXPORT-MANIFEST.json`
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

Desde `verared/gerarion`, la integridad y (opcionalmente) la autenticidad de firma separada se verifican con:

```bash
python3 tools/export_module.py --verify-existing /ruta/a/gt-gts
# Con verificación criptográfica de EXPORT-MANIFEST.json.sig:
python3 tools/export_module.py --verify-existing /ruta/a/gt-gts --trusted-pub-key /ruta/a/release-pub.pem
```

## Contrato de sincronización con `verared/gerarion`

Este paquete es **generado, no editado a mano**: se regenera byte a
byte desde `verared/gerarion v3.3.0` con
`python3 tools/export_module.py --module gt-gts --out <dir>`. La fuente
de verdad normativa (especificaciones, vectores CC0, núcleos de
referencia de las tres plataformas y la batería completa) permanece en
`verared/gerarion`; los satélites `verared/gt-gts` la consumen y no forkean la
aritmética. Las actualizaciones fluyen regenerando la exportación desde
un tag del repositorio base; nunca editando los archivos exportados.
