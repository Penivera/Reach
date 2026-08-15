from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_db, get_current_user
from schemas import ServiceCreate, ServiceResponse, ServiceUpdate, ServiceStatus, NearbyServiceQuery, ServiceRequestResponse, ServiceRequestCreate, ServiceRequestStatus
from models import Category, Service, ServiceRequest, Business
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_GeogFromText

router = APIRouter(prefix="/services", tags=["services"])

@router.post("", response_model=ServiceResponse)
async def create_service(service_data: ServiceCreate, db: AsyncSession = Depends(get_db),
                         current_user=Depends(get_current_user)):
    # 1. Get the user's business
    result = await db.execute(
        select(Business).where(
            Business.id == service_data.business_id,
            Business.owner_id == current_user.id
        )
    )

    business = result.scalar_one_or_none()

    if not business:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Business not found or you do not own this business"
        )

    # Check if category exists
    result = await db.execute(
        select(Category).where(
            Category.id == service_data.category_id
        )
    )

    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )

    # Create geographic point
    point = ST_GeogFromText(
        f"POINT({service_data.longitude} {service_data.latitude})"
    )

    # Convert schema data to dictionary
    data = service_data.model_dump()

    # Remove latitude and longitude because they
    # aren't actual Service database columns
    data.pop("latitude")
    data.pop("longitude")

    data["location"] = point

    new_service = Service(**data)

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
async def get_my_services(db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):

    result = await db.execute(select(Service).join(Business).where(Business.owner_id == current_user.id,Service.status != ServiceStatus.ARCHIVED))

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
async def update_service(service_id: int, data: ServiceUpdate, db: AsyncSession = Depends(get_db), 
                         current_user=Depends(get_current_user)):
    
    result = await db.execute(select(Service).join(Business)
                              .where(Service.id == service_id, Business.owner_id == current_user.id))

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service not found or you do not own this service")

    # Validate category if it is being changed
    if data.category_id is not None:
        result = await db.execute(
            select(Category).where(
                Category.id == data.category_id
            )
        )

        category = result.scalar_one_or_none()

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found."
            )

    #Get only fields that were provided
    update_data = data.model_dump(exclude_unset=True)

    # Check coordinates
    has_lat = "latitude" in update_data
    has_lon = "longitude" in update_data

    if has_lat != has_lon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Latitude and longitude must be provided together."
        )

    # Convert coordinates to PostGIS point
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
async def archive_service(service_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Service).join(Business).where(Service.id == service_id, Business.owner_id == current_user.id))

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="service not found or you do not own this service"
        )

    if service.status == ServiceStatus.ARCHIVED:
        return {
            "message": "service is already archived"
        }

    service.status = ServiceStatus.ARCHIVED

    try:
        await db.commit()
        await db.refresh(service)

    except Exception:
        await db.rollback()
        raise

    return {"message": "service archived successfully"}


#client 

@router.post("/requests", response_model=ServiceRequestResponse)
async def create_service_request(requests_data: ServiceRequestCreate, db: AsyncSession = Depends(get_db), 
                                 current_user=Depends(get_current_user)):
    
    result = await db.execute(
        select(Service)
        .join(Business)
        .where(
            Service.id == requests_data.service_id,
            Service.status == ServiceStatus.ACTIVE
        )
    )

    service = result.scalar_one_or_none()

    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="service not found"
        )

    # Get the owner of the business
    result = await db.execute(
        select(Business.owner_id)
        .where(Business.id == service.business_id)
    )

    provider_id = result.scalar_one()

    # Prevent requesting your own service
    if provider_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you cannot request your own service"
        )

    # Prevent duplicate requests
    result = await db.execute(
        select(ServiceRequest).where(
            ServiceRequest.service_id == service.id,
            ServiceRequest.requester_id == current_user.id
        )
    )

    existing_service_request = result.scalar_one_or_none()

    if existing_service_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a request for this service."
        )

    # Create PostGIS point
    point = ST_GeogFromText(f"POINT({requests_data.longitude} {requests_data.latitude})")

    data = requests_data.model_dump()

    data.pop("latitude")
    data.pop("longitude")

    data["location"] = point


    new_request = ServiceRequest(**data, requester_id=current_user.id, provider_id=provider_id)

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
async def get_service_request(request_id: int, db: AsyncSession = Depends(get_db),
                              current_user=Depends(get_current_user)):
    
    result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == request_id))

    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="service request not found")

    if (request.requester_id != current_user.id and request.provider_id != current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you do not have access to this service request"
        )

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