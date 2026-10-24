"""The Reach server relayer.

The architecture doc describes the backend relayer as a "FastAPI Keypair
Engine" that holds an automated Solana keypair and signs on the user's behalf
(`payer_type = "custodial"`). This module is that engine:

* it holds the relayer keypair (loaded from the environment, never the database);
* it enforces a small policy before anything is signed;
* it builds the Anchor instructions, submits them, and waits for confirmation.

The relayer is the escrow's counterparty on-chain, so its token account must
hold the USDC that backs every custodial task.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from solders.instruction import AccountMeta, Instruction
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction

from core.solana import (
    ASSOCIATED_TOKEN_PROGRAM_ID,
    SYSTEM_PROGRAM_ID,
    TOKEN_PROGRAM_ID,
    AnchorProgram,
    SolanaRpc,
    TaskState,
    TransactionConfirmation,
    build_versioned_transaction,
    decode_task_account,
)


class RelayerError(RuntimeError):
    pass


class RelayerNotConfigured(RelayerError):
    """Raised when the relayer has no keypair or RPC endpoint configured."""


class PolicyViolation(RelayerError):
    """Raised when a request fails the relayer's pre-signing checks."""


@dataclass(frozen=True)
class FinancialTerms:
    """The `FinancialTerms` struct the Anchor program expects."""

    labor_fee: int
    material_cost: int
    upfront_release_pct: int = 0
    required_provider_collateral: int = 0

    @property
    def total(self) -> int:
        return self.labor_fee + self.material_cost

    def to_dict(self) -> dict[str, int]:
        return {
            "labor_fee": self.labor_fee,
            "material_cost": self.material_cost,
            "upfront_release_pct": self.upfront_release_pct,
            "required_provider_collateral": self.required_provider_collateral,
        }


@dataclass(frozen=True)
class RelayerConfig:
    rpc_url: str
    program_id: str
    stable_mint: str
    secret_key: str | None
    confirm_timeout_seconds: float = 60.0
    min_escrow_units: int = 1

    @classmethod
    def from_env(cls) -> "RelayerConfig":
        return cls(
            rpc_url=os.getenv("REACH_SOLANA_RPC_URL", ""),
            program_id=os.getenv("REACH_PROGRAM_ID", ""),
            stable_mint=os.getenv("REACH_STABLE_MINT", ""),
            secret_key=os.getenv("REACH_RELAYER_SECRET_KEY"),
            confirm_timeout_seconds=float(
                os.getenv("REACH_RELAYER_CONFIRM_TIMEOUT", "60")
            ),
            min_escrow_units=int(os.getenv("REACH_MIN_ESCROW_UNITS", "1")),
        )


