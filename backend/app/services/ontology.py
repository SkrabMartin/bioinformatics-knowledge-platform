from math import ceil
from typing import cast

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    BiologicalProcess,
    Gene,
    GeneBiologicalProcess,
    GenePathway,
    MolecularFunction,
    OntologyParent,
    OntologyTerm,
    Organism,
    Pathway,
    Protein,
    ProteinMolecularFunction,
)
from app.repositories.ontology import KnowledgeRepository
from app.schemas.common import Page
from app.schemas.ontology import (
    AnnotationCreate,
    KnowledgeKind,
    ParentCreate,
    PathwayCreate,
    PathwayRead,
    TermCreate,
    TermRead,
)
from app.schemas.relationship import RelationshipRead, RelationshipType
from app.services.entities import model_values
from app.services.errors import ConflictError, NotFoundError
from app.services.relationships import RelationshipService


class KnowledgeService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = KnowledgeRepository(session)

    def get(self, kind: KnowledgeKind, identifier: int) -> Pathway | OntologyTerm:
        models: dict[KnowledgeKind, type[Pathway] | type[OntologyTerm]] = {
            "pathway": Pathway,
            "biological_process": BiologicalProcess,
            "molecular_function": MolecularFunction,
        }
        record = cast(Pathway | OntologyTerm | None, self.session.get(models[kind], identifier))
        if record is None:
            raise NotFoundError(f"{kind} {identifier} was not found.")
        return record

    def browse(
        self, kind: KnowledgeKind, *, page: int, page_size: int, query: str | None
    ) -> Page[PathwayRead | TermRead]:
        items, total = self.repository.browse(kind, page=page, page_size=page_size, query=query)
        return Page(
            items=[
                PathwayRead.model_validate(row)
                if isinstance(row, Pathway)
                else TermRead.model_validate(row)
                for row in items
            ],
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def create_pathway(self, data: PathwayCreate) -> Pathway:
        if data.organism_id is not None and self.session.get(Organism, data.organism_id) is None:
            raise NotFoundError(f"Organism {data.organism_id} was not found.")
        record = Pathway(**model_values(data))
        self._persist(record)
        return record

    def create_term(self, data: TermCreate) -> OntologyTerm:
        model = BiologicalProcess if data.kind == "biological_process" else MolecularFunction
        record = model(**model_values(data))
        self._persist(record)
        return record

    def _persist(
        self,
        record: Pathway
        | OntologyTerm
        | OntologyParent
        | GenePathway
        | GeneBiologicalProcess
        | ProteinMolecularFunction,
    ) -> None:
        try:
            self.session.add(record)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError(
                "Record conflicts with an existing identifier or assertion."
            ) from exc

    def annotate(
        self, kind: KnowledgeKind, identifier: int, data: AnnotationCreate
    ) -> RelationshipRead:
        target = self.get(kind, identifier)
        entity_model: type[Protein] | type[Gene] = Protein if kind == "molecular_function" else Gene
        entity = cast(Gene | Protein | None, self.session.get(entity_model, data.entity_id))
        if entity is None:
            raise NotFoundError(f"{entity_model.__name__} {data.entity_id} was not found.")
        values = model_values(data)
        values.pop("entity_id")
        relation: RelationshipType
        if isinstance(target, Pathway):
            # Serialize with gene-organism updates, which use the same row lock.
            self.session.refresh(entity, with_for_update=True)
            if target.organism_id is not None and entity.organism_id != target.organism_id:
                raise ConflictError("Gene and organism-specific pathway must share an organism.")
            edge: GenePathway | GeneBiologicalProcess | ProteinMolecularFunction = GenePathway(
                gene_id=entity.id, pathway_id=identifier, **values
            )
            relation = "gene_pathway"
        elif kind == "biological_process":
            edge = GeneBiologicalProcess(gene_id=entity.id, term_id=identifier, **values)
            relation = "gene_biological_process"
        else:
            edge = ProteinMolecularFunction(protein_id=entity.id, term_id=identifier, **values)
            relation = "protein_molecular_function"
        self._persist(edge)
        return RelationshipService(self.session).read_many([(relation, edge.id)])[0]

    def add_parent(
        self, kind: KnowledgeKind, identifier: int, data: ParentCreate
    ) -> RelationshipRead:
        if kind == "pathway":
            raise ConflictError("Pathway hierarchy is not an ontology is_a hierarchy.")
        self.get(kind, identifier)
        self.get(kind, data.parent_id)
        if identifier == data.parent_id:
            raise ConflictError("A term cannot be its own parent.")
        # Nonblocking transaction lock serializes hierarchy mutation checks.
        # READ COMMITTED's next statement sees the last committed DAG.
        if self.session.get_bind().dialect.name == "postgresql" and not self.session.scalar(
            text("SELECT pg_try_advisory_xact_lock(724017)")
        ):
            raise ConflictError("Ontology hierarchy is being updated; retry the operation.")
        ancestors = self.repository.ancestors(data.parent_id)
        if identifier in ancestors:
            raise ConflictError("This parent would introduce an ontology cycle.")
        if len(ancestors) > 1000:
            raise ConflictError("Hierarchy validation exceeds its bounded ancestor budget.")
        values = model_values(data)
        values.pop("parent_id")
        edge = OntologyParent(child_id=identifier, parent_id=data.parent_id, kind=kind, **values)
        self._persist(edge)
        relation: RelationshipType = (
            "biological_process_parent"
            if kind == "biological_process"
            else "molecular_function_parent"
        )
        return RelationshipService(self.session).read_many([(relation, edge.id)])[0]
