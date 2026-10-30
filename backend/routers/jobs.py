from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from solders.pubkey import Pubkey
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, true, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from core import settings
from core.relayer import RelayerNotConfigured
from models import Category, Job, JobApplication, Media, User
from utils import upload_image
from dependencies import get_db, get_current_user
from schemas import (JobCreate, JobUpdate, JobResponse, JobApplicationCreate,
                     JobApplicationStatusUpdate, JobApplicationUpdate, JobAppplicationResponse,
                       JobApplicantResponse,
                       JobOnchainPrepareResponse, JobOnchainSubmitRequest,
                       JobOnchainFundRequest, JobOnchainStateResponse,
                       JobStatus, UrgencyLevel, ApplicationStatus, NearbyJobQuery, MediaType,
                       FundingStatus, PayerType, ProviderAction, ChainTransactionResponse)
from geoalchemy2.functions import ST_GeogFromText, ST_DWithin, ST_Distance
from services.chain import get_relayer, notify_nearby_providers
from services.funding import FundingError, budget_naira, to_usdc_units
from services.provider_flow import (
    ProviderFlowError,
    ProviderStateError,
    ProviderTransactionInvalid,
    ProviderWalletMissing,
    accept_application_onchain,
    prepare_provider_transaction,
    submit_provider_transaction,
)
from services.creator_flow import (
    CreatorFlowError,
    CreatorStateError,
    CreatorTransactionInvalid,
    CreatorWalletMissing,
    prepare_accept,
    prepare_create_task,
    prepare_release,
    read_task_state,
    submit_accept,
    submit_create_task,
    submit_release,
)


router = APIRouter(prefix="/jobs", tags=["jobs"])


def _funded_clause():
    return Job.funding_status == FundingStatus.FUNDED if settings.ESCROW_ENABLED else true()


_URGENCY_WINDOW = {
    UrgencyLevel.ASAP: timedelta(days=2),
    UrgencyLevel.THIS_WEEK: timedelta(days=7),
    UrgencyLevel.FLEXIBLE: timedelta(days=30),
}


def _compute_expiry(urgency, scheduled_for=None):
    if scheduled_for is not None:
        return scheduled_for
    return datetime.now(timezone.utc) + _URGENCY_WINDOW[urgency]


def _is_duplicate_job_application_error(exc: IntegrityError) -> bool:
    constraint_name = getattr(
        getattr(exc.orig, "diag", None), "constraint_name", None
    )
    sqlite_unique_error = (
        "UNIQUE constraint failed: "
        "job_applications.job_id, job_applications.applicant_id"
    )
    return (
        constraint_name == "uq_job_applications_job_applicant"
        or sqlite_unique_error in str(exc.orig)
    )


def _not_expired():
    return Job.expires_at > func.now()


def _provider_flow_error(exc: ProviderFlowError) -> HTTPException:
    if isinstance(exc, ProviderWalletMissing):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ProviderTransactionInvalid):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, ProviderStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, RelayerNotConfigured):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _creator_flow_error(exc: CreatorFlowError) -> HTTPException:
    if isinstance(exc, CreatorWalletMissing):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, CreatorTransactionInvalid):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    if isinstance(exc, CreatorStateError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, RelayerNotConfigured):
        return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc))
    return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc))


def _creator_prepare_response(prepared) -> JobOnchainPrepareResponse:
    return JobOnchainPrepareResponse(
        action=prepared.action.value,
        job_id=prepared.job_id,
        task_id=prepared.task_id,
        signer_address=prepared.signer_address,
        provider_address=prepared.provider_address,
        transaction=prepared.transaction,
        recent_blockhash=prepared.recent_blockhash,
        amount_units=prepared.amount_units,
        escrow_units=prepared.escrow_units,
        creation_fee_units=prepared.creation_fee_units,
        already_done=prepared.already_done,
    )


async def _get_job_or_404(job_id: int, db: AsyncSession) -> Job:
    job = (await db.execute(select(Job).where(Job.id == job_id))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")
    return job


async def _get_accepted_application_or_400(
    job_id: int, db: AsyncSession
) -> JobApplication:
    application = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job_id,
                JobApplication.status == ApplicationStatus.ACCEPTED,
            )
        )
    ).scalar_one_or_none()
    if not application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="no accepted applicant for this job",
        )
    return application

