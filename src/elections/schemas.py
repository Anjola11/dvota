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
    startTime: datetime
    stopTime: datetime

class CreateElectionResponse(BaseModel):
    success: bool
    message: str
    data: Election

class DeleteElection(BaseModel):
    election_id: uuid.UUID

class ElectionResponse(BaseModel):
    success: bool
    message: str
    data: Election

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