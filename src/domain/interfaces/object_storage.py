from abc import ABC, abstractmethod


class IObjectStorage(ABC):
    @abstractmethod
    def upload(self, path: str, data: bytes) -> None:
        pass

    @abstractmethod
    def download(self, path: str) -> bytes:
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        pass