@router.post("", response_model=JobResponse)
async def create_job(job_data:JobCreate, db:AsyncSession=Depends(get_db), current_user = Depends(get_current_user)):

    category = (
        await db.execute(select(Category).where(Category.id == job_data.category_id))
    ).scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    point = ST_GeogFromText(f"POINT({job_data.longitude} {job_data.latitude})")

    data = job_data.model_dump()
    data["expires_at"] = _compute_expiry(job_data.urgency, job_data.scheduled_for)

    if settings.ESCROW_ENABLED:
        try:
            data["budget"] = float(budget_naira(job_data.budget))
        except FundingError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    data.pop("latitude")
    data.pop("longitude")
    data["location"] = point

    new_job = Job(
        **data,
        owner_id=current_user.id,
        # Escrow-backed tasks open for providers once funding is on-chain.
        status=JobStatus.PENDING_FUNDING if settings.ESCROW_ENABLED else JobStatus.OPEN,
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
    # Escrow-backed tasks appear in the provider-facing feed only after funding.
    result = await db.execute(
        select(Job)
        .where(
            Job.status == JobStatus.OPEN,
            _funded_clause(),
            _not_expired(),
        )
        .order_by(Job.created_at.desc())
    )

    jobs = result.scalars().all()

    return jobs

@router.get("/me", response_model=list[JobResponse])
async def my_jobs(db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.owner_id == current_user.id))

    my_jobs = result.scalars().all()

    return my_jobs


@router.get("/nearby", response_model=list[JobResponse])
async def get_nearby_jobs(data: NearbyJobQuery = Depends(), db: AsyncSession = Depends(get_db)):
    search_point = func.ST_GeogFromText(f"POINT({data.longitude} {data.latitude})")

    query = select(Job).where(
        Job.status == JobStatus.OPEN,
        _funded_clause(),
        _not_expired(),
        ST_DWithin(Job.location, search_point, data.radius * 1000),
    )

    if data.category_id is not None:
        query = query.where(Job.category_id == data.category_id)

    query = query.order_by(ST_Distance(Job.location, search_point))

    result = await db.execute(query)

    jobs = result.scalars().all()

    return jobs


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

    if job.status not in (JobStatus.OPEN, JobStatus.PENDING_FUNDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open or pending-funding jobs can be updated",
        )

    data = job_data.model_dump(exclude_unset=True)

    if "urgency" in data or "scheduled_for" in data:
        data["expires_at"] = _compute_expiry(
            data.get("urgency", job.urgency),
            data.get("scheduled_for", job.scheduled_for),
        )

    if settings.ESCROW_ENABLED and "budget" in data:
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
        # When escrow is enabled, the provider must first complete the on-chain
        # instruction so the DB does not get ahead of the escrow state.
        if settings.ESCROW_ENABLED and job.onchain_status != "AwaitingApproval":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Complete the task on-chain from your Solana wallet first."
                ),
            )
        job.worker_completed = True

    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you are not involved in this job")


    if not settings.ESCROW_ENABLED and job.client_completed and job.worker_completed:
        job.status = JobStatus.COMPLETED

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

    if job.status not in (JobStatus.OPEN, JobStatus.PENDING_FUNDING):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only open jobs can be deleted",
        )
    job.status = JobStatus.CANCELLED

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

@router.get("/{job_id}/address")
async def get_job_address(job_id: int, db: AsyncSession = Depends(get_db), current_user=Depends(get_current_user)):
    job = await _get_job_or_404(job_id, db)
    if job.owner_id != current_user.id:
        accepted = (await db.execute(select(JobApplication).where(
            JobApplication.job_id == job.id,
            JobApplication.applicant_id == current_user.id,
            JobApplication.status == ApplicationStatus.ACCEPTED))).scalar_one_or_none()
        if not accepted:
            raise HTTPException(status_code=403, detail="not allowed to see this address")
    return {"address_details": job.address_details}

#Job Applications

