"""Shared verification for wallet-signed Anchor transactions.

A browser wallet signs exactly the transaction the backend prepared. Before
submitting it, the backend re-checks the bytes:

* it must be a legacy transaction (what Phantom / Solflare / Backpack return);
* the expected wallet must be the fee payer and the only signer;
* the signature must verify;
* there must be exactly one instruction, and it must match the expected
  program, discriminator, arguments and account list.

This module is shared by the provider-signed flow and the creator-signed
(client-funded) flow so both enforce the same rules.
"""

from __future__ import annotations

from solders.instruction import Instruction
from solders.pubkey import Pubkey
from solders.transaction import Transaction


class OnchainVerificationError(ValueError):
    """The signed transaction is not the one the backend prepared."""


def instruction_matches(transaction: Transaction, expected: Instruction) -> bool:
    message = transaction.message

    # The prepared transaction has exactly one top-level instruction. Refuse
    # anything else so a wallet cannot smuggle a second instruction into the
    # transaction the backend submits.
    if len(message.instructions) != 1:
        return False

    compiled = message.instructions[0]

    if message.account_keys[compiled.program_id_index] != expected.program_id:
        return False

    if bytes(compiled.data) != bytes(expected.data):
        return False

    actual_accounts = [message.account_keys[index] for index in compiled.accounts]
    expected_accounts = [meta.pubkey for meta in expected.accounts]

    return actual_accounts == expected_accounts


def verify_signed_transaction(
    raw: bytes,
    *,
    signer: Pubkey,
    expected: Instruction,
    role: str = "user",
) -> Transaction:
    """Decode and verify a single-instruction wallet transaction."""
    try:
        transaction = Transaction.from_bytes(raw)
    except Exception as exc:  # noqa: BLE001 - solders raises ValueError
        raise OnchainVerificationError(
            "The signed transaction could not be decoded."
        ) from exc

    if not transaction.message.account_keys:
        raise OnchainVerificationError("The signed transaction has no accounts.")

    if transaction.message.account_keys[0] != signer:
        raise OnchainVerificationError(
            f"The transaction fee payer must be the {role}'s wallet."
        )

    if len(transaction.signatures) != 1:
        raise OnchainVerificationError(
            f"The transaction must be signed by the {role}'s wallet only."
        )

    if not all(transaction.verify_with_results()):
        raise OnchainVerificationError(
            f"The {role}'s wallet signature is missing or invalid."
        )

    if not instruction_matches(transaction, expected):
        raise OnchainVerificationError(
            "The signed transaction does not match the prepared instruction."
        )

    return transaction
