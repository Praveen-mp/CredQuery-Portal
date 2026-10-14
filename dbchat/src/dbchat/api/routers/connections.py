from fastapi import APIRouter, Depends, HTTPException

from dbchat.api.schemas.connections import (
    ConnectionCreate,
    ConnectionSummary,
    ConnectionTestRequest,
    ConnectionTestResult,
)
from dbchat.deps import get_connection_service
from dbchat.services.connection_service import ConnectionService

router = APIRouter(prefix="/connections", tags=["connections"])


@router.get("", response_model=list[ConnectionSummary])
def list_connections(service: ConnectionService = Depends(get_connection_service)):
    return service.list()


@router.post("/test", response_model=ConnectionTestResult)
def test_connection(
    payload: ConnectionTestRequest, service: ConnectionService = Depends(get_connection_service)
):
    ok, message = service.test(**payload.model_dump())
    return ConnectionTestResult(ok=ok, message=message)


@router.post("", response_model=ConnectionSummary, status_code=201)
def create_connection(
    payload: ConnectionCreate, service: ConnectionService = Depends(get_connection_service)
):
    try:
        connection_id = service.create(**payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return next(c for c in service.list() if c["id"] == connection_id)


@router.delete("/{connection_id}", status_code=204)
def delete_connection(connection_id: int, service: ConnectionService = Depends(get_connection_service)):
    service.delete(connection_id)