@router.post("/{job_id}/apply", response_model=JobAppplicationResponse)
async def create_job_application(job_id:int, data: JobApplicationCreate, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job.owner_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you cannot apply to your own job")

    if job.status != JobStatus.OPEN or job.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This job is no longer accepting applications")

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

    except IntegrityError as exc:
        await db.rollback()
        if _is_duplicate_job_application_error(exc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="you already applied",
            ) from exc
        raise
    except Exception:
        await db.rollback()
        raise

    return application

@router.post(
    "/{job_id}/onchain/apply",
    response_model=JobOnchainPrepareResponse,
)
async def prepare_onchain_application(
    job_id: int,
    data: JobApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Create the DB application and return the `apply` transaction to sign.

    `apply` requires the provider's own Solana key. The backend creates the
    local application row, builds the instruction, and returns it as a legacy
    transaction for the provider's wallet. Call
    `POST /jobs/{job_id}/onchain/apply/submit` with the signed bytes.
    """
    job = await _get_job_or_404(job_id, db)

    if job.owner_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="you cannot apply to your own job",
        )

    if (
        job.status != JobStatus.OPEN
        or job.funding_status != FundingStatus.FUNDED
        or (
            job.expires_at is not None
            and job.expires_at < datetime.now(timezone.utc)
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This job is not open for applications on-chain yet",
        )

    existing = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job.id,
                JobApplication.applicant_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if existing and existing.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This application can no longer be changed",
        )

    try:
        prepared = await prepare_provider_transaction(
            db,
            job=job,
            user=current_user,
            action=ProviderAction.APPLY,
        )
    except ProviderFlowError as exc:
        raise _provider_flow_error(exc)
    except RelayerNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    application = existing
    if application is None:
        application = JobApplication(
            **data.model_dump(),
            job_id=job.id,
            applicant_id=current_user.id,
        )
        db.add(application)

        try:
            await db.commit()
            await db.refresh(application)
        except IntegrityError as exc:
            await db.rollback()
            if _is_duplicate_job_application_error(exc):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="you already applied",
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    return JobOnchainPrepareResponse(
        action=prepared.action.value,
        job_id=prepared.job_id,
        task_id=prepared.task_id,
        provider_address=prepared.provider_address,
        transaction=prepared.transaction,
        recent_blockhash=prepared.recent_blockhash,
        expires_at=prepared.expires_at,
        escrow_units=prepared.escrow_units,
        already_done=prepared.already_done,
        application=JobAppplicationResponse.model_validate(application),
    )


@router.post(
    "/{job_id}/onchain/apply/submit",
    response_model=ChainTransactionResponse,
)
async def submit_onchain_application(
    job_id: int,
    data: JobOnchainSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit the provider-signed `apply` transaction."""
    job = await _get_job_or_404(job_id, db)

    application = (
        await db.execute(
            select(JobApplication).where(
                JobApplication.job_id == job.id,
                JobApplication.applicant_id == current_user.id,
                JobApplication.status == ApplicationStatus.PENDING,
            )
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create the application before submitting it on-chain",
        )

    try:
        transaction = await submit_provider_transaction(
            db,
            job=job,
            user=current_user,
            action=ProviderAction.APPLY,
            signed_transaction=data.signed_transaction,
        )
    except ProviderFlowError as exc:
        raise _provider_flow_error(exc)
    except RelayerNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    return ChainTransactionResponse.model_validate(transaction)


@router.post(
    "/{job_id}/onchain/complete",
    response_model=JobOnchainPrepareResponse,
)
async def prepare_onchain_completion(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the `complete_task` transaction for the accepted provider."""
    job = await _get_job_or_404(job_id, db)
    application = await _get_accepted_application_or_400(job.id, db)

    if application.applicant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the accepted provider can complete this task",
        )

    try:
        prepared = await prepare_provider_transaction(
            db,
            job=job,
            user=current_user,
            action=ProviderAction.COMPLETE,
        )
    except ProviderFlowError as exc:
        raise _provider_flow_error(exc)
    except RelayerNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    return JobOnchainPrepareResponse(
        action=prepared.action.value,
        job_id=prepared.job_id,
        task_id=prepared.task_id,
        provider_address=prepared.provider_address,
        transaction=prepared.transaction,
        recent_blockhash=prepared.recent_blockhash,
        expires_at=prepared.expires_at,
        escrow_units=prepared.escrow_units,
        already_done=prepared.already_done,
    )


@router.post(
    "/{job_id}/onchain/complete/submit",
    response_model=ChainTransactionResponse,
)
async def submit_onchain_completion(
    job_id: int,
    data: JobOnchainSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit the provider-signed `complete_task` transaction."""
    job = await _get_job_or_404(job_id, db)
    application = await _get_accepted_application_or_400(job.id, db)

    if application.applicant_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the accepted provider can complete this task",
        )

    try:
        transaction = await submit_provider_transaction(
            db,
            job=job,
            user=current_user,
            action=ProviderAction.COMPLETE,
            signed_transaction=data.signed_transaction,
        )
    except ProviderFlowError as exc:
        raise _provider_flow_error(exc)
    except RelayerNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )

    return ChainTransactionResponse.model_validate(transaction)


# -- creator-signed (wallet-funded) escrow --------------------------------


@router.post(
    "/{job_id}/onchain/fund",
    response_model=JobOnchainPrepareResponse,
)
async def prepare_onchain_funding(
    job_id: int,
    data: JobOnchainFundRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the ``create_task`` transaction for the client's wallet.

    The client becomes the on-chain creator, so the escrow is funded directly
    from their USDC token account. Sign the returned transaction and call
    ``POST /jobs/{job_id}/onchain/fund/submit`` with the signed bytes.
    """
    job = await _get_job_or_404(job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can fund this task",
        )

    try:
        units = to_usdc_units(data.usdc_amount)
    except FundingError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    try:
        prepared = await prepare_create_task(
            db,
            job=job,
            user=current_user,
            usdc_units=units,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return _creator_prepare_response(prepared)


@router.post(
    "/{job_id}/onchain/fund/submit",
    response_model=ChainTransactionResponse,
)
async def submit_onchain_funding(
    job_id: int,
    data: JobOnchainSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit the client-signed ``create_task`` transaction."""
    job = await _get_job_or_404(job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can fund this task",
        )

    try:
        transaction = await submit_create_task(
            db,
            job=job,
            user=current_user,
            signed_transaction=data.signed_transaction,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return ChainTransactionResponse.model_validate(transaction)


@router.post(
    "/applications/{application_id}/onchain/accept",
    response_model=JobOnchainPrepareResponse,
)
async def prepare_onchain_acceptance(
    application_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the ``accept`` transaction for a wallet-funded task."""
    application = (
        await db.execute(
            select(JobApplication).where(JobApplication.id == application_id)
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    job = await _get_job_or_404(application.job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can accept an application",
        )

    provider = await db.get(User, application.applicant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The applicant no longer exists",
        )

    try:
        prepared = await prepare_accept(
            db,
            job=job,
            application=application,
            user=current_user,
            provider=provider,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return _creator_prepare_response(prepared)


@router.post(
    "/applications/{application_id}/onchain/accept/submit",
    response_model=ChainTransactionResponse,
)
async def submit_onchain_acceptance(
    application_id: int,
    data: JobOnchainSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit the client-signed ``accept`` transaction."""
    application = (
        await db.execute(
            select(JobApplication).where(JobApplication.id == application_id)
        )
    ).scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    job = await _get_job_or_404(application.job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can accept an application",
        )

    provider = await db.get(User, application.applicant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The applicant no longer exists",
        )

    try:
        transaction = await submit_accept(
            db,
            job=job,
            application=application,
            user=current_user,
            provider=provider,
            signed_transaction=data.signed_transaction,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return ChainTransactionResponse.model_validate(transaction)


@router.post(
    "/{job_id}/onchain/release",
    response_model=JobOnchainPrepareResponse,
)
async def prepare_onchain_release(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the ``approve_work`` transaction for a wallet-funded task."""
    job = await _get_job_or_404(job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can release the escrow",
        )

    application = await _get_accepted_application_or_400(job.id, db)
    provider = await db.get(User, application.applicant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The accepted provider no longer exists",
        )

    try:
        prepared = await prepare_release(
            db,
            job=job,
            application=application,
            user=current_user,
            provider=provider,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return _creator_prepare_response(prepared)


@router.post(
    "/{job_id}/onchain/release/submit",
    response_model=ChainTransactionResponse,
)
async def submit_onchain_release(
    job_id: int,
    data: JobOnchainSubmitRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Submit the client-signed ``approve_work`` transaction."""
    job = await _get_job_or_404(job_id, db)

    if job.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the job owner can release the escrow",
        )

    application = await _get_accepted_application_or_400(job.id, db)
    provider = await db.get(User, application.applicant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The accepted provider no longer exists",
        )

    try:
        transaction = await submit_release(
            db,
            job=job,
            application=application,
            user=current_user,
            provider=provider,
            signed_transaction=data.signed_transaction,
        )
    except (CreatorFlowError, RelayerNotConfigured) as exc:
        raise _creator_flow_error(exc)

    return ChainTransactionResponse.model_validate(transaction)


@router.get(
    "/{job_id}/onchain",
    response_model=JobOnchainStateResponse,
)
async def get_onchain_task(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Read the task state from Solana."""
    job = await _get_job_or_404(job_id, db)

    if job.owner_id != current_user.id:
        accepted = (
            await db.execute(
                select(JobApplication).where(
                    JobApplication.job_id == job.id,
                    JobApplication.applicant_id == current_user.id,
                    JobApplication.status == ApplicationStatus.ACCEPTED,
                )
            )
        ).scalar_one_or_none()
        if not accepted:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not allowed to view this task",
            )

    try:
        relayer = get_relayer()
        state = await read_task_state(relayer, job.id)
    except RelayerNotConfigured as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        )
    except CreatorFlowError as exc:
        raise _creator_flow_error(exc)

    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The task has no on-chain state yet",
        )

    return JobOnchainStateResponse(
        task_id=state.id,
        creator=str(state.creator),
        provider=str(state.provider) if state.provider else None,
        status=state.status,
        labor_fee=state.labor_fee,
        material_cost=state.material_cost,
        creator_locked_balance=state.creator_locked_balance,
        provider_locked_balance=state.provider_locked_balance,
        advanced_disbursed=state.advanced_disbursed,
        created_at=state.created_at,
        updated_at=state.updated_at,
    )


@router.get("/{job_id}/applications", response_model=list[JobApplicantResponse])
async def get_job_applications(job_id:int, db:AsyncSession=Depends(get_db),
                               current_user=Depends(get_current_user)):

    result = await db.execute(select(Job).where(Job.id == job_id))

    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    if job.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only job owner can see applicants")

    result = await db.execute(
        select(JobApplication)
        .options(selectinload(JobApplication.applicant))
        .where(JobApplication.job_id == job_id)
    )

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

    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending applications can be changed",
        )

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


@router.delete("/applications/{id}")
async def delete(id:int, db:AsyncSession=Depends(get_db), current_user=Depends(get_current_user)):
    result = await db.execute(select(JobApplication).where(JobApplication.id == id))

    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="application not found")

    if application.applicant_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="you are not authorized to delete this application")

    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending applications can be changed",
        )

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

        if job.payer_type == PayerType.WALLET:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This escrow was created by the client's wallet. Accept "
                    "the application from that wallet via "
                    f"POST /jobs/applications/{application.id}/onchain/accept."
                ),
            )

        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending applications can be accepted.",
            )

        # Escrow-backed tasks cannot be staffed until their funding is on-chain.
        if settings.ESCROW_ENABLED and job.funding_status != FundingStatus.FUNDED:
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

        provider = await db.get(User, application.applicant_id)
        if not provider:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The applicant no longer exists",
            )

        if settings.ESCROW_ENABLED:
            # The program's `accept` is signed by the task creator. For a
            # custodial escrow the relayer is the creator, so the backend signs it.
            # This also verifies that the provider actually applied on-chain.
            try:
                await accept_application_onchain(
                    db,
                    job=job,
                    provider=provider,
                )
            except ProviderFlowError as exc:
                raise _provider_flow_error(exc)
            except RelayerNotConfigured as exc:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
                )

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

        # Mirror the accepted task in the application lifecycle. When escrow
        # is enabled, the on-chain accept instruction also moves it to InProgress.
        job.status = JobStatus.IN_PROGRESS

    # Rejecting an applicant
    elif data.status == ApplicationStatus.REJECTED:
        if application.status != ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only pending applications can be rejected",
            )
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
        if not onchain_tx_hash:
            raise HTTPException(
                status_code=400,
                detail="onchain_tx_hash is required to link a task",
            )

        wallet = (getattr(current_user, "onchain_address", None) or "").strip()
        if not wallet:
            raise HTTPException(
                status_code=400,
                detail="Add your Solana wallet before linking an on-chain task",
            )
        try:
            wallet_pubkey = Pubkey.from_string(wallet)
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="The saved Solana wallet address is not valid",
            )

        try:
            state = await read_task_state(get_relayer(), job.id)
        except RelayerNotConfigured as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
            )
        except CreatorFlowError as exc:
            raise _creator_flow_error(exc)

        if state is None:
            raise HTTPException(
                status_code=400,
                detail="No on-chain task was found for this job",
            )
        if state.creator != wallet_pubkey:
            raise HTTPException(
                status_code=403,
                detail="The on-chain task was not created by your wallet",
            )
        if state.status != "Open":
            raise HTTPException(
                status_code=400,
                detail=f"The task is already '{state.status}' on-chain",
            )

        job.onchain_task_id = job.id
        job.onchain_tx_hash = onchain_tx_hash
        job.funding_status = FundingStatus.FUNDED
        job.payer_type = PayerType.WALLET
        job.onchain_status = state.status
        job.status = JobStatus.OPEN
    elif onchain_tx_hash is not None:
        job.onchain_tx_hash = onchain_tx_hash

    await db.commit()
    await db.refresh(job)
    if task_id_val is not None:
        await notify_nearby_providers(db, job)
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
