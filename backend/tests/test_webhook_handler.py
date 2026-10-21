import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeProvider, FakeRequest, FakeSession

from fastapi import HTTPException

from schemas import JobStatus, PaymentStatus, WebhookStatus
import routers.webhooks as webhooks
from routers.webhooks import fossapay_webhook

SECRET = "test-webhook-secret"


def make_body(data, event_type="checkout.completed", event_id="evt_1"):
    data_bytes = json.dumps(data, separators=(",", ":")).encode()
    raw = (
        b'{"eventId":"'
        + event_id.encode()
        + b'","eventType":"'
        + event_type.encode()
        + b'","data":'
        + data_bytes
        + b"}"
    )
    return raw, data_bytes


def sign(data_bytes):
    return hmac.new(SECRET.encode(), data_bytes, hashlib.sha256).hexdigest()


def make_intent():
    return SimpleNamespace(
        id=7,
        job_id=5,
        reference="job-1-abc",
        provider_checkout_id="co_1",
        amount_kobo=1_000_000,
        amount_payable_kobo=1_000_000,
        status=PaymentStatus.PENDING,
        paid_at=None,
    )


class WebhookHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_valid_event_funds_the_job(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, data_bytes = make_body(data)
        request = FakeRequest(raw, {"x-fossapay-signature": sign(data_bytes)})

        intent = make_intent()
        job = SimpleNamespace(id=5, status=JobStatus.AWAITING_PAYMENT)
        db = FakeSession([None, None, intent, job])

        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "10000.00",
            }
        )

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await fossapay_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(db.added[0].status, WebhookStatus.PROCESSED)
        self.assertTrue(db.added[0].signature_valid)

    async def test_replay_with_new_event_id_is_ignored(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, data_bytes = make_body(data, event_id="evt_replay")
        request = FakeRequest(raw, {"x-fossapay-signature": sign(data_bytes)})

        already_processed = SimpleNamespace(
            event_id="evt_1",
            event_type="checkout.completed",
            reference="job-1-abc",
            provider_object_id="co_1",
            signature_valid=True,
            status=WebhookStatus.PROCESSED,
            last_error=None,
            processed_at=None,
        )
        db = FakeSession([None, already_processed])
        provider = FakeProvider()

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await fossapay_webhook(request, db)

        self.assertEqual(provider.checkout_calls, [])
        self.assertEqual(len(db.added), 0)

    async def test_changed_event_type_still_syncs_the_checkout(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, data_bytes = make_body(data, event_type="payout.completed")
        request = FakeRequest(raw, {"x-fossapay-signature": sign(data_bytes)})

        intent = make_intent()
        job = SimpleNamespace(id=5, status=JobStatus.AWAITING_PAYMENT)
        # event lookup x2, then intent + job for the checkout sync
        db = FakeSession([None, None, intent, job])

        provider = FakeProvider(
            checkout={
                "id": "co_1",
                "status": "completed",
                "reference": "job-1-abc",
                "amountPayable": "10000.00",
            }
        )

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await fossapay_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(provider.payout_calls, [])

    async def test_invalid_signature_is_rejected_and_recorded(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, _ = make_body(data)
        request = FakeRequest(raw, {"x-fossapay-signature": "deadbeef"})
        db = FakeSession()

        with self.assertRaises(HTTPException) as ctx:
            await fossapay_webhook(request, db)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(db.added[0].status, WebhookStatus.REJECTED)
        self.assertFalse(db.added[0].signature_valid)

    async def test_missing_signature_is_rejected(self):
        data = {"checkoutId": "co_1", "reference": "job-1-abc"}
        raw, _ = make_body(data)
        request = FakeRequest(raw, {})
        db = FakeSession()

        with self.assertRaises(HTTPException) as ctx:
            await fossapay_webhook(request, db)

        self.assertEqual(ctx.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
