from pydantic import BaseModel, EmailStr, ConfigDict
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

class UpdateElectionDetailsInput(BaseModel):
    election_id: uuid.UUID
    election_name: Optional[str] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None

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

class UpdatePositionDetailsInput(BaseModel):
    election_id: uuid.UUID
    position_id: uuid.UUID
    position_name: Optional[str] = None
  

class CheckUserByEmailInput(BaseModel):
    email: EmailStr

class CheckUserByEmailResponse(BaseModel):
    success: bool
    message: str
    data: dict = {}


class Candidate(BaseModel):
    id: uuid.UUID 

    #left it if I want to implement users must have an registred account

    # user_id: uuid.UUID 
    fullName: str
    nickname: Optional[str] = None
    position_id: uuid.UUID 
    candidate_picture_url: str

    model_config = ConfigDict(from_attributes=True)

class CreateCandidateInput(BaseModel):
    election_id: uuid.UUID

    #left it if I want to implement users must have an registred account
    
    # email: EmailStr
    fullName: str
    nickname: Optional[str] = None
    position_id: uuid.UUID

class CreateCandidateResponse(BaseModel):
    success: bool
    message: str
    data: Candidate

class UpdateCandidateDetailsInput(BaseModel):
    election_id: uuid.UUID
    candidate_id: uuid.UUID
    fullName: Optional[str] = None
    nickname: Optional[str] = None

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
    creator_id: uuid.UUID
    vote_status: str
    start_time: datetime
    stop_time: datetime

class GetMyBallotResponse(BaseModel):
    success: bool
    message: str
    data: List[Ballot]