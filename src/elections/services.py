from src.elections.schemas import (
    CreateElectionInput, 
    CreatePositionInput, 
    CheckUserByEmailInput,
    CreateCandidateInput,
    DeleteElectionInput,
    DeletePositionInput,
    DeleteCandidateInput,
    AddAllowedVotersInput,
    DeleteAllowedVoterInput,
    VoteInput
)
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.elections.models import Election, Position, Candidate, AllowedVoter, Vote
from src.auth.models import User
from sqlmodel import select
from sqlalchemy.exc import DatabaseError, IntegrityError

from datetime import datetime, timezone
from sqlalchemy.orm import selectinload


class ElectionServices:
    """
    Service layer handling the business logic for elections, 
    including management, whitelisting, and voting operations.
    """

    async def get_user_by_email(self, user_email, session: AsyncSession, raise_Exception: bool = False):
        """Fetches a user ID by email for candidate/voter registration."""
        statement = select(User).where(User.email == user_email)

        try:
            result = await session.exec(statement)
            user = result.first()
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        if not user:
            if raise_Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user does not exist"
                )
            return {
                "success": False,
                "user_email": user_email
            }
        
        user_id = user.user_id
        return {
            "success": True,
            "user_id": user_id
        }
    
    async def verify_creator(self, creator_id, election_id, session: AsyncSession):
        """Security check to ensure only the election admin can modify election settings."""
        statement = select(Election).where(Election.id == election_id)

        try:
            result = await session.exec(statement)
            election = result.first()
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="election does not exist"
            )
        
        # Verify ownership
        if str(election.creator_id) != str(creator_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="you are not authorized to make changes to this election"
            )
        
        return True

    async def create_election(self, election_details: CreateElectionInput, creator_id: str, session: AsyncSession):
        """Initializes a new election event with timing constraints."""
        if election_details.stop_time < election_details.start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stopTime must be greater than startTime"
            )
        
        new_election = Election(
            creator_id=creator_id,
            election_name=election_details.election_name,
            start_time=election_details.start_time,
            stop_time=election_details.stop_time
        )
        
        new_allowed_voter = AllowedVoter(
            user_id=creator_id,
            election_id=new_election.id 
        )

        try:
            
            session.add(new_election) 
            await session.flush()
            session.add(new_allowed_voter) 
            
            await session.commit() 
            await session.refresh(new_election)
            return new_election
        
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)
            
            if "unique_Creator_election_name" in error_msg:
                detail = "You have already created an election with this name."
            else:
                detail = "Database integrity error. Check if the name is unique."

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
    
    async def delete_election(self, election_details: DeleteElectionInput, creator_id: str, session: AsyncSession):
        """Removes a position and its associated candidates."""
        await self.verify_creator(creator_id,election_details.election_id, session)
        
        statement = select(Election).where(Election.id == election_details.election_id)
        try:
            result = await session.exec(statement)
            election = result.first()

            if election:
                await session.delete(election)
                await session.commit()
                return True
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Election not found"
            )
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def create_position(self, creator_id, position_details: CreatePositionInput, session: AsyncSession):
        """Adds a category (e.g., 'President') to an existing election."""
        await self.verify_creator(creator_id, position_details.election_id, session)

        new_position = Position(
            election_id =  position_details.election_id,
            position_name= position_details.position_name
        )

        try:
            session.add(new_position)
            await session.commit()
            await session.refresh(new_position)
            return new_position
        
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)

            if "unique_election_postion_name" in error_msg:
                detail = f"The position '{new_position.position_name}' already exists in this election."
            else:
                detail = "Integrity error: make sure the election exists."

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail
            )
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        
        
    async def delete_position(self, position_details: DeletePositionInput, creator_id: str, session: AsyncSession):
        """Removes a position and its associated candidates."""
        await self.verify_creator(creator_id, position_details.election_id, session)
        
        statement = select(Position).where(Position.id == position_details.position_id)
        try:
            result = await session.exec(statement)
            position = result.first()

            if position:
                await session.delete(position)
                await session.commit()
                return True
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="position not found"
            )
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def create_candidates(self, creator_id, candidate_details: CreateCandidateInput, session: AsyncSession):
        """Enrolls a user as a candidate and automatically whitelists them to vote."""
        await self.verify_creator(creator_id, election_id=candidate_details.election_id, session=session)

        user = await self.get_user_by_email(candidate_details.email, session, raise_Exception=True)
        user_id = user.get('user_id')

        new_candidate = Candidate(
            user_id=user_id,
            fullname=candidate_details.fullname,
            nickname=candidate_details.nickname,
            position_id=candidate_details.position_id
        )

        try:
            session.add(new_candidate)
            
            # Check for existing whitelist entry to prevent unique constraint failures
            stmt = select(AllowedVoter).where(
                AllowedVoter.user_id == user_id, 
                AllowedVoter.election_id == candidate_details.election_id
            )
            existing = await session.exec(stmt)
            if not existing.first():
                new_allowed_voter = AllowedVoter(
                    user_id=user_id,
                    election_id=candidate_details.election_id
                )
                session.add(new_allowed_voter)

            await session.commit()
            await session.refresh(new_candidate)
            return new_candidate

        except IntegrityError as e:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, 
                detail="User is already a candidate for this position"
                )
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def delete_candidate(self, candidate_details: DeleteCandidateInput, creator_id: str, session: AsyncSession):
        """Removes a candidate and their corresponding whitelist record."""
        await self.verify_creator(creator_id, candidate_details.election_id, session)
        
        candidate_statement = select(Candidate).where(Candidate.id == candidate_details.candidate_id)
        result = await session.exec(candidate_statement)
        candidate = result.first()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="Candidate not found"
                )

        candidate_user_id = candidate.user_id

        try:
            await session.delete(candidate)

            # Cleanup whitelist specifically for this election
            voter_stmt = select(AllowedVoter).where(
                AllowedVoter.user_id == candidate_user_id,
                AllowedVoter.election_id == candidate_details.election_id
            )
            voter_result = await session.exec(voter_stmt)
            voter_record = voter_result.first()

            if voter_record:
                await session.delete(voter_record)

            await session.commit()
            return True

        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Internal server error"
                )
        
    async def add_allowed_voters(self, creator_id, voters_details: AddAllowedVotersInput, session: AsyncSession):
        """Bulk whitelists users for an election using their email addresses."""
        await self.verify_creator(creator_id, voters_details.election_id, session)

        # Pre-fetch existing IDs to skip duplicates
        statement = select(AllowedVoter.user_id).where(AllowedVoter.election_id == voters_details.election_id)
        result = await session.exec(statement)
        existing_voter_ids = set(result.all())

        voters_to_add_ids = []
        already_present_emails = [] 
        unregistered_emails = []

        try:
            for email in voters_details.emails:
                user_data = await self.get_user_by_email(email, session, raise_Exception=False)
                
                if user_data.get('success'):
                    u_id = user_data.get('user_id')
                    if u_id in existing_voter_ids:
                        already_present_emails.append(email)
                    else:
                        voters_to_add_ids.append(u_id)
                else:
                    unregistered_emails.append(email)

            for u_id in voters_to_add_ids:
                allowed_voter = AllowedVoter(
                    user_id=u_id,
                    election_id=voters_details.election_id)
                session.add(allowed_voter)

            await session.commit()

            return {
                "added_count": len(voters_to_add_ids),
                "already_enrolled": already_present_emails,
                "not_registered": unregistered_emails
            }
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )

    async def delete_allowed_voters(self, creator_id, voters_details: DeleteAllowedVoterInput, session: AsyncSession):
        """Revokes voting privileges for a specific user."""
        await self.verify_creator(creator_id, voters_details.election_id, session)

        user_data = await self.get_user_by_email(voters_details.email, session, raise_Exception=True)
        user_id = user_data.get('user_id')

        statement = select(AllowedVoter).where(
            AllowedVoter.election_id == voters_details.election_id,
            AllowedVoter.user_id == user_id
        )
        
        try:
            result = await session.exec(statement)
            voter_record = result.first()

            if not voter_record:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User is not on the whitelist for this election")

            await session.delete(voter_record)
            await session.commit()
            return True

        except DatabaseError:
            await session.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")
        
    async def get_election_details(self, user_id, election_id, session: AsyncSession):
        """
        Retrieves the 'ballot paper' for a voter. 
        Fetches positions and candidates without exposing vote counts.
        """
        
        # Verify the user is whitelisted for this specific election
        allowed_statement = select(AllowedVoter).where(
            AllowedVoter.user_id == user_id,
            AllowedVoter.election_id == election_id
        )
        allowed_result = await session.exec(allowed_statement)
        
        if not allowed_result.first():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not whitelisted for this election"
            )

        # Optimized Eager Loading: Fetch the election structure in 3 optimized steps
        statement = (
            select(Election)
            .where(Election.id == election_id)
            .options(
                selectinload(Election.positions)
                .selectinload(Position.candidates)
            )
        )

        try:
            result = await session.exec(statement)
            election = result.first()

            if not election:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Election does not exist"
                )
            
            allowed_voters_list = None
            if str(election.creator_id) == str(user_id):
                voters_statement = select(User.email).join(
                    AllowedVoter, AllowedVoter.user_id == User.user_id
                    ).where(
                        AllowedVoter.election_id == election_id
                    )
                result = await session.exec(voters_statement)
                allowed_voters_list = result.all()
            election_data = {
                "id": str(election.id),
                "creator_id": str(election.creator_id),
                "election_name": election.election_name,
                "start_time": election.start_time.isoformat(),
                "stop_time": election.stop_time.isoformat(),
                "created_at": election.created_at.isoformat(),
                "positions": [
                    {
                        "id": str(pos.id),
                        "position_name": pos.position_name,
                        "candidates": [
                            {
                                "id": str(cand.id),
                                "user_id": str(cand.user_id),
                                "fullname": cand.fullname,
                                "nickname": cand.nickname,
                            }
                            for cand in pos.candidates
                        ]
                    }
                    for pos in election.positions
                ],
                "allowed_voters": allowed_voters_list
            }
            return election_data

        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        

    async def vote(self, user_id, voter_input: VoteInput, session: AsyncSession):
        """Cast a vote. Handles timing, whitelist, and double-voting security."""
        election_statement = select(Election).where(Election.id == voter_input.election_id)
        election_result = await session.exec(election_statement)
        election = election_result.first()

        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Election does not exist"
            )

        # Time-window validation
        now = datetime.now(timezone.utc)
        if election.start_time > now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The election has not started"
            )
        if election.stop_time < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The election has ended"
            )

        # Verify whitelist
        allowed_voter_statement = select(AllowedVoter).where(
            AllowedVoter.user_id == user_id,
            AllowedVoter.election_id == voter_input.election_id
        )
        allowed_voter_result = await session.exec(allowed_voter_statement)

        if not allowed_voter_result.first():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="You are not authorized to vote in this election"
            )

        # Validate candidate belongs to this specific election
        candidate_stmt = (
            select(Candidate)
            .join(Position)
            .where(
                Candidate.id == voter_input.candidate_id,
                Position.election_id == voter_input.election_id
            )
        )
        candidate_res = await session.exec(candidate_stmt)
        candidate_voted = candidate_res.first()

        if not candidate_voted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate selection for this election"
            )

        # Atomic update: increment count and record vote audit
        candidate_voted.vote_count += 1
        new_vote = Vote(
            user_id=user_id,
            position_id=candidate_voted.position_id,
            candidate_id=voter_input.candidate_id
        )

        try:
            session.add(candidate_voted)
            session.add(new_vote)
            await session.commit()
            return True

        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)
            if "duplicate_vote" in error_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already voted for this position"
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A conflict occurred while recording your vote"
            )

        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )

    async def get_election_result(self, creator_id, election_id, session: AsyncSession):
        """Generates a leaderboard for an election. Optimized with eager loading."""
        await self.verify_creator(creator_id, election_id, session)

        # selectinload chain fetches Election -> Positions -> Candidates in optimized queries
        election_statement = (
            select(Election)
            .where(Election.id == election_id)
            .options(
                selectinload(Election.positions)
                .selectinload(Position.candidates)
            )
        )

        try:
            result = await session.exec(election_statement)
            election = result.first()

            if not election:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Election not found"
                )

            # Transform raw data into a sorted leaderboard
            leaderboard = []
            for pos in election.positions:
                sorted_candidates = sorted(
                    pos.candidates, 
                    key=lambda c: c.vote_count, 
                    reverse=True
                )
                leaderboard.append({
                    "position_name": pos.position_name,
                    "candidates": sorted_candidates
                })

            return {
                "election_name": election.election_name,
                "leaderboard": leaderboard
            }

        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error"
            )
        
    async def get_my_ballot(self, user_id, session):
        """Retrieves eligible ballots for a user and calculates voting status."""
        user_statement = select(User).where(
            User.user_id == user_id
        ).options(
            selectinload(User.allowed_elections).selectinload(Election.positions),
            selectinload(User.position_voted)
        )

        result = await session.exec(user_statement)
        user = result.first()
         
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found"
            )
        
        # Pull already voted position IDs into a set for fast lookup
        position_voted_id = {p.id for p in user.position_voted}

        ballot_list = []
        now = datetime.now(timezone.utc)

        for election in user.allowed_elections:
            # Check if user has interacted with any position in this election
            has_voted = any(p.id in position_voted_id for p in election.positions)
            vote_status = "voted" if has_voted else "not voted"

            # Dynamic status calculation
            election_status = "upcoming"
            if election.stop_time > now and now > election.start_time:
                election_status = "active"
            
            if election.stop_time < now:
                election_status = "ended"

            ballot = {
                "election_id": election.id,
                "election_name": election.election_name,
                "election_status": election_status,
                "creator_id": election.creator_id,
                "vote_status": vote_status,
                "start_time": election.start_time,
                "stop_time": election.stop_time
            }
            ballot_list.append(ballot)

        return ballot_list