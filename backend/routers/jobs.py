from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from models import Job, JobApplication
from dependencies import get_db, get_current_user
from schemas import (JobCreate, JobUpdate, JobResponse, JobApplicationCreate, 
                     JobApplicationStatusUpdate, JobApplicationUpdate, JobAppplicationResponse, JobStatus, ApplicationStatus)

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("", response_model=JobResponse)
async def create_job(data:JobCreate, db:AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):
    new_job = Job(**data.model_dump(), owner_id=current_user.id)

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
async def update_job(job_id:int, data:JobUpdate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to update this job")
    
    job_data = data.model_dump(exclude_unset=True)

    for field, value in job_data.items():
        setattr(job,field, value)

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
                                                           JobApplication.user_id == current_user.id))
    
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
async def update_application_status(id:int, data: JobApplicationStatusUpdate,
                                    db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(JobApplication).where(JobApplication.id == id))

    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")
    
    result = await db.execute(select(Job).where(Job.id == application.job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="only job owner can change status" )
    
    update_data = data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(application, field, value)

    try:
        await db.commit()
        await db.refresh(application)

    except Exception:
        await db.rollback()
        raise

    return application