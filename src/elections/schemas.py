from pydantic import BaseModel, EmailStr
from datetime import datetime
import uuid
from typing import Optional, List
from enum import Enum


class Election(BaseModel):

    id: uuid.UUID 
    creator_id: uuid.UUID
    election_name: str
    start_time: datetime
    stop_time: datetime 
    created_at: datetime 

class CreateElectionInput(BaseModel):
    election_name: str
    start_time: datetime
    stop_time: datetime

class CreateElectionResponse(BaseModel):
    success: bool
    message: str
    data: Election

class DeleteElectionInput(BaseModel):
    election_id: uuid.UUID

class DeleteElectionResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class Position(BaseModel):
    id: uuid.UUID 
    election_id: uuid.UUID 
    position_name: str
    created_at: datetime 

class CreatePositionInput(BaseModel):
    election_id: uuid.UUID 
    position_name: str

class CreatePositionResponse(BaseModel):
    success: bool
    message: str
    data: Position

class DeletePositionInput(BaseModel):
    election_id: uuid.UUID
    position_id: uuid.UUID

class DeletePositionResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class Candidate(BaseModel):
    id: uuid.UUID 
    user_id: uuid.UUID 
    fullname: str
    nickname: Optional[str] = None
    position_id: uuid.UUID 

class CreateCandidateInput(BaseModel):
    election_id: uuid.UUID
    email: str
    fullname: str
    nickname: Optional[str] = None
    position_id: uuid.UUID

class CreateCandidateResponse(BaseModel):
    success: bool
    message: str
    data: Candidate

class DeleteCandidateInput(BaseModel):
    election_id: uuid.UUID
    candidate_id: uuid.UUID

class DeleteCandidateResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class AddAllowedVotersInput(BaseModel):
    election_id: uuid.UUID
    emails: List[EmailStr]

class AddedAllowedVoters(BaseModel):
    added_count: int
    already_enrolled: List[EmailStr]
    not_registered: List[EmailStr]

class AddedAllowedVotersResponse(BaseModel):
    success: bool
    message: str
    data: AddedAllowedVoters

class DeleteAllowedVoterInput(BaseModel):
    election_id: uuid.UUID
    email: EmailStr

class DeleteAllowedVoterResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class GetElectionDetailsResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class VoteInput(BaseModel):
    election_id: uuid.UUID
    position_id: uuid.UUID 
    candidate_id: uuid.UUID 

class VoteResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}

class GetElectionResultResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}


class Ballot(BaseModel):
    election_id: uuid.UUID
    election_name: str
    election_status: str
    vote_status: str
    start_time: datetime
    stop_time: datetime

class GetMyBallotResponse(BaseModel):
    success: bool
    message: str
    data: List[Ballot]