from dataclasses import dataclass
from typing import Any

from sqlalchemy import literal, or_, select, union_all
from sqlalchemy.orm import Session
from sqlalchemy.sql import ColumnElement

from app.models import (
    GeneDiseaseAssociation,
    Protein,
    ProteinInteraction,
    PublicationDisease,
    PublicationGene,
    PublicationProtein,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.schemas.graph import GraphLimits
from app.schemas.relationship import EntityType, RelationshipType


@dataclass(frozen=True)
class EdgeSpec:
    kind: RelationshipType
    model: Any
    subject_type: EntityType
    subject: Any
    object_type: EntityType
    object: Any


SPECS = (
    EdgeSpec("gene_protein", Protein, "gene", Protein.gene_id, "protein", Protein.id),
    EdgeSpec(
        "gene_disease",
        GeneDiseaseAssociation,
        "gene",
        GeneDiseaseAssociation.gene_id,
        "disease",
        GeneDiseaseAssociation.disease_id,
    ),
    EdgeSpec(
        "variant_gene",
        VariantGeneLocation,
        "variant",
        VariantGeneLocation.variant_id,
        "gene",
        VariantGeneLocation.gene_id,
    ),
    EdgeSpec(
        "variant_disease",
        VariantDiseaseAssociation,
        "variant",
        VariantDiseaseAssociation.variant_id,
        "disease",
        VariantDiseaseAssociation.disease_id,
    ),
    EdgeSpec(
        "protein_interaction",
        ProteinInteraction,
        "protein",
        ProteinInteraction.protein_a_id,
        "protein",
        ProteinInteraction.protein_b_id,
    ),
    EdgeSpec(
        "publication_gene",
        PublicationGene,
        "publication",
        PublicationGene.publication_id,
        "gene",
        PublicationGene.gene_id,
    ),
    EdgeSpec(
        "publication_protein",
        PublicationProtein,
        "publication",
        PublicationProtein.publication_id,
        "protein",
        PublicationProtein.protein_id,
    ),
    EdgeSpec(
        "publication_disease",
        PublicationDisease,
        "publication",
        PublicationDisease.publication_id,
        "disease",
        PublicationDisease.disease_id,
    ),
)


@dataclass(frozen=True)
class EdgeIndex:
    kind: RelationshipType
    entity_id: int
    subject_type: EntityType
    subject_id: int
    object_type: EntityType
    object_id: int


class GraphRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def incident(
        self,
        frontier: dict[EntityType, list[int]],
        *,
        limits: GraphLimits,
        seen: dict[RelationshipType, list[int]],
        limit: int,
        within: dict[EntityType, list[int]] | None = None,
    ) -> list[EdgeIndex]:
        statements = []
        for spec in SPECS:
            if limits.relationship_types and spec.kind not in limits.relationship_types:
                continue
            if limits.entity_types and (
                spec.subject_type not in limits.entity_types
                or spec.object_type not in limits.entity_types
            ):
                continue
            conditions: list[ColumnElement[bool]] = []
            if ids := frontier.get(spec.subject_type):
                conditions.append(spec.subject.in_(ids))
            if ids := frontier.get(spec.object_type):
                conditions.append(spec.object.in_(ids))
            if not conditions:
                continue
            statement = select(
                literal(spec.kind).label("kind"),
                spec.model.id.label("relation_id"),
                literal(spec.subject_type).label("subject_type"),
                spec.subject.label("subject_id"),
                literal(spec.object_type).label("object_type"),
                spec.object.label("object_id"),
            ).where(or_(*conditions), spec.subject.is_not(None), spec.object.is_not(None))
            if excluded := seen.get(spec.kind):
                statement = statement.where(spec.model.id.not_in(excluded))
            if within is not None:
                statement = statement.where(
                    spec.subject.in_(within.get(spec.subject_type, [])),
                    spec.object.in_(within.get(spec.object_type, [])),
                )
            # Bound each branch before combining/sorting; don't enumerate a hub's entire degree.
            branch = statement.order_by(spec.model.id).limit(limit).subquery()
            statements.append(select(branch))
        if not statements:
            return []
        combined = union_all(*statements).subquery()
        rows = self.session.execute(
            select(combined)
            .order_by(
                combined.c.kind,
                combined.c.relation_id,
            )
            .limit(limit)
        ).mappings()
        return [
            EdgeIndex(
                row["kind"],
                row["relation_id"],
                row["subject_type"],
                row["subject_id"],
                row["object_type"],
                row["object_id"],
            )
            for row in rows
        ]
