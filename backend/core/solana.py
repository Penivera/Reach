"""Solana settlement layer (Model 1).

The Anchor program in `sol-contract/` is the canonical escrow for Reach. This
module knows how to talk to it:

* it builds instructions from the program's IDL, so the account layout and the
  instruction data always match the deployed program;
* it derives the PDAs and token accounts the program expects;
* it reads task state back out of the chain.

It never holds funds and never holds a key. The relayer keypair lives in
`core.relayer`.
"""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import httpx
from solders.hash import Hash
from solders.instruction import AccountMeta, Instruction
from solders.message import MessageV0
from solders.pubkey import Pubkey
from solders.system_program import ID as SYSTEM_PROGRAM_ID
from solders.transaction import VersionedTransaction

TOKEN_PROGRAM_ID = Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA")
ASSOCIATED_TOKEN_PROGRAM_ID = Pubkey.from_string(
    "ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL"
)
RENT_SYSVAR_ID = Pubkey.from_string("SysvarRent111111111111111111111111111111111")

# Programs and sysvars the IDL expects to be passed in verbatim.
WELL_KNOWN_ACCOUNTS = {
    "system_program": SYSTEM_PROGRAM_ID,
    "token_program": TOKEN_PROGRAM_ID,
    "associated_token_program": ASSOCIATED_TOKEN_PROGRAM_ID,
    "rent": RENT_SYSVAR_ID,
}

DEFAULT_IDL_PATH = (
    Path(__file__).resolve().parents[2] / "sol-contract" / "idl.json"
)


class SolanaError(RuntimeError):
    """Raised when the chain layer cannot fulfil a request."""


class InstructionBuildError(SolanaError):
    """Raised when an instruction cannot be assembled from the IDL."""


# ---------------------------------------------------------------------------
# Borsh encoding
# ---------------------------------------------------------------------------


class BorshError(ValueError):
    pass


def _u64(value: Any) -> bytes:
    return int(value).to_bytes(8, "little")


def _u32(value: Any) -> bytes:
    return int(value).to_bytes(4, "little")


def _u16(value: Any) -> bytes:
    return int(value).to_bytes(2, "little")


def _u8(value: Any) -> bytes:
    return int(value).to_bytes(1, "little")


def _bool(value: Any) -> bytes:
    return b"\x01" if value else b"\x00"


def _pubkey(value: Any) -> bytes:
    if isinstance(value, Pubkey):
        return bytes(value)
    if isinstance(value, str):
        return bytes(Pubkey.from_string(value))
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise BorshError(f"Cannot encode {value!r} as a pubkey")


def _string(value: Any) -> bytes:
    if not isinstance(value, str):
        raise BorshError(f"Cannot encode {value!r} as a string")
    raw = value.encode("utf-8")
    return _u32(len(raw)) + raw


class BorshEncoder:
    """Encodes values using the type definitions from an Anchor IDL."""

    def __init__(self, defined_types: dict[str, dict] | None = None):
        self.defined_types = defined_types or {}

    def encode(self, spec: Any, value: Any) -> bytes:
        if isinstance(spec, str):
            return self._encode_primitive(spec, value)

        if not isinstance(spec, dict):
            raise BorshError(f"Unsupported type specification: {spec!r}")

        if "option" in spec:
            if value is None:
                return b"\x00"
            return b"\x01" + self.encode(spec["option"], value)

        if "vec" in spec:
            if not isinstance(value, (list, tuple)):
                raise BorshError(f"Expected a sequence, got {value!r}")
            return _u32(len(value)) + b"".join(
                self.encode(spec["vec"], item) for item in value
            )

        if "array" in spec:
            inner, length = spec["array"]
            if len(value) != length:
                raise BorshError(f"Expected {length} items, got {len(value)}")
            return b"".join(self.encode(inner, item) for item in value)

        if "defined" in spec:
            name = spec["defined"]["name"]
            return self._encode_defined(name, value)

        if "generic" in spec:
            raise BorshError("Generic IDL types are not supported")

        raise BorshError(f"Unsupported type specification: {spec!r}")

    def _encode_primitive(self, name: str, value: Any) -> bytes:
        if name == "bool":
            return _bool(value)
        if name == "u8":
            return _u8(value)
        if name == "u16":
            return _u16(value)
        if name == "u32":
            return _u32(value)
        if name in ("u64", "i64"):
            return _u64(value)
        if name in ("u128", "i128"):
            return int(value).to_bytes(16, "little")
        if name.startswith("i") and name[1:].isdigit():
            size = int(name[1:])
            return int(value).to_bytes(size, "little", signed=True)
        if name == "string":
            return _string(value)
        if name == "pubkey":
            return _pubkey(value)
        if name == "bytes":
            raw = bytes(value)
            return _u32(len(raw)) + raw
        raise BorshError(f"Unsupported primitive type: {name}")

    def _encode_defined(self, name: str, value: Any) -> bytes:
        definition = self.defined_types.get(name)
        if definition is None:
            raise BorshError(f"Unknown defined type: {name}")

        kind = definition["type"]["kind"]

        if kind == "struct":
            out = b""
            for field in definition["type"]["fields"]:
                if not isinstance(value, dict) or field["name"] not in value:
                    raise BorshError(f"Missing field {name}.{field['name']}")
                out += self.encode(field["type"], value[field["name"]])
            return out

        if kind == "enum":
            variants = definition["type"]["variants"]
            if isinstance(value, str):
                index = next(
                    (i for i, v in enumerate(variants) if v["name"] == value),
                    None,
                )
                if index is None:
                    raise BorshError(f"Unknown variant {value!r} for {name}")
                return _u8(index)
            raise BorshError(f"Expected a variant name for {name}")

        raise BorshError(f"Unsupported defined type kind: {kind}")


