"""Explicit gene identifier namespaces; aliases never establish identity."""

import re
from typing import Literal

GeneIdentifierNamespace = Literal["ncbi_gene", "ensembl_gene"]


def canonical_gene_identifier(namespace: str, reported: str) -> str:
    value = reported.strip()
    if namespace == "ncbi_gene" and re.fullmatch(r"[1-9][0-9]{0,15}", value):
        return value
    if namespace == "ensembl_gene" and re.fullmatch(
        r"ENS[A-Z]*G[0-9]{6,20}(?:\.[1-9][0-9]{0,8})?", value
    ):
        return value.split(".", 1)[0]
    raise ValueError("Unsupported gene identifier namespace or format.")
