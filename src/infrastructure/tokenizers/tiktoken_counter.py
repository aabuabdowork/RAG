import tiktoken

from src.core.config import settings
from src.domain.interfaces.token_counter import ITokenCounter


class TiktokenCounter(ITokenCounter):
    def __init__(self, encoding: str = settings.token_encoding) -> None:
        self._encoding = tiktoken.get_encoding(encoding)

    def count(self, text: str) -> int:
        return len(self._encoding.encode(text, disallowed_special=()))
