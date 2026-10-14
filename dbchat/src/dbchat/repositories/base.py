from abc import ABC, abstractmethod


class ConnectionRepository(ABC):
    """Persistence boundary for saved database connections. Services depend
    on this interface, never on `storage.store` or SQLAlchemy directly —
    that's what makes a service testable with a fake repository and swappable
    to a different backing store later without touching business logic."""

    @abstractmethod
    def save(  # pylint: disable=too-many-arguments
        self,
        *,
        name: str,
        db_type: str,
        host: str,
        port: int,
        database_name: str,
        username: str,
        password: str,
        sslmode: str = "prefer",
        readonly_confirmed: bool = False,
    ) -> int: ...

    @abstractmethod
    def list(self) -> list[dict]:
        """Connection metadata WITHOUT passwords — safe to return in an API response."""

    @abstractmethod
    def get_with_credentials(self, connection_id: int) -> dict | None:
        """Includes the decrypted password. Only call where a live connection is
        actually being built (never to serve an API/UI response)."""

    @abstractmethod
    def delete(self, connection_id: int) -> None: ...


class ReportRepository(ABC):
    """Persistence boundary for saved, reusable report questions."""

    @abstractmethod
    def save(self, *, connection_id: int, name: str, question: str) -> int: ...

    @abstractmethod
    def list(self, connection_id: int | None = None) -> list[dict]: ...

    @abstractmethod
    def get(self, report_id: int) -> dict | None: ...

    @abstractmethod
    def delete(self, report_id: int) -> None: ...


class LLMConfigRepository(ABC):
    """Persistence boundary for the deployment's single LLM provider config."""

    @abstractmethod
    def save(
        self, *, provider: str, endpoint: str, deployment_name: str, api_version: str, api_key: str
    ) -> None: ...

    @abstractmethod
    def get(self) -> dict | None:
        """Includes the decrypted API key. Never return this directly in an
        API/UI response model — strip the key first."""
