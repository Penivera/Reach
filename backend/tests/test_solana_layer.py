"""Tests for the Solana layer.

These check the parts that are easy to get subtly wrong: the program's PDA
seeds, the token accounts, the instruction encoding, and the decoding of the
task account.
"""

import base64
import unittest

from solders.hash import Hash
from solders.instruction import Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from core.relayer import FinancialTerms, base58_decode, base58_encode
from core.solana import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    AnchorProgram,
    SolanaError,
    SolanaRpc,
    build_legacy_transaction,
    decode_task_account,
)

USDC = Pubkey.from_string("EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
PROGRAM_ID = Pubkey.from_string("5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY")
TASK_SEED = b"task"


class BorshReader:
    """A tiny independent decoder, so the encoder is checked against something."""

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, size: int) -> bytes:
        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def u8(self) -> int:
        return int.from_bytes(self.take(1), "little")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "little")

    def u128(self) -> int:
        return int.from_bytes(self.take(16), "little")

    def bool(self) -> bool:
        return self.u8() != 0

    def string(self) -> str:
        length = int.from_bytes(self.take(4), "little")
        return self.take(length).decode()

    def option_string(self):
        if self.u8() == 0:
            return None
        return self.string()


class AnchorProgramTests(unittest.TestCase):
    def setUp(self):
        self.program = AnchorProgram.from_idl_path()

    def test_program_id_matches_the_idl(self):
        self.assertEqual(self.program.program_id, PROGRAM_ID)

    def test_task_pda_uses_the_task_seed_and_little_endian_id(self):
        task, bump = self.program.task_address(42)
        expected, expected_bump = Pubkey.find_program_address(
            [TASK_SEED, (42).to_bytes(8, "little")], PROGRAM_ID
        )

        self.assertEqual(task, expected)
        self.assertEqual(bump, expected_bump)

    def test_task_vault_is_seeded_with_the_task_pda(self):
        task, _ = self.program.task_address(42)
        vault, _ = self.program.task_vault_address(42)
        expected, _ = Pubkey.find_program_address(
            [TASK_SEED, bytes(task)], PROGRAM_ID
        )

        self.assertEqual(vault, expected)

    def test_application_is_seeded_with_the_provider_and_task(self):
        provider = Pubkey.new_unique()
        task, _ = self.program.task_address(42)
        application, _ = self.program.application_address(42, provider)
        expected, _ = Pubkey.find_program_address(
            [b"application", bytes(provider), bytes(task)], PROGRAM_ID
        )

        self.assertEqual(application, expected)

    def test_associated_token_account_uses_the_token_program(self):
        owner = Pubkey.new_unique()
        ata = self.program.associated_token_address(owner, USDC)
        expected, _ = Pubkey.find_program_address(
            [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(USDC)],
            ASSOCIATED_TOKEN_PROGRAM_ID,
        )

        self.assertEqual(ata, expected)

    def test_create_task_encodes_its_arguments(self):
        creator = Keypair().pubkey()

        instruction = self.program.build_instruction(
            "create_task",
            accounts={"creator": creator, "stable_coin_mint": USDC},
            args={
                "task_id": 42,
                "terms": FinancialTerms(1_500_000, 500_000, 25, 250_000).to_dict(),
                "tag": "plumbing",
                "desc": "Fix the kitchen sink",
            },
        )

        self.assertEqual(instruction.program_id, PROGRAM_ID)
        self.assertEqual(len(instruction.accounts), 11)

        # The first account is the creator, and it is the only signer.
        self.assertEqual(instruction.accounts[0].pubkey, creator)
        self.assertTrue(instruction.accounts[0].is_signer)
        self.assertTrue(instruction.accounts[0].is_writable)
        self.assertEqual(
            sum(1 for account in instruction.accounts if account.is_signer), 1
        )

        reader = BorshReader(instruction.data)

        self.assertEqual(bytes(reader.take(8)), bytes(self.program.instructions["create_task"]["discriminator"]))

        self.assertEqual(reader.u64(), 42)
        self.assertEqual(reader.u64(), 1_500_000)  # labor_fee
        self.assertEqual(reader.u64(), 500_000)  # material_cost
        self.assertEqual(reader.u8(), 25)  # upfront_release_pct
        self.assertEqual(reader.u64(), 250_000)  # required_provider_collateral
        self.assertEqual(reader.option_string(), "plumbing")
        self.assertEqual(reader.option_string(), "Fix the kitchen sink")

    def test_create_task_accounts_match_the_program_layout(self):
        creator = Keypair().pubkey()

        instruction = self.program.build_instruction(
            "create_task",
            accounts={"creator": creator, "stable_coin_mint": USDC},
            args={
                "task_id": 42,
                "terms": FinancialTerms(1, 0, 0, 0).to_dict(),
                "tag": None,
                "desc": None,
            },
        )

        accounts = list(instruction.accounts)
        task, _ = self.program.task_address(42)
        vault, _ = self.program.task_vault_address(42)

        self.assertEqual(accounts[1].pubkey, USDC)
        self.assertEqual(accounts[5].pubkey, task)
        self.assertEqual(accounts[6].pubkey, vault)
        self.assertEqual(
            accounts[7].pubkey,
            self.program.associated_token_address(creator, USDC),
        )
        self.assertEqual(accounts[9].pubkey, TOKEN_PROGRAM_ID)

    def test_approve_work_pays_the_providers_token_account(self):
        creator = Keypair().pubkey()
        provider = Keypair().pubkey()

        instruction = self.program.build_instruction(
            "approve_work",
            accounts={
                "creator": creator,
                "provider_token_account": self.program.associated_token_address(
                    provider, USDC
                ),
                "stable_coin_mint": USDC,
            },
            args={"task_id": 42},
        )

        accounts = list(instruction.accounts)
        self.assertEqual(len(accounts), 6)
        self.assertEqual(
            accounts[3].pubkey,
            self.program.associated_token_address(provider, USDC),
        )
        self.assertTrue(accounts[3].is_writable)

    def test_unknown_instruction_is_rejected(self):
        with self.assertRaises(SolanaError):
            self.program.build_instruction("not_an_instruction", {}, {})

    def test_missing_account_is_rejected(self):
        with self.assertRaises(SolanaError):
            self.program.build_instruction(
                "approve_work",
                accounts={"creator": Keypair().pubkey()},
                args={"task_id": 1},
            )


