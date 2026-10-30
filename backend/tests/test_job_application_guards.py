from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import unittest

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import Index, UniqueConstraint
from sqlalchemy.exc import IntegrityError

from support import FakeSession
from models import JobApplication
from schemas import (
    ApplicationStatus,
    JobApplicantResponse,
    JobApplicationStatusUpdate,
    JobStatus,
    JobUpdate,
)
from routers.jobs import (
    create_job_application,
    delete,
    delete_job,
    update_application,
    update_application_status,
    update_job,
)


def make_job(**overrides):
    values = dict(id=5, owner_id=1, status=JobStatus.OPEN)
    values.update(overrides)
    return SimpleNamespace(**values)


def make_application(**overrides):
    values = dict(
        id=7,
        job_id=5,
        applicant_id=2,
        proposal_text="I can do this",
        proposed_price=100.0,
        status=ApplicationStatus.PENDING,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class JobApplicationGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_accepted_applicant_cannot_change_application(self):
        application = make_application(status=ApplicationStatus.ACCEPTED)
        db = FakeSession([application])

        with self.assertRaises(HTTPException) as ctx:
            await update_application(
                7,
                SimpleNamespace(model_dump=lambda **_: {"proposed_price": 1.0}),
                db=db,
                current_user=SimpleNamespace(id=2),
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.detail, "Only pending applications can be changed"
        )
        self.assertEqual(db.commits, 0)

    async def test_accepted_applicant_cannot_delete_application(self):
        application = make_application(status=ApplicationStatus.ACCEPTED)
        db = FakeSession([application])

        with self.assertRaises(HTTPException) as ctx:
            await delete(7, db=db, current_user=SimpleNamespace(id=2))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.detail, "Only pending applications can be changed"
        )
        self.assertEqual(db.commits, 0)

    async def test_owner_cannot_reject_accepted_application(self):
        application = make_application(status=ApplicationStatus.ACCEPTED)
        db = FakeSession([application, make_job(status=JobStatus.IN_PROGRESS)])

        with self.assertRaises(HTTPException) as ctx:
            await update_application_status(
                7,
                JobApplicationStatusUpdate(status=ApplicationStatus.REJECTED),
                db=db,
                current_user=SimpleNamespace(id=1),
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.detail, "Only pending applications can be rejected"
        )
        self.assertEqual(db.commits, 0)

    async def test_job_delete_cancels_open_job(self):
        job = make_job()
        db = FakeSession([job])

        await delete_job(5, db=db, current_user=SimpleNamespace(id=1))

        self.assertEqual(job.status, JobStatus.CANCELLED)
        self.assertEqual(db.commits, 1)

    async def test_job_delete_rejects_in_progress_job(self):
        db = FakeSession([make_job(status=JobStatus.IN_PROGRESS)])

        with self.assertRaises(HTTPException) as ctx:
            await delete_job(5, db=db, current_user=SimpleNamespace(id=1))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Only open jobs can be deleted")
        self.assertEqual(db.commits, 0)

    async def test_job_update_rejects_in_progress_job(self):
        db = FakeSession([make_job(status=JobStatus.IN_PROGRESS)])

        with self.assertRaises(HTTPException) as ctx:
            await update_job(
                5,
                JobUpdate(budget=200),
                db=db,
                current_user=SimpleNamespace(id=1),
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(
            ctx.exception.detail,
            "Only open or pending-funding jobs can be updated",
        )
        self.assertEqual(db.commits, 0)

    async def test_concurrent_duplicate_application_returns_conflict(self):
        class UniqueViolation(Exception):
            diag = SimpleNamespace(
                constraint_name="uq_job_applications_job_applicant"
            )

        class FailingCommitSession(FakeSession):
            async def commit(self):
                raise IntegrityError("INSERT", {}, UniqueViolation())

        job = make_job(expires_at=datetime.now(timezone.utc) + timedelta(days=1))
        db = FailingCommitSession([job, None])

        with self.assertRaises(HTTPException) as ctx:
            await create_job_application(
                5,
                SimpleNamespace(
                    model_dump=lambda: {
                        "proposal_text": "I can do this",
                        "proposed_price": 100.0,
                    }
                ),
                db=db,
                current_user=SimpleNamespace(id=2),
            )

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "you already applied")
        self.assertEqual(db.rollbacks, 1)

    def test_application_table_enforces_unique_job_applicant_pair(self):
        table = JobApplication.__table__
        unique_constraint = next(
            constraint
            for constraint in table.constraints
            if isinstance(constraint, UniqueConstraint)
            and constraint.name == "uq_job_applications_job_applicant"
        )

        self.assertEqual(
            [column.name for column in unique_constraint.columns],
            ["job_id", "applicant_id"],
        )
        self.assertTrue(
            any(
                isinstance(index, Index)
                and index.name == "ix_job_applications_job_id"
                for index in table.indexes
            )
        )

    def test_job_update_rejects_explicit_null_urgency(self):
        with self.assertRaises(ValidationError):
            JobUpdate.model_validate({"urgency": None})

    def test_applicant_response_includes_chat_user_fields(self):
        response = JobApplicantResponse.model_validate(
            SimpleNamespace(
                id=7,
                job_id=5,
                applicant_id=2,
                proposal_text="I can do this",
                proposed_price=100.0,
                status=ApplicationStatus.PENDING,
                onchain_application_id=None,
                near_application_id=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                applicant=SimpleNamespace(
                    id=2,
                    username="provider",
                    first_name="Provider",
                    last_name="Person",
                    profile_image=None,
                ),
            )
        )

        self.assertEqual(response.applicant.username, "provider")


if __name__ == "__main__":
    unittest.main()
