from fastapi import APIRouter

router = APIRouter(tags=["operations"])


@router.get("/health", summary="Check API liveness")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "bio-knowledge-platform-api"}
