"""Punto de entrada compatible. La implementación está en backend/."""
from backend import create_app, create_api
from backend.config import BASE_DATOS

__all__ = ["create_app", "create_api", "BASE_DATOS"]
