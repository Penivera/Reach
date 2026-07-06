from fastapi import APIRouter, Depends, HTTPException, status
from models import Skill, UserSkill
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from dependencies import get_current_user, get_db
from schemas import SkillCreate, UserSkillUpdate, SkillResponse, SkillUpdate, UserRole



router = APIRouter(prefix="/skills", tags=["skills"])

@router.get("", response_model=list[SkillResponse])
async def get_skills(db:AsyncSession=Depends(get_db)):
    
    result = await db.execute(select(Skill))

    skills = result.scalars().all()

    return skills

@router.get("/{skill_id}")
async def get_skill(skill_id:int, db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Skill).where(Skill.id == skill_id))

    skill = result.scalar_one_or_none()

    if not skill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill not found")
    
    return skill

#Admin
@router.post("", response_model=SkillResponse)
async def create_skill(skill_data: SkillCreate,
                        db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create skill")
    
    new_skill = Skill(**skill_data.model_dump())

    db.add(new_skill)

    try:
        await db.commit()

        await db.refresh(new_skill)

    except Exception:
        await db.rollback()
        raise

    return new_skill

@router.patch("/{skill_id}")
async def update_skill(skill_id:int, skill_data: SkillUpdate,
                        db: AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can update skill")
    
    result = await db.execute(select(Skill).where(Skill.id == skill_id))

    skill = result.scalar_one_or_none()

    if not skill: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill not found")
    
    update_data = skill_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(skill, field, value)

    try: 
        await db.commit()

        await db.refresh(skill)

    except Exception:
        await db.rollback()
        raise

    return skill


@router.delete("/{skill_id}")
async def delete_skill(skill_id:int,
                        db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can delete skill")
    
    result = await db.execute(select(Skill).where(Skill.id == skill_id))

    skill = result.scalar_one_or_none()

    if not skill: 
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="skill not found")
    
    await db.delete(skill)

    try:
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return {"message": "skill deleted successfully"}