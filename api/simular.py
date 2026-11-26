"""Função da Vercel para POST /api/simular.

Reaproveita o manipulador do servidor local (src/servidor.py):
a mesma lógica responde no computador e na Vercel.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from servidor import Manipulador  # noqa: E402


class handler(Manipulador):
    """Nome exigido pela Vercel para funções Python."""
