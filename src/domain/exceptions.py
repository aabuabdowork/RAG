class BudgetExceededError(Exception):
    pass


class ServiceUnavailableError(Exception):
    def __init__(self, service: str, error: Exception) -> None:
        super().__init__(f"{service} is unavailable ({type(error).__name__})")
        self.service = service
