from typing import TYPE_CHECKING

from sqlalchemy import Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import ProvenanceMixin
from app.models.types import BIGINT_PK

if TYPE_CHECKING:
    from app.models.gene import Gene
    from app.models.protein import Protein


class Organism(ProvenanceMixin, Base):
    __tablename__ = "organisms"
    __table_args__ = (
        UniqueConstraint("taxonomy_id", name="uq_organisms_taxonomy_id"),
        Index(
            "ix_organisms_search_document",
            text(
                "to_tsvector('simple', coalesce(scientific_name, '') || ' ' || "
                "coalesce(common_name, '') || ' ' || coalesce(taxonomy_id, ''))"
            ),
            postgresql_using="gin",
        ).ddl_if(dialect="postgresql"),
        Index(
            "ix_organisms_scientific_name_trgm",
            "scientific_name",
            postgresql_using="gin",
            postgresql_ops={"scientific_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_organisms_common_name_trgm",
            "common_name",
            postgresql_using="gin",
            postgresql_ops={"common_name": "gin_trgm_ops"},
        ),
        Index(
            "ix_organisms_taxonomy_id_trgm",
            "taxonomy_id",
            postgresql_using="gin",
            postgresql_ops={"taxonomy_id": "gin_trgm_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PK, primary_key=True, autoincrement=True)
    scientific_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    common_name: Mapped[str | None] = mapped_column(String(255))
    taxonomy_id: Mapped[str | None] = mapped_column(String(32), index=True)

    genes: Mapped[list["Gene"]] = relationship(back_populates="organism")
    proteins: Mapped[list["Protein"]] = relationship(back_populates="organism")
