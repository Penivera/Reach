"""Prevent duplicate applications for the same job.

Revision ID: 2a7c9e4d1f6b
Revises: b7c1f2a9d4e6, 4c56c8d467f2
Create Date: 2026-10-29 12:03:21.021000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "2a7c9e4d1f6b"
down_revision: Union[str, Sequence[str], None] = (
    "b7c1f2a9d4e6",
    "4c56c8d467f2",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_job_applications_job_id",
        "job_applications",
        ["job_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_job_applications_job_applicant",
        "job_applications",
        ["job_id", "applicant_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_job_applications_job_applicant",
        "job_applications",
        type_="unique",
    )
    op.drop_index(
        "ix_job_applications_job_id",
        table_name="job_applications",
    )
