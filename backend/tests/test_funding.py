"""Tests for the funding maths and the chain status mapping."""

import unittest

from schemas.enums import JobStatus
from services.chain import (
    ONCHAIN_STATUS_TO_JOB_STATUS,
    build_terms,
    escrow_units_for,
)
from services.funding import to_kobo, to_usdc_units


class EscrowMathTests(unittest.TestCase):
    def test_the_creation_fee_leaves_room_in_the_funded_amount(self):
        # 10 USDC arrives; the 2.5% creation fee is charged on top of the
        # escrow, so 9.75 USDC can be locked.
        escrow = escrow_units_for(10_000_000, 250)

        self.assertEqual(escrow, 9_756_097)

    def test_a_zero_fee_locks_everything(self):
        self.assertEqual(escrow_units_for(10_000_000, 0), 10_000_000)

    def test_a_non_positive_amount_is_rejected(self):
        with self.assertRaises(Exception):
            escrow_units_for(0, 250)

    def test_the_terms_treat_the_budget_as_labour(self):
        terms = build_terms(1_000_000)

        self.assertEqual(terms.labor_fee, 1_000_000)
        self.assertEqual(terms.material_cost, 0)
        self.assertEqual(terms.total, 1_000_000)


class StatusMappingTests(unittest.TestCase):
    def test_every_program_status_has_a_job_status(self):
        self.assertEqual(
            set(ONCHAIN_STATUS_TO_JOB_STATUS),
            {
                "Open",
                "InProgress",
                "AwaitingEscrow",
                "AwaitingApproval",
                "Completed",
                "Disputed",
                "Refunded",
            },
        )

    def test_the_program_drives_the_job_status(self):
        self.assertEqual(ONCHAIN_STATUS_TO_JOB_STATUS["Open"], JobStatus.OPEN)
        self.assertEqual(
            ONCHAIN_STATUS_TO_JOB_STATUS["Completed"], JobStatus.COMPLETED
        )
        self.assertEqual(
            ONCHAIN_STATUS_TO_JOB_STATUS["Refunded"], JobStatus.CANCELLED
        )
        self.assertEqual(
            ONCHAIN_STATUS_TO_JOB_STATUS["Disputed"], JobStatus.IN_PROGRESS
        )


class AmountTests(unittest.TestCase):
    def test_usdc_amounts_are_converted_to_base_units(self):
        self.assertEqual(to_usdc_units("3.12"), 3_120_000)
        self.assertEqual(to_usdc_units(25), 25_000_000)
        self.assertEqual(to_usdc_units("0.000001"), 1)

    def test_usdc_amounts_are_truncated_not_rounded(self):
        self.assertEqual(to_usdc_units("1.0000009"), 1_000_000)

    def test_naira_amounts_are_converted_to_kobo(self):
        self.assertEqual(to_kobo(5000), 500_000)
        self.assertEqual(to_kobo("5000.50"), 500_050)

    def test_sub_kobo_amounts_are_rejected(self):
        with self.assertRaises(Exception):
            to_kobo("5000.005")


if __name__ == "__main__":
    unittest.main()
