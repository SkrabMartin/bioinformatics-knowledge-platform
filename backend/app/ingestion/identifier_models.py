from pydantic import Field, model_validator

from app.core.identifiers import GeneIdentifierNamespace, canonical_gene_identifier
from app.ingestion.models_base import NormalizedModel


class NormalizedGeneIdentifier(NormalizedModel):
    namespace: GeneIdentifierNamespace
    accession: str = Field(min_length=1, max_length=64)
    reported_accession: str = Field(min_length=1, max_length=80)

    @model_validator(mode="after")
    def valid_identity(self) -> "NormalizedGeneIdentifier":
        if canonical_gene_identifier(self.namespace, self.reported_accession) != self.accession:
            raise ValueError("Reported and canonical identifier disagree.")
        return self
