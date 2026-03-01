from fastapi import APIRouter, Depends

from services.members_service import MembersService, get_members_service
from schemas.member_schema import MemberCreate, MemberRead

router = APIRouter(prefix='/members', tags=['members'])

@router.get('/', response_model=list[MemberRead])
async def get_all_members(service: MembersService = Depends(get_members_service)) -> list[MemberRead]:
    """Получить всех участников."""
    return await service.get_all_members()

@router.post('/', response_model=MemberRead)
async def create_member(member: MemberCreate, service: MembersService = Depends(get_members_service)) -> MemberRead:
    """Создать нового участника."""
    return await service.create_member(member)



