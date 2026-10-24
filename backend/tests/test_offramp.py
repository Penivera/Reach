"""Tests for the provider USDC-to-NGN off-ramp."""

import unittest
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from support import FakeObiex, FakeSession

from core import settings
from core.obiex import ObiexError
from models import OffRampWithdrawal, User
from schemas import OffRampStatus
from services import offramp

# The test runner may import core.settings before the support module sets the
# environment, so pin the off-ramp flags for these tests explicitly.
settings.REACH_OFFRAMP_ENABLED = True
settings.REACH_OFFRAMP_MIN_USDC_UNITS = 1_000_000
settings.REACH_OFFRAMP_MAX_USDC_UNITS = 1_000_000_000
settings.REACH_OFFRAMP_MIN_NGN_KOBO = 100_000


def make_user(**overrides):
    values = dict(
        id=1,
        first_name="Ada",
        last_name="Okafor",
        onchain_address="7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_withdrawal(**overrides):
    values = dict(
        id=1,
        user_id=1,
        reference="offramp-test",
        idempotency_key=None,
        status=OffRampStatus.AWAITING_DEPOSIT,
        amount_usdc_units=10_000_000,
        received_usdc_units=0,
        quoted_rate=Decimal("1580"),
        gross_ngn_kobo=1_580_000,
        fee_kobo=5_000,
        net_ngn_kobo=1_575_000,
        bank_name="Fake Bank",
        bank_code="058",
        bank_account_number="9012345678",
        bank_account_name="Ada Okafor",
        deposit_address="7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY",
        deposit_address_reference="addr_1",
        deposit_currency="USDC",
        deposit_network="SOL",
        deposit_provider_reference=None,
        deposit_tx_hash=None,
        swap_reference=None,
        swap_rate=None,
        swapped_at=None,
        provider_withdrawal_id=None,
        provider_reference=None,
        failure_reason=None,
        refund_reference=None,
        refund_transaction_id=None,
        expires_at=None,
        deposit_confirmed_at=None,
        paid_at=None,
        refunded_at=None,
    )
    values.update(overrides)
    return OffRampWithdrawal(**values)


class QuoteTests(unittest.IsolatedAsyncioTestCase):
    async def test_quote_uses_the_sell_rate_and_never_rounds_up(self):
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            quote = await offramp.quote_offramp(Decimal("10"))

        self.assertEqual(quote["amount_usdc_units"], 10_000_000)
        self.assertEqual(quote["rate_ngn_per_usdc"], Decimal("1580"))
        self.assertEqual(quote["gross_ngn_kobo"], 1_580_000)
        self.assertEqual(quote["fee_kobo"], 5_000)
        self.assertEqual(quote["net_ngn_kobo"], 1_575_000)

    async def test_the_feature_flag_blocks_quotes_when_disabled(self):
        with mock.patch.object(settings, "REACH_OFFRAMP_ENABLED", False):
            with self.assertRaises(offramp.OffRampDisabled):
                await offramp.quote_offramp(Decimal("10"))

    async def test_sub_cent_usdc_is_rejected_instead_of_rounded(self):
        with self.assertRaises(offramp.OffRampAmountError):
            offramp.to_usdc_units_exact("1.0000001")

    async def test_sub_kobo_payout_is_rejected(self):
        with self.assertRaises(offramp.OffRampAmountError):
            offramp._kobo_exact("10.001")

    async def test_a_quote_below_the_minimum_after_fees_is_rejected(self):
        with mock.patch.object(
            settings, "REACH_OFFRAMP_MIN_NGN_KOBO", 1_575_001
        ):
            with self.assertRaises(offramp.OffRampAmountError):
                await offramp.quote_offramp(Decimal("10"))

    def test_a_zero_padded_bank_code_matches_a_numeric_sort_code(self):
        bank = {"name": "Fake Bank", "sortCode": 58}

        self.assertIs(offramp._bank_for([bank], "058"), bank)


class NameMatchTests(unittest.TestCase):
    def test_case_and_middle_names_do_not_block_a_match(self):
        user = make_user()

        self.assertTrue(offramp.names_match(user, "ADA CHIOMA OKAFOR"))

    def test_a_different_person_is_rejected(self):
        user = make_user()

        self.assertFalse(offramp.names_match(user, "John Doe"))


class CreateTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_returns_a_deposit_address_and_snapshots_the_bank(self):
        user = make_user()
        profile = SimpleNamespace(
            bank_code="058",
            bank_account_number="9012345678",
            bank_account_name="Ada Okafor",
        )
        db = FakeSession([None, None, profile])
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            withdrawal = await offramp.create_withdrawal(
                db,
                user=user,
                amount_usdc=Decimal("10"),
                idempotency_key="idem-1",
            )

        self.assertEqual(withdrawal.status, OffRampStatus.AWAITING_DEPOSIT)
        self.assertEqual(withdrawal.deposit_address, client_address())
        self.assertEqual(withdrawal.bank_account_name, "Ada Okafor")
        self.assertEqual(withdrawal.bank_name, "Fake Bank")
        self.assertEqual(withdrawal.bank_code, "058")
        self.assertEqual(len(db.added), 1)
        self.assertEqual(db.commits, 1)

    async def test_create_rejects_an_account_in_another_name(self):
        user = make_user(first_name="Ada", last_name="Okafor")
        profile = SimpleNamespace(
            bank_code="058",
            bank_account_number="9012345678",
            bank_account_name="Someone Else",
        )
        db = FakeSession([None, profile])
        client = FakeObiex()
        client.resolve_naira_account = mock.AsyncMock(
            return_value={
                "accountNumber": "9012345678",
                "accountName": "John Doe",
            }
        )

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            with self.assertRaises(offramp.OffRampError):
                await offramp.create_withdrawal(
                    db,
                    user=user,
                    amount_usdc=Decimal("10"),
                )

        self.assertEqual(len(db.added), 0)


def client_address():
    return "7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY"


class DepositTests(unittest.IsolatedAsyncioTestCase):
    def payload(self, amount):
        return {
            "type": "DEPOSIT",
            "status": "CONFIRMED",
            "currency": "USDC",
            "amount": amount,
            "address": client_address(),
            "transactionId": f"tx-{amount}",
            "hash": "hash-1",
        }

    async def test_a_partial_deposit_waits_for_the_remainder(self):
        withdrawal = make_withdrawal()

        await offramp.handle_deposit(
            FakeSession(), withdrawal, self.payload(5)
        )

        self.assertEqual(withdrawal.status, OffRampStatus.PARTIALLY_FUNDED)
        self.assertEqual(withdrawal.received_usdc_units, 5_000_000)
        self.assertIn("below the requested amount", withdrawal.failure_reason)

    async def test_an_overpayment_is_held_instead_of_paid_out(self):
        withdrawal = make_withdrawal()

        await offramp.handle_deposit(
            FakeSession(), withdrawal, self.payload(12)
        )

        self.assertEqual(withdrawal.status, OffRampStatus.HELD)
        self.assertEqual(withdrawal.received_usdc_units, 12_000_000)

    async def test_a_full_deposit_swaps_and_starts_the_bank_payout(self):
        withdrawal = make_withdrawal()
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            await offramp.handle_deposit(
                FakeSession(), withdrawal, self.payload(10)
            )

        self.assertEqual(withdrawal.status, OffRampStatus.WITHDRAWING)
        self.assertEqual(withdrawal.gross_ngn_kobo, 1_580_000)
        self.assertEqual(withdrawal.fee_kobo, 5_000)
        self.assertEqual(withdrawal.net_ngn_kobo, 1_575_000)
        self.assertEqual(
            withdrawal.provider_reference, "fake_fiat_withdrawal_reference"
        )
        self.assertEqual(withdrawal.swap_reference, "fake_swap_ngnx")

    async def test_a_duplicate_deposit_webhook_is_ignored(self):
        withdrawal = make_withdrawal(
            received_usdc_units=10_000_000,
            deposit_provider_reference="tx-10",
            status=OffRampStatus.WITHDRAWING,
        )

        await offramp.handle_deposit(
            FakeSession(), withdrawal, self.payload(10)
        )

        self.assertEqual(withdrawal.status, OffRampStatus.WITHDRAWING)
        self.assertEqual(withdrawal.received_usdc_units, 10_000_000)

    async def test_a_new_deposit_after_the_payout_started_is_held(self):
        withdrawal = make_withdrawal(
            received_usdc_units=10_000_000,
            deposit_provider_reference="tx-old",
            status=OffRampStatus.WITHDRAWING,
        )

        await offramp.handle_deposit(
            FakeSession(), withdrawal, self.payload(5)
        )

        self.assertEqual(withdrawal.status, OffRampStatus.HELD)
        self.assertEqual(withdrawal.received_usdc_units, 15_000_000)
        self.assertIn("already in progress", withdrawal.failure_reason)

    async def test_a_late_deposit_after_payment_keeps_the_paid_status(self):
        withdrawal = make_withdrawal(
            received_usdc_units=10_000_000,
            deposit_provider_reference="tx-old",
            status=OffRampStatus.PAID,
            paid_at=datetime.now(timezone.utc),
        )

        await offramp.handle_deposit(
            FakeSession(), withdrawal, self.payload(5)
        )

        self.assertEqual(withdrawal.status, OffRampStatus.PAID)
        self.assertEqual(withdrawal.received_usdc_units, 15_000_000)
        self.assertIn("late USDC", withdrawal.failure_reason)


class PayoutTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_successful_withdrawal_is_paid(self):
        withdrawal = make_withdrawal(status=OffRampStatus.WITHDRAWING)

        await offramp.handle_withdrawal(
            FakeSession(), withdrawal, {"status": "SUCCESSFUL"}
        )

        self.assertEqual(withdrawal.status, OffRampStatus.PAID)
        self.assertIsNotNone(withdrawal.paid_at)

    async def test_a_failed_withdrawal_is_recorded_for_retry(self):
        withdrawal = make_withdrawal(status=OffRampStatus.WITHDRAWING)

        await offramp.handle_withdrawal(
            FakeSession(),
            withdrawal,
            {"status": "FAILED", "message": "Bank rejected the name"},
        )

        self.assertEqual(withdrawal.status, OffRampStatus.FAILED)
        self.assertEqual(withdrawal.failure_reason, "Bank rejected the name")


class PartialSwapTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_failed_fallback_leg_is_held_and_marked_as_swapped(self):
        class FallbackOnly(FakeObiex):
            async def get_trade_pairs(self):
                return [
                    {"source": {"code": "USDC"}, "target": {"code": "USDT"}},
                    {"source": {"code": "USDT"}, "target": {"code": "NGNX"}},
                ]

            async def instant_swap(self, *, source_id, target_id, amount):
                if target_id == "NGNX":
                    raise ObiexError("second leg failed")
                return {
                    "id": "first-leg",
                    "amountReceived": amount,
                    "status": "SUCCESSFUL",
                }

        withdrawal = make_withdrawal(
            status=OffRampStatus.DEPOSIT_CONFIRMED,
            received_usdc_units=10_000_000,
        )
        client = FallbackOnly()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            with self.assertRaises(offramp.OffRampPartialSwap):
                await offramp.settle_withdrawal(FakeSession(), withdrawal)

        self.assertEqual(withdrawal.status, OffRampStatus.HELD)
        self.assertIsNotNone(withdrawal.swapped_at)
        self.assertEqual(withdrawal.swap_reference, "first-leg")


class RetryTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_bank_payout_retry_does_not_swap_the_usdc_again(self):
        withdrawal = make_withdrawal(
            status=OffRampStatus.FAILED,
            received_usdc_units=10_000_000,
            swapped_at=datetime.now(timezone.utc),
            gross_ngn_kobo=1_580_000,
            swap_reference="fake_swap_ngnx",
            swap_rate=Decimal("1580"),
        )
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            await offramp.settle_withdrawal(FakeSession(), withdrawal)

        self.assertNotIn("instant_swap", client.calls)
        self.assertEqual(withdrawal.status, OffRampStatus.WITHDRAWING)
        self.assertEqual(withdrawal.gross_ngn_kobo, 1_580_000)

    async def test_a_retry_with_a_reference_polls_instead_of_paying_again(self):
        withdrawal = make_withdrawal(
            status=OffRampStatus.WITHDRAWING,
            received_usdc_units=10_000_000,
            provider_reference="withdrawal-1",
        )
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            await offramp.refresh_withdrawal(FakeSession(), withdrawal)

        self.assertNotIn("request_fiat_withdrawal", client.calls)
        self.assertEqual(withdrawal.status, OffRampStatus.PAID)


class RefundTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_held_deposit_is_refunded_to_the_provider_wallet(self):
        withdrawal = make_withdrawal(
            status=OffRampStatus.HELD,
            received_usdc_units=10_000_000,
        )
        user = make_user()
        db = FakeSession(get_results={(User, 1): user})
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            await offramp.refund_withdrawal(db, withdrawal)

        self.assertEqual(withdrawal.status, OffRampStatus.REFUNDING)
        self.assertEqual(withdrawal.refund_reference, "fake_withdrawal_reference")

        await offramp.handle_refund(
            db, withdrawal, {"status": "SUCCESSFUL"}
        )

        self.assertEqual(withdrawal.status, OffRampStatus.REFUNDED)
        self.assertIsNotNone(withdrawal.refunded_at)


class BankResolveTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolve_account_returns_the_bank_and_account_name(self):
        client = FakeObiex()

        with mock.patch.object(offramp, "get_obiex_client", return_value=client):
            resolved = await offramp.resolve_account(
                bank_code="058",
                account_number="9012345678",
            )

        self.assertEqual(resolved["account_name"], "Ada Okafor")
        self.assertEqual(resolved["account_number"], "9012345678")
        self.assertEqual(resolved["bank_name"], "Fake Bank")
        self.assertEqual(resolved["bank_code"], "058")

    async def test_list_banks_still_works_while_payouts_are_disabled(self):
        client = FakeObiex()

        with mock.patch.object(
            offramp, "get_obiex_client", return_value=client
        ), mock.patch.object(settings, "REACH_OFFRAMP_ENABLED", False):
            banks = await offramp.list_banks()

        self.assertEqual(banks[0]["name"], "Fake Bank")
