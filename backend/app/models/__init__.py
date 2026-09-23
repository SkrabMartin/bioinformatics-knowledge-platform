from app.models.disease import Disease
from app.models.gene import Gene
from app.models.organism import Organism
from app.models.protein import Protein
from app.models.relationships import (
    GeneDiseaseAssociation,
    ProteinInteraction,
    VariantDiseaseAssociation,
    VariantGeneLocation,
)
from app.models.variant import Variant

__all__ = [
    "Disease",
    "Gene",
    "GeneDiseaseAssociation",
    "Organism",
    "Protein",
    "ProteinInteraction",
    "Variant",
    "VariantDiseaseAssociation",
    "VariantGeneLocation",
]
