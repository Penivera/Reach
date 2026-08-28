from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from models import Report, User, Job
from schemas import ReportCreate, ReportResponse
from dependencies import get_current_user, get_db


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(report_data: ReportCreate, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    # A report must target either a user or a job
    if (
        report_data.reported_user_id is None
        and report_data.reported_job_id is None
    ):
        raise HTTPException(
            status_code=400,
            detail="A report must target a user or a job."
        )

    # A report cannot target both
    if (
        report_data.reported_user_id is not None
        and report_data.reported_job_id is not None
    ):
        raise HTTPException(
            status_code=400,
            detail="A report cannot target both a user and a job."
        )

    # Cannot report yourself
    if report_data.reported_user_id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="You cannot report yourself."
        )

    # Check reported user exists
    if report_data.reported_user_id is not None:

        result = await db.execute(
            select(User).where(
                User.id == report_data.reported_user_id
            )
        )

        reported_user = result.scalar_one_or_none()

        if not reported_user:
            raise HTTPException(
                status_code=404,
                detail="Reported user not found."
            )

    # Check reported job exists
    if report_data.reported_job_id is not None:

        result = await db.execute(
            select(Job).where(
                Job.id == report_data.reported_job_id
            )
        )

        reported_job = result.scalar_one_or_none()

        if not reported_job:
            raise HTTPException(
                status_code=404,
                detail="Reported job not found."
            )

    # Create report
    report = Report(
        reporter_id=current_user.id,
        reported_user_id=report_data.reported_user_id,
        reported_job_id=report_data.reported_job_id,
        reason=report_data.reason,
        description=report_data.description,
        status="PENDING"
    )

    db.add(report)

    await db.commit()
    await db.refresh(report)

    return report


@router.get("/my", response_model=list[ReportResponse])
async def get_my_reports(db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    result = await db.execute(
        select(Report)
        .where(
            Report.reporter_id == current_user.id
        )
        .order_by(Report.created_at.desc())
    )

    reports = result.scalars().all()

    return reports


@router.get("/{report_id}", response_model=ReportResponse)
async def get_my_report(report_id: int, db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)):

    result = await db.execute(
        select(Report).where(
            Report.id == report_id,
            Report.reporter_id == current_user.id
        )
    )

    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=404,
            detail="Report not found."
        )

    return report


