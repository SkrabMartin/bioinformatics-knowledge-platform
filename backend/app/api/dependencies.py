from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.search import SearchService
from app.services.entities import (
    DiseaseService,
    GeneService,
    OrganismService,
    ProteinService,
    VariantService,
)
from app.services.relationships import RelationshipService

DatabaseSession = Annotated[Session, Depends(get_db_session)]


def get_organism_service(session: DatabaseSession) -> OrganismService:
    return OrganismService(session)


def get_gene_service(session: DatabaseSession) -> GeneService:
    return GeneService(session)


def get_protein_service(session: DatabaseSession) -> ProteinService:
    return ProteinService(session)


def get_disease_service(session: DatabaseSession) -> DiseaseService:
    return DiseaseService(session)


def get_variant_service(session: DatabaseSession) -> VariantService:
    return VariantService(session)


def get_relationship_service(session: DatabaseSession) -> RelationshipService:
    return RelationshipService(session)


def get_search_service(session: DatabaseSession) -> SearchService:
    return SearchService(session)


OrganismServiceDependency = Annotated[OrganismService, Depends(get_organism_service)]
GeneServiceDependency = Annotated[GeneService, Depends(get_gene_service)]
ProteinServiceDependency = Annotated[ProteinService, Depends(get_protein_service)]
DiseaseServiceDependency = Annotated[DiseaseService, Depends(get_disease_service)]
VariantServiceDependency = Annotated[VariantService, Depends(get_variant_service)]
RelationshipServiceDependency = Annotated[RelationshipService, Depends(get_relationship_service)]
SearchServiceDependency = Annotated[SearchService, Depends(get_search_service)]
