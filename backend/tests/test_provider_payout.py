"""Tests for the provider payout destination (case A: their own Solana address)."""

import unittest
from types import SimpleNamespace
from unittest import mock

from support import FakeSession

from fastapi import HTTPException

from models import User
from payment_validation import PaymentProfileValidationError, validate_solana_address
from routers.users import update_onchain_address

VALID = "7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Qp5cY"


class SolanaAddressValidationTests(unittest.TestCase):
    def test_a_valid_address_is_accepted(self):
        self.assertEqual(validate_solana_address(VALID), VALID)

    def test_whitespace_is_trimmed(self):
        self.assertEqual(validate_solana_address(f"  {VALID}  "), VALID)

    def test_a_non_address_is_rejected(self):
        with self.assertRaises(PaymentProfileValidationError):
            validate_solana_address("not-an-address")

    def test_the_system_program_is_rejected(self):
        with self.assertRaises(PaymentProfileValidationError):
            validate_solana_address("11111111111111111111111111111111")

    def test_a_short_address_is_rejected(self):
        # A zero-padded key that nobody controls.
        with self.assertRaises(PaymentProfileValidationError):
            validate_solana_address("7EcJ1eB6J3ggRrGkQWsT4ZP8dkqPZ4JmW4YRwR7Q")

    def test_an_empty_address_is_rejected(self):
        with self.assertRaises(PaymentProfileValidationError):
            validate_solana_address("   ")


class OnchainAddressEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_address_is_saved(self):
        user = SimpleNamespace(id=1, onchain_address=None)
        db = FakeSession()

        result = await update_onchain_address(
            SimpleNamespace(onchain_address=VALID), db=db, current_user=user
        )

        self.assertEqual(user.onchain_address, VALID)
        self.assertEqual(result.onchain_address, VALID)
        self.assertEqual(db.commits, 1)

    async def test_an_invalid_address_is_rejected(self):
        user = SimpleNamespace(id=1, onchain_address=None)
        db = FakeSession()

        with self.assertRaises(HTTPException) as ctx:
            await update_onchain_address(
                SimpleNamespace(onchain_address="nope"),
                db=db,
                current_user=user,
            )

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertIsNone(user.onchain_address)
        self.assertEqual(db.commits, 0)


if __name__ == "__main__":
    unittest.main()
