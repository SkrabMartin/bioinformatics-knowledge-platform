from app.core.identifiers import GeneIdentifierNamespace
from app.schemas.common import ApiModel, StoredProvenanceFields


class GeneIdentifierEvidenceRead(StoredProvenanceFields):
    reported_accession: str
    source_record_version: str | None


class GeneExternalIdentifierRead(ApiModel):
    id: int
    namespace: GeneIdentifierNamespace
    accession: str
    evidence: list[GeneIdentifierEvidenceRead]
