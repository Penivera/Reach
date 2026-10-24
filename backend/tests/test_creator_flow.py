"""Tests for the client-signed (wallet-funded) escrow lifecycle.

The client's wallet is the on-chain creator, so it signs ``create_task``,
``accept`` and ``approve_work``. The backend prepares each transaction, the
wallet signs it, and the backend verifies the signed bytes before submitting.
"""

import base64
import unittest
from types import SimpleNamespace
from unittest import mock

from solders.hash import Hash
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import Transaction

from fastapi import HTTPException

from support import FakeSession

from core.relayer import Relayer, RelayerConfig
from core.solana import TaskState, TransactionConfirmation
from models import PaymentIntent
from schemas import (
    ApplicationStatus,
    CreatorAction,
    FundingStatus,
    JobApplicationStatusUpdate,
    JobStatus,
    PayerType,
)
from routers.jobs import update_application_status
from routers.payments import release_job_payment
import services.creator_flow as creator_flow
from services.creator_flow import (
    CreatorStateError,
    CreatorTransactionInvalid,
    prepare_accept,
    prepare_create_task,
    prepare_release,
    submit_accept,
    submit_create_task,
    submit_release,
)

USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
PROGRAM_ID = "5iCtrxFDsPQf6qyR2nfjkDgUJyuH7oxoA5Lf1qQiDfwY"
ESCROW = (10_000_000 * 10_000) // 10_250


class FakeRpc:
    def __init__(self):
        self.blockhash = Hash.new_unique()
        self.sent = []
        self.confirmed = []
        self.token_balance = {"value": {"amount": "1000000000"}}

    async def get_latest_blockhash(self):
        return self.blockhash

    async def get_account_info(self, address):
        return b"exists"

    async def get_token_account_balance(self, address):
        return self.token_balance

    async def send_transaction(self, transaction):
        self.sent.append(transaction)
        return "sig-creator"

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


def make_job(**overrides):
    values = dict(
        id=5,
        owner_id=1,
        title="Fix the sink",
        description="Leaking tap",
        budget=5_000,
        status=JobStatus.PENDING_FUNDING,
        funding_status=FundingStatus.PENDING,
        payer_type=None,
        onchain_task_id=None,
        onchain_tx_hash=None,
        onchain_status=None,
        client_completed=False,
        worker_completed=False,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def make_user(wallet: Keypair, user_id: int = 1):
    return SimpleNamespace(id=user_id, onchain_address=str(wallet.pubkey()))


def make_application(**overrides):
    values = dict(
        id=7,
        job_id=5,
        applicant_id=2,
        status=ApplicationStatus.PENDING,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def task_state(
    *,
    creator: Pubkey,
    provider: Pubkey | None = None,
    status: str = "Open",
    labor_fee: int = ESCROW,
):
    return TaskState(
        id=5,
        creator=creator,
        provider=provider,
        stable_coin_mint=Pubkey.from_string(USDC),
        desc="Leaking tap",
        tag="Fix the sink",
        status=status,
        labor_fee=labor_fee,
        material_cost=0,
        upfront_release_pct=0,
        required_provider_collateral=0,
        creator_locked_balance=labor_fee,
        provider_locked_balance=None,
        advanced_disbursed=False,
        created_at=1_700_000_000,
        updated_at=1_700_000_100,
    )


async def _prepare_create(relayer, client, job):
    with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
         mock.patch.object(
             relayer, "read_task", new=mock.AsyncMock(return_value=None)
         ), \
         mock.patch.object(
             relayer,
             "ensure_token_account",
             new=mock.AsyncMock(return_value=client.pubkey()),
         ):
        return await prepare_create_task(
            FakeSession([[]]),
            job=job,
            user=make_user(client),
            usdc_units=10_000_000,
        )


def _sign(prepared, signer: Keypair) -> str:
    transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
    transaction.sign([signer], transaction.message.recent_blockhash)
    return base64.b64encode(bytes(transaction)).decode("ascii")


class PrepareCreateTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_task_is_built_for_the_client_wallet(self):
        relayer = build_relayer()
        client = Keypair()
        job = make_job()

        prepared = await _prepare_create(relayer, client, job)

        self.assertEqual(prepared.action, CreatorAction.CREATE)
        self.assertFalse(prepared.already_done)
        self.assertEqual(prepared.escrow_units, ESCROW)
        self.assertIsNotNone(prepared.transaction)

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        self.assertEqual(transaction.message.account_keys[0], client.pubkey())

        compiled = transaction.message.instructions[0]
        self.assertEqual(
            transaction.message.account_keys[compiled.program_id_index],
            relayer.program.program_id,
        )
        self.assertTrue(
            bytes(compiled.data).startswith(
                bytes(relayer.program.instructions["create_task"]["discriminator"])
            )
        )

    async def test_create_task_is_idempotent_when_the_task_exists(self):
        relayer = build_relayer()
        client = Keypair()
        job = make_job()
        state = task_state(creator=client.pubkey())

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=state)
             ):
            prepared = await prepare_create_task(
                FakeSession([[]]),
                job=job,
                user=make_user(client),
                usdc_units=10_000_000,
            )

        self.assertTrue(prepared.already_done)
        self.assertIsNone(prepared.transaction)
        self.assertEqual(job.funding_status, FundingStatus.FUNDED)
        self.assertEqual(job.payer_type, PayerType.WALLET)

    async def test_a_different_creator_cannot_reuse_the_task_id(self):
        relayer = build_relayer()
        client = Keypair()
        other = Keypair()
        job = make_job()

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(creator=other.pubkey())
                 ),
             ):
            with self.assertRaises(CreatorStateError):
                await prepare_create_task(
                    FakeSession([]),
                    job=job,
                    user=make_user(client),
                    usdc_units=10_000_000,
                )


