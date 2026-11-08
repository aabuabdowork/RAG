from abc import ABC, abstractmethod
from typing import Any, Dict, List


class IMetrics(ABC):
    @abstractmethod
    def record(self, event: str, **fields: Any) -> None:
        pass

    @abstractmethod
    def events(self) -> List[Dict[str, Any]]:
        pass