# ---------------------------------------------------------------------------
# Anchor program
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DerivedAccount:
    pubkey: Pubkey
    is_signer: bool = False
    is_writable: bool = False


class AnchorProgram:
    """Builds instructions for the Reach Anchor program from its IDL."""

    def __init__(self, idl: dict, program_id: Pubkey):
        self.idl = idl
        self.program_id = program_id
        self.instructions = {i["name"]: i for i in idl.get("instructions", [])}
        self.defined_types = {t["name"]: t for t in idl.get("types", [])}
        self.encoder = BorshEncoder(self.defined_types)
        self._arg_types = {
            instruction["name"]: {a["name"]: a["type"] for a in instruction["args"]}
            for instruction in idl.get("instructions", [])
        }

    @classmethod
    def from_idl_path(cls, path: str | os.PathLike | None = None) -> "AnchorProgram":
        idl_path = Path(path or os.getenv("REACH_ANCHOR_IDL_PATH") or DEFAULT_IDL_PATH)
        with open(idl_path, "r", encoding="utf-8") as handle:
            idl = json.load(handle)
        program_id = Pubkey.from_string(
            os.getenv("REACH_PROGRAM_ID") or idl["address"]
        )
        return cls(idl, program_id)

    # -- helpers ---------------------------------------------------------

    def find_program_address(
        self, seeds: Iterable[bytes], program_id: Pubkey | None = None
    ) -> tuple[Pubkey, int]:
        return Pubkey.find_program_address(list(seeds), program_id or self.program_id)

    def associated_token_address(self, owner: Pubkey, mint: Pubkey) -> Pubkey:
        return Pubkey.find_program_address(
            [bytes(owner), bytes(TOKEN_PROGRAM_ID), bytes(mint)],
            ASSOCIATED_TOKEN_PROGRAM_ID,
        )[0]

    def task_address(self, task_id: int) -> tuple[Pubkey, int]:
        return self.find_program_address(
            [b"task", int(task_id).to_bytes(8, "little")]
        )

    def task_vault_address(self, task_id: int) -> tuple[Pubkey, int]:
        task, _ = self.task_address(task_id)
        return self.find_program_address([b"task", bytes(task)])

    def application_address(self, task_id: int, provider: Pubkey) -> tuple[Pubkey, int]:
        task, _ = self.task_address(task_id)
        return self.find_program_address(
            [b"application", bytes(provider), bytes(task)]
        )

    # -- instruction building -------------------------------------------

    def build_instruction(
        self,
        name: str,
        accounts: dict[str, Pubkey] | None = None,
        args: dict[str, Any] | None = None,
    ) -> Instruction:
        spec = self.instructions.get(name)
        if spec is None:
            raise InstructionBuildError(f"Unknown instruction: {name}")

        supplied = dict(accounts or {})
        values = dict(args or {})
        account_specs = {a["name"]: a for a in spec["accounts"]}

        resolved: dict[str, Pubkey] = {}

        metas: list[AccountMeta] = []
        for account in spec["accounts"]:
            pubkey = self._resolve_account(
                account["name"], account_specs, supplied, values, resolved
            )
            metas.append(
                AccountMeta(
                    pubkey,
                    bool(account.get("signer")),
                    bool(account.get("writable")),
                )
            )

        data = bytes(spec["discriminator"])
        arg_types = self._arg_types.get(name, {})
        for arg in spec["args"]:
            if arg["name"] not in values:
                raise InstructionBuildError(
                    f"Missing argument {arg['name']} for instruction {name}"
                )
            data += self.encoder.encode(
                arg_types[arg["name"]], values[arg["name"]]
            )

        return Instruction(self.program_id, data, metas)

    def _resolve_account(
        self,
        name: str,
        account_specs: dict[str, dict],
        supplied: dict[str, Pubkey],
        values: dict[str, Any],
        resolved: dict[str, Pubkey],
    ) -> Pubkey:
        """Resolve one account of an instruction.

        Accounts can depend on each other: `task_vault` is seeded with the
        `task` PDA, and `application` is seeded with the `task` PDA. The
        resolution is therefore recursive and memoized.
        """
        if name in resolved:
            return resolved[name]

        account = account_specs.get(name)
        if account is None:
            raise InstructionBuildError(
                f"Account {name} is not part of this instruction"
            )

        pda = account.get("pda")
        if pda:
            seeds: list[bytes] = []
            for seed in pda["seeds"]:
                kind = seed["kind"]
                if kind == "const":
                    seeds.append(bytes(seed["value"]))
                elif kind == "account":
                    seeds.append(
                        bytes(
                            self._resolve_account(
                                seed["path"], account_specs, supplied, values, resolved
                            )
                        )
                    )
                elif kind == "arg":
                    seeds.append(self._encode_seed_arg(seed["path"], values))
                else:
                    raise InstructionBuildError(
                        f"Unsupported seed kind {kind} for account {name}"
                    )

            program_id = self.program_id
            program = pda.get("program")
            if program and program.get("kind") == "const":
                program_id = Pubkey.from_bytes(bytes(program["value"]))

            pubkey, _ = Pubkey.find_program_address(seeds, program_id)
            resolved[name] = pubkey
            return pubkey

        if name in supplied:
            resolved[name] = supplied[name]
            return supplied[name]

        if name in WELL_KNOWN_ACCOUNTS:
            resolved[name] = WELL_KNOWN_ACCOUNTS[name]
            return WELL_KNOWN_ACCOUNTS[name]

        raise InstructionBuildError(
            f"No public key supplied for account {name} of this instruction"
        )

    def _encode_seed_arg(self, path: str, values: dict[str, Any]) -> bytes:
        if path not in values:
            raise InstructionBuildError(f"Missing argument {path} used as a seed")
        spec = self._arg_type_of(path, values)
        return self.encoder.encode(spec, values[path])

    def _arg_type_of(self, path: str, values: dict[str, Any]) -> Any:
        # Seed args are always scalars in this program; the IDL argument types
        # are resolved lazily because a seed can reference an argument of any
        # instruction.
        for arg_types in self._arg_types.values():
            if path in arg_types:
                return arg_types[path]
        raise InstructionBuildError(f"Unknown argument {path} used as a seed")