class SubmitCreateTests(unittest.IsolatedAsyncioTestCase):
    async def test_create_task_submits_and_marks_the_job_funded(self):
        relayer = build_relayer()
        client = Keypair()
        job = make_job()
        prepared = await _prepare_create(relayer, client, job)
        signed = _sign(prepared, client)
        intent = SimpleNamespace(usdc_amount=10_000_000, status="pending")
        db = FakeSession([None, intent, None, intent])

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     side_effect=[
                         None,
                         task_state(creator=client.pubkey()),
                     ]
                 ),
             ), \
             mock.patch.object(
                 creator_flow,
                 "notify_nearby_providers",
                 new=mock.AsyncMock(),
             ):
            record = await submit_create_task(
                db,
                job=job,
                user=make_user(client),
                signed_transaction=signed,
            )

        self.assertEqual(record.signature, "sig-creator")
        self.assertEqual(record.kind, "create_task")
        self.assertEqual(job.funding_status, FundingStatus.FUNDED)
        self.assertEqual(job.payer_type, PayerType.WALLET)
        self.assertEqual(job.status, JobStatus.OPEN)
        self.assertEqual(job.onchain_task_id, 5)
        self.assertEqual(relayer.rpc.confirmed, ["sig-creator"])

    async def test_a_tampered_create_task_is_rejected(self):
        relayer = build_relayer()
        client = Keypair()
        job = make_job()
        prepared = await _prepare_create(relayer, client, job)
        raw = bytearray(base64.b64decode(prepared.transaction))
        raw[1] ^= 0xFF
        tampered = base64.b64encode(bytes(raw)).decode("ascii")
        intent = SimpleNamespace(usdc_amount=10_000_000, status="pending")

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer, "read_task", new=mock.AsyncMock(return_value=None)
             ):
            with self.assertRaises(CreatorTransactionInvalid):
                await submit_create_task(
                    FakeSession([None, intent]),
                    job=job,
                    user=make_user(client),
                    signed_transaction=tampered,
                )


class PrepareAcceptTests(unittest.IsolatedAsyncioTestCase):
    async def test_accept_is_built_for_the_client(self):
        relayer = build_relayer()
        client = Keypair()
        provider = Keypair()
        job = make_job(
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="Open",
        )
        application = make_application()

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(creator=client.pubkey())
                 ),
             ), \
             mock.patch.object(
                 creator_flow,
                 "_read_application_or_raise",
                 new=mock.AsyncMock(return_value=SimpleNamespace(status="Pending")),
             ):
            prepared = await prepare_accept(
                FakeSession([]),
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
            )

        self.assertEqual(prepared.action, CreatorAction.ACCEPT)
        self.assertFalse(prepared.already_done)

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        self.assertEqual(transaction.message.account_keys[0], client.pubkey())
        compiled = transaction.message.instructions[0]
        self.assertTrue(
            bytes(compiled.data).startswith(
                bytes(relayer.program.instructions["accept"]["discriminator"])
            )
        )


class SubmitAcceptTests(unittest.IsolatedAsyncioTestCase):
    async def test_accept_updates_the_application_and_job(self):
        relayer = build_relayer()
        client = Keypair()
        provider = Keypair()
        job = make_job(
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="Open",
        )
        application = make_application()

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(creator=client.pubkey())
                 ),
             ), \
             mock.patch.object(
                 creator_flow,
                 "_read_application_or_raise",
                 new=mock.AsyncMock(return_value=SimpleNamespace(status="Pending")),
             ):
            prepared = await prepare_accept(
                FakeSession([]),
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
            )

        signed = _sign(prepared, client)
        db = FakeSession([None, None, []])

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     side_effect=[
                         task_state(creator=client.pubkey()),
                         task_state(
                             creator=client.pubkey(),
                             provider=provider.pubkey(),
                             status="InProgress",
                         ),
                     ]
                 ),
             ):
            record = await submit_accept(
                db,
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
                signed_transaction=signed,
            )

        self.assertEqual(record.kind, "accept_application")
        self.assertEqual(application.status, ApplicationStatus.ACCEPTED)
        self.assertEqual(job.status, JobStatus.IN_PROGRESS)
        self.assertEqual(job.onchain_status, "InProgress")


class PrepareReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_release_is_built_for_the_client(self):
        relayer = build_relayer()
        client = Keypair()
        provider = Keypair()
        job = make_job(
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="AwaitingApproval",
            client_completed=True,
            worker_completed=True,
        )
        application = make_application(status=ApplicationStatus.ACCEPTED)

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         creator=client.pubkey(),
                         provider=provider.pubkey(),
                         status="AwaitingApproval",
                     )
                 ),
             ), \
             mock.patch.object(
                 relayer,
                 "ensure_token_account",
                 new=mock.AsyncMock(return_value=provider.pubkey()),
             ):
            prepared = await prepare_release(
                FakeSession([]),
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
            )

        self.assertEqual(prepared.action, CreatorAction.RELEASE)
        self.assertFalse(prepared.already_done)

        transaction = Transaction.from_bytes(base64.b64decode(prepared.transaction))
        self.assertEqual(transaction.message.account_keys[0], client.pubkey())
        compiled = transaction.message.instructions[0]
        self.assertTrue(
            bytes(compiled.data).startswith(
                bytes(relayer.program.instructions["approve_work"]["discriminator"])
            )
        )

    async def test_release_requires_both_completion_flags(self):
        relayer = build_relayer()
        client = Keypair()
        provider = Keypair()
        job = make_job(
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="AwaitingApproval",
            client_completed=True,
            worker_completed=False,
        )

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer):
            with self.assertRaises(CreatorStateError):
                await prepare_release(
                    FakeSession([]),
                    job=job,
                    application=make_application(status=ApplicationStatus.ACCEPTED),
                    user=make_user(client),
                    provider=make_user(provider, user_id=2),
                )


class SubmitReleaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_release_marks_the_job_completed(self):
        relayer = build_relayer()
        client = Keypair()
        provider = Keypair()
        job = make_job(
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="AwaitingApproval",
            client_completed=True,
            worker_completed=True,
        )
        application = make_application(status=ApplicationStatus.ACCEPTED)

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     return_value=task_state(
                         creator=client.pubkey(),
                         provider=provider.pubkey(),
                         status="AwaitingApproval",
                     )
                 ),
             ), \
             mock.patch.object(
                 relayer,
                 "ensure_token_account",
                 new=mock.AsyncMock(return_value=provider.pubkey()),
             ):
            prepared = await prepare_release(
                FakeSession([]),
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
            )

        signed = _sign(prepared, client)
        db = FakeSession([None, None])

        with mock.patch.object(creator_flow, "get_relayer", return_value=relayer), \
             mock.patch.object(
                 relayer,
                 "read_task",
                 new=mock.AsyncMock(
                     side_effect=[
                         task_state(
                             creator=client.pubkey(),
                             provider=provider.pubkey(),
                             status="AwaitingApproval",
                         ),
                         task_state(
                             creator=client.pubkey(),
                             provider=provider.pubkey(),
                             status="Completed",
                         ),
                     ]
                 ),
             ):
            record = await submit_release(
                db,
                job=job,
                application=application,
                user=make_user(client),
                provider=make_user(provider, user_id=2),
                signed_transaction=signed,
            )

        self.assertEqual(record.kind, "approve_work")
        self.assertEqual(job.status, JobStatus.COMPLETED)
        self.assertEqual(job.onchain_status, "Completed")


class CustodialBranchTests(unittest.IsolatedAsyncioTestCase):
    async def test_patch_accept_rejects_a_wallet_funded_job(self):
        application = make_application()
        job = make_job(
            owner_id=1,
            status=JobStatus.OPEN,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
        )
        db = FakeSession([application, job])

        with self.assertRaises(HTTPException) as ctx:
            await update_application_status(
                7,
                JobApplicationStatusUpdate(status=ApplicationStatus.ACCEPTED),
                db=db,
                current_user=SimpleNamespace(id=1),
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("onchain/accept", ctx.exception.detail)

    async def test_relayer_release_rejects_a_wallet_funded_job(self):
        job = make_job(
            owner_id=1,
            status=JobStatus.IN_PROGRESS,
            funding_status=FundingStatus.FUNDED,
            payer_type=PayerType.WALLET,
            onchain_status="AwaitingApproval",
            client_completed=True,
            worker_completed=True,
        )
        db = FakeSession([job])

        with self.assertRaises(HTTPException) as ctx:
            await release_job_payment(
                5, db=db, current_user=SimpleNamespace(id=1)
            )

        self.assertEqual(ctx.exception.status_code, 409)
        self.assertIn("onchain/release", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
