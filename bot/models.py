from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class Signal:
    action: Action
    reason: str
    indicators: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AIContext:
    """Contexto NUMÉRICO que se le pasa al asesor de IA.

    Solo datos de mercado/riesgo: nunca claves, ni PII, ni el objeto Position
    (se usa has_position: bool para no filtrar cantidades/precios de cuenta).
    """

    symbol: str
    action: Action
    reason: str
    price: float
    has_position: bool
    indicators: dict[str, float] = field(default_factory=dict)
    risk: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class AIVerdict:
    """Veredicto del asesor. `confirm` es el ÚNICO campo con poder de ejecución
    (True = mantener la acción; False = vetar). El motor jamás lee un 'lado'."""

    confirm: bool
    confidence: float
    rationale: str
    ai_used: bool = False
