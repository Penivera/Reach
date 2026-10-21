import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeProvider, FakeSession

from fastapi import HTTPException

from schemas import ApplicationStatus, PaymentStatus, PayoutStatus, ProvisioningStatus
import routers.payments as payments_router
from routers.payments import release_job_payment


class ReleaseFlowTests(unittest.IsolatedAsyncioTestCase):
    def _job(self, **overrides):
        values = dict(
            id=5,
            owner_id=1,
            client_completed=True,
            worker_completed=True,
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
        )

    async def test_release_pays_the_provider_net_of_commission(self):
        job = self._job()
        intent = self._intent()
        application = SimpleNamespace(
            id=2, job_id=5, applicant_id=2, status=ApplicationStatus.ACCEPTED
        )
        provider = SimpleNamespace(
            id=2, first_name="Ada", last_name="Okoro", username="ada"
        )

        # job, intent, existing payout (none), application, provider account
        db = FakeSession(
            [job, intent, None, application, self._provider_account()],
            get_results={2: provider},
        )
        current_user = SimpleNamespace(id=1)
        fake_provider = FakeProvider()

        with mock.patch.object(
            payments_router, "get_fossapay_client", return_value=fake_provider
        ):
            payout = await release_job_payment(
                job_id=5, db=db, current_user=current_user
            )

        self.assertEqual(payout.amount_kobo, 1_000_000)
        self.assertEqual(payout.commission_kobo, 50_000)
        self.assertEqual(payout.provider_payout_kobo, 950_000)
        self.assertEqual(payout.status, PayoutStatus.COMPLETED)
        self.assertEqual(payout.provider_payout_id, "po_test_1")
        self.assertEqual(fake_provider.payout_calls, ["payout-job-5-7"])

    async def test_release_requires_both_parties_to_complete(self):
        job = self._job(client_completed=False)
        db = FakeSession([job])
        current_user = SimpleNamespace(id=1)

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(
                job_id=5, db=db, current_user=current_user
            )

        self.assertEqual(ctx.exception.status_code, 400)

    async def test_release_is_idempotent(self):
        job = self._job()
        intent = self._intent()
        existing = SimpleNamespace(
            id=3,
            payment_intent_id=7,
            reference="payout-job-5-7",
            amount_kobo=1_000_000,
            commission_kobo=50_000,
            provider_payout_kobo=950_000,
            status=PayoutStatus.COMPLETED,
            provider_payout_id="po_test_1",
            failure_reason=None,
            completed_at=None,
        )
        # job, intent, existing payout
        db = FakeSession([job, intent, existing])
        current_user = SimpleNamespace(id=1)
        fake_provider = FakeProvider()

        with mock.patch.object(
            payments_router, "get_fossapay_client", return_value=fake_provider
        ):
            payout = await release_job_payment(
                job_id=5, db=db, current_user=current_user
            )

        self.assertIs(payout, existing)
        self.assertEqual(fake_provider.payout_calls, [])
        self.assertEqual(len(db.added), 0)

    async def test_only_the_job_owner_can_release(self):
        job = self._job(owner_id=99)
        db = FakeSession([job])
        current_user = SimpleNamespace(id=1)

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(
                job_id=5, db=db, current_user=current_user
            )

        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
