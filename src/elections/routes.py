from fastapi import APIRouter, Depends, status
from src.utils.auth import get_current_user
from src.elections.schemas import (
    CreateElectionInput, 
    CreateElectionResponse,
    DeleteElection,
    CreatePositionInput,
    CreatePositionResponse,
    CreateCandidateInput,
    CreateCandidateResponse,
    AddAllowedVotersInput,
    AddedAllowedVotersResponse
    )
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session

from src.elections.services import ElectionServices


electionRouter = APIRouter()
electionServices = ElectionServices()

@electionRouter.post("/create-election", response_model=CreateElectionResponse, status_code=status.HTTP_201_CREATED)
async def create_election(election_details: CreateElectionInput, session: AsyncSession = Depends(get_Session),
creator_id: str = Depends(get_current_user), ):

    election = await electionServices.create_election(election_details, creator_id, session)

    return {
        "success": True,
        "message": "election successfuly created",
        "data": election
    }


@electionRouter.post("/add-position", response_model=CreatePositionResponse, status_code=status.HTTP_201_CREATED)
async def add_position(
    position_details: CreatePositionInput,
    creator_id: str = Depends(get_current_user),  
    session: AsyncSession = Depends(get_Session)
):
    position = await electionServices.create_position(creator_id, position_details, session)

    return {
        "success": True,
        "message": "position successfuly added",
        "data": position
    }
    
@electionRouter.post("/add-candidate", response_model=CreateCandidateResponse, status_code=status.HTTP_201_CREATED)
async def add_candidate(
    candidate_details: CreateCandidateInput,
    creator_id: str = Depends(get_current_user), 
    session: AsyncSession = Depends(get_Session)
):
   candidate  = await electionServices.create_candidates(creator_id, candidate_details, session)
   return {
       "success": True,
        "message": "position successfuly added",
        "data": candidate
   }

@electionRouter.post("/add-allowed-voters", response_model=AddedAllowedVotersResponse, status_code=status.HTTP_201_CREATED)
async def add_voters(
   voter_details: AddAllowedVotersInput,
    creator_id: str = Depends(get_current_user), 
    session: AsyncSession = Depends(get_Session)
):
   added_voter  = await electionServices.add_allowed_voters(creator_id, voter_details, session)

   return {
       "success": True,
        "message": "position successfuly added",
        "data": added_voter
   }