from pydantic import BaseModel, Field


class ConnectionTestRequest(BaseModel):
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    password: str
    sslmode: str = "prefer"


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str


class ConnectionCreate(ConnectionTestRequest):
    name: str
    readonly_confirmed: bool = Field(
        ..., description="Must be true — the database user must be confirmed read-only before saving."
    )


class ConnectionSummary(BaseModel):
    """Never includes the password, encrypted or otherwise — this is what an
    API client or the UI's connection list actually sees."""

    id: int
    name: str
    db_type: str
    host: str
    port: int
    database_name: str
    username: str
    sslmode: str
    readonly_confirmed: bool
