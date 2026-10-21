import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeProvider, FakeSession

from schemas import JobStatus, PaymentStatus, PayoutStatus
import routers.webhooks as webhooks
from routers.webhooks import WebhookProcessingError, _sync_checkout, _sync_payout


def make_intent(**overrides):
    values = dict(
        id=7,
        job_id=5,
        reference="job-1-abc",
        provider_checkout_id="co_1",
        amount_kobo=1_000_000,
        amount_payable_kobo=1_000_000,
        status=PaymentStatus.PENDING,
        paid_at=None,
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
        job = SimpleNamespace(id=5, status=JobStatus.AWAITING_PAYMENT)
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "10000.00",
            }
        )
        db = FakeSession([intent, job])
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(provider.checkout_calls, ["co_1"])

    async def test_amount_mismatch_marks_the_intent_failed(self):
        intent = make_intent()
        job = SimpleNamespace(id=5, status=JobStatus.AWAITING_PAYMENT)
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "9999.00",
            }
        )
        db = FakeSession([intent, job])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.FAILED)
        self.assertEqual(job.status, JobStatus.AWAITING_PAYMENT)

    async def test_replayed_completed_checkout_does_nothing(self):
        intent = make_intent(status=PaymentStatus.PAID)
        provider = FakeProvider()
        db = FakeSession([intent])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_checkout(data, db)

        self.assertEqual(provider.checkout_calls, [])
        self.assertEqual(db.commits, 0)

    async def test_unknown_checkout_reference_raises(self):
        # lookup by reference, then by checkout id
        db = FakeSession([None, None])
        data = {"checkoutId": "co_1", "reference": "job-unknown"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=FakeProvider()
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_checkout(data, db)

    async def test_provider_failure_is_not_completed(self):
        intent = make_intent()
        job = SimpleNamespace(id=5, status=JobStatus.AWAITING_PAYMENT)
        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "processing",
                "reference": "job-1-abc",
            }
        )
        db = FakeSession([intent, job])
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_checkout(data, db)

        self.assertEqual(intent.status, PaymentStatus.PENDING)


class PayoutSyncTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_payout_is_marked_completed(self):
        payout = make_payout()
        provider = FakeProvider(
            payout={
                "id": "po_1",
                "reference": "payout-job-5-7",
                "status": "completed",
            }
        )
        db = FakeSession([payout])
        data = {"payoutId": "po_1", "reference": "payout-job-5-7"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_payout(data, payout_reference="payout-job-5-7", db=db)

        self.assertEqual(payout.status, PayoutStatus.COMPLETED)
        self.assertIsNotNone(payout.completed_at)

    async def test_failed_payout_is_marked_failed(self):
        payout = make_payout()
        provider = FakeProvider(
            payout={
                "id": "po_1",
                "reference": "payout-job-5-7",
                "status": "failed",
            }
        )
        db = FakeSession([payout])
        data = {"payoutId": "po_1", "reference": "payout-job-5-7"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await _sync_payout(data, payout_reference="payout-job-5-7", db=db)

        self.assertEqual(payout.status, PayoutStatus.FAILED)

    async def test_reference_mismatch_raises(self):
        payout = make_payout()
        provider = FakeProvider(
            payout={
                "id": "po_1",
                "reference": "payout-other",
                "status": "completed",
            }
        )
        db = FakeSession([payout])
        data = {"payoutId": "po_1", "reference": "payout-job-5-7"}

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            with self.assertRaises(WebhookProcessingError):
                await _sync_payout(
                    data, payout_reference="payout-job-5-7", db=db
                )


if __name__ == "__main__":
    unittest.main()