# ---------------------------------------------------------------------------
# On-chain task state
# ---------------------------------------------------------------------------

TASK_STATUS_NAMES = [
    "Open",
    "InProgress",
    "AwaitingEscrow",
    "AwaitingApproval",
    "Completed",
    "Disputed",
    "Refunded",
]


@dataclass(frozen=True)
class TaskState:
    id: int
    creator: Pubkey
    provider: Pubkey | None
    stable_coin_mint: Pubkey
    desc: str | None
    tag: str | None
    status: str
    labor_fee: int
    material_cost: int
    upfront_release_pct: int
    required_provider_collateral: int
    creator_locked_balance: int
    provider_locked_balance: int | None
    advanced_disbursed: bool
    created_at: int
    updated_at: int


class _Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def take(self, size: int) -> bytes:
        if self.offset + size > len(self.data):
            raise SolanaError("Account data ended earlier than expected")
        chunk = self.data[self.offset : self.offset + size]
        self.offset += size
        return chunk

    def u8(self) -> int:
        return int.from_bytes(self.take(1), "little")

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "little")

    def i64(self) -> int:
        return int.from_bytes(self.take(8), "little", signed=True)

    def bool(self) -> bool:
        return self.u8() != 0

    def pubkey(self) -> Pubkey:
        return Pubkey(self.take(32))

    def string(self) -> str:
        length = int.from_bytes(self.take(4), "little")
        return self.take(length).decode("utf-8", errors="replace")

    def option_string(self) -> str | None:
        if self.u8() == 0:
            return None
        return self.string()

    def option_pubkey(self) -> Pubkey | None:
        if self.u8() == 0:
            return None
        return self.pubkey()

    def option_u64(self) -> int | None:
        if self.u8() == 0:
            return None
        return self.u64()


