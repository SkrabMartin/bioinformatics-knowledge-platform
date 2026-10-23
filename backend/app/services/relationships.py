from collections import defaultdict
from math import ceil
from typing import Any, cast
from urllib.parse import quote

from sqlalchemy import func, literal, or_, select, union_all
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import (
    BiologicalProcess,
    Disease,
    Gene,
    GeneBiologicalProcess,
    GeneDiseaseAssociation,
    GenePathway,
    MolecularFunction,
    OntologyParent,
    OntologyTerm,
    Pathway,
    Protein,
    ProteinInteraction,
    ProteinMolecularFunction,
    Publication,
    PublicationDisease,
    PublicationGene,
    PublicationProtein,
    Variant,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.schemas.common import Page
from app.schemas.relationship import (
    EntityType,
    GeneDiseaseCreate,
    Predicate,
    ProteinInteractionCreate,
    RelationshipNode,
    RelationshipRead,
    RelationshipType,
    VariantDiseaseCreate,
    VariantGeneCreate,
)
from app.services import ontology_relationships as knowledge
from app.services.entities import model_values
from app.services.errors import ConflictError, InvalidInputError, NotFoundError

RelationshipRecord = (
    GeneDiseaseAssociation
    | VariantGeneLocation
    | VariantDiseaseAssociation
    | ProteinInteraction
    | Protein
    | PublicationGene
    | PublicationProtein
    | PublicationDisease
    | GenePathway
    | GeneBiologicalProcess
    | ProteinMolecularFunction
    | OntologyParent
)

PUBLICATION_RELATIONS: tuple[tuple[str, Any, Any], ...] = (
    ("publication_gene", PublicationGene, PublicationGene.gene),
    ("publication_protein", PublicationProtein, PublicationProtein.protein),
    ("publication_disease", PublicationDisease, PublicationDisease.disease),
)


class RelationshipService:
    """Persist typed edges and page an entity's incident edges in the database."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def node_for(self, entity_type: EntityType, entity_id: int) -> RelationshipNode:
        model = {
            "gene": Gene,
            "protein": Protein,
            "variant": Variant,
            "disease": Disease,
            "publication": Publication,
            "pathway": Pathway,
            "biological_process": BiologicalProcess,
            "molecular_function": MolecularFunction,
        }[entity_type]
        record = self._require(model, entity_id)
        if isinstance(record, (Pathway, OntologyTerm)):
            return knowledge.knowledge_node(record)
        if isinstance(record, Gene):
            return _gene_node(record)
        if isinstance(record, Protein):
            return _protein_node(record)
        if isinstance(record, Variant):
            return _variant_node(record)
        if isinstance(record, Disease):
            return _disease_node(record)
        return _publication_node(cast(Publication, record))

    def read_many(self, references: list[tuple[RelationshipType, int]]) -> list[RelationshipRead]:
        """Hydrate only a bounded set of explicit edge references, without count queries."""
        ids: dict[str, set[int]] = defaultdict(set)
        for kind, identifier in references:
            ids[kind].add(identifier)
        records = self._load_records(ids)
        result = []
        for kind, identifier in references:
            record = records.get(kind, {}).get(identifier)
            if record is None or (isinstance(record, Protein) and record.gene is None):
                continue
            result.append(self._serialize(kind, record))
        return result

    def create_gene_disease(self, data: GeneDiseaseCreate) -> RelationshipRead:
        self._require(Gene, data.gene_id)
        self._require(Disease, data.disease_id)
        edge = GeneDiseaseAssociation(**model_values(data))
        return self._persist(edge, "gene_disease")

    def create_publication_link(
        self, edge: PublicationGene | PublicationProtein | PublicationDisease, kind: str
    ) -> RelationshipRead:
        return self._persist(edge, kind)

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
        model = {
            "gene": Gene,
            "protein": Protein,
            "variant": Variant,
            "disease": Disease,
            "publication": Publication,
            "pathway": Pathway,
            "biological_process": BiologicalProcess,
            "molecular_function": MolecularFunction,
        }[entity_type]
        self._require(model, entity_id)
        statements = self._index_statements(entity_type, entity_id)
        statements.extend(knowledge.index_statements(entity_type, entity_id))
        for kind, edge_model, foreign_key in (
            ("publication_gene", PublicationGene, PublicationGene.gene_id),
            ("publication_protein", PublicationProtein, PublicationProtein.protein_id),
            ("publication_disease", PublicationDisease, PublicationDisease.disease_id),
        ):
            if entity_type == "publication" or entity_type == kind.removeprefix("publication_"):
                condition = (
                    edge_model.publication_id == entity_id
                    if entity_type == "publication"
                    else foreign_key == entity_id
                )
                statements.append(
                    select(
                        literal(kind).label("kind"),
                        edge_model.id.label("relation_id"),
                        edge_model.created_at.label("created_at"),
                    ).where(condition)
                )
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
        if entity_type == "publication" or entity_type in knowledge.KNOWLEDGE_KINDS:
            return []

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
        records: dict[str, dict[int, RelationshipRecord]] = knowledge.load_records(
            self.session, ids_by_kind
        )
        for kind, edge_model, target in PUBLICATION_RELATIONS:
            if ids := ids_by_kind.get(kind):
                options = [selectinload(edge_model.publication), selectinload(target)]
                if kind == "publication_gene":
                    options.append(selectinload(PublicationGene.gene).selectinload(Gene.organism))
                rows = self.session.scalars(
                    select(edge_model).where(edge_model.id.in_(ids)).options(*options)
                ).all()
                records[kind] = {row.id: row for row in rows}
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
        predicate: Predicate
        if isinstance(
            record, (GenePathway, GeneBiologicalProcess, ProteinMolecularFunction, OntologyParent)
        ):
            first, second, predicate = knowledge.endpoints(record)
            if isinstance(first, Gene):
                subject = _gene_node(first)
            elif isinstance(first, Protein):
                subject = _protein_node(first)
            else:
                subject = knowledge.knowledge_node(first)
            object_ = knowledge.knowledge_node(second)
        elif isinstance(record, (PublicationGene, PublicationProtein, PublicationDisease)):
            subject = _publication_node(record.publication)
            if isinstance(record, PublicationGene):
                object_, predicate = _gene_node(record.gene), "mentions"
            elif isinstance(record, PublicationProtein):
                object_, predicate = _protein_node(record.protein), "discusses"
            else:
                object_, predicate = _disease_node(record.disease), "studies"
        elif isinstance(record, GeneDiseaseAssociation):
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
            relationship_type=cast(RelationshipType, kind),
            relationship_id=record.id,
            predicate=predicate,
            subject=subject,
            object=object_,
            source=record.source,
            source_identifier=record.source_identifier,
            source_url=record.source_url,
            imported_at=record.imported_at,
            evidence_text=None if isinstance(record, Protein) else record.evidence_text,
            evidence_kind=record.evidence_kind
            if isinstance(
                record,
                (
                    PublicationGene,
                    PublicationProtein,
                    PublicationDisease,
                    GenePathway,
                    GeneBiologicalProcess,
                    ProteinMolecularFunction,
                ),
            )
            else None,
            source_release=getattr(record, "source_release", None),
            evidence_code=getattr(record, "evidence_code", None),
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


def _publication_node(publication: Publication) -> RelationshipNode:
    return RelationshipNode(
        entity_type="publication",
        entity_id=publication.id,
        label=publication.title,
        href=f"/publication/{publication.id}",
    )
