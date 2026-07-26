from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db, get_current_user
from schemas import ServiceCreate, ServiceResponse, ServiceUpdate, ServiceStatus
from models import Category, Service, ServiceRequest

router = APIRouter(prefix="/services", tags=["services"])

@router.post("", response_model=ServiceResponse)
async def create_service(data: ServiceCreate, db: AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == data.category_id))

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found!")
    
    new_service = Service(**data.model_dump(), owner_id=current_user.id)

    db.add(new_service)

    try:
        await db.commit()

        await db.refresh(new_service)
    except Exception:
        await db.rollback()
        raise

    return new_service


@router.patch("/{service_id}", response_model=ServiceResponse)
async def update_service(service_id: int, data: ServiceUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found!")

    if service.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only owner can update this service")
    
    if data.category_id is not None:
        result = await db.execute(
            select(Category).where(Category.id == data.category_id)
        )

        category = result.scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=404,
                detail="Category not found."
            )
        
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(service, field, value)

    try:
        await db.commit()
        await db.refresh(service)

    except Exception:
        await db.rollback()
        raise

    return service

    
@router.get("", response_model=list[ServiceResponse])
async def get_services(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.status == ServiceStatus.ACTIVE))

    services = result.scalars().all()

    return services

@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found!")

    return service

@router.delete("/{service_id}")
async def archive_service(service_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.id == service_id))

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found!")
    
    if service.owner_id != current_user.id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="only service owner can delete service")
    
    service.status = ServiceStatus.ARCHIVED

    try:
        await db.commit()

        await db.refresh(service)

    except Exception:
        await db.rollback()
        raise

    return {"message" "service archived successfully"}