import unittest
from datetime import date

from payment_validation import (
    PaymentProfileValidationError,
    normalize_phone_number,
    validate_date_of_birth,
    validate_single_name,
)


class PaymentValidationTests(unittest.TestCase):
    def test_nigerian_phone_formats(self):
        self.assertEqual(normalize_phone_number("08031234567"), "+2348031234567")
        self.assertEqual(normalize_phone_number("8031234567"), "+2348031234567")
        self.assertEqual(normalize_phone_number("+2348031234567"), "+2348031234567")

    def test_single_name_accepts_one_token(self):
        self.assertEqual(validate_single_name("Ada", "first_name"), "Ada")

    def test_single_name_rejects_spaces_and_digits(self):
        with self.assertRaises(PaymentProfileValidationError):
            validate_single_name("Ada Ngozi", "first_name")
        with self.assertRaises(PaymentProfileValidationError):
            validate_single_name("Ada2", "first_name")

    def test_date_of_birth_requires_adult(self):
        self.assertEqual(
            validate_date_of_birth(date(1990, 8, 15)),
            date(1990, 8, 15),
        )
        with self.assertRaises(PaymentProfileValidationError):
            validate_date_of_birth(date.today())


if __name__ == "__main__":
    unittest.main()
