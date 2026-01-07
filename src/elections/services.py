from src.elections.schemas import (
    CreateElectionInput, 
    CreatePositionInput, 
    CreateCandidateInput,
    UpdateElectionDetailsInput,
    DeleteElectionInput,
    DeletePositionInput,
    UpdatePositionDetailsInput,
    UpdateCandidateDetailsInput,
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
    """
    Service layer containing the business logic for the Election System.
    
    Responsibilities:
    - Managing Election lifecycle (Create, Update, Delete)
    - Handling hierarchical data (Positions, Candidates)
    - Managing Access Control (Whitelisting voters)
    - Processing Votes securely
    """

    async def get_user_by_email(self, user_email, session: AsyncSession, raise_Exception: bool = False):
        """
        Helper function to look up a User's UUID using their email address.

        Args:
            user_email (str): The email to search for.
            session (AsyncSession): Database session.
            raise_Exception (bool): If True, raises 404 immediately if user is missing.

        Returns:
            dict: A dictionary containing success status and user_id.
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
        
        return {
            "success": True,
            "user_id": user.user_id
        }
    
    async def verify_creator(self, creator_id, election_id, session: AsyncSession):
        """
        Security Check: Verifies that the current user is the Creator of the election.
        
        This implements Role-Based Access Control (RBAC) at the resource level.
        Only the creator is allowed to modify the election, positions, or candidates.
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
        
        # Strict string comparison to ensure IDs match exactly
        if str(election.creator_id) != str(creator_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="you are not authorized to make changes to this election"
            )
        
        return True

    async def create_election(self, election_details: CreateElectionInput, creator_id: str, session: AsyncSession):
        """
        Creates a new election.

        Validations:
        - Ensures Stop Time is strictly after Start Time.
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
            # Parse the specific database error to return a helpful message
            error_msg = str(e.orig)
            
            if "unique_Creator_election_name" in error_msg:
                detail = "You have already created an election with this name."
            else:
                detail = "Database integrity error. Check if the name is unique."

            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)
        
    async def update_election_details(self, update_election_details_input: UpdateElectionDetailsInput, creator_id: str, session: AsyncSession):
        """
        Updates election metadata with strict integrity locks.

        Integrity Logic:
        1. Prevents setting start/stop times in illogical order.
        2. Prevents moving the election deadline to the past.
        3. 'Time Lock': If the election has already started, the start_time becomes immutable 
           to preserve the integrity of votes already cast.
        """
        await self.verify_creator(creator_id, update_election_details_input.election_id, session)

        statement = select(Election).where(Election.id == update_election_details_input.election_id)

        try:
            result = await session.exec(statement)
            election = result.first()
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Election not found"
            )
        
        # Use UTC for consistent time comparisons
        datetime_now = datetime.now(timezone.utc)

        # Merge Logic: If input is None, use existing DB value.
        # This allows valid comparison even if the user is only updating one field.
        new_start = update_election_details_input.start_time or election.start_time
        new_stop = update_election_details_input.stop_time or election.stop_time

        if new_start >= new_stop:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stopTime must be greater than startTime"
            )

        if update_election_details_input.start_time and new_start < datetime_now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail = "start_time must be in the future"
            )
        
        # Prevent retroactive termination (ending an election in the past)
        if new_stop < datetime_now and new_stop != election.stop_time:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail = "stoptime must be greater than the current time"
            )
        
        # INTEGRITY LOCK: If election is Active, block start_time changes.
        if election.start_time <= datetime_now:
            if update_election_details_input.start_time:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Election has already started. You cannot change the start time."
                )

        # Dynamic Update Loop
        # exclude_unset=True ensures we don't wipe existing data with Nulls
        for key, value in update_election_details_input.model_dump(exclude_unset=True).items():
            
            # Sanitization: Skip explicit None values
            if value is None:
                continue
            
            # Sanitization: Skip empty strings. 
            # We use isinstance check because .strip() on a datetime object causes a crash.
            if isinstance(value, str) and value.strip() == "":
                continue

            setattr(election, key, value)

        try:
            await session.commit()
            await session.refresh(election)
            return election
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )

    async def delete_election(self, election_details: DeleteElectionInput, creator_id: str, session: AsyncSession):
        """
        Permanently deletes an election.
        
        Due to database cascading, this also deletes:
        - Positions
        - Candidates
        - Votes
        - Whitelist entries
        """
        await self.verify_creator(creator_id, election_details.election_id, session)
        
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
        """Adds a voting position (e.g., 'President') to an election."""
        await self.verify_creator(creator_id, position_details.election_id, session)

        new_position = Position(
            election_id=position_details.election_id,
            position_name=position_details.position_name
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
        """Removes a position from the election."""
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
    
    async def update_position_details(self, update_position_details_input: UpdatePositionDetailsInput, creator_id: str, session: AsyncSession):
        """
        Updates position details securely.
        
        Security:
        - Verifies that the Position actually belongs to the Election (Prevents IDOR).
        - Verifies that the Election has NOT started (Time Lock).
        """
        await self.verify_creator(creator_id, update_position_details_input.election_id, session)

        # Optimization: Eager load 'election' relationship to avoid extra query for start_time check
        statement = select(Position).where(Position.id == update_position_details_input.position_id).options(
            selectinload(Position.election)
        )

        try:
            result = await session.exec(statement)
            position = result.first()
            
            # Security Cross-Check: Ensure Position belongs to provided Election ID
            if position.election_id != update_position_details_input.election_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="you are not authorized to edit this position"
                )

        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        if not position:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="position not found"
            )
        
        # Integrity Lock: Cannot edit structure of active election
        datetime_now = datetime.now(timezone.utc)
        if position.election.start_time <= datetime_now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't edit the position, the election has started"
            )

        # Prepare update data
        input_data = update_position_details_input.model_dump(exclude_unset=True)
        # Protect Primary/Foreign Keys from modification
        input_data.pop("election_id", None)
        input_data.pop("position_id", None)

        for key, value in input_data.items():
            # Sanitization Check
            if value is None:
                continue
            
            if isinstance(value, str) and value.strip() == "":
                continue

            setattr(position, key, value)

        try:
            await session.commit()
            await session.refresh(position)
            return position
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )

        
    async def create_candidates(self, creator_id, candidate_details: CreateCandidateInput, session: AsyncSession):
        """
        Adds a candidate to the election.
        
        Feature:
        - Automatically checks if the candidate is in the 'AllowedVoter' table.
        - If not, adds them to the whitelist (candidates can usually vote for themselves).
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
            
            # Auto-whitelist logic
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
        
    async def update_candidate_details(self, update_candidate_details_input: UpdateCandidateDetailsInput, creator_id: str, session: AsyncSession):
        """
        Updates candidate information securely.
        
        Complexity Note:
        Since 'Candidate' is linked to 'Position', which is linked to 'Election',
        we must chain loaders to access the Election's properties (like start_time).
        """
        await self.verify_creator(creator_id, update_candidate_details_input.election_id, session)

        # Chained Loading: Candidate -> Position -> Election
        statement = select(Candidate).where(Candidate.id == update_candidate_details_input.candidate_id).options(
            selectinload(Candidate.position).selectinload(Position.election)
        )

        try:
            result = await session.exec(statement)
            candidate = result.first()
            
            # Security: Ensure Candidate belongs to the provided Election context
            if candidate.position.election_id != update_candidate_details_input.election_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="you are not authorized to edit this candidate"
                )

        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="candidate not found"
            )
        
        # Integrity Lock: No editing candidates once voting begins
        datetime_now = datetime.now(timezone.utc)
        if candidate.position.election.start_time <= datetime_now:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can't edit the candidate, the election has started"
            )

        # Update Loop with Sanitization
        input_data = update_candidate_details_input.model_dump(exclude_unset=True)
        input_data.pop("election_id", None)
        input_data.pop("candidate_id", None)

        for key, value in input_data.items():
            if value is None:
                continue
            
            if isinstance(value, str) and value.strip() == "":
                continue

            setattr(candidate, key, value)

        try:
            await session.commit()
            await session.refresh(candidate)
            return candidate
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
    async def delete_candidate(self, candidate_details: DeleteCandidateInput, creator_id: str, session: AsyncSession):
        """
        Deletes a candidate.
        
        Cleanup:
        Removes the candidate's specific whitelist entry for this election 
        to keep the database clean.
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

            # Cleanup whitelist
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
        """
        Updates a candidate's profile picture via Cloudinary.
        
        Uses `file_upload_service` to handle the external API call.
        """
        await self.verify_creator(creator_id, election_id, session)

        candidate_statement = select(Candidate).where(Candidate.id == candidate_id)
        result = await session.exec(candidate_statement)

        candidate = result.first()

        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="candidate not found"
            )
        
        # Pass old ID to allow replacement/cleanup in Cloudinary
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
        """
        Bulk whitelist registration.
        
        Logic:
        1. Checks database for existing entries to prevent duplicates.
        2. Filters out emails that don't exist in the Users table.
        3. Returns a report of success/failure counts.
        """
        await self.verify_creator(creator_id, voters_details.election_id, session)

        # Optimization: Fetch all existing whitelist entries once (Set lookup is O(1))
        statement = select(AllowedVoter.user_id).where(AllowedVoter.election_id == voters_details.election_id)
        result = await session.exec(statement)
        existing_voter_ids = set(result.all())

        voters_to_add_ids = []
        already_present_emails = [] 
        unregistered_emails = []

        try:
            for email in voters_details.emails:
                # Reuse helper to find User ID by email
                user_data = await self.get_user_by_email(email, session, raise_Exception=False)
                
                if user_data.get('success'):
                    u_id = user_data.get('user_id')

                    # Prevent self-whitelist (optional business logic)
                    if str(u_id) == str(creator_id):
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="you can add yourself as a voter in this election"
                        )
                    if u_id in existing_voter_ids:
                        already_present_emails.append(email)
                    else:
                        voters_to_add_ids.append(u_id)
                else:
                    unregistered_emails.append(email)

            # Bulk Insert
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
        """Revokes voting rights for a single user."""
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
        Retrieves the full election hierarchy (Election -> Positions -> Candidates).
        
        Optimization:
        Uses `selectinload` to eager-load all nested data in one query, preventing
        performance bottlenecks.
        
        Security:
        Blocks access if user is neither the Creator nor a Whitelisted Voter.
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
        
        # Access Control: Check Whitelist
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

        # Deep Loading
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
            
            # Privacy: Only show full voter list to the Creator
            allowed_voters_list = None
            if str(election.creator_id) == str(user_id):
                voters_statement = select(User.email).join(
                    AllowedVoter, AllowedVoter.user_id == User.user_id
                    ).where(
                        AllowedVoter.election_id == election_id
                    )
                result = await session.exec(voters_statement)
                allowed_voters_list = result.all()
                
            # Manual Serialization
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
                                "candidate_picture_url": cand.candidate_picture_url,
                                
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
        

    async def vote(self, user_id: uuid.UUID, voter_input: VoteInput, session: AsyncSession):
        """
        Executes a Vote.
        
        Security Steps:
        1. Validates Election Window (Is it active?).
        2. Validates Whitelist (Can this user vote?).
        3. Validates Candidate (Does the candidate match the position?).
        4. Checks Duplicates (Did user already vote for this position?).
        """
        election_statement = select(Election).where(Election.id == voter_input.election_id)
        election_result = await session.exec(election_statement)
        election = election_result.first()

        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Election does not exist"
            )

        # 1. Time Check
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

        # 2. Whitelist Check
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

        # 3. Integrity Check (Candidate <-> Position Link)
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
        
        if candidate_voted.position_id != voter_input.position_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Candidate is not running for this position")

        # 4 & 5. Atomic Update
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
            # Detect duplicate key violation for (user_id, position_id)
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
        """
        Generates the Election Leaderboard.
        
        Returns:
        A structure containing positions, each with a list of candidates sorted by
        vote count (Descending).
        """
        await self.verify_creator(creator_id, election_id, session)

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

            leaderboard = []
            for pos in election.positions:
                # Sort candidates in Python (Descending order of votes)
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
        """
        Aggregates all elections a user is involved in (Created or Whitelisted).
        
        Calculates:
        - Election Status (Upcoming, Active, Ended)
        - Vote Status (Has the user participated?)
        """
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
        
        # Combine lists and remove duplicates using dictionary comprehension
        elections_combined = (user.allowed_elections + user.election_created)
        relevant_elections = {e.id: e for e in elections_combined}
        
        # Optimize lookup: Create a set of positions the user has already voted for
        position_voted_id = {p.id for p in user.position_voted}

        ballot_list = []
        now = datetime.now(timezone.utc)

        for election in relevant_elections.values():
            # Status: Has user cast at least one vote here?
            has_voted = any(p.id in position_voted_id for p in election.positions)
            vote_status = "voted" if has_voted else "not voted"

            # Status: Election Lifecycle
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