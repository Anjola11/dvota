from fastapi import APIRouter, Depends, status
from src.utils.auth import get_current_user
from src.elections.schemas import (
    CreateElectionInput, CreateElectionResponse,
    DeleteElectionInput,DeleteElectionResponse,

    CreatePositionInput,CreatePositionResponse,DeletePositionInput,DeletePositionResponse,

    CheckUserByEmailInput,CheckUserByEmailResponse,

    CreateCandidateInput,CreateCandidateResponse,
    DeleteCandidateInput,DeleteCandidateResponse,

    AddAllowedVotersInput,AddedAllowedVotersResponse,
    DeleteAllowedVoterInput,  DeleteAllowedVoterResponse,
    GetElectionDetailsResponse,
    VoteInput, VoteResponse,
    GetElectionResultResponse,
    GetMyBallotResponse
    )
from sqlmodel.ext.asyncio.session import AsyncSession
from src.db.main import get_Session

from src.elections.services import ElectionServices
import uuid


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

@electionRouter.delete("/delete-election",response_model=DeleteElectionResponse, status_code=status.HTTP_201_CREATED)
async def delete_election(election_details: DeleteElectionInput, session: AsyncSession = Depends(get_Session),
creator_id: str = Depends(get_current_user), ):

    await electionServices.delete_election(election_details, creator_id, session)

    return {
        "success": True,
        "message": "election successfuly deleted",
        "data": {}
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

@electionRouter.delete("/delete-position", response_model=DeletePositionResponse, status_code=status.HTTP_200_OK)
async def delete_position(position_details: DeletePositionInput, session: AsyncSession = Depends(get_Session), creator_id: str = Depends(get_current_user)):
    
    await electionServices.delete_position(position_details, creator_id, session)
    return {
        "success": True, 
        "message": "position successfully deleted", 
        "data": {}
        }


@electionRouter.post("/check-user", status_code=status.HTTP_200_OK, response_model=CheckUserByEmailResponse)
async def check_user(user_input: CheckUserByEmailInput, session: AsyncSession = Depends(get_Session)):
    user = await electionServices.get_user_by_email(user_input.email, session, raise_Exception=True)

    if user:
        return {
        "success": True,
        "message": "User exists",
        "data": {}
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


@electionRouter.delete("/delete-candidate", response_model=DeleteCandidateResponse, status_code=status.HTTP_200_OK)
async def delete_candidate(candidate_details: DeleteCandidateInput, session: AsyncSession = Depends(get_Session), creator_id: str = Depends(get_current_user)):
    
    await electionServices.delete_candidate(candidate_details, creator_id, session)
    return {
        "success": True, 
        "message": "candidate successfully deleted", 
        "data": {}}

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

@electionRouter.delete("/delete-allowed-voter", response_model=DeleteAllowedVoterResponse, status_code=status.HTTP_200_OK)
async def delete_voter(voter_details: DeleteAllowedVoterInput, session: AsyncSession = Depends(get_Session), creator_id: str = Depends(get_current_user)):
    
    await electionServices.delete_allowed_voter(creator_id, voter_details, session)
    return {
        "success": True, 
        "message": "Voter successfully removed", 
        "data": {}
        }

@electionRouter.get("/get-election-details/{election_id}", response_model=GetElectionDetailsResponse, status_code=status.HTTP_200_OK) 
async def get_election_result(
    election_id: uuid.UUID,
    user_id: str = Depends(get_current_user), 
    session: AsyncSession = Depends(get_Session)
):
    
    result = await electionServices.get_election_details(user_id, election_id, session)

    return {
        "success": True,
        "message": "Election details fetched successfully",
        "data": result
    }

@electionRouter.post("/vote", response_model= VoteResponse, status_code=status.HTTP_201_CREATED)
async def vote(voter_input: VoteInput, user_id: str = Depends(get_current_user), session: AsyncSession = Depends(get_Session)):
    await electionServices.vote(user_id,voter_input,session)

    return {
        "success": True,
        "message": "vote successful",
        "data": {}
    }

@electionRouter.get("/get-election-result/{election_id}", response_model=GetElectionResultResponse, status_code=status.HTTP_200_OK) 
async def get_election_result(
    election_id: uuid.UUID,
    creator_id: str = Depends(get_current_user), 
    session: AsyncSession = Depends(get_Session)
):
    
    result = await electionServices.get_election_result(creator_id, election_id, session)

    return {
        "success": True,
        "message": "Election results fetched successfully",
        "data": result
    }


@electionRouter.get("/get-my-ballot", response_model=GetMyBallotResponse, status_code=status.HTTP_200_OK)
async def get_my_ballot(
    user_id: str = Depends(get_current_user),
    session: AsyncSession = Depends(get_Session)
):
    ballot_list = await electionServices.get_my_ballot(user_id, session)

    return {
        "success": True,
        "message": "Election results fetched successfully",
        "data": ballot_list
    }
    