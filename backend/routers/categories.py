from fastapi import APIRouter, Depends, HTTPException, status
from dependencies import get_current_user, get_db
from models import Category
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from schemas import CategoryCreate, CategoryResponse, CategoryUpdate, UserRole

router = APIRouter(prefix="/categories", tags=["categories"])

#Admin only
@router.post("", response_model=CategoryResponse)
async def create_category(category_data:CategoryCreate,
                           db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can create category")
    
    new_category = Category(**category_data.model_dump())

    db.add(new_category)

    try:
        await db.commit()

        await db.refresh(new_category)
    
    except Exception:
        await db.rollback()
        raise

    return new_category

@router.get("", response_model=list[CategoryResponse])
async def get_categories(db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Category))

    categories = result.scalars().all()

    return categories


#Admin only
@router.patch("/{category_id}")
async def update_category(category_id: int, data: CategoryUpdate,
                           db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can update category")
    
    result = await db.execute(select(Category).where(Category.id == category_id))

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(category, field, value)

    try: 
        await db.commit()

        await db.refresh(category)

    except Exception:
        await db.rollback()
        raise

    return category

@router.get("/{category_id}")
async def get_category(category_id:int, db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Category).where(Category.id == category_id))

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    
    return category

@router.delete("/{category_id}")
async def delete_category(category_id:int, db:AsyncSession=Depends(get_db),
                           current_user=Depends(get_current_user)):
    
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admin can delete category")
    
    result = await db.execute(select(Category).where(Category.id == category_id))

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found")
    
    await db.delete(category)

    try: 
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return {"message": "category deleted successfully"}