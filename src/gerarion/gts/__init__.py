# SPDX-License-Identifier: MIT OR Apache-2.0
# SPDX-FileCopyrightText: 2026 verared contributors
"""Dominio GTS — sincronización y calidad de reloj (spec §6.3).

Módulos: ``gerarion.gts.clock`` (máquina de estados) y
``gerarion.gts.roughtime`` (perfil experimental).

Compatibilidad retroactiva: el antiguo módulo plano ``gerarion.gts``
(ahora ``gerarion.gst.envelope``) reexporta aquí sus nombres públicos,
de modo que ``from gerarion import gts; gts.create(...)`` y
``gts.verify(...)`` siguen funcionando sin cambios.
"""

from ..gst.envelope import *  # noqa: F401,F403
from ..gst import envelope as _envelope

globals().update(
    {
        _k: _v
        for _k, _v in vars(_envelope).items()
        if not _k.startswith("__") and _k not in globals()
    }
)

from . import clock as clock  # noqa: E402,F401
from . import roughtime as roughtime  # noqa: E402,F401
