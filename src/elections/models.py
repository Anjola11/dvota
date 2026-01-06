from sqlmodel import SQLModel, Field, Column,Relationship
from typing import List, Optional
import uuid
from datetime import datetime, timezone
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import UniqueConstraint
import cloudinary.utils


def utc_now():
    return datetime.now(timezone.utc)

class AllowedVoter(SQLModel, table = True):

    __tablename__ = "allowed_voters"

    user_id: uuid.UUID= Field(
        foreign_key="users.user_id",
        ondelete="CASCADE",
        primary_key=True
    )
    election_id: uuid.UUID = Field(
        foreign_key="elections.id",
        ondelete="CASCADE",
        primary_key=True
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))

class Vote(SQLModel, table = True):

    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint(
        "user_id", "position_id", name="duplicate_vote"
    ),
    )

    user_id: uuid.UUID= Field(
        foreign_key="users.user_id",
        primary_key=True
    )
    position_id: uuid.UUID = Field(
        foreign_key="positions.id",
        ondelete="CASCADE",
        primary_key=True
    )
    candidate_id: uuid.UUID = Field(
        ondelete="CASCADE",
        foreign_key="candidates.id",
    )
    
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True)))

class Election(SQLModel, table = True):

    __tablename__ = "elections"
    __table_args__ = (
        UniqueConstraint("creator_id", "election_name", name="unique_Creator_election_name"),
    )
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        primary_key=True
    )
    creator_id: uuid.UUID = Field(
        foreign_key="users.user_id",
        ondelete="CASCADE"
    )
    election_name: str
    start_time: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    stop_time: datetime = Field(
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

    #relationships
    creator: Optional["User"] = Relationship(
        back_populates="election_created",
    )
    positions: List["Position"] = Relationship(
        back_populates="election",
         sa_relationship_kwargs={
            "cascade": "all, delete-orphan"
        }
    )
    #many to many
    allowed_voters: List["User"] = Relationship(
        back_populates="allowed_elections",
        link_model=AllowedVoter
    )
    


class Position(SQLModel, table = True):

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint("election_id", "position_name", name="unique_election_postion_name"),
    )
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    election_id: uuid.UUID = Field(
        foreign_key="elections.id",
        ondelete="CASCADE"
        )
    position_name: str
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )

    #relationship
    election: Optional["Election"] = Relationship(
        back_populates="positions"
    )
    candidates: List["Candidate"] = Relationship(
        back_populates="position",
         sa_relationship_kwargs={
            "cascade": "all, delete-orphan"
        }
    )
    voters: List["User"] = Relationship(
        back_populates="position_voted",
        link_model=Vote
    )

class Candidate(SQLModel, table = True):

    __tablename__ = "candidates"
    
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="users.user_id"
    )
    fullName: str
    nickname: Optional[str] = None
    vote_count: int = Field(default=0)
    position_id: uuid.UUID = Field(foreign_key="positions.id", ondelete="CASCADE")
    candidate_picture_id: Optional[str] = Field(default=None)

    @property
    def candidate_picture_url(self):

        if not self.candidate_picture_id:
            return f"https://ui-avatars.com/api/?name={self.fullName}&background=random"
        
        url, options = cloudinary.utils.cloudinary_url(
            self.candidate_picture_id,
            width=200,
            height=200,
            crop="fill",
            gravity="face",
            quality="auto",
            fetch_format="auto"
        )

        return url
    #relationship
    position: Optional["Position"] = Relationship(
        back_populates="candidates"
    )
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(pg.TIMESTAMP(timezone=True))
    )
    voters: List["User"] = Relationship(
        back_populates="candidate_voted",
        link_model=Vote
    )
    