class Relayer:
    """Signs and submits Reach program instructions on behalf of the platform."""

    def __init__(
        self,
        config: RelayerConfig,
        rpc: SolanaRpc | None = None,
        program: AnchorProgram | None = None,
        keypair: Keypair | None = None,
    ):
        self.config = config
        self.rpc = rpc or SolanaRpc(config.rpc_url)
        self.program = program or AnchorProgram.from_idl_path()
        self._keypair = keypair

    # -- identity --------------------------------------------------------

    @property
    def keypair(self) -> Keypair:
        if self._keypair is None:
            if not self.config.secret_key:
                raise RelayerNotConfigured(
                    "REACH_RELAYER_SECRET_KEY is not set; the relayer cannot sign"
                )
            try:
                raw = base58_decode(self.config.secret_key)
            except ValueError as exc:
                raise RelayerNotConfigured("The relayer secret key is not base58") from exc
            self._keypair = Keypair.from_bytes(raw)
        return self._keypair

    @property
    def address(self) -> Pubkey:
        return self.keypair.pubkey()

    @property
    def mint(self) -> Pubkey:
        if not self.config.stable_mint:
            raise RelayerNotConfigured("REACH_STABLE_MINT is not set")
        return Pubkey.from_string(self.config.stable_mint)

    @property
    def enabled(self) -> bool:
        return bool(self.config.rpc_url and self.config.secret_key)

    # -- balances --------------------------------------------------------

    async def token_account_address(self, owner: Pubkey) -> Pubkey:
        return self.program.associated_token_address(owner, self.mint)

    async def token_balance(self, owner: Pubkey | None = None) -> int:
        owner = owner or self.address
        ata = await self.token_account_address(owner)
        balance = await self.rpc.get_token_account_balance(ata)
        if not balance:
            return 0
        return int(balance["value"]["amount"])

    async def ensure_token_account(self, owner: Pubkey | None = None) -> Pubkey:
        """Create a USDC token account if it does not exist yet.

        The owner pays the rent. For the relayer that is the escrow's source
        account; for a provider it is the account their payout is released
        into, which does not exist until they have held USDC on Solana.
        """
        owner = owner or self.address
        ata = self.program.associated_token_address(owner, self.mint)
        existing = await self.rpc.get_account_info(ata)
        if existing is not None:
            return ata

        # Associated token program `CreateIdempotent` creates and initializes
        # the account in one instruction. The account order is
        # [payer, ata, owner, mint, system, token].
        create_ata = Instruction(
            ASSOCIATED_TOKEN_PROGRAM_ID,
            bytes([1]),
            [
                AccountMeta(self.address, True, True),
                AccountMeta(ata, False, True),
                AccountMeta(owner, False, False),
                AccountMeta(self.mint, False, False),
                AccountMeta(SYSTEM_PROGRAM_ID, False, False),
                AccountMeta(TOKEN_PROGRAM_ID, False, False),
            ],
        )

        await self.submit(
            [create_ata],
            idempotency_key=f"ata-{ata}",
        )
        return ata

    # -- policy ----------------------------------------------------------

    def check_policy(
        self,
        *,
        task_id: int,
        terms: FinancialTerms | None = None,
    ) -> None:
        if task_id <= 0:
            raise PolicyViolation("task_id must be a positive integer")

        if not self.config.stable_mint:
            raise RelayerNotConfigured("REACH_STABLE_MINT is not set")

        if terms is not None:
            if terms.total < self.config.min_escrow_units:
                raise PolicyViolation(
                    "The escrow amount is below the configured minimum"
                )
            if terms.upfront_release_pct > 100:
                raise PolicyViolation("upfront_release_pct cannot exceed 100")
            if terms.required_provider_collateral < 0:
                raise PolicyViolation(
                    "required_provider_collateral cannot be negative"
                )

    # -- submission ------------------------------------------------------

    async def submit(
        self,
        instructions: list[Instruction],
        *,
        idempotency_key: str,
        confirm_timeout: float | None = None,
    ) -> TransactionConfirmation:
        """Sign, submit and confirm a transaction built from `instructions`."""
        if not instructions:
            raise RelayerError("No instructions to submit")

        for instruction in instructions:
            if instruction.program_id != self.program.program_id and (
                instruction.program_id
                not in (SYSTEM_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID)
            ):
                raise PolicyViolation(
                    f"Refusing to sign for program {instruction.program_id}"
                )

        blockhash = await self.rpc.get_latest_blockhash()
        transaction: VersionedTransaction = build_versioned_transaction(
            self.address, instructions, blockhash, [self.keypair]
        )

        signature = await self.rpc.send_transaction(transaction)

        return await self.rpc.confirm_transaction(
            signature,
            timeout_seconds=confirm_timeout or self.config.confirm_timeout_seconds,
        )

    # -- task lifecycle --------------------------------------------------

    async def create_task(
        self,
        *,
        task_id: int,
        terms: FinancialTerms,
        tag: str | None = None,
        desc: str | None = None,
        idempotency_key: str | None = None,
    ) -> TransactionConfirmation:
        """Lock the creator's escrow and open the task on-chain."""
        self.check_policy(task_id=task_id, terms=terms)

        instruction = self.program.build_instruction(
            "create_task",
            accounts={
                "creator": self.address,
                "stable_coin_mint": self.mint,
            },
            args={
                "task_id": task_id,
                "terms": terms.to_dict(),
                "tag": tag,
                "desc": desc,
            },
        )

        return await self.submit(
            [instruction],
            idempotency_key=idempotency_key or f"create-task-{task_id}",
        )

    async def accept_application(
        self,
        *,
        task_id: int,
        provider_address: Pubkey,
        idempotency_key: str | None = None,
    ) -> TransactionConfirmation:
        """Accept a provider's on-chain application as the task creator.

        The relayer is the creator for custodial tasks, so it signs this. A
        task funded by the creator's own wallet cannot use this path; the
        creator has to accept from that wallet instead.
        """
        self.check_policy(task_id=task_id)

        instruction = self.program.build_instruction(
            "accept",
            accounts={"owner": self.address},
            args={
                "task_id": task_id,
                "provider": provider_address,
            },
        )

        return await self.submit(
            [instruction],
            idempotency_key=idempotency_key
            or f"accept-application-{task_id}-{provider_address}",
        )

    async def approve_work(
        self,
        *,
        task_id: int,
        provider_address: Pubkey,
        idempotency_key: str | None = None,
    ) -> TransactionConfirmation:
        """Release the escrow to the provider."""
        self.check_policy(task_id=task_id)

        instruction = self.program.build_instruction(
            "approve_work",
            accounts={
                "creator": self.address,
                "provider_token_account": self.program.associated_token_address(
                    provider_address, self.mint
                ),
                "stable_coin_mint": self.mint,
            },
            args={"task_id": task_id},
        )

        return await self.submit(
            [instruction],
            idempotency_key=idempotency_key or f"approve-work-{task_id}",
        )

    async def cancel_task(
        self,
        *,
        task_id: int,
        idempotency_key: str | None = None,
    ) -> TransactionConfirmation:
        """Cancel an open task and refund the creator minus the cancellation fee."""
        self.check_policy(task_id=task_id)

        instruction = self.program.build_instruction(
            "cancel_task",
            accounts={
                "creator": self.address,
                "creator_token_account": self.program.associated_token_address(
                    self.address, self.mint
                ),
                "stable_coin_mint": self.mint,
            },
            args={"task_id": task_id},
        )

        return await self.submit(
            [instruction],
            idempotency_key=idempotency_key or f"cancel-task-{task_id}",
        )

    async def raise_dispute(
        self,
        *,
        task_id: int,
        idempotency_key: str | None = None,
    ) -> TransactionConfirmation:
        self.check_policy(task_id=task_id)

        instruction = self.program.build_instruction(
            "raise_dispute",
            accounts={"caller": self.address},
            args={"task_id": task_id},
        )

        return await self.submit(
            [instruction],
            idempotency_key=idempotency_key or f"raise-dispute-{task_id}",
        )

    # -- reads -----------------------------------------------------------

    async def read_task(self, task_id: int) -> TaskState | None:
        task_address, _ = self.program.task_address(task_id)
        data = await self.rpc.get_account_info(task_address)
        if data is None:
            return None
        return decode_task_account(data)


def base58_decode(value: str) -> bytes:
    """Decode a base58 string (used for the relayer's secret key)."""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = 0
    for character in value:
        index = alphabet.find(character)
        if index < 0:
            raise ValueError(f"Invalid base58 character: {character}")
        number = number * 58 + index

    body = number.to_bytes((number.bit_length() + 7) // 8, "big")

    zeros = 0
    for character in value:
        if character != "1":
            break
        zeros += 1

    return b"\x00" * zeros + body


def base58_encode(raw: bytes) -> str:
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    number = int.from_bytes(raw, "big")
    encoded = ""
    while number > 0:
        number, remainder = divmod(number, 58)
        encoded = alphabet[remainder] + encoded

    zeros = 0
    for byte in raw:
        if byte != 0:
            break
        zeros += 1

    return "1" * zeros + encoded


def relayer_from_env() -> Relayer:
    """Build a relayer from the environment. Raises if it is not configured."""
    config = RelayerConfig.from_env()
    if not config.rpc_url:
        raise RelayerNotConfigured("REACH_SOLANA_RPC_URL is not set")
    if not config.secret_key:
        raise RelayerNotConfigured("REACH_RELAYER_SECRET_KEY is not set")
    return Relayer(config)
