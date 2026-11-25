"""Estruturas básicas: o bloco de memória e as opções dos comandos alloc e defrag."""

from dataclasses import dataclass
from enum import Enum


class FitAlg(Enum):
    """Algoritmo de alocação. O valor é a palavra usada no comando alloc."""

    FIRST = "first"
    BEST = "best"
    WORST = "worst"
    NEXT = "next"


class Option(Enum):
    """Opção do defrag. O valor é a palavra usada no comando defrag."""

    INIT = "init"
    END = "end"
    OPT = "opt"


@dataclass
class Bloco:
    """Trecho contíguo da memória: alocado (tem id) ou buraco livre (id None)."""

    inicio: int
    tamanho: int
    id: int | None = None

    @property
    def fim(self) -> int:
        """Primeiro endereço depois do bloco."""
        return self.inicio + self.tamanho

    @property
    def livre(self) -> bool:
        """True se o bloco é um buraco."""
        return self.id is None
