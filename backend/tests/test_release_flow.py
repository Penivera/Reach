import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeSession

from fastapi import HTTPException

from models import User
from schemas import (
    ApplicationStatus,
    FundingStatus,
    JobStatus,
    PaymentStatus,
    ProvisioningStatus,
)
import routers.payments as payments_router
from routers.payments import release_job_payment


class ReleaseFlowTests(unittest.IsolatedAsyncioTestCase):
    def _job(self, **overrides):
        values = dict(
            id=5,
            owner_id=1,
            client_completed=True,
            worker_completed=True,
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
            onchain_tx_hash="sig-1",
            onchain_status="AwaitingApproval",
            payer_type=None,
        )
        values.update(overrides)
        return SimpleNamespace(**values)

    def _intent(self):
        return SimpleNamespace(
            id=7,
            job_id=5,
            amount_kobo=1_000_000,
            amount_payable_kobo=1_000_000,
            status=PaymentStatus.PAID,
        )

    def _provider_account(self):
        return SimpleNamespace(
            status=ProvisioningStatus.PROVISIONED,
            account_number="9900000001",
            account_name="ADA OKORO",
            bank_name="Fake Bank",
            bank_code="000",
            crypto_wallet_address="7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
            crypto_wallet_id="cw_1",
            crypto_network="solana",
        )

    async def test_release_signs_approve_work_on_chain(self):
        job = self._job()
        application = SimpleNamespace(
            id=2, job_id=5, applicant_id=2, status=ApplicationStatus.ACCEPTED
        )
        provider = SimpleNamespace(
            id=2,
            first_name="Ada",
            last_name="Okoro",
            onchain_address="7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
        )

        db = FakeSession(
            [job, application],
            get_results={(User, 2): provider},
        )

        transaction = SimpleNamespace(
            id=9,
            job_id=5,
            kind="approve_work",
            idempotency_key="approve-work-5",
            signature="sig-approve",
            status="confirmed",
            slot=123,
            error=None,
            processed_at=None,
        )

        with mock.patch.object(
            payments_router, "release_task_escrow", return_value=transaction
        ) as release:
            result = await release_job_payment(
                5, db=db, current_user=SimpleNamespace(id=1)
            )

        self.assertTrue(release.called)
        self.assertEqual(
            release.await_args.kwargs["provider_address"],
            "7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
        )
        self.assertEqual(result.signature, "sig-approve")

    async def test_release_requires_a_funded_escrow(self):
        job = self._job(funding_status=FundingStatus.PENDING)
        db = FakeSession([job])

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(5, db=db, current_user=SimpleNamespace(id=1))

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_release_requires_the_job_owner(self):
        job = self._job()
        db = FakeSession([job])

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(5, db=db, current_user=SimpleNamespace(id=99))

        self.assertEqual(ctx.exception.status_code, 403)

    async def test_release_requires_the_provider_to_have_an_address(self):
        job = self._job()
        application = SimpleNamespace(
            id=2, job_id=5, applicant_id=2, status=ApplicationStatus.ACCEPTED
        )
        provider = SimpleNamespace(
            id=2, first_name="Ada", last_name="Okoro", onchain_address=None
        )

        db = FakeSession(
            [job, application],
            get_results={(User, 2): provider},
        )

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(
                5, db=db, current_user=SimpleNamespace(id=1)
            )

        self.assertEqual(ctx.exception.status_code, 400)


if __name__ == "__main__":
    unittest.main()
