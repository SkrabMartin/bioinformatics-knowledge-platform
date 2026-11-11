from fastapi import APIRouter

from app.api.v1 import (
    data_quality,
    diseases,
    genes,
    graph,
    import_jobs,
    ontology,
    organisms,
    phenotypes,
    proteins,
    publications,
    relationships,
    search,
    transcripts,
    variant_placements,
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
router.include_router(graph.router)
router.include_router(ontology.router)

router.include_router(import_jobs.router)

router.include_router(transcripts.router)

router.include_router(data_quality.router)

router.include_router(phenotypes.router)

router.include_router(variant_placements.router)
