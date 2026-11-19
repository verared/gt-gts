# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Perfil GUS-Roughtime: testigos externos ligados al campo anchor de la GST.

Documento normativo: docs/profiles/gus-roughtime-perfil.md (ES espejo) /
docs/en/profiles/gus-roughtime-profile.md (EN normativo).

Qué resuelve: el notario k-de-n da una cota superior de existencia desde
DENTRO del clúster GUS. Roughtime añade testigos INDEPENDIENTES del
clúster que firman, con Ed25519, la respuesta a un nonce elegido por
quien sella. Comprometer los notarios ya no basta: hay que aplicar las
firmas de todos los testigos externos también.

Formato de receipt (JSON, "gusroughtime-001"):

    {"type": "gusroughtime-001",
     "midpoint_rfc3339": "2026-05-23T09:30:12Z",   # RFC 3339 Z (GUS-3339)
     "radius_s": 3,                                # aserción de ventana
     "pubkey_b64": "<Ed25519 pk del servidor>",
     "signed_b64": "<bytes exactos firmados: dominio || nonce || midp || radius>",
     "sig_b64": "<Ed25519 sig>"}

Relación con el wire-format UDP del draft Roughtime: parsear y encadenar
la negociación completa de shards UDP es la parte RED del protocolo y no
pertenece a esta capa (queda registrado como pendiente TODO-002); este
módulo define y verifica el RECEIPT: la unidad firmada que un proxy o un
cliente completo produce, con verificación offline sin dependencias.

Anchor en la GST (campo `anchor`):

    {"type": "roughtime", "midpoint_rfc3339": ..., "radius_s": ...,
     "pubkey_b64": ..., "signed_b64": ..., "sig_b64": ...}

Garantías y límites (el .md normativo es vinculante):
- Cota superior de existencia por un testigo externo (igual que la TSA
  de GUS-3161, pero con nonce anti-replay ligado al bundle).
- NUNCA prueba la veracidad del instante declarado; acota [midp−radius,
  midp+radius] como ventana del testigo.
- El verificador decide su lista de claves de testigo de confianza
  (trust root de testigos); sin esa lista, receipt no verificado.

Ed25519: implementación de REFERENCIA RFC 8032 en Python puro (stdlib
puro, como todo el repo). Lenta pero auditable; una implementación real
debe usar una librería validada — el cambio de verificador no cambia
vectores (Ed25519 es un estándar VERIFY-side, la firma de prueba se
regenera). NO usar esta implementación para firmar producción.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from typing import Iterable, Optional

from ..interop import profiles as _g3339

RECEIPT_TYPE = "gusroughtime-001"
ANCHOR_TYPE = "roughtime"

# ---------------------------------------------------------------------------
# Ed25519 — RFC 8032 (implementación de referencia, Python puro)
# ---------------------------------------------------------------------------

_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493
_D = (-121665 * pow(121666, _P - 2, _P)) % _P


def _inv(x: int) -> int:
    return pow(x, _P - 2, _P)


_BY = 4 * _inv(5) % _P


