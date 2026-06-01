from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from trump_market_alert.models import SourceItem


class BaseSource(ABC):
    name: str

    @abstractmethod
    def fetch(self) -> list[SourceItem]:
        raise NotImplementedError
