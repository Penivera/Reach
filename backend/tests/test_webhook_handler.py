import hashlib
import hmac
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeProvider, FakeRequest, FakeSession

from fastapi import HTTPException

from models import Job
from schemas import FundingStatus, JobStatus, PaymentStatus, WebhookStatus
import routers.webhooks as webhooks
from routers.webhooks import fossapay_webhook, obiex_webhook

SECRET = "test-webhook-secret"
OBIEX_SECRET = "test-obiex-secret"


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


def sign_body(raw):
    return hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


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


class FossaPayWebhookTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_checkout_locks_the_escrow(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, data_bytes = make_body(data)
        request = FakeRequest(raw, {"x-fossapay-signature": sign(data_bytes)})

        intent = make_intent()
        job = make_job()
        db = FakeSession([None, intent], get_results={(Job, 5): job})

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
        ), mock.patch.object(
            webhooks, "estimate_usdc_units", return_value=6_250_000
        ), mock.patch.object(
            webhooks, "fund_task_escrow", return_value=None
        ) as fund:
            await fossapay_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(intent.usdc_amount, 6_250_000)
        self.assertEqual(job.funding_status, FundingStatus.PAID)
        self.assertTrue(fund.called)
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
        db = FakeSession([already_processed])
        provider = FakeProvider()

        with mock.patch.object(
            webhooks, "get_fossapay_client", return_value=provider
        ):
            await fossapay_webhook(request, db)

        self.assertEqual(provider.checkout_calls, [])
        self.assertEqual(len(db.added), 0)

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

    async def test_v2_signature_over_the_body_is_accepted(self):
        data = {
            "checkoutId": "co_1",
            "reference": "job-1-abc",
            "amountPayable": "10000.00",
        }
        raw, _ = make_body(data)
        request = FakeRequest(raw, {"x-fossapay-signature-v2": sign_body(raw)})

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
        db = FakeSession([already_processed])

        await fossapay_webhook(request, db)

        self.assertEqual(len(db.added), 0)


class ObiexWebhookTests(unittest.IsolatedAsyncioTestCase):
    def _body(self, payload):
        return json.dumps(payload, separators=(",", ":")).encode()

    def _signature(self, raw):
        return hmac.new(OBIEX_SECRET.encode(), raw, hashlib.sha512).hexdigest()

    async def test_completed_collection_locks_the_escrow(self):
        payload = {
            "type": "COLLECTION",
            "reference": "col_1",
            "customerId": "cus_1",
            "status": "COMPLETED",
            "sourceCurrency": "NGNX",
            "sourceAmount": 10000,
            "targetCurrency": "USDC",
            "targetAmount": 3.12,
        }
        raw = self._body(payload)
        request = FakeRequest(raw, {"x-obiex-signature": self._signature(raw)})

        intent = make_intent(provider_reference="col_1", reference="fund-1")
        job = make_job()
        db = FakeSession([None, intent], get_results={(Job, 5): job})

        with mock.patch.object(
            webhooks, "fund_task_escrow", return_value=None
        ) as fund:
            await obiex_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(intent.usdc_amount, 3_120_000)
        self.assertTrue(fund.called)

    async def test_held_collection_is_not_funded(self):
        payload = {
            "type": "COLLECTION",
            "reference": "col_2",
            "status": "HELD",
            "targetCurrency": "USDC",
            "targetAmount": None,
        }
        raw = self._body(payload)
        request = FakeRequest(raw, {"x-obiex-signature": self._signature(raw)})

        intent = make_intent(provider_reference="col_2")
        job = make_job()
        db = FakeSession([None, intent], get_results={(Job, 5): job})

        with mock.patch.object(webhooks, "fund_task_escrow") as fund:
            await obiex_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.HELD)
        self.assertEqual(job.funding_status, FundingStatus.HELD)
        self.assertFalse(fund.called)

    async def test_confirmed_deposit_locks_the_escrow(self):
        payload = {
            "type": "DEPOSIT",
            "status": "CONFIRMED",
            "currency": "USDC",
            "amount": 25.0,
            "address": "7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
            "transactionId": "tx_1",
        }
        raw = self._body(payload)
        request = FakeRequest(raw, {"x-obiex-signature": self._signature(raw)})

        intent = make_intent(
            deposit_address="7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY"
        )
        job = make_job()
        db = FakeSession([None, None, intent], get_results={(Job, 5): job})

        with mock.patch.object(
            webhooks, "fund_task_escrow", return_value=None
        ) as fund:
            await obiex_webhook(request, db)

        self.assertEqual(intent.usdc_amount, 25_000_000)
        self.assertTrue(fund.called)

    async def test_invalid_signature_is_rejected(self):
        raw = self._body({"type": "COLLECTION", "reference": "col_1"})
        request = FakeRequest(raw, {"x-obiex-signature": "deadbeef"})
        db = FakeSession()

        with self.assertRaises(HTTPException) as ctx:
            await obiex_webhook(request, db)

        self.assertEqual(ctx.exception.status_code, 401)


class OffRampWebhookDispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_deposit_to_an_offramp_address_goes_to_offramp(self):
        withdrawal = SimpleNamespace(deposit_address="offramp-address")
        db = FakeSession([withdrawal])

        with mock.patch.object(
            webhooks.offramp,
            "handle_deposit",
            new=mock.AsyncMock(return_value=withdrawal),
        ) as handle:
            await webhooks._sync_deposit(
                {
                    "status": "CONFIRMED",
                    "address": "offramp-address",
                    "currency": "USDC",
                    "amount": 10,
                },
                db,
            )

        handle.assert_awaited_once()

    async def test_a_withdrawal_reference_goes_to_offramp_when_not_treasury(self):
        withdrawal = SimpleNamespace(provider_reference="withdrawal-1")
        # The treasury lookup returns None, then the off-ramp lookup returns
        # the row.
        db = FakeSession([None, withdrawal])

        with mock.patch.object(
            webhooks.offramp,
            "handle_withdrawal",
            new=mock.AsyncMock(return_value=withdrawal),
        ) as handle:
            await webhooks._sync_withdrawal(
                {"status": "SUCCESSFUL", "reference": "withdrawal-1"},
                db,
            )

        handle.assert_awaited_once()

    async def test_a_refund_reference_goes_to_the_refund_handler(self):
        withdrawal = SimpleNamespace(refund_reference="refund-1")
        # Treasury miss, bank-payout miss, refund hit.
        db = FakeSession([None, None, withdrawal])

        with mock.patch.object(
            webhooks.offramp,
            "handle_refund",
            new=mock.AsyncMock(return_value=withdrawal),
        ) as handle:
            await webhooks._sync_withdrawal(
                {"status": "SUCCESSFUL", "reference": "refund-1"},
                db,
            )

        handle.assert_awaited_once()


class FundingGuardTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_second_payment_for_a_funded_task_is_reversed(self):
        from routers.webhooks import _fund_intent

        intent = make_intent(status=PaymentStatus.PENDING)
        job = make_job(funding_status=FundingStatus.FUNDED)
        db = FakeSession(get_results={(Job, 5): job})

        await _fund_intent(db, intent, usdc_units=1_000_000)

        self.assertEqual(intent.status, PaymentStatus.REVERSED)
        self.assertIn("already funded", intent.failure_reason)
        self.assertEqual(job.funding_status, FundingStatus.FUNDED)

    async def test_a_replayed_paid_intent_is_not_refunded_or_refunded_twice(self):
        from routers.webhooks import _fund_intent

        intent = make_intent(status=PaymentStatus.PAID, usdc_amount=1_000_000)
        job = make_job(funding_status=FundingStatus.PAID)
        db = FakeSession(get_results={(Job, 5): job})

        await _fund_intent(db, intent, usdc_units=1_000_000)

        self.assertEqual(intent.status, PaymentStatus.PAID)
        self.assertEqual(job.funding_status, FundingStatus.PAID)


class ObiexAmountGuardTests(unittest.IsolatedAsyncioTestCase):
    def _body(self, payload):
        return json.dumps(payload, separators=(",", ":")).encode()

    def _signature(self, raw):
        return hmac.new(OBIEX_SECRET.encode(), raw, hashlib.sha512).hexdigest()

    async def test_a_mismatched_collection_is_held_not_funded(self):
        payload = {
            "type": "COLLECTION",
            "reference": "col_1",
            "status": "COMPLETED",
            "sourceCurrency": "NGNX",
            "sourceAmount": 5000,
            "targetCurrency": "USDC",
            "targetAmount": 3.12,
        }
        raw = self._body(payload)
        request = FakeRequest(raw, {"x-obiex-signature": self._signature(raw)})

        intent = make_intent(provider_reference="col_1", reference="fund-1")
        job = make_job()
        db = FakeSession([None, intent], get_results={(Job, 5): job})

        with mock.patch.object(webhooks, "fund_task_escrow") as fund:
            await obiex_webhook(request, db)

        self.assertEqual(intent.status, PaymentStatus.HELD)
        self.assertEqual(job.funding_status, FundingStatus.HELD)
        self.assertFalse(fund.called)


if __name__ == "__main__":
    unittest.main()
