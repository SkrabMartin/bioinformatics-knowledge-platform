from app.models.disease import Disease
from app.models.gene import Gene
from app.models.gene_context import GeneAlias, GeneGenomicLocation
from app.models.gene_identifier import GeneExternalIdentifier, GeneIdentifierEvidence
from app.models.import_job import ImportJob, ImportJobItem
from app.models.ontology import (
    BiologicalProcess,
    CellularComponent,
    GeneBiologicalProcess,
    GenePathway,
    MolecularFunction,
    OntologyParent,
    OntologyTerm,
    Pathway,
    ProteinCellularComponent,
    ProteinMolecularFunction,
)
from app.models.organism import Organism
from app.models.phenotype import DiseasePhenotype, Phenotype
from app.models.protein import Protein
from app.models.publication import (
    Publication,
    PublicationDisease,
    PublicationGene,
    PublicationProtein,
)
from app.models.relationships import (
    GeneDiseaseAssociation,
    ProteinInteraction,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.models.transcript import Transcript
from app.models.variant import Variant
from app.models.variant_placement import VariantPlacement

__all__ = [
    "BiologicalProcess",
    "CellularComponent",
    "Disease",
    "DiseasePhenotype",
    "Gene",
    "GeneAlias",
    "GeneBiologicalProcess",
    "GeneDiseaseAssociation",
    "GeneExternalIdentifier",
    "GeneGenomicLocation",
    "GeneIdentifierEvidence",
    "GenePathway",
    "ImportJob",
    "ImportJobItem",
    "MolecularFunction",
    "OntologyParent",
    "OntologyTerm",
    "Organism",
    "Pathway",
    "Phenotype",
    "Protein",
    "ProteinCellularComponent",
    "ProteinInteraction",
    "ProteinMolecularFunction",
    "Publication",
    "PublicationDisease",
    "PublicationGene",
    "PublicationProtein",
    "Transcript",
    "Variant",
    "VariantDiseaseAssociation",
    "VariantGeneLocation",
    "VariantPlacement",
]
