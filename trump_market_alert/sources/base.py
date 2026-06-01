from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ..models import Event


class Source(ABC):
    name: str

    @abstractmethod
    def fetch(self, limit: int = 20) -> Iterable[Event]:
        raise NotImplementedError
