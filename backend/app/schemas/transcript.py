from typing import Literal

from app.schemas.common import ApiModel, StoredProvenanceFields
from app.schemas.organism import OrganismSummary


class TranscriptSummary(StoredProvenanceFields):
    ensembl_transcript_id: str
    version: int | None
    name: str | None
    biotype: str | None
    assembly_name: str
    sequence_region: str
    start_position: int
    end_position: int
    strand: Literal["+", "-"]
    source_release: str


class TranscriptGene(ApiModel):
    id: int
    symbol: str
    name: str
    organism: OrganismSummary


class TranscriptRead(TranscriptSummary):
    gene_id: int
    gene: TranscriptGene
