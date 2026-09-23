from collections import defaultdict
from math import ceil
from typing import Any
from urllib.parse import quote

from sqlalchemy import func, literal, or_, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Disease,
    Gene,
    GeneDiseaseAssociation,
    Protein,
    ProteinInteraction,
    Variant,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.schemas.common import Page
from app.schemas.relationship import (
    EntityType,
    GeneDiseaseCreate,
    ProteinInteractionCreate,
    RelationshipNode,
    RelationshipRead,
    VariantDiseaseCreate,
    VariantGeneCreate,
)
from app.services.entities import model_values
from app.services.errors import ConflictError, InvalidInputError, NotFoundError

RelationshipRecord = (
    GeneDiseaseAssociation
    | VariantGeneLocation
    | VariantDiseaseAssociation
    | ProteinInteraction
    | Protein
)


class RelationshipService:
    """Persist typed edges and page an entity's incident edges in the database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def create_gene_disease(self, data: GeneDiseaseCreate) -> RelationshipRead:
        self._require(Gene, data.gene_id)
        self._require(Disease, data.disease_id)
        edge = GeneDiseaseAssociation(**model_values(data))
        return self._persist(edge, "gene_disease")

    def create_variant_gene(self, data: VariantGeneCreate) -> RelationshipRead:
        variant = self._require(Variant, data.variant_id)
        gene = self._require(Gene, data.gene_id)
        if variant.organism_id != gene.organism_id:
            raise ConflictError("Variant and gene must belong to the same organism.")
        edge = VariantGeneLocation(**model_values(data))
        return self._persist(edge, "variant_gene")

    def create_variant_disease(self, data: VariantDiseaseCreate) -> RelationshipRead:
        self._require(Variant, data.variant_id)
        self._require(Disease, data.disease_id)
        edge = VariantDiseaseAssociation(**model_values(data))
        return self._persist(edge, "variant_disease")

    def create_protein_interaction(self, data: ProteinInteractionCreate) -> RelationshipRead:
        protein_a = self._require(Protein, data.protein_a_id)
        protein_b = self._require(Protein, data.protein_b_id)
        first, second = sorted((protein_a.id, protein_b.id))
        values = model_values(data)
        values["protein_a_id"] = first
        values["protein_b_id"] = second
        edge = ProteinInteraction(**values)
        return self._persist(edge, "protein_interaction")

    def list_for(
        self, entity_type: EntityType, entity_id: int, *, page: int, page_size: int
    ) -> Page[RelationshipRead]:
        model = {"gene": Gene, "protein": Protein, "variant": Variant, "disease": Disease}[
            entity_type
        ]
        self._require(model, entity_id)
        statements = self._index_statements(entity_type, entity_id)
        combined = union_all(*statements).subquery()
        total = self.session.scalar(select(func.count()).select_from(combined)) or 0
        rows = self.session.execute(
            select(combined.c.kind, combined.c.relation_id)
            .order_by(combined.c.created_at.desc(), combined.c.kind, combined.c.relation_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        ids_by_kind: dict[str, set[int]] = defaultdict(set)
        for kind, relation_id in rows:
            ids_by_kind[kind].add(relation_id)
        records = self._load_records(ids_by_kind)
        items = [self._serialize(kind, records[kind][relation_id]) for kind, relation_id in rows]
        return Page(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=ceil(total / page_size) if total else 0,
        )

    def _persist(self, edge: RelationshipRecord, kind: str) -> RelationshipRead:
        try:
            self.session.add(edge)
            self.session.commit()
        except IntegrityError as exc:
            self.session.rollback()
            raise ConflictError("Relationship conflicts with an existing assertion.") from exc
        records = self._load_records({kind: {edge.id}})
        return self._serialize(kind, records[kind][edge.id])

    def _require[ModelT](self, model: type[ModelT], entity_id: int) -> ModelT:
        entity = self.session.get(model, entity_id)
        if entity is None:
            raise NotFoundError(f"{model.__name__} {entity_id} was not found.")
        return entity

    def _index_statements(self, entity_type: EntityType, entity_id: int) -> list[Any]:
        def indexed(kind: str, model: Any, condition: Any) -> Any:
            return select(
                literal(kind).label("kind"),
                model.id.label("relation_id"),
                model.created_at.label("created_at"),
            ).where(condition)

        if entity_type == "gene":
            return [
                indexed(
                    "gene_disease",
                    GeneDiseaseAssociation,
                    GeneDiseaseAssociation.gene_id == entity_id,
                ),
                indexed(
                    "variant_gene", VariantGeneLocation, VariantGeneLocation.gene_id == entity_id
                ),
                indexed("gene_protein", Protein, Protein.gene_id == entity_id),
            ]
        if entity_type == "disease":
            return [
                indexed(
                    "gene_disease",
                    GeneDiseaseAssociation,
                    GeneDiseaseAssociation.disease_id == entity_id,
                ),
                indexed(
                    "variant_disease",
                    VariantDiseaseAssociation,
                    VariantDiseaseAssociation.disease_id == entity_id,
                ),
            ]
        if entity_type == "variant":
            return [
                indexed(
                    "variant_gene", VariantGeneLocation, VariantGeneLocation.variant_id == entity_id
                ),
                indexed(
                    "variant_disease",
                    VariantDiseaseAssociation,
                    VariantDiseaseAssociation.variant_id == entity_id,
                ),
            ]
        return [
            indexed(
                "gene_protein", Protein, (Protein.id == entity_id) & Protein.gene_id.is_not(None)
            ),
            indexed(
                "protein_interaction",
                ProteinInteraction,
                or_(
                    ProteinInteraction.protein_a_id == entity_id,
                    ProteinInteraction.protein_b_id == entity_id,
                ),
            ),
        ]

    def _load_records(
        self, ids_by_kind: dict[str, set[int]]
    ) -> dict[str, dict[int, RelationshipRecord]]:
        records: dict[str, dict[int, RelationshipRecord]] = {}
        if ids := ids_by_kind.get("gene_disease"):
            gene_disease_rows = self.session.scalars(
                select(GeneDiseaseAssociation)
                .where(GeneDiseaseAssociation.id.in_(ids))
                .options(
                    selectinload(GeneDiseaseAssociation.gene).selectinload(Gene.organism),
                    selectinload(GeneDiseaseAssociation.disease),
                )
            ).all()
            records["gene_disease"] = {row.id: row for row in gene_disease_rows}
        if ids := ids_by_kind.get("variant_gene"):
            variant_gene_rows = self.session.scalars(
                select(VariantGeneLocation)
                .where(VariantGeneLocation.id.in_(ids))
                .options(
                    selectinload(VariantGeneLocation.variant),
                    selectinload(VariantGeneLocation.gene).selectinload(Gene.organism),
                )
            ).all()
            records["variant_gene"] = {row.id: row for row in variant_gene_rows}
        if ids := ids_by_kind.get("variant_disease"):
            variant_disease_rows = self.session.scalars(
                select(VariantDiseaseAssociation)
                .where(VariantDiseaseAssociation.id.in_(ids))
                .options(
                    selectinload(VariantDiseaseAssociation.variant),
                    selectinload(VariantDiseaseAssociation.disease),
                )
            ).all()
            records["variant_disease"] = {row.id: row for row in variant_disease_rows}
        if ids := ids_by_kind.get("protein_interaction"):
            protein_interaction_rows = self.session.scalars(
                select(ProteinInteraction)
                .where(ProteinInteraction.id.in_(ids))
                .options(
                    selectinload(ProteinInteraction.protein_a),
                    selectinload(ProteinInteraction.protein_b),
                )
            ).all()
            records["protein_interaction"] = {row.id: row for row in protein_interaction_rows}
        if ids := ids_by_kind.get("gene_protein"):
            gene_protein_rows = self.session.scalars(
                select(Protein)
                .where(Protein.id.in_(ids))
                .options(selectinload(Protein.gene).selectinload(Gene.organism))
            ).all()
            records["gene_protein"] = {row.id: row for row in gene_protein_rows}
        return records

    def _serialize(self, kind: str, record: RelationshipRecord) -> RelationshipRead:
        if isinstance(record, GeneDiseaseAssociation):
            subject, object_ = _gene_node(record.gene), _disease_node(record.disease)
            predicate = "associated_with"
        elif isinstance(record, VariantGeneLocation):
            subject, object_ = _variant_node(record.variant), _gene_node(record.gene)
            predicate = "located_in"
        elif isinstance(record, VariantDiseaseAssociation):
            subject, object_ = _variant_node(record.variant), _disease_node(record.disease)
            predicate = "associated_with"
        elif isinstance(record, ProteinInteraction):
            subject, object_ = _protein_node(record.protein_a), _protein_node(record.protein_b)
            predicate = "interacts_with"
        else:
            if record.gene is None:
                raise InvalidInputError("Unlinked protein cannot form an encoding relationship.")
            subject, object_ = _gene_node(record.gene), _protein_node(record)
            predicate = "encodes"
        return RelationshipRead(
            relationship_type=kind,
            relationship_id=record.id,
            predicate=predicate,
            subject=subject,
            object=object_,
            source=record.source,
            source_identifier=record.source_identifier,
            source_url=record.source_url,
            imported_at=record.imported_at,
            evidence_text=None if isinstance(record, Protein) else record.evidence_text,
            provenance_basis=(
                "protein_record" if isinstance(record, Protein) else "relationship_assertion"
            ),
            created_at=record.created_at,
            updated_at=record.updated_at,
        )


def _gene_node(gene: Gene) -> RelationshipNode:
    taxonomy = gene.organism.taxonomy_id
    suffix = f"?taxonomy_id={quote(taxonomy, safe='')}" if taxonomy else ""
    return RelationshipNode(
        entity_type="gene",
        entity_id=gene.id,
        label=gene.symbol,
        href=f"/gene/{quote(gene.symbol, safe='')}{suffix}",
    )


def _protein_node(protein: Protein) -> RelationshipNode:
    return RelationshipNode(
        entity_type="protein",
        entity_id=protein.id,
        label=protein.accession,
        href=f"/protein/{quote(protein.accession, safe='')}",
    )


def _variant_node(variant: Variant) -> RelationshipNode:
    return RelationshipNode(
        entity_type="variant",
        entity_id=variant.id,
        label=variant.rsid or variant.hgvs or str(variant.id),
        href=f"/variant/{variant.id}",
    )


def _disease_node(disease: Disease) -> RelationshipNode:
    return RelationshipNode(
        entity_type="disease",
        entity_id=disease.id,
        label=disease.name,
        href=f"/disease/{disease.id}",
    )