class TaskAccountDecodingTests(unittest.TestCase):
    def _encode_task(self, **overrides) -> bytes:
        values = dict(
            task_id=42,
            creator=Keypair().pubkey(),
            provider=Keypair().pubkey(),
            desc="Fix the sink",
            tag="plumbing",
            status=0,
            labor_fee=1_000_000,
            material_cost=500_000,
            upfront_release_pct=25,
            required_collateral=250_000,
            creator_locked=1_500_000,
            provider_locked=250_000,
            advanced_disbursed=False,
            created_at=1_700_000_000,
            updated_at=1_700_000_100,
        )
        values.update(overrides)

        out = bytearray()
        # Anchor account data starts with the 8-byte account discriminator.
        out += bytes.fromhex("5f2b1c4a7d3e9f01")
        out += values["task_id"].to_bytes(8, "little")
        out += bytes(values["creator"])
        if values["provider"] is None:
            out += b"\x00"
        else:
            out += b"\x01" + bytes(values["provider"])
        out += bytes(USDC)

        desc = values["desc"].encode()
        out += b"\x01" + len(desc).to_bytes(4, "little") + desc

        tag = values["tag"].encode()
        out += b"\x01" + len(tag).to_bytes(4, "little") + tag

        out += bytes([values["status"]])
        out += values["labor_fee"].to_bytes(8, "little")
        out += values["material_cost"].to_bytes(8, "little")
        out += bytes([values["upfront_release_pct"]])
        out += values["required_collateral"].to_bytes(8, "little")
        out += values["creator_locked"].to_bytes(8, "little")

        if values["provider_locked"] is None:
            out += b"\x00"
        else:
            out += b"\x01" + values["provider_locked"].to_bytes(8, "little")

        out += b"\x01" if values["advanced_disbursed"] else b"\x00"
        out += values["created_at"].to_bytes(8, "little", signed=True)
        out += values["updated_at"].to_bytes(8, "little", signed=True)

        return bytes(out)

    def test_decodes_a_task_account(self):
        state = decode_task_account(self._encode_task())

        self.assertEqual(state.id, 42)
        self.assertEqual(state.status, "Open")
        self.assertEqual(state.labor_fee, 1_000_000)
        self.assertEqual(state.material_cost, 500_000)
        self.assertEqual(state.upfront_release_pct, 25)
        self.assertEqual(state.required_provider_collateral, 250_000)
        self.assertEqual(state.creator_locked_balance, 1_500_000)
        self.assertEqual(state.provider_locked_balance, 250_000)
        self.assertFalse(state.advanced_disbursed)
        self.assertEqual(state.desc, "Fix the sink")
        self.assertEqual(state.tag, "plumbing")

    def test_decodes_a_task_without_a_provider(self):
        state = decode_task_account(self._encode_task(provider=None))

        self.assertIsNone(state.provider)
        self.assertEqual(state.provider_locked_balance, 250_000)

    def test_decodes_a_task_without_provider_collateral(self):
        state = decode_task_account(self._encode_task(provider_locked=None))

        self.assertIsNone(state.provider_locked_balance)

    def test_truncated_account_is_rejected(self):
        with self.assertRaises(SolanaError):
            decode_task_account(self._encode_task()[:20])


class SolanaRpcTests(unittest.IsolatedAsyncioTestCase):
    async def test_send_transaction_serializes_a_legacy_transaction(self):
        rpc = SolanaRpc("http://localhost:8899")
        calls = []

        async def fake_call(method, params=None):
            calls.append((method, params))
            return "sig-1"

        rpc._call = fake_call
        payer = Keypair().pubkey()
        instruction = Instruction(PROGRAM_ID, b"\x01", [])
        transaction = build_legacy_transaction(
            payer, [instruction], Hash.new_unique()
        )

        signature = await rpc.send_transaction(transaction)

        self.assertEqual(signature, "sig-1")
        method, params = calls[0]
        self.assertEqual(method, "sendTransaction")
        decoded = VersionedTransaction.from_bytes(base64.b64decode(params[0]))
        self.assertEqual(decoded.message.account_keys[0], payer)


class Base58Tests(unittest.TestCase):
    def test_round_trip(self):
        raw = bytes(range(32))
        self.assertEqual(base58_decode(base58_encode(raw)), raw)

    def test_leading_zeroes_are_kept(self):
        raw = b"\x00\x00\x01"
        self.assertEqual(base58_decode(base58_encode(raw)), raw)

    def test_invalid_character_is_rejected(self):
        with self.assertRaises(ValueError):
            base58_decode("0OIl")


if __name__ == "__main__":
    unittest.main()
