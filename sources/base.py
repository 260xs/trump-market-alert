from __future__ import annotations

import abc
from datetime import datetime, timezone
from typing import Iterable

from database.models import SourceConfig, Statement


class SourceMonitor(abc.ABC):
    def __init__(self, source: SourceConfig):
        self.source = source

    @abc.abstractmethod
    def fetch(self) -> list[Statement]:
        raise NotImplementedError


def utc_now() -> datetime:
    return datetime.now(timezone.utc)
