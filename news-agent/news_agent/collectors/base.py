from abc import ABC, abstractmethod


class BaseCollector(ABC):

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def collect(self, max_results: int = 25) -> list[dict]:
        """Return list of raw article dicts with keys: url, title, description, content, publishedAt, source."""
        ...
