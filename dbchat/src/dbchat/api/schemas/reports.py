from pydantic import BaseModel


class ReportCreate(BaseModel):
    connection_id: int
    name: str
    question: str


class ReportSummary(BaseModel):
    id: int
    connection_id: int
    name: str
    question: str


class ReportRunResult(BaseModel):
    answer: str
    rows: list[dict] | None = None
