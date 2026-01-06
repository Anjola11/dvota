from src.elections.schemas import (
    CreateElectionInput, 
    CreatePositionInput, 
    CreateCandidateInput,
    DeleteElectionInput,
    DeletePositionInput,
    DeleteCandidateInput,
    AddAllowedVotersInput,
    DeleteAllowedVoterInput,
    VoteInput
)
from fastapi import HTTPException, status, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from src.elections.models import Election, Position, Candidate, AllowedVoter, Vote
from src.auth.models import User
from sqlmodel import select
from sqlalchemy.exc import DatabaseError, IntegrityError

from datetime import datetime, timezone
from sqlalchemy.orm import selectinload
from src.file_uploads.services import FileUploadServices
import uuid

file_upload_service = FileUploadServices()

class ElectionServices:
    """Service layer for election lifecycle, whitelisting, and voting logic."""

    async def get_user_by_email(self, user_email, session: AsyncSession, raise_Exception: bool = False):
        """Finds a user by email to retrieve their UUID.
        
        Args:
            user_email: The email string to search for.
            session: The database session.
            raise_Exception: If True, raises 404 on missing user.
            
        Returns:
            A dict containing success status and user_id if found.
        """
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
        """Authorizes a user as the creator of a specific election.
        
        Args:
            creator_id: The UUID of the user to verify.
            election_id: The UUID of the election.
            session: The database session.
            
        Returns:
            True if authorized, else raises HTTPException.
        """
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
        """Creates a new election and automatically whitelists the creator.
        
        Args:
            election_details: Pydantic model with name and timeframes.
            creator_id: UUID of the user creating the election.
            session: The database session.
            
        Returns:
            The created Election object.
        """
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
        
        

        try:
            session.add(new_election)
            
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
        """Permanently deletes an election and all cascading relationships.
        
        Args:
            election_details: Input model containing the target election_id.
            creator_id: UUID of the requestor for authorization.
            session: The database session.
        """
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
        """Adds a position to an existing election.
        
        Args:
            creator_id: UUID of the admin.
            position_details: Input model with position name and election ID.
            session: The database session.
        """
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
        """Removes a position category from the election.
        
        Args:
            position_details: Input model containing election and position IDs.
            creator_id: UUID for authorization.
        """
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
        """Registers a candidate and ensures they are whitelisted as a voter.
        
        Args:
            creator_id: UUID of the election admin.
            candidate_details: Model containing email and position ID.
        """
        await self.verify_creator(creator_id, election_id=candidate_details.election_id, session=session)

        user = await self.get_user_by_email(candidate_details.email, session, raise_Exception=True)
        user_id = user.get('user_id')

        new_candidate = Candidate(
            user_id=user_id,
            fullName=candidate_details.fullName,
            nickname=candidate_details.nickname,
            position_id=candidate_details.position_id
        )

        try:
            session.add(new_candidate)
            
            # Auto-whitelist candidate if not already present
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
        """Deletes a candidate and removes their associated whitelist record.
        
        Args:
            candidate_details: Input model with IDs for the candidate and election.
        """
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

            # Cleanup whitelist entry for this specific election
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
    async def upload_candidate_picture(self, creator_id, election_id, candidate_id: uuid.UUID, file: UploadFile, session: AsyncSession):

        await self.verify_creator(creator_id, election_id, session)

        candidate_statement = select(Candidate).where(Candidate.id == candidate_id)
        result = await session.exec(candidate_statement)

        candidate = result.first()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="candidate not found"
            )
        old_candidate_picture_id = candidate.candidate_picture_id
        candidate_picture_id = await file_upload_service.upload_image(old_candidate_picture_id, file, type="candidate")

        candidate.candidate_picture_id = candidate_picture_id

        try:
            await session.commit()
            await session.refresh(candidate)

            return candidate
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal serval error"
            )
        
    async def add_allowed_voters(self, creator_id, voters_details: AddAllowedVotersInput, session: AsyncSession):
        """Whitelists a list of users for an election in bulk.
        
        Args:
            creator_id: UUID of the election admin.
            voters_details: Model containing election ID and list of emails.
            
        Returns:
            A report dict showing success, duplicate, and unregistered counts.
        """
        await self.verify_creator(creator_id, voters_details.election_id, session)

        # Pre-fetch existing voter IDs to prevent double entry
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

    async def delete_allowed_voter(self, creator_id, voters_details: DeleteAllowedVoterInput, session: AsyncSession):
        """Removes a specific user's voting rights for an election.
        
        Args:
            creator_id: UUID of the admin.
            voters_details: Model with user email and election ID.
        """
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
        """Retrieves full election structure for authorized creators or whitelisted voters.
        
        Fetches the hierarchy of positions and candidates while enforcing access 
        control. If the requestor is the admin, also returns the voter email list.

        Args:
            user_id: UUID of the user requesting details.
            election_id: UUID of the election to retrieve.
            session: The asynchronous database session.

        Returns:
            A dictionary containing serialized election data and participant info.
        """
        # Initial check to verify election existence
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
        
        # Security: Verify user is either whitelisted or the election creator
        allowed_statement = select(AllowedVoter).where(
            AllowedVoter.user_id == user_id,
            AllowedVoter.election_id == election_id
        )
        allowed_result = await session.exec(allowed_statement)
        
        if not allowed_result.first() and str(user_id) != str(election.creator_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not whitelisted for this election"
            )

        # Eager load Positions -> Candidates to avoid N+1 query overhead
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
            
            # Fetch full participant list only if the requestor is the admin
            allowed_voters_list = None
            if str(election.creator_id) == str(user_id):
                voters_statement = select(User.email).join(
                    AllowedVoter, AllowedVoter.user_id == User.user_id
                    ).where(
                        AllowedVoter.election_id == election_id
                    )
                result = await session.exec(voters_statement)
                allowed_voters_list = result.all()
                
            # Serialize the nested object structure into a response dictionary
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
                                "fullname": cand.fullName,
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
        

    async def vote(self, user_id:uuid.UUID, voter_input: VoteInput, session: AsyncSession):
        """Records a vote after verifying timeframe, whitelist, and duplicate status.
        
        Args:
            user_id: UUID of the voter.
            voter_input: Input model containing election and candidate IDs.
        """
        election_statement = select(Election).where(Election.id == voter_input.election_id)
        election_result = await session.exec(election_statement)
        election = election_result.first()

        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Election does not exist"
            )

        # Validate election time window
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

        # Verify whitelisted status
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

        # Ensure candidate is actually part of this specific election
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
        
        # INTEGRITY CHECK: Ensure candidate actually belongs to the position the user claims to vote for
        if candidate_voted.position_id != voter_input.position_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate is not running for this position")

        # Perform atomic update on vote count and record audit trail
        candidate_voted.vote_count = Candidate.vote_count + 1
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
        """Calculates election leaderboard sorted by vote counts.
        
        Args:
            creator_id: Admin UUID for authorization.
            election_id: UUID of the election.
        """
        await self.verify_creator(creator_id, election_id, session)

        # Load nested objects via optimized eager loading
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

            # Build leaderboard by sorting candidates per position
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
        
    async def get_my_ballot(self, user_id, session: AsyncSession):
        """Retrieves eligible ballots for a user, including created and whitelisted elections.
        
        This method fetches all elections relevant to a user in a single pass using 
        optimized eager loading. It merges created and whitelisted elections, 
        deduplicates them, and calculates the voting status and lifecycle phase.

        Args:
            user_id: The UUID of the user requesting their dashboard.
            session: The asynchronous database session.

        Returns:
            A list of dictionaries representing the user's election dashboard data.
        """
        # Fetch user with nested relationships for whitelists, ownership, and vote history
        user_statement = select(User).where(
            User.user_id == user_id
        ).options(
            selectinload(User.allowed_elections).selectinload(Election.positions),
            selectinload(User.election_created).selectinload(Election.positions),
            selectinload(User.position_voted)
        )

        try:
            result = await session.exec(user_statement)
            user = result.first()
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
          
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="user not found"
            )
        
        # Merge created and whitelisted elections; deduplicate via ID-keyed dictionary
        elections_combined = (user.allowed_elections + user.election_created)
        relevant_elections = {e.id: e for e in elections_combined}
        
        # Convert voted positions into a set for O(1) membership testing
        position_voted_id = {p.id for p in user.position_voted}

        ballot_list = []
        now = datetime.now(timezone.utc)

        # Process each unique election object
        for election in relevant_elections.values():
            # Check if user has participated in any position within this election
            has_voted = any(p.id in position_voted_id for p in election.positions)
            vote_status = "voted" if has_voted else "not voted"

            # Dynamic lifecycle status calculation
            election_status = "upcoming"
            if election.stop_time > now and now > election.start_time:
                election_status = "active"
            
            if election.stop_time < now:
                election_status = "ended"

            # Prepare serialized ballot data
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