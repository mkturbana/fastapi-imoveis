import logging
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.requests import Request

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handler para erros HTTP"""
    error_detail = exc.detail if exc.detail else "Erro desconhecido"
    logging.error(f"Erro HTTP: {error_detail}")
    return JSONResponse(status_code=exc.status_code, content={"detail": error_detail})

async def custom_exception_handler(request: Request, exc: Exception):
    """Handler para erros genéricos"""
    logging.exception(f"Erro interno: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor."})
