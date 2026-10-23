from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from models import Job, JobApplication, Media
from utils import upload_image
from dependencies import get_db, get_current_user
from schemas import (JobCreate, JobUpdate, JobResponse, JobApplicationCreate,
                     JobApplicationStatusUpdate, JobApplicationUpdate, JobAppplicationResponse,
                       JobStatus, ApplicationStatus, NearbyJobQuery, MediaType,
                       FundingStatus, PayerType)
from geoalchemy2.functions import ST_GeogFromText, ST_DWithin, ST_Distance
from services.funding import FundingError, budget_naira


router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse)
async def create_job(job_data:JobCreate, db:AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    
    point = ST_GeogFromText(f"POINT({job_data.longitude} {job_data.latitude})")
    
    data = job_data.model_dump()

    try:
        # Reject a budget that cannot be funded before the job exists, so the
        # failure happens at creation rather than at checkout.
        data["budget"] = float(budget_naira(job_data.budget))
    except FundingError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    data.pop("latitude")
    data.pop("longitude")
    data["location"] = point

    new_job = Job(
        **data,
        owner_id=current_user.id,
        # Model 1: a task is created waiting for its escrow to be locked.
        # It opens for providers once the funding is on-chain.
        status=JobStatus.PENDING_FUNDING,
    )


    db.add(new_job)
    try:
        await db.commit()

        await db.refresh(new_job)
    except Exception:
        await db.rollback()
        raise

    return new_job

@router.get("", response_model=list[JobResponse])
async def get_jobs(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job))

    jobs = result.scalars().all()

    return jobs
    
@router.get("/me", response_model=list[JobResponse])
async def my_jobs(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.owner_id == current_user.id))

    my_jobs = result.scalars().all()

    return my_jobs

