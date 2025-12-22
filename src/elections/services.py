from src.elections.schemas import CreateElectionInput, CreatePositionInput, CreateCandidateInput, AddAllowedVotersInput
from fastapi import HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession
from src.elections.models import Election, Position, Candidate, AllowedVoter
from src.auth.models import User
from sqlmodel import select
from sqlalchemy.exc import DatabaseError, IntegrityError


class ElectionServices:

    async def get_user_by_email(self,user_email,session: AsyncSession,raise_Exception: bool = False):
        statement = select(User).where(User.email == user_email)

        try:
            result = await session.exec(statement)
            user = result.first()
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail= "internal server error"
            )
        if not user:
            if raise_Exception:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="user does not exist"
                )
            return {
                "success": False,
                "user_email":user_email
                }
        
        user_id = user.user_id
        return {
                "success": True,
                "user_id":user_id
                }
    
    """Verify if the user is the one that created the election"""
    async def verify_creator(self,creator_id, election_id, session: AsyncSession):
        statement = select(Election).where(Election.id == election_id)

        try:
            result = await session.exec(statement)
            election = result.first()
        except DatabaseError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail= "internal server error"
            )
        if not election:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="election does not exist"
            )
        
        if str(election.creator_id) != str(creator_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="you are not authorized to make changes to this election"
            )
        
        return True

    async def create_election(self,election_details: CreateElectionInput, creator_id: str, session: AsyncSession):
        if election_details.stopTime < election_details.startTime:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="stopTime must be greater than startTime"
            )
        
        new_election = Election(
            creator_id=creator_id,
            election_name=election_details.election_name,
            start_time=election_details.startTime,
            stop_time=election_details.stopTime
        )

        try:
            session.add(new_election)
            await session.commit()
            await session.refresh(new_election)
            return new_election
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)
            
            if "unique_Creator_election_name" in error_msg:
                detail = "You have already created an election with this name."
            elif "foreign_key" in error_msg:
                detail = "Invalid creator ID. User does not exist."
            else:
                detail = "A database integrity conflict occurred."

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail
            )
        
    async def create_position(self, creator_id, position_details: CreatePositionInput, session: AsyncSession):

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
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
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
        
    async def create_candidates(self,creator_id, candidate_details: CreateCandidateInput, session:AsyncSession):
        await self.verify_creator(creator_id,election_id=candidate_details.election_id, session=session)

        user = await self.get_user_by_email(candidate_details.email,session, raise_Exception=True)

        user_id = user.get('user_id')

        new_candidate = Candidate(
            user_id=user_id,
            fullname= candidate_details.fullname,
            nickname= candidate_details.nickname,
            position_id= candidate_details.position_id
        )

        try:
            session.add(new_candidate)
            await session.commit()
            await session.refresh(new_candidate)
            return new_candidate
        
        except DatabaseError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="internal server error"
            )
        
        except IntegrityError as e:
            await session.rollback()
            error_msg = str(e.orig)
            
            if "unique_candidate_per_position" in error_msg:
                detail = "This user is already a candidate for this position."
            elif "foreign_key" in error_msg:
                detail = "The specified position does not exist."
            else:
                detail = "A conflict occurred while adding the candidate."

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=detail
            )
        

    async def add_allowed_voters(self, creator_id, voters_details: AddAllowedVotersInput, session: AsyncSession):
        await self.verify_creator(creator_id, voters_details.election_id, session)

        #Fetch current whitelist to avoid internal duplicates
        stmt = select(AllowedVoter.user_id).where(AllowedVoter.election_id == voters_details.election_id)

        result = await session.exec(stmt)
        existing_voter_ids = set(result.all())

        voters_to_add_ids = []
        already_present_emails = [] 
        unregistered_emails = []

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

        # Add valid users
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