def _recover_x(y: int, sign: int) -> int:
    """RFC 8032 §5.1.3 paso 2: recuperación de x desde y."""
    if y >= _P:
        return -1
    x2 = (y * y - 1) * _inv(_D * y * y + 1) % _P
    if x2 == 0:
        if sign:
            return -1
        return 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P != 0:
        x = x * pow(2, (_P - 1) // 4, _P) % _P
    if (x * x - x2) % _P != 0:
        return -1
    if (x & 1) != sign:
        x = _P - x
    return x


def _basjoint():  # punto base
    bx = _recover_x(_BY, 0)
    return (bx, _BY, 1, bx * _BY % _P)


_G = _basjoint()


# Punto en coordenadas extendidas (X, Y, Z, T)

def _edwards_add(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = (y1 - x1) * (y2 - x2) % _P
    b = (y1 + x1) * (y2 + x2) % _P
    c = 2 * t1 * t2 * _D % _P
    dd = 2 * z1 * z2 % _P
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _scalarmult(P, e: int):
    Q = (0, 1, 1, 0)
    while e > 0:
        if e & 1:
            Q = _edwards_add(Q, P)
        P = _edwards_add(P, P)
        e >>= 1
    return Q


def _point_compress(P) -> bytes:
    x, y, z, _ = P
    zi = _inv(z)
    x = x * zi % _P
    y = y * zi % _P
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _point_decompress(s: bytes):
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x == -1:
        return None
    return (x, y, 1, x * y % _P)


def ed25519_public_key(private_key: bytes) -> bytes:
    h = hashlib.sha512(private_key).digest()
    a = int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254)
    return _point_compress(_scalarmult(_G, a))


def ed25519_sign(private_key: bytes, message: bytes) -> bytes:
    h = hashlib.sha512(private_key).digest()
    a = int.from_bytes(h[:32], "little") & ((1 << 254) - 8) | (1 << 254)
    prefix = h[32:]
    pk = _point_compress(_scalarmult(_G, a))
    r = int.from_bytes(
        hashlib.sha512(prefix + message).digest(), "little"
    ) % _L
    R = _point_compress(_scalarmult(_G, r))
    k = int.from_bytes(hashlib.sha512(R + pk + message).digest(), "little") % _L
    return R + int.to_bytes(r + k * a % _L, 32, "little")


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(public_key) != 32 or len(signature) != 64:
        return False
    A = _point_decompress(public_key)
    R = _point_decompress(signature[:32])
    if A is None or R is None:
        return False
    k = int.from_bytes(
        hashlib.sha512(signature[:32] + public_key + message).digest(), "little"
    ) % _L
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:
        return False
    left = _scalarmult(_G, s)
    right = _edwards_add(R, _scalarmult(A, k))
    return _point_compress(left) == _point_compress(right)


# ---------------------------------------------------------------------------
# Receipts GUS-Roughtime
# ---------------------------------------------------------------------------

_SIGNED_DOMAIN = "GUS-ROUGH-TIME"


def signed_bytes(nonce: bytes, midpoint_rfc3339: str, radius_s: int) -> bytes:
    """Los bytes EXACTOS que firma el testigo: dominio || b'\n' || nonce || b'\n'
    || midpoint (RFC 3339) || b'\n' || radius decimal || b'\n'."""
    return b"\n".join([
        _SIGNED_DOMAIN.encode("ascii"),
        nonce,
        midpoint_rfc3339.encode("ascii"),
        str(int(radius_s)).encode("ascii"),
    ]) + b"\n"


def make_receipt(nonce: bytes, midpoint_rfc3339: str, radius_s: int,
                 private_key: bytes) -> dict:
    """Construye un receipt firmado (para el test y para un proxy Roughtime real)."""
    signed = signed_bytes(nonce, midpoint_rfc3339, radius_s)
    pub = ed25519_public_key(private_key)
    return {
        "type": RECEIPT_TYPE,
        "midpoint_rfc3339": midpoint_rfc3339,
        "radius_s": radius_s,
        "pubkey_b64": base64.b64encode(pub).decode("ascii"),
        "signed_b64": base64.b64encode(signed).decode("ascii"),
        "sig_b64": base64.b64encode(ed25519_sign(private_key, signed)).decode("ascii"),
    }


def verify_receipt(receipt: dict, trusted_pubkeys_b64: Iterable[str] = (),
                   expected_nonce: Optional[bytes] = None) -> dict:
    """Verifica el receipt y devuelve la ventana [min, max] en instante GUS.

    Devuelve {"ok": bool, "errors": [...], "window": (lo, hi) | None}.
    La ventana es la aserción del testigo, no la verdad del instante.

    `expected_nonce` (S7): cuando el verificador conoce el nonce de SU
    consulta (el hash del bundle/artefacto que envió), debe pasarlo aquí:
    el receipt solo prueba existencia si responde a ESE nonce; uno que
    responda a otro nonce no dice nada sobre la marca verificada.
    """
    errors = []
    if receipt.get("type") != RECEIPT_TYPE:
        return {"ok": False, "errors": ["type inválido"], "window": None}
    pub = base64.b64decode(receipt["pubkey_b64"])
    if receipt["pubkey_b64"] not in set(trusted_pubkeys_b64):
        errors.append("testigo no está en el trust root del verificador")
    signed = base64.b64decode(receipt["signed_b64"])
    sig = base64.b64decode(receipt["sig_b64"])
    if not ed25519_verify(pub, signed, sig):
        return {"ok": False, "errors": ["firma del testigo inválida"], "window": None}
    try:
        midp = _g3339.instant_from_rfc3339(receipt["midpoint_rfc3339"])
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "errors": [f"midpoint fuera de perfil: {exc}"], "window": None}
    radius = int(receipt["radius_s"])
    if radius < 0:
        errors.append("radius negativo: aserción de ventana inválida, receipt no usable")
    parts_signed = signed.split(b"\n")
    # Formato: dominio || nonce(32 B) || midpoint(20 B) || radius || ''.
    # El nonce es binario y PUEDE contener 0x0a: se reensambla separando
    # midpoint y radius desde el final (ambos libres de \n por construcción),
    # nunca asumiendo una posición fija del nonce en el split.
    if len(parts_signed) < 4:
        return {"ok": False, "errors": ["bytes firmados malformados"], "window": None}
    nonce = b"\n".join(parts_signed[1:-3])
    if expected_nonce is not None and not hmac.compare_digest(nonce, expected_nonce):
        errors.append("el nonce del receipt no coincide con el nonce de la consulta: "
                      "el receipt no prueba la existencia de LA marca verificada")
    recomputed = signed_bytes(nonce, receipt["midpoint_rfc3339"], radius)
    if recomputed != signed:
        errors.append("los bytes firmados no corresponden a los campos del receipt")
    return {
        "ok": not errors,
        "errors": errors,
        "window": (midp - radius, midp + radius) if midp - radius >= 0 else (0, midp + radius),
        "nonce": nonce.hex(),
    }


def bind_anchor(receipt: dict) -> dict:
    """Extrae el anchor (campo GST) desde un receipt verificado."""
    return {
        "type": ANCHOR_TYPE,
        "midpoint_rfc3339": receipt["midpoint_rfc3339"],
        "radius_s": receipt["radius_s"],
        "pubkey_b64": receipt["pubkey_b64"],
        "signed_b64": receipt["signed_b64"],
        "sig_b64": receipt["sig_b64"],
    }


def verify_anchor(anchor: dict, trusted_pubkeys_b64: Iterable[str] = (),
                  gst_instant: Optional[int] = None) -> dict:
    """Verifica un anchor de la GST: receipt + coherencia de ventana.

    Si se pasa gst_instant, comprueba la cota de existencia:
    gst_instant <= midp + radius (el testigo vio el nonce después del sellado).
    """
    receipt = dict(anchor)
    receipt["type"] = RECEIPT_TYPE
    res = verify_receipt(receipt, trusted_pubkeys_b64)
    if not res["ok"]:
        return res
    lo, hi = res["window"]
    if gst_instant is not None and gst_instant > hi:
        return {
            "ok": False,
            "errors": [f"coherencia: gst_instant ({gst_instant}) > ventana del testigo ({hi})"],
            "window": (lo, hi),
        }
    return res
