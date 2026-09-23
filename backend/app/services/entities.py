from math import ceil
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models import (
    Disease,
    Gene,
    Organism,
    Protein,
    Variant,
    VariantGeneLocation,
)
from app.repositories.base import Repository
from app.repositories.diseases import DiseaseRepository
from app.repositories.genes import GeneRepository
from app.repositories.organisms import OrganismRepository
from app.repositories.proteins import ProteinRepository
from app.repositories.variants import VariantRepository
from app.schemas.common import Page
from app.schemas.disease import DiseaseCreate, DiseaseUpdate
from app.schemas.gene import GeneCreate, GeneUpdate
from app.schemas.organism import OrganismCreate, OrganismUpdate
from app.schemas.protein import ProteinCreate, ProteinUpdate
from app.schemas.variant import VariantCreate, VariantUpdate
from app.services.errors import ConflictError, InvalidInputError, NotFoundError


class EntityService[ModelT: Base]:
    entity_name: str

    def __init__(self, session: Session, repository: Repository[ModelT]) -> None:
        self.session = session
        self.repository = repository

    def get(self, entity_id: int) -> ModelT:
        entity = self.repository.get(entity_id)
        if entity is None:
            error = NotFoundError(f"{self.entity_name} {entity_id} was not found.")
            error.code = f"{self.entity_name.lower()}_not_found"
            raise error
        return entity

    def list(self, *, page: int, page_size: int) -> Page[Any]:
        items, total = self.repository.list(page=page, page_size=page_size)
        return Page(
            items=list(items),
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def persist(self, entity: ModelT) -> ModelT:
        try:
            self.repository.add(entity)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(f"{self.entity_name} conflicts with an existing record.") from exc
        return self.get(cast(int, getattr(entity, "id")))  # noqa: B009

    def update_fields(self, entity: ModelT, values: dict[str, Any]) -> ModelT:
        for field, value in values.items():
            setattr(entity, field, value)
        try:
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(f"{self.entity_name} conflicts with an existing record.") from exc
        return self.get(cast(int, getattr(entity, "id")))  # noqa: B009


class OrganismService(EntityService[Organism]):
    entity_name = "Organism"

    def __init__(self, session: Session) -> None:
        super().__init__(session, OrganismRepository(session))

    def create(self, data: OrganismCreate) -> Organism:
        return self.persist(Organism(**model_values(data)))

    def update(self, entity_id: int, data: OrganismUpdate) -> Organism:
        return self.update_fields(self.get(entity_id), model_values(data, exclude_unset=True))


class GeneService(EntityService[Gene]):
    entity_name = "Gene"

    def __init__(self, session: Session) -> None:
        self.gene_repository = GeneRepository(session)
        super().__init__(session, self.gene_repository)

    def _require_organism(self, organism_id: int) -> None:
        if OrganismRepository(self.session).get(organism_id) is None:
            raise NotFoundError(f"Organism {organism_id} was not found.")

    def create(self, data: GeneCreate) -> Gene:
        self._require_organism(data.organism_id)
        return self.persist(Gene(**model_values(data)))

    def get_by_symbol(self, symbol: str, taxonomy_id: str) -> Gene:
        gene = self.gene_repository.by_symbol_and_taxonomy(symbol, taxonomy_id)
        if gene is None:
            raise NotFoundError(f"Gene {symbol} was not found for taxonomy {taxonomy_id}.")
        return gene

    def update(self, entity_id: int, data: GeneUpdate) -> Gene:
        entity = self.get(entity_id)
        values = model_values(data, exclude_unset=True)
        if "organism_id" in values:
            self._require_organism(values["organism_id"])
            if values["organism_id"] != entity.organism_id:
                linked_protein = self.session.scalar(
                    select(Protein.id).where(Protein.gene_id == entity_id).limit(1)
                )
                linked_variant = self.session.scalar(
                    select(VariantGeneLocation.id)
                    .where(VariantGeneLocation.gene_id == entity_id)
                    .limit(1)
                )
                if linked_protein is not None or linked_variant is not None:
                    raise ConflictError(
                        "Cannot change a gene's organism while relationships exist."
                    )
        start = values.get("start_position", entity.start_position)
        end = values.get("end_position", entity.end_position)
        if start is not None and end is not None and end < start:
            raise InvalidInputError("end_position must be greater than or equal to start_position.")
        return self.update_fields(entity, values)


class ProteinService(EntityService[Protein]):
    entity_name = "Protein"

    def __init__(self, session: Session) -> None:
        self.protein_repository = ProteinRepository(session)
        super().__init__(session, self.protein_repository)

    def _validate_links(self, organism_id: int, gene_id: int | None) -> None:
        if OrganismRepository(self.session).get(organism_id) is None:
            raise NotFoundError(f"Organism {organism_id} was not found.")
        if gene_id is not None:
            gene = GeneRepository(self.session).get(gene_id)
            if gene is None:
                raise NotFoundError(f"Gene {gene_id} was not found.")
            if gene.organism_id != organism_id:
                raise ConflictError("Protein and encoding gene must belong to the same organism.")

    def create(self, data: ProteinCreate) -> Protein:
        self._validate_links(data.organism_id, data.gene_id)
        return self.persist(Protein(**model_values(data)))

    def get_by_accession(self, accession: str) -> Protein:
        protein = self.protein_repository.by_accession(accession)
        if protein is None:
            raise NotFoundError(f"Protein {accession} was not found.")
        return protein

    def update(self, entity_id: int, data: ProteinUpdate) -> Protein:
        entity = self.get(entity_id)
        values = model_values(data, exclude_unset=True)
        organism_id = values.get("organism_id", entity.organism_id)
        gene_id = values.get("gene_id", entity.gene_id)
        self._validate_links(organism_id, gene_id)
        return self.update_fields(entity, values)


class DiseaseService(EntityService[Disease]):
    entity_name = "Disease"

    def __init__(self, session: Session) -> None:
        self.disease_repository = DiseaseRepository(session)
        super().__init__(session, self.disease_repository)

    def create(self, data: DiseaseCreate) -> Disease:
        return self.persist(Disease(**model_values(data)))

    def get_by_mondo_id(self, mondo_id: str) -> Disease:
        disease = self.disease_repository.by_mondo_id(mondo_id)
        if disease is None:
            raise NotFoundError(f"Disease {mondo_id} was not found.")
        return disease

    def update(self, entity_id: int, data: DiseaseUpdate) -> Disease:
        return self.update_fields(self.get(entity_id), model_values(data, exclude_unset=True))


class VariantService(EntityService[Variant]):
    entity_name = "Variant"

    def __init__(self, session: Session) -> None:
        self.variant_repository = VariantRepository(session)
        super().__init__(session, self.variant_repository)

    def create(self, data: VariantCreate) -> Variant:
        if OrganismRepository(self.session).get(data.organism_id) is None:
            raise NotFoundError(f"Organism {data.organism_id} was not found.")
        return self.persist(Variant(**model_values(data)))

    def get_by_rsid(self, rsid: str) -> Variant:
        variant = self.variant_repository.by_rsid(rsid)
        if variant is None:
            raise NotFoundError(f"Variant {rsid} was not found.")
        return variant

    def update(self, entity_id: int, data: VariantUpdate) -> Variant:
        entity = self.get(entity_id)
        values = model_values(data, exclude_unset=True)
        if (
            "organism_id" in values
            and OrganismRepository(self.session).get(values["organism_id"]) is None
        ):
            raise NotFoundError(f"Organism {values['organism_id']} was not found.")
        if "organism_id" in values and values["organism_id"] != entity.organism_id:
            linked_gene = self.session.scalar(
                select(VariantGeneLocation.id)
                .where(VariantGeneLocation.variant_id == entity_id)
                .limit(1)
            )
            if linked_gene is not None:
                raise ConflictError("Cannot change a variant's organism while gene links exist.")
        if not values.get("rsid", entity.rsid) and not values.get("hgvs", entity.hgvs):
            raise InvalidInputError("A variant requires an rsID or HGVS expression.")
        return self.update_fields(entity, values)


def model_values(model: Any, *, exclude_unset: bool = False) -> dict[str, Any]:
    values: dict[str, Any] = model.model_dump(exclude_unset=exclude_unset)
    if values.get("source_url") is not None:
        values["source_url"] = str(values["source_url"])
    return values
