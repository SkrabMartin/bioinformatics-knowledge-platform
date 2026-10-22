import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings
from app.services.errors import ApplicationError

bearer = HTTPBearer(auto_error=False)


class AdminAccessError(ApplicationError):
    status_code = 401
    code = "admin_access_required"


def require_admin(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> None:
    configured = get_settings().admin_api_token
    if not configured or not configured.get_secret_value():
        error = AdminAccessError(
            "New write endpoints are disabled until BKP_ADMIN_API_TOKEN is configured."
        )
        error.status_code = 503
        raise error
    supplied = credentials.credentials if credentials else ""
    if not secrets.compare_digest(supplied.encode(), configured.get_secret_value().encode()):
        raise AdminAccessError("A valid administrator bearer token is required.")
