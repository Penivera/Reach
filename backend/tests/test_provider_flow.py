"""Tests for the provider-signed apply / complete_task lifecycle.

The provider's own wallet is the only key that can sign `apply` and
`complete_task`, so the backend prepares a transaction, the wallet signs it,
and the backend verifies the signed bytes before submitting them.
"""

import base64
import unittest
from types import SimpleNamespace
from unittest import mock

from solders.hash import Hash
from solders.keypair import Keypair
from solders.transaction import Transaction

from support import FakeSession

from core.relayer import Relayer, RelayerConfig
from core.solana import TaskState, TransactionConfirmation
from schemas import (
    ChainTransactionStatus,
    FundingStatus,
    JobStatus,
    ProviderAction,
)
import services.provider_flow as provider_flow
from services.provider_flow import (
    ProviderFlowError,
    ProviderStateError,
    ProviderTransactionInvalid,
    _idempotency_key,
    accept_application_onchain,
    prepare_provider_transaction,
    submit_provider_transaction,
)

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
PROGRAM_ID = "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY"


class FakeRpc:
    def __init__(self):
        self.blockhash = Hash.new_unique()
        self.account_info = None
        self.sent = []
        self.confirmed = []

    async def get_latest_blockhash(self):
        return self.blockhash

    async def get_account_info(self, address):
        return self.account_info

    async def send_transaction(self, transaction):
        self.sent.append(transaction)
        return "sig-provider"

    async def confirm_transaction(self, signature, timeout_seconds=60.0):
        self.confirmed.append(signature)
        return TransactionConfirmation(signature, 123, "confirmed")


def build_relayer() -> Relayer:
    config = RelayerConfig(
        rpc_url="http://localhost:8899",
        program_id=PROGRAM_ID,
        stable_mint=USDC,
        secret_key=None,
        min_escrow_units=1,
    )
    relayer = Relayer(config, rpc=FakeRpc())
    relayer._keypair = Keypair()
    return relayer


def task_state(*, status="Open", provider=None, creator=None) -> TaskState:
    return TaskState(
        id=5,
        creator=creator or Keypair().pubkey(),
        provider=provider,
        stable_coin_mint=Keypair().pubkey(),
        desc="Fix the sink",
        tag="plumbing",
        status=status,
        labor_fee=1_000_000,
        material_cost=0,
        upfront_release_pct=0,
        required_provider_collateral=0,
        creator_locked_balance=1_000_000,
        provider_locked_balance=None,
        advanced_disbursed=False,
        created_at=1_700_000_000,
        updated_at=1_700_000_100,
    )


class IdempotencyKeyTests(unittest.TestCase):
    def test_application_keys_are_per_provider(self):
        first = Keypair().pubkey()
        second = Keypair().pubkey()

        self.assertNotEqual(
            _idempotency_key(ProviderAction.APPLY, 5, first),
            _idempotency_key(ProviderAction.APPLY, 5, second),
        )


class PrepareTests(unittest.IsolatedAsyncioTestCase):
    async def test_apply_builds_a_transaction_for_the_provider(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=task_state())
             ), \
             mock.patch.object(
                 relayer.rpc, "get_account_info", new=mock.AsyncMock(return_value=None)
             ):
            prepared = await prepare_provider_transaction(
                FakeSession(), job=job, user=user, action=ProviderAction.APPLY
            )

        self.assertFalse(prepared.already_done)
        self.assertIsNotNone(prepared.transaction)

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        self.assertEqual(transaction.message.account_keys[0], provider.pubkey())

        compiled = transaction.message.instructions[0]
        self.assertEqual(
            transaction.message.account_keys[compiled.program_id_index],
            relayer.program.program_id,
        )
        self.assertTrue(
            bytes(compiled.data).startswith(
                bytes(relayer.program.instructions["apply"]["discriminator"])
            )
        )

    async def test_apply_is_idempotent_when_the_application_exists(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=task_state())
             ), \
             mock.patch.object(
                 relayer.rpc,
                 "get_account_info",
                 new=mock.AsyncMock(return_value=b"already-there"),
             ):
            prepared = await prepare_provider_transaction(
                FakeSession(), job=job, user=user, action=ProviderAction.APPLY
            )

        self.assertTrue(prepared.already_done)
        self.assertIsNone(prepared.transaction)

    async def test_complete_requires_the_accepted_provider(self):
        relayer = build_relayer()
        provider = Keypair()
        someone_else = Keypair().pubkey()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(status="InProgress", provider=someone_else)
                 ),
             ):
            with self.assertRaises(ProviderStateError):
                await prepare_provider_transaction(
                    FakeSession(), job=job, user=user, action=ProviderAction.COMPLETE
                )


