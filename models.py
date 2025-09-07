from typing import List

from sqlalchemy import ForeignKey
from sqlalchemy.orm import registry, relationship, Mapped, mapped_column

mapper_registry = registry()

@mapper_registry.mapped
class Source:
    __tablename__ = 'source'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    quotes: Mapped[List["Quote"]] = relationship(back_populates="source")

@mapper_registry.mapped
class Quote:
    __tablename__ = 'quote'

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    text: Mapped[str] = mapped_column(unique=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("source.id"), nullable=False)
    weight: Mapped[float] = mapped_column(default=1.0, nullable=False)
    views: Mapped[int] = mapped_column(default=0, nullable=False)
    likes: Mapped[int] = mapped_column(default=0, nullable=False)
    dislikes: Mapped[int] = mapped_column(default=0, nullable=False)

    source: Mapped[Source] = relationship(back_populates="quotes")
