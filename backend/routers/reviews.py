from fastapi import APIRouter, Depends, HTTPException, status
from models import Review, User, Job, JobApplication, Service, ServiceRequest
from schemas import ReviewCreate, ReviewResponse, JobStatus, ApplicationStatus, ServiceRequestStatus
from sqlalchemy.ext.asyncio import AsyncSession
from dependencies import get_current_user, get_db
from sqlalchemy import select
router = APIRouter(prefix="/reviews", tags=["Reviews"])

@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(review_data: ReviewCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    
    # Review must belong to either a job or a service
    if review_data.job_id is None and review_data.service_id is None:
        raise HTTPException(status_code=400, detail="A review must be associated with a job or service.")

    if review_data.job_id is not None and review_data.service_id is not None:
        raise HTTPException(status_code=400, detail="A review cannot belong to both a job and a service.")

    # User cannot review themselves
    if review_data.reviewed_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot review yourself.")


    # JOB REVIEW
    if review_data.job_id is not None:

        result = await db.execute(
            select(Job).where(Job.id == review_data.job_id)
        )

        job = result.scalar_one_or_none()

        if not job:
            raise HTTPException(
                status_code=404,
                detail="Job not found."
            )

        # Job must be completed
        if job.status != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail="You can only review a completed job."
            )

        # Check whether current user is the job owner
        if job.owner_id == current_user.id:

            # Find accepted application
            result = await db.execute(
                select(JobApplication)
                .where(
                    JobApplication.job_id == job.id,
                    JobApplication.status == ApplicationStatus.ACCEPTED
                )
            )

            application = result.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=400,
                    detail="This job does not have an accepted worker."
                )

            if application.applicant_id != review_data.reviewed_user_id:
                raise HTTPException(
                    status_code=403,
                    detail="You can only review the worker who completed this job."
                )

        else:
            # Current user must be the accepted worker
            result = await db.execute(
                select(JobApplication)
                .where(
                    JobApplication.job_id == job.id,
                    JobApplication.applicant_id == current_user.id,
                    JobApplication.status == ApplicationStatus.ACCEPTED
                )
            )

            application = result.scalar_one_or_none()

            if not application:
                raise HTTPException(
                    status_code=403,
                    detail="You did not participate in this job."
                )

            # Worker can only review the job owner
            if review_data.reviewed_user_id != job.owner_id:
                raise HTTPException(
                    status_code=403,
                    detail="You can only review the job owner."
                )


    # SERVICE REVIEW
    if review_data.service_id is not None:

        result = await db.execute(
            select(Service).where(Service.id == review_data.service_id)
        )

        service = result.scalar_one_or_none()

        if not service:
            raise HTTPException(
                status_code=404,
                detail="Service not found."
            )

        # Find completed service request
        result = await db.execute(
            select(ServiceRequest)
            .where(
                ServiceRequest.service_id == service.id,
                ServiceRequest.status == ServiceRequestStatus.COMPLETED
            )
        )

        requests = result.scalars().all()

        valid_request = None

        for request in requests:
            if (
                request.requester_id == current_user.id
                and request.provider_id == review_data.reviewed_user_id
            ):
                valid_request = request
                break

            if (
                request.provider_id == current_user.id
                and request.requester_id == review_data.reviewed_user_id
            ):
                valid_request = request
                break

        if not valid_request:
            raise HTTPException(
                status_code=403,
                detail="You did not complete this service transaction."
            )


    # PREVENT DUPLICATE REVIEW
    query = select(Review).where(
        Review.reviewer_id == current_user.id
    )

    if review_data.job_id is not None:
        query = query.where(
            Review.job_id == review_data.job_id
        )

    if review_data.service_id is not None:
        query = query.where(
            Review.service_id == review_data.service_id
        )

    result = await db.execute(query)

    existing_review = result.scalar_one_or_none()

    if existing_review:
        raise HTTPException(
            status_code=400,
            detail="You have already reviewed this transaction."
        )


    # CREATE REVIEW

    review = Review(
        reviewer_id=current_user.id,
        reviewed_user_id=review_data.reviewed_user_id,
        job_id=review_data.job_id,
        service_id=review_data.service_id,
        rating=review_data.rating,
        comment=review_data.comment
    )

    db.add(review)

    await db.commit()
    await db.refresh(review)

    return review

@router.get("/job/{job_id}", response_model=list[ReviewResponse])
async def get_job_reviews(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Review)
        .where(Review.job_id == job_id)
        .order_by(Review.created_at.desc())
    )

    return result.scalars().all()


@router.get("/service/{service_id}", response_model=list[ReviewResponse])
async def get_service_reviews(service_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Review)
        .where(Review.service_id == service_id)
        .order_by(Review.created_at.desc())
    )

    reviews = result.scalars().all()

    return reviews

@router.get("/user/{user_id}", response_model=list[ReviewResponse])
async def get_user_reviews(user_id: int, db: AsyncSession = Depends(get_db)):

    result = await db.execute(
        select(Review)
        .where(Review.reviewed_user_id == user_id)
        .order_by(Review.created_at.desc()))

    reviews = result.scalars().all()

    return reviews


@router.delete("/{review_id}")
async def delete_review(review_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):
    result = await db.execute(select(Review).where(Review.id == review_id))

    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(status_code=404, detail="Review not found.")

    if review.reviewer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own reviews.")

    await db.delete(review)
    await db.commit()

    return {"message": "Review deleted successfully."}