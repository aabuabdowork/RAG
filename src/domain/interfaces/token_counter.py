from abc import ABC, abstractmethod


class ITokenCounter(ABC):
    @abstractmethod
    def count(self, text: str) -> int:
        pass
