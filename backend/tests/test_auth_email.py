"""Signup must trigger the verification email, not just create a token."""

import unittest
from unittest import mock

from support import FakeSession

from schemas import UserCreate
import routers.auth as auth


def make_signup() -> UserCreate:
    return UserCreate(
        first_name="Ada",
        last_name="Okoro",
        email="ada@example.com",
        username="ada",
        phone_number="+2348000000000",
        hashed_password="secret123",
        confirm_password="secret123",
    )


class SignupEmailTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_user_sends_the_verification_email(self):
        db = FakeSession([None, None])

        with mock.patch.object(
            auth, "hash_password", new=mock.AsyncMock(return_value="hashed")
        ), mock.patch.object(
            auth, "generate_token", new=mock.AsyncMock(return_value="token-1")
        ), mock.patch.object(
            auth, "send_verification_email", new=mock.AsyncMock()
        ) as send:
            user = await auth.create_user(make_signup(), db=db)

        self.assertEqual(user.email, "ada@example.com")
        send.assert_awaited_once_with("ada@example.com", "token-1")

    async def test_create_user_survives_a_mail_outage(self):
        db = FakeSession([None, None])

        with mock.patch.object(
            auth, "hash_password", new=mock.AsyncMock(return_value="hashed")
        ), mock.patch.object(
            auth, "generate_token", new=mock.AsyncMock(return_value="token-1")
        ), mock.patch.object(
            auth,
            "send_verification_email",
            new=mock.AsyncMock(side_effect=Exception("smtp down")),
        ), mock.patch.object(auth, "logger"):
            user = await auth.create_user(make_signup(), db=db)

        # The account and verification token are already committed; the user
        # can retry with /auth/resend-verification.
        self.assertEqual(user.email, "ada@example.com")


if __name__ == "__main__":
    unittest.main()