class SubmitTests(unittest.IsolatedAsyncioTestCase):
    async def _signed_apply(self, relayer, provider, job, user):
        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=task_state())
             ), \
             mock.patch.object(
                 relayer.rpc, "get_account_info", new=mock.AsyncMock(return_value=None)
             ):
            prepared = await prepare_provider_transaction(
                FakeSession(), job=job, user=user, action=ProviderAction.APPLY
            )

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        transaction.sign([provider], transaction.message.recent_blockhash)
        return base64.b64encode(bytes(transaction)).decode("ascii")

    async def test_apply_submits_and_records_the_transaction(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
            onchain_status="Open",
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))
        signed = await self._signed_apply(relayer, provider, job, user)
        db = FakeSession([None, None])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=task_state())
             ), \
             mock.patch.object(
                 provider_flow,
                 "_read_application_or_raise",
                 new=mock.AsyncMock(return_value=SimpleNamespace(status="Pending")),
             ):
            record = await submit_provider_transaction(
                db,
                job=job,
                user=user,
                action=ProviderAction.APPLY,
                signed_transaction=signed,
            )

        self.assertEqual(record.signature, "sig-provider")
        self.assertEqual(record.kind, "apply")
        self.assertEqual(relayer.rpc.confirmed, ["sig-provider"])

    async def test_complete_marks_the_job_awaiting_approval(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
            onchain_status="InProgress",
            worker_completed=False,
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="InProgress", provider=provider.pubkey()
                     )
                 ),
             ):
            prepared = await prepare_provider_transaction(
                FakeSession(), job=job, user=user, action=ProviderAction.COMPLETE
            )

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        transaction.sign([provider], transaction.message.recent_blockhash)
        signed = base64.b64encode(bytes(transaction)).decode("ascii")
        db = FakeSession([None, None])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="AwaitingApproval", provider=provider.pubkey()
                     )
                 ),
             ):
            record = await submit_provider_transaction(
                db,
                job=job,
                user=user,
                action=ProviderAction.COMPLETE,
                signed_transaction=signed,
            )

        self.assertEqual(record.kind, "complete")
        self.assertTrue(job.worker_completed)
        self.assertEqual(job.onchain_status, "AwaitingApproval")

    async def test_a_tampered_transaction_is_rejected(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            onchain_task_id=5,
            onchain_status="Open",
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))
        signed = await self._signed_apply(relayer, provider, job, user)

        # Corrupt the provider's signature bytes. Re-signing with a different
        # keypair is not possible because the provider is the fee payer.
        raw = bytearray(base64.b64decode(signed))
        raw[1] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode("ascii")

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer):
            with self.assertRaises(ProviderTransactionInvalid):
                await submit_provider_transaction(
                    FakeSession([None]),
                    job=job,
                    user=user,
                    action=ProviderAction.APPLY,
                    signed_transaction=tampered,
                )


    async def test_a_confirmed_submit_reconciles_the_job_on_replay(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            onchain_status="InProgress",
            worker_completed=False,
        )
        user = SimpleNamespace(onchain_address=str(provider.pubkey()))
        record = SimpleNamespace(status=ChainTransactionStatus.CONFIRMED)
        db = FakeSession([record])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="AwaitingApproval", provider=provider.pubkey()
                     )
                 ),
             ):
            result = await submit_provider_transaction(
                db,
                job=job,
                user=user,
                action=ProviderAction.COMPLETE,
                signed_transaction="not-used",
            )

        self.assertIs(result, record)
        self.assertTrue(job.worker_completed)
        self.assertEqual(job.onchain_status, "AwaitingApproval")


