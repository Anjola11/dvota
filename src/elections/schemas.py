from pydantic import BaseModel
from datetime import datetime
import uuid
from typing import Optional


class Election(BaseModel):

    id: uuid.UUID 
    creator_id: uuid.UUID
    election_name: str
    start_time: datetime
    stop_time: datetime 
    created_at: datetime 

class CreateElection(BaseModel):
    election_name: str
    startTime: datetime
    stopTime: datetime

class ElectionCreateResponse(BaseModel):
    success: bool
    message: str
    data: Election


class Position(BaseModel):

    id: uuid.UUID 
    election_id: uuid.UUID 
    position_name: str
    created_at: datetime 

class CreatePosition(BaseModel):
    election_id: uuid.UUID 
    position_name: str

class PositionCreateResponse(BaseModel):
    success: bool
    message: str
    data: Position

class Candidate(BaseModel):
    id: uuid.UUID 
    user_id: uuid.UUID 
    fullname: str
    nickname: Optional[str] = None
    position_id: uuid.UUID 

class CreateCandidate(BaseModel):
    election_id: uuid.UUID
    email: str
    fullname: str
    nickname: Optional[str] = None
    position_id: uuid.UUID

class CandidateCreateResponse(BaseModel):
    success: bool
    message: str
    data: Candidate