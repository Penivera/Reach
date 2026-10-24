"""Tests for the relayer's identity and associated-token-account handling.

These are the two pieces that were broken in a way that would only show up
against a real RPC: `address` called the pubkey twice, and the ATA instruction
was built with the wrong account order (and created the account twice).
"""

import unittest
from unittest import mock

from solders.keypair import Keypair
from solders.pubkey import Pubkey

from core.relayer import Relayer, RelayerConfig
from core.solana import ASSOCIATED_TOKEN_PROGRAM_ID

USDC = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
PROGRAM_ID = "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY"


class FakeRpc:
    def __init__(self):
        self.account_info = None

    async def get_account_info(self, address):
        return self.account_info


def build_relayer() -> Relayer:
    keypair = Keypair()
    config = RelayerConfig(
        rpc_url="http://localhost:8899",
        program_id=PROGRAM_ID,
        stable_mint=str(USDC),
        secret_key=None,
        min_escrow_units=1,
    )
    relayer = Relayer(config, rpc=FakeRpc())
    relayer._keypair = keypair
    return relayer


class RelayerIdentityTests(unittest.TestCase):
    def test_address_returns_the_keypair_pubkey(self):
        relayer = build_relayer()

        # Regression: this used to be `self.keypair.pubkey()()`, which raised
        # "'Pubkey' object is not callable".
        self.assertEqual(relayer.address, relayer.keypair.pubkey())

    def test_the_relayer_is_not_enabled_without_a_secret(self):
        relayer = build_relayer()

        self.assertFalse(relayer.enabled)


class EnsureTokenAccountTests(unittest.IsolatedAsyncioTestCase):
    async def test_creates_the_ata_with_one_idempotent_instruction(self):
        relayer = build_relayer()
        owner = Pubkey.new_unique()
        expected_ata = relayer.program.associated_token_address(owner, USDC)

        with mock.patch.object(
            relayer, "submit", new=mock.AsyncMock()
        ) as submit:
            ata = await relayer.ensure_token_account(owner)

        self.assertEqual(ata, expected_ata)
        submit.assert_awaited_once()

        instructions = submit.call_args.args[0]
        self.assertEqual(len(instructions), 1)

        instruction = instructions[0]
        self.assertEqual(instruction.program_id, ASSOCIATED_TOKEN_PROGRAM_ID)

        accounts = list(instruction.accounts)
        # [payer, ata, owner, mint, system, token]
        self.assertEqual(accounts[0].pubkey, relayer.address)
        self.assertTrue(accounts[0].is_signer)
        self.assertTrue(accounts[0].is_writable)
        self.assertEqual(accounts[1].pubkey, expected_ata)
        self.assertTrue(accounts[1].is_writable)
        self.assertEqual(accounts[2].pubkey, owner)
        self.assertFalse(accounts[2].is_writable)
        self.assertEqual(accounts[3].pubkey, USDC)

    async def test_an_existing_ata_is_not_recreated(self):
        relayer = build_relayer()
        relayer.rpc.account_info = object()
        owner = Pubkey.new_unique()

        with mock.patch.object(
            relayer, "submit", new=mock.AsyncMock()
        ) as submit:
            await relayer.ensure_token_account(owner)

        submit.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
