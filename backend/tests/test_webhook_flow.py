import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeProvider, FakeSession

from models import Job
from schemas import FundingStatus, JobStatus, PaymentStatus, PayoutStatus
import routers.webhooks as webhooks
from routers.webhooks import WebhookProcessingError, _sync_checkout, _sync_payout


def make_intent(**overrides):
    values = dict(
        id=7,
        job_id=5,
        reference="job-1-abc",
        provider_checkout_id="co_1",
        provider_reference=None,
        deposit_address=None,
        amount_kobo=1_000_000,
        amount_payable_kobo=1_000_000,
        usdc_amount=None,
        status=PaymentStatus.PENDING,
        paid_at=None,
        failure_reason=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_job(**overrides):
    values = dict(
        id=5,
        owner_id=1,
        title="Fix the sink",
        description="Leaking tap",
        status=JobStatus.PENDING_FUNDING,
        funding_status=FundingStatus.PENDING,
        payer_type=None,
        onchain_task_id=None,
        onchain_tx_hash=None,
        onchain_status=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_payout(**overrides):
    values = dict(
        id=3,
        payment_intent_id=7,
        reference="payout-job-5-7",
        provider_payout_id="po_1",
        status=PayoutStatus.PROCESSING,
        completed_at=None,
        failure_reason=None,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


class CheckoutSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_checkout_funds_the_intent(self):
        intent = make_intent()
        job = make_job()
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "10000.00",
            }
        )
        db = FakeSession([intent], get_results={(Job, 5): job})
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ), mock.patch.object(
            webhooks, "estimate_usdc_units", return_value=6_250_000
        ), mock.patch.object(
            webhooks, "fund_task_escrow", return_value=None
        ) as fund:
            await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(intent.usdc_amount, 6_250_000)
        self.assertTrue(fund.called)

    async def test_amount_mismatch_fails_the_intent(self):
        intent = make_intent()
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "999.00",
            }
        )
        db = FakeSession([intent])
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.FAILED)

    async def test_unknown_checkout_is_reported(self):
        provider = FakeProvider()
        db = FakeSession([None, None])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_checkout(data, db)

    async def test_checkout_id_mismatch_is_reported(self):
        intent = make_intent()
        provider = FakeProvider()
        db = FakeSession([intent])
        data = {"checkoutId": "co_other", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_checkout(data, db)

    async def test_expired_checkout_marks_the_intent(self):
        intent = make_intent()
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "expired",
                "reference": "job-1-abc",
            }
        )
        db = FakeSession([intent])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.EXPIRED)

    async def test_provider_failure_is_reported(self):
        intent = make_intent()
        provider = FakeProvider(error="provider is down")
        db = FakeSession([intent])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_checkout(data, db)


class PayoutSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_payout_is_recorded(self):
        payout = make_payout()
        provider = FakeProvider(
            payout={
                "id": "po_1",
                "reference": "payout-job-5-7",
                "status": "completed",
            }
        )
        db = FakeSession([payout])

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_payout(
                {"payoutId": "po_1"}, payout_reference="payout-job-5-7", db=db
            )

        self.assertEqual(payout.status, PayoutStatus.COMPLETED)
        self.assertIsNotNone(payout.completed_at)

    async def test_failed_payout_is_recorded(self):
        payout = make_payout()
        provider = FakeProvider(
            payout={
                "id": "po_1",
                "reference": "payout-job-5-7",
                "status": "failed",
            }
        )
        db = FakeSession([payout])

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_payout(
                {"payoutId": "po_1"}, payout_reference="payout-job-5-7", db=db
            )

        self.assertEqual(payout.status, PayoutStatus.FAILED)

    async def test_unknown_payout_is_reported(self):
        db = FakeSession([None, None])

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=FakeProvider()
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_payout(
                    {"payoutId": "po_1"}, payout_reference="payout-job-5-7", db=db
                )


if __name__ == "__main__":
    unittest.main()