@router.get("/{job_id}",response_model=JobResponse)
async def get_job(job_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    return job

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(job_id:int, job_data:JobUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to update this job")
    
    data = job_data.model_dump(exclude_unset=True)

    if "budget" in data:
        try:
            data["budget"] = float(budget_naira(data["budget"]))
        except FundingError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    if "latitude" in data or "longitude" in data:
        if "latitude" not in data or "longitude" not in data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="latitude and longitude must be updated together",
            )

        point = ST_GeogFromText(f"POINT({data['longitude']} {data['latitude']})")

        data.pop("latitude")
        data.pop("longitude")
        data["location"] = point

    for field, value in data.items():
        setattr(job, field, value)

    try:
        await db.commit()
        await db.refresh(job)
    except Exception:
        await db.rollback()
        raise

    return job

@router.patch("/{job_id}/completion", response_model=JobResponse)
async def complete_job(job_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    #get job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    #check if job exist
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    #verify if job is in progress
    if job.status != JobStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="only jobs in progress can be completed")

    #get accepted applicant
    result = await db.execute(select(JobApplication).where(JobApplication.job_id == job_id,
                                                        JobApplication.status == ApplicationStatus.ACCEPTED))

    application = result.scalar_one_or_none()


    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no applicant not found for this job")

    #Determine who is comleting the job (either employer or worker) and update the status
    if current_user.id == job.owner_id:
        job.client_completed = True

    elif current_user.id == application.applicant_id:
        job.worker_completed = True

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you are not involved in this job")


    # Both confirmations are recorded, but the job stays IN_PROGRESS. In
    # Model 1 the program completes the task when the creator signs
    # `approve_work`; that is also when the provider is paid. Marking the job
    # complete before the escrow is released would make the DB claim a
    # settlement that has not happened.

    try:
        await db.commit()
        await db.refresh(job)
    except Exception:
        await db.rollback()
        raise

    return job
    



@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(job_id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you are not allowed to delete this job")
    
    await db.delete(job)

    try: 
        await db.commit()

    except Exception:
        await db.rollback()
        raise

    return

@router.post("/{job_id}/images")
async def upload_job_image(job_id: int, file: UploadFile = File(...), 
                           db: AsyncSession = Depends(get_db),current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    #Only the job owner can upload images
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only upload images to your own job")


    image_url = await upload_image(file, folder=f"jobs/{job.id}")

    media = Media(url=image_url, media_type=MediaType.JOB, uploaded_by=current_user.id, job_id=job.id)

    db.add(media)


    try:
        await db.commit()
        await db.refresh(media)

    except Exception:
        await db.rollback()
        raise

    return media

#Job Applications

@router.post("/{job_id}/apply", response_model=JobAppplicationResponse)
async def create_job_application(job_id:int, data: JobApplicationCreate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    
    if job.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you cannot apply to your own job")
    
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This job is no longer accepting application")
    
    #prevent duplicate application

    result = await db.execute(select(JobApplication).where(JobApplication.job_id == job.id, 
                                                           JobApplication.applicant_id == current_user.id))
    
    existing_application = result.scalar_one_or_none()

    if existing_application:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="you already applied")
    
    application = JobApplication(**data.model_dump(),
                                 job_id=job.id, applicant_id = current_user.id)

    db.add(application)

    try:
        await db.commit()
        await db.refresh(application)

    except Exception:
        await db.rollback()
        raise

    return application

@router.get("/nearby", response_model=list[JobResponse])
async def get_nearby_jobs(data:NearbyJobQuery=Depends(), db:AsyncSession=Depends(get_db)):
    search_point = func.ST_GeogFromText(f"POINT({data.longitude} {data.latitude})")

    query = select(Job).where(ST_DWithin(Job.location, search_point, data.radius*1000))

    if data.category_id is not None:
        query = query.where(Job.category_id == data.category_id)

    query = query.order_by(ST_Distance(Job.location, search_point))

    result = await db.execute(query)
    
    jobs = result.scalars().all()

    return jobs


@router.get("/{job_id}/applications", response_model=list[JobAppplicationResponse])
async def get_job_applications(job_id:int, db:AsyncSession=Depends(get_db),
                               current_user=Depends(get_current_user)):
    
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job owner can see applicants")

    result = await db.execute(select(JobApplication).where(JobApplication.job_id == job_id))

    applications = result.scalars().all()

    return applications



@router.get("/applications/me", response_model=list[JobAppplicationResponse])
async def get_my_job_applications(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(JobApplication).where(JobApplication.applicant_id == current_user.id))

    applications = result.scalars().all()

    return applications

@router.patch("/applications/{id}", response_model=JobAppplicationResponse)
async def update_application(id:int, data: JobApplicationUpdate,
                             db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):

    result = await db.execute(select(JobApplication).where(JobApplication.id == id))

    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    
    if application.applicant_id  != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only applied users can edit their application")
    
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(application, field, value)

    try:

        await db.commit()
        await db.refresh(application)

    except Exception:
        await db.rollback()
        raise
    

@router.delete("/applications/{id}")
async def delete(id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(JobApplication).where(JobApplication.id == id))

    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")

    if application.applicant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you are not authorized to delete this application")
    

    await db.delete(application)

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    return {"message": "application deleted successfully"}

@router.patch("/applications/{id}/status", response_model=JobAppplicationResponse)
async def update_application_status(id: int,data: JobApplicationStatusUpdate, 
                                    db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    
    # Get application
    result = await db.execute(select(JobApplication).where(JobApplication.id == id))

    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Application not found")

    # Get job
    result = await db.execute(select(Job).where(Job.id == application.job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    #Only the job owner can change application status
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the job owner can change application status")

    # Accepting an applicant
    if data.status == ApplicationStatus.ACCEPTED:

        # Model 1: the escrow is locked when the task is created, so a task
        # cannot be staffed until its funding is on-chain.
        if job.funding_status != FundingStatus.FUNDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This task is not funded yet. Providers can be accepted once the escrow is on-chain.",
            )

        if job.status != JobStatus.OPEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only open tasks can accept an applicant.",
            )

        # Prevent accepting another applicant if one is already accepted
        result = await db.execute(select(JobApplication).where(JobApplication.job_id == job.id, JobApplication.status == ApplicationStatus.ACCEPTED, JobApplication.id != application.id))
        
        existing_accepted = result.scalar_one_or_none()

        if existing_accepted:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This job already has an accepted applicant.")

        # Accept this application
        application.status = ApplicationStatus.ACCEPTED

        # Reject every other pending application
        result = await db.execute(select(JobApplication).where(
                                JobApplication.job_id == job.id,
                                JobApplication.id != application.id,
                                JobApplication.status == ApplicationStatus.PENDING))

        pending_applications = result.scalars().all()

        for pending_application in pending_applications:
            pending_application.status = ApplicationStatus.REJECTED

        # The program moves the task to InProgress when the creator accepts.
        # This mirrors that state; the on-chain `accept` instruction must be
        # signed by the creator before the provider can complete the task.
        job.status = JobStatus.IN_PROGRESS

    # Rejecting an applicant
    elif data.status == ApplicationStatus.REJECTED:
        application.status = ApplicationStatus.REJECTED

    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid application status.")

    try:
        await db.commit()
        await db.refresh(application)

    except Exception:
        await db.rollback()
        raise

    return application


# routers/jobs.py

@router.get("/{job_id}/accepted-application", response_model=JobAppplicationResponse)
async def get_accepted_application(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    result = await db.execute(select(JobApplication).where(
        JobApplication.job_id == job.id,
        JobApplication.status == ApplicationStatus.ACCEPTED))
    accepted_applicant = result.scalar_one_or_none()

    if not accepted_applicant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no accepted application yet")

    is_owner = job.owner_id == current_user.id
    is_accepted_applicant = accepted_applicant.applicant_id == current_user.id

    if not (is_owner or is_accepted_applicant):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="not authorized to view this")

    return accepted_applicant

@router.patch("/{job_id}/link-chain", response_model=JobResponse)
async def link_job_chain(
    job_id: int,
    onchain_task_id: int | None = None,
    near_task_id: int | None = None,  # Deprecated: retained for legacy compatibility
    onchain_tx_hash: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="job not found")
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="not your job")
    
    task_id_val = onchain_task_id if onchain_task_id is not None else near_task_id
    if task_id_val is not None:
        if task_id_val != job.id:
            raise HTTPException(
                status_code=400,
                detail="onchain_task_id must match the job id",
            )
        job.onchain_task_id = task_id_val
        # A native wallet payer signs `create_task` themselves, so this is the
        # point at which the escrow is known to be on-chain and the task can
        # open for providers.
        job.funding_status = FundingStatus.FUNDED
        job.payer_type = PayerType.WALLET
        job.onchain_status = "Open"
        job.status = JobStatus.OPEN
    if onchain_tx_hash is not None:
        job.onchain_tx_hash = onchain_tx_hash

    await db.commit()
    await db.refresh(job)
    return job

@router.patch("/applications/{id}/link-chain", response_model=JobAppplicationResponse)
async def link_application_chain(
    id: int,
    onchain_application_id: int | None = None,
    near_application_id: int | None = None,  # Deprecated: retained for legacy compatibility
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    result = await db.execute(select(JobApplication).where(JobApplication.id == id))
    application = result.scalar_one_or_none()
    if not application:
        raise HTTPException(status_code=404, detail="application not found")
    if application.applicant_id != current_user.id:
        raise HTTPException(status_code=403, detail="not your application")
    
    app_id_val = onchain_application_id if onchain_application_id is not None else near_application_id
    if app_id_val is not None:
        application.onchain_application_id = app_id_val

    await db.commit()
    await db.refresh(application)
    return application
