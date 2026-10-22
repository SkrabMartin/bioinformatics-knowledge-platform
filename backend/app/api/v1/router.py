from fastapi import APIRouter

from app.api.v1 import (
    diseases,
    genes,
    organisms,
    proteins,
    publications,
    relationships,
    search,
    variants,
)

router = APIRouter(prefix="/v1")
router.include_router(organisms.router)
router.include_router(genes.router)
router.include_router(proteins.router)
router.include_router(diseases.router)
router.include_router(variants.router)
router.include_router(relationships.router)
router.include_router(search.router)
router.include_router(publications.router)
