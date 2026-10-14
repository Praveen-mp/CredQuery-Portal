from fastapi import APIRouter, Depends, HTTPException

from dbchat.agent.builder import LLMNotConfiguredError
from dbchat.api.schemas.reports import ReportCreate, ReportRunResult, ReportSummary
from dbchat.deps import get_report_service
from dbchat.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportSummary])
def list_reports(connection_id: int | None = None, service: ReportService = Depends(get_report_service)):
    return service.list(connection_id=connection_id)


@router.post("", response_model=ReportSummary, status_code=201)
def create_report(payload: ReportCreate, service: ReportService = Depends(get_report_service)):
    report_id = service.save(**payload.model_dump())
    return next(r for r in service.list(connection_id=payload.connection_id) if r["id"] == report_id)


@router.post("/{report_id}/run", response_model=ReportRunResult)
def run_report(report_id: int, service: ReportService = Depends(get_report_service)):
    try:
        return service.run(report_id)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # the connection may be unreachable, creds changed, etc.
        raise HTTPException(status_code=502, detail=f"Couldn't run report: {exc}") from exc


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, service: ReportService = Depends(get_report_service)):
    service.delete(report_id)
