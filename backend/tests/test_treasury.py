"""Tests for the treasury: the on-chain float and the provider balance."""

import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeSession

from core import settings
from services import treasury
from services.treasury import TreasuryError, plan_top_up, to_units


class AmountTests(unittest.TestCase):
    def test_usdc_amounts_are_converted_to_base_units(self):
        self.assertEqual(to_units("10"), 10_000_000)
        self.assertEqual(to_units(2.5), 2_500_000)

    def test_invalid_amounts_are_rejected(self):
        with self.assertRaises(TreasuryError):
            to_units("not a number")


class PlanTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_covered_float_needs_no_withdrawal(self):
        plan = await plan_top_up(
            required_units=10_000_000,
            onchain=50_000_000,
            provider=100_000_000,
        )

        self.assertTrue(plan["ready"])
        self.assertEqual(plan["shortfall_units"], 0)

    async def test_a_short_float_sweeps_the_provider_down_to_the_target(self):
        plan = await plan_top_up(
            required_units=100_000_000,
            onchain=10_000_000,
            provider=600_000_000,
        )

        self.assertFalse(plan["ready"])
        self.assertEqual(plan["shortfall_units"], 90_000_000)
        # Sweep to the target rather than taking only the shortfall, so the
        # next jobs do not each need their own withdrawal.
        self.assertEqual(
            plan["withdraw_units"],
            600_000_000 - settings.REACH_TREASURY_TARGET_UNITS,
        )

    async def test_a_withdrawal_below_the_minimum_is_not_attempted(self):
        plan = await plan_top_up(
            required_units=100_000_000,
            onchain=0,
            provider=1_000_000,
        )

        self.assertFalse(plan["ready"])
        self.assertEqual(plan["withdraw_units"], 0)

    async def test_the_provider_balance_is_read_from_the_wallet_response(self):
        client = SimpleNamespace(
            get_wallet_balance=mock.AsyncMock(
                return_value={"wallet": {"availableBalance": 42.5}}
            )
        )

        with mock.patch.object(treasury, "get_obiex_client", return_value=client):
            balance = await treasury.provider_balance()

        self.assertEqual(balance, 42_500_000)


class WithdrawalTests(unittest.IsolatedAsyncioTestCase):
    async def test_a_withdrawal_below_the_minimum_is_rejected(self):
        with self.assertRaises(TreasuryError):
            await treasury.request_withdrawal(
                FakeSession(), amount_units=1_000_000
            )

    async def test_a_withdrawal_is_recorded(self):
        client = SimpleNamespace(
            request_crypto_withdrawal=_record_withdrawal,
        )

        db = FakeSession()

        with mock.patch.object(treasury, "get_obiex_client", return_value=client), \
            mock.patch.object(
                treasury, "relayer_address", new=mock.AsyncMock(return_value="relayer-address")
            ):
            transfer = await treasury.request_withdrawal(
                db, amount_units=50_000_000
            )

        self.assertEqual(transfer.amount_units, 50_000_000)
        self.assertEqual(transfer.reference, "withdrawal_1")
        self.assertEqual(transfer.destination, "relayer-address")
        self.assertEqual(len(db.added), 1)


def _async_value(value):
    async def _inner():
        return value

    return _inner()


async def _record_withdrawal(**kwargs):
    return {
        "id": "withdrawal_1",
        "reference": "withdrawal_1",
        "payout": {"status": "APPROVED"},
    }


if __name__ == "__main__":
    unittest.main()
