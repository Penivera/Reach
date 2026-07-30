from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db, get_current_user
from schemas import ServiceCreate, ServiceResponse, ServiceUpdate, ServiceStatus, NearbyServiceQuery, ServiceRequestResponse, ServiceRequestCreate, ServiceRequestStatus
from models import Category, Service, ServiceRequest
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromText

router = APIRouter(prefix="/services", tags=["services"])

@router.post("", response_model=ServiceResponse)
async def create_service(service_data: ServiceCreate, db: AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Category).where(Category.id == service_data.category_id))

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="category not found!")

    point = ST_GeogFromText(f"POINT({service_data.longitude} {service_data.latitude})")
        
    data = service_data.model_dump()

    data.pop("latitude")
    data.pop("longitude")
    data["location"] = point

    new_service = Service(**data, owner_id=current_user.id)

    db.add(new_service)

    try:
        await db.commit()

        await db.refresh(new_service)
    except Exception:
        await db.rollback()
        raise

    return new_service

@router.get("", response_model=list[ServiceResponse])
async def get_services(db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Service).where(Service.status == ServiceStatus.ACTIVE))

    services = result.scalars().all()

    return services


@router.get("/me", response_model=list[ServiceResponse])
async def get_my_services(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.owner_id == current_user.id, Service.status != ServiceStatus.ARCHIVED))

    services = result.scalars().all()

    return services

@router.get("/nearby", response_model=list[ServiceResponse])
async def get_services_nearby(data:NearbyServiceQuery=Depends(), db:AsyncSession=Depends(get_db)):
    search_point = ST_GeogFromText(f"POINT({data.longitude} {data.latitude})")
    
    query = select(Service).where(Service.status != ServiceStatus.ARCHIVED,
                                  ST_DWithin(Service.location, search_point, data.radius*1000))

    if data.category_id is not None:
        query = query.where(Service.category_id == data.category_id)

    query = query.order_by(ST_Distance(Service.location, search_point))

    result = await db.execute(query)
    
    services = result.scalars().all()

    return services


@router.get("/{service_id}", response_model=ServiceResponse)
async def get_service(service_id: int, db:AsyncSession=Depends(get_db)):
    result = await db.execute(select(Service).where(Service.id == service_id, Service.status != ServiceStatus.ARCHIVED))
    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found!")

    return service


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
            raise HTTPException(status_code=404,detail="Category not found.")

    update_data = data.model_dump(exclude_unset=True)


    has_lat = "latitude" in update_data
    has_lon = "longitude" in update_data

    if has_lat != has_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and longitude must be provided together."
        )

    if has_lat:
        point = ST_GeogFromText(
            f"POINT({update_data['longitude']} {update_data['latitude']})"
        )

        update_data.pop("latitude")
        update_data.pop("longitude")
        update_data["location"] = point

    

    for field, value in update_data.items():
        setattr(service, field, value)

    try:
        await db.commit()
        await db.refresh(service)

    except Exception:
        await db.rollback()
        raise

    return service

    

@router.delete("/{service_id}")
async def archive_service(service_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.id == service_id))

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found!")
    
    if service.owner_id != current_user.id:
        raise HTTPException(status_code= status.HTTP_403_FORBIDDEN, detail="only service owner can delete service")

    if service.status == ServiceStatus.ARCHIVED:
        return {"message": "service is already archived"}

    
    service.status = ServiceStatus.ARCHIVED

    try:
        await db.commit()

        await db.refresh(service)

    except Exception:
        await db.rollback()
        raise

    return {"message" : "service archived successfully"}


#client 

@router.post("/requests", response_model=ServiceRequestResponse)
async def create_service_request(requests_data:ServiceRequestCreate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).where(Service.id == requests_data.service_id,
                                                    Service.status == ServiceStatus.ACTIVE))

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found")

    if service.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you cannot request your own service")


    # prevent duplicate service requests

    result = await db.execute(select(ServiceRequest).where(ServiceRequest.service_id == service.id,
                                                           ServiceRequest.requester_id == current_user.id))

    existing_service_requests = result.scalar_one_or_none()

    if existing_service_requests:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You already have a pending request for this service.")

    point = ST_GeogFromText(f"POINT({requests_data.longitude} {requests_data.latitude})")
            
    data = requests_data.model_dump()

    data.pop("latitude")
    data.pop("longitude")
    data["location"] = point

    new_request = ServiceRequest(**data,requester_id=current_user.id, 
                                 provider_id=service.owner_id)

    db.add(new_request)

    try:
        await db.commit()
        await db.refresh(new_request)
    except Exception:
        await db.rollback()
        raise

    return new_request
    

@router.get("/requests/me", response_model=list[ServiceRequestResponse])
async def get_service_requests(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.requester_id == current_user.id))

    requests = result.scalars().all()

    return requests

@router.patch("/requests/{request_id}/cancel")
async def cancel_service_request(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if request.requester_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only requester can cancel request")

    if request.status != ServiceRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Only pending requests can be cancelled.")
    
    request.status = ServiceRequestStatus.CANCELLED

    try:
        await db.commit()
        await db.refresh(request)
    except Exception:
        await db.rollback()
        raise

    return {"message": "service request cancelled successfully"}

@router.get("/requests/{request_id}", response_model=ServiceRequestResponse)
async def get_service_request(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    return request


# Provider

@router.get("/requests/received", response_model=list[ServiceRequestResponse])
async def get_service_request_received(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.provider_id == current_user.id))

    received_request = result.scalars().all()

    return received_request

@router.patch("/requests/{request_id}/accept")
async def accept_service_request(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if request.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only service provider can update this request status")

    if request.status != ServiceRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only pending service request can be accepted")

    request.status = ServiceRequestStatus.ACCEPTED


    try:
        await db.commit()
        await db.refresh(request)
    except Exception:
        await db.rollback()
        raise

    return {"message" : "service request accepted successfully"}


@router.patch("/requests/{request_id}/decline")
async def decline_service_request(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if request.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only assigned service provider is allowed to update this request status")

    if request.status != ServiceRequestStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only pending request can be declined")

    request.status = ServiceRequestStatus.DECLINED

    try:
        await db.commit()
        await db.refresh(request)
    except Exception:
        await db.rollback()
        raise

    return {"message": "service request declined successfully"}

@router.patch("/requests/{request_id}/start")
async def start_work(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if request.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only assigned service providers can update this request status")

    if request.status != ServiceRequestStatus.ACCEPTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="you can only start accepted service request")

    request.status = ServiceRequestStatus.START

    try:
        await db.commit()
        await db.refresh(request)
    except Exception:
        await db.rollback()
        raise 

    return {"message": "work started successfully"}

@router.patch("/requests/{request_id}/complete")
async def service_request_completed(request_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if request.provider_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only assigned service provider can update this service request")

    if request.status != ServiceRequestStatus.START:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only START requests can be comleted")

    request.status = ServiceRequestStatus.COMPLETED

    try:
        await db.commit()
        await db.refresh(request)
    except Exception:
        await db.rollback()
        raise

    return {"message" : "service request completed successfully"}