"""Focused serialization and hydration for Phase 7's explicit relationship tables."""

from typing import Any, cast

from sqlalchemy import literal, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Gene,
    GeneBiologicalProcess,
    GenePathway,
    OntologyParent,
    OntologyTerm,
    Pathway,
    Protein,
    ProteinMolecularFunction,
)
from app.schemas.relationship import EntityType, Predicate, RelationshipNode

KnowledgeEdge = GenePathway | GeneBiologicalProcess | ProteinMolecularFunction | OntologyParent
KNOWLEDGE_KINDS = {"pathway", "biological_process", "molecular_function"}


def knowledge_node(record: Pathway | OntologyTerm) -> RelationshipNode:
    kind = "pathway" if isinstance(record, Pathway) else record.kind
    label = record.name if isinstance(record, Pathway) else f"{record.go_id} · {record.name}"
    return RelationshipNode(
        entity_type=cast(EntityType, kind),
        entity_id=record.id,
        label=label,
        href=f"/{kind.replace('_', '-')}/{record.id}",
    )


def specs() -> list[tuple[str, Any, EntityType, Any, EntityType, Any, Any]]:
    return [
        (
            "gene_pathway",
            GenePathway,
            "gene",
            GenePathway.gene_id,
            "pathway",
            GenePathway.pathway_id,
            None,
        ),
        (
            "gene_biological_process",
            GeneBiologicalProcess,
            "gene",
            GeneBiologicalProcess.gene_id,
            "biological_process",
            GeneBiologicalProcess.term_id,
            None,
        ),
        (
            "protein_molecular_function",
            ProteinMolecularFunction,
            "protein",
            ProteinMolecularFunction.protein_id,
            "molecular_function",
            ProteinMolecularFunction.term_id,
            None,
        ),
        (
            "biological_process_parent",
            OntologyParent,
            "biological_process",
            OntologyParent.child_id,
            "biological_process",
            OntologyParent.parent_id,
            OntologyParent.kind == "biological_process",
        ),
        (
            "molecular_function_parent",
            OntologyParent,
            "molecular_function",
            OntologyParent.child_id,
            "molecular_function",
            OntologyParent.parent_id,
            OntologyParent.kind == "molecular_function",
        ),
    ]


def index_statements(entity_type: EntityType, entity_id: int) -> list[Any]:
    result = []
    for kind, model, subject_type, subject, object_type, object_, extra in specs():
        conditions = []
        if entity_type == subject_type:
            conditions.append(subject == entity_id)
        if entity_type == object_type:
            conditions.append(object_ == entity_id)
        if conditions:
            statement = select(
                literal(kind).label("kind"),
                model.id.label("relation_id"),
                model.created_at.label("created_at"),
            ).where(or_(*conditions))
            result.append(statement if extra is None else statement.where(extra))
    return result


def load_records(session: Session, ids: dict[str, set[int]]) -> dict[str, dict[int, Any]]:
    result = {}
    options = {
        "gene_pathway": [
            selectinload(GenePathway.gene).selectinload(Gene.organism),
            selectinload(GenePathway.pathway),
        ],
        "gene_biological_process": [
            selectinload(GeneBiologicalProcess.gene).selectinload(Gene.organism),
            selectinload(GeneBiologicalProcess.term),
        ],
        "protein_molecular_function": [
            selectinload(ProteinMolecularFunction.protein),
            selectinload(ProteinMolecularFunction.term),
        ],
        "biological_process_parent": [
            selectinload(OntologyParent.child),
            selectinload(OntologyParent.parent),
        ],
        "molecular_function_parent": [
            selectinload(OntologyParent.child),
            selectinload(OntologyParent.parent),
        ],
    }
    for kind, model, *_ in specs():
        if identifiers := ids.get(kind):
            rows = session.scalars(
                select(model).where(model.id.in_(identifiers)).options(*options[kind])
            ).all()
            result[kind] = {row.id: row for row in rows}
    return result


def endpoints(
    record: KnowledgeEdge,
) -> tuple[OntologyTerm | Gene | Protein, Pathway | OntologyTerm, Predicate]:
    if isinstance(record, GenePathway):
        return record.gene, record.pathway, "participates_in"
    if isinstance(record, GeneBiologicalProcess):
        return record.gene, record.term, "involved_in"
    if isinstance(record, ProteinMolecularFunction):
        return record.protein, record.term, "has_function"
    return record.child, record.parent, "is_a"