def decode_task_account(data: bytes) -> TaskState:
    """Decode the Reach `Task` account (Anchor borsh layout)."""
    reader = _Reader(data)

    task_id = reader.u64()
    creator = reader.pubkey()
    provider = reader.option_pubkey()
    mint = reader.pubkey()
    desc = reader.option_string()
    tag = reader.option_string()
    status_index = reader.u8()
    labor_fee = reader.u64()
    material_cost = reader.u64()
    upfront_release_pct = reader.u8()
    required_collateral = reader.u64()
    creator_locked = reader.u64()
    provider_locked = reader.option_u64()
    advanced_disbursed = reader.bool()
    created_at = reader.i64()
    updated_at = reader.i64()

    status = (
        TASK_STATUS_NAMES[status_index]
        if 0 <= status_index < len(TASK_STATUS_NAMES)
        else f"Unknown({status_index})"
    )

    return TaskState(
        id=task_id,
        creator=creator,
        provider=provider,
        stable_coin_mint=mint,
        desc=desc,
        tag=tag,
        status=status,
        labor_fee=labor_fee,
        material_cost=material_cost,
        upfront_release_pct=upfront_release_pct,
        required_provider_collateral=required_collateral,
        creator_locked_balance=creator_locked,
        provider_locked_balance=provider_locked,
        advanced_disbursed=advanced_disbursed,
        created_at=created_at,
        updated_at=updated_at,
    )


# ---------------------------------------------------------------------------
# JSON-RPC client
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TransactionConfirmation:
    signature: str
    slot: int
    status: str  # confirmed | finalized | failed
    error: str | None = None


class SolanaRpc:
    """Minimal async Solana JSON-RPC client."""

    def __init__(self, rpc_url: str, timeout: float = 30.0):
        self.rpc_url = rpc_url
        self.timeout = timeout
        self._request_id = 0

    async def _call(self, method: str, params: list | None = None) -> Any:
        self._request_id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params or [],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.rpc_url, json=payload)

        response.raise_for_status()
        body = response.json()

        if "error" in body:
            error = body["error"]
            message = error.get("message") if isinstance(error, dict) else str(error)
            raise SolanaError(f"{method} failed: {message}")

        return body.get("result")

    async def get_latest_blockhash(self, commitment: str = "confirmed") -> Hash:
        result = await self._call(
            "getLatestBlockhash", [{"commitment": commitment}]
        )
        return Hash.from_string(result["value"]["blockhash"])

    async def send_transaction(
        self, transaction: VersionedTransaction, skip_preflight: bool = False
    ) -> str:
        payload = base64.b64encode(bytes(transaction.serialize())).decode("ascii")
        result = await self._call(
            "sendTransaction",
            [
                payload,
                {
                    "encoding": "base64",
                    "skipPreflight": skip_preflight,
                    "preflightCommitment": "confirmed",
                },
            ],
        )
        return result

    async def get_signature_statuses(
        self, signature: str
    ) -> list[dict]:
        result = await self._call(
            "getSignatureStatuses", [[signature], {"searchTransactionHistory": True}]
        )
        return (result or {}).get("value") or []

    async def get_account_info(self, address: Pubkey) -> bytes | None:
        result = await self._call(
            "getAccountInfo",
            [str(address), {"encoding": "base64", "commitment": "confirmed"}],
        )
        if not result:
            return None
        data = result.get("data")
        if not data:
            return None
        encoded = data[0] if isinstance(data, list) else data
        return base64.b64decode(encoded)

    async def get_token_account_balance(
        self, owner: Pubkey, mint: Pubkey
    ) -> dict | None:
        try:
            return await self._call(
                "getTokenAccountBalance",
                [str(owner), {"mint": str(mint), "commitment": "confirmed"}],
            )
        except SolanaError:
            return None

    async def get_minimum_balance_for_rent_exemption(self, size: int) -> int:
        result = await self._call(
            "getMinimumBalanceForRentExemption", [size]
        )
        return int(result)

    async def confirm_transaction(
        self,
        signature: str,
        timeout_seconds: float = 60.0,
        poll_interval: float = 2.0,
    ) -> TransactionConfirmation:
        import asyncio

        deadline = asyncio.get_running_loop().time() + timeout_seconds
        while True:
            statuses = await self.get_signature_statuses(signature)
            if statuses:
                status = statuses[0]
                if status.get("err"):
                    return TransactionConfirmation(
                        signature=signature,
                        slot=int(status.get("slot") or 0),
                        status="failed",
                        error=str(status.get("err")),
                    )
                confirmation = status.get("confirmationStatus")
                if confirmation in ("confirmed", "finalized"):
                    return TransactionConfirmation(
                        signature=signature,
                        slot=int(status.get("slot") or 0),
                        status=confirmation,
                    )
            if asyncio.get_running_loop().time() >= deadline:
                raise SolanaError(
                    f"Transaction {signature} was not confirmed within {timeout_seconds}s"
                )
            await asyncio.sleep(poll_interval)


def build_versioned_transaction(
    payer: Pubkey, instructions: list[Instruction], blockhash: Hash
) -> VersionedTransaction:
    message = MessageV0.try_compile(payer, instructions, [])
    return VersionedTransaction(message, [])