class AcceptTests(unittest.IsolatedAsyncioTestCase):
    async def test_the_relayer_accepts_the_provider(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(
            id=5,
            status=JobStatus.OPEN,
            onchain_status="Open",
        )
        user = SimpleNamespace(id=2, onchain_address=str(provider.pubkey()))
        db = FakeSession([None])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     side_effect=[
                         task_state(status="Open", creator=relayer.address),
                         task_state(
                             status="InProgress",
                             creator=relayer.address,
                             provider=provider.pubkey(),
                         ),
                     ]
                 ),
             ), \
             mock.patch.object(
                 provider_flow,
                 "_read_application_or_raise",
                 new=mock.AsyncMock(return_value=SimpleNamespace(status="Pending")),
             ), \
             mock.patch.object(
                 relayer,
                 "accept_application",
                 new=mock.AsyncMock(
                     return_value=TransactionConfirmation("sig-accept", 10, "confirmed")
                 ),
             ):
            record = await accept_application_onchain(
                db, job=job, provider=user
            )

        self.assertEqual(record.signature, "sig-accept")
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(job.onchain_status, "InProgress")

    async def test_a_retry_after_accept_reconciles_the_job(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(id=5, status=JobStatus.OPEN, onchain_status="Open")
        user = SimpleNamespace(id=2, onchain_address=str(provider.pubkey()))
        db = FakeSession([None])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="InProgress",
                         creator=relayer.address,
                         provider=provider.pubkey(),
                     )
                 ),
             ):
            record = await accept_application_onchain(
                db, job=job, provider=user
            )

        self.assertEqual(record.status, ChainTransactionStatus.CONFIRMED)
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(job.onchain_status, "InProgress")

    async def test_a_failed_accept_is_recorded(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(id=5, status=JobStatus.OPEN, onchain_status="Open")
        user = SimpleNamespace(id=2, onchain_address=str(provider.pubkey()))
        db = FakeSession([None])

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="Open", creator=relayer.address
                     )
                 ),
             ), \
             mock.patch.object(
                 provider_flow,
                 "_read_application_or_raise",
                 new=mock.AsyncMock(return_value=SimpleNamespace(status="Pending")),
             ), \
             mock.patch.object(
                 relayer,
                 "accept_application",
                 new=mock.AsyncMock(
                     return_value=TransactionConfirmation(
                         "sig-accept", 10, "failed", "program error"
                     )
                 ),
             ):
            with self.assertRaises(ProviderFlowError):
                await accept_application_onchain(
                    db, job=job, provider=user
                )

        self.assertEqual(db.added[0].status, ChainTransactionStatus.FAILED)
        self.assertEqual(db.added[0].signature, "sig-accept")

    async def test_a_wallet_created_task_cannot_be_accepted_by_the_relayer(self):
        relayer = build_relayer()
        provider = Keypair()
        job = SimpleNamespace(id=5, status=JobStatus.OPEN, onchain_status="Open")
        user = SimpleNamespace(id=2, onchain_address=str(provider.pubkey()))

        with mock.patch.object(provider_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         status="Open", creator=Keypair().pubkey()
                     )
                 ),
             ):
            with self.assertRaises(ProviderStateError):
                await accept_application_onchain(
                    FakeSession(), job=job, provider=user
                )


if __name__ == "__main__":
    unittest.main()
