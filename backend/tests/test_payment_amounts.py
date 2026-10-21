import unittest

from payment_amounts import AmountError, commission_kobo, to_kobo, to_ngn


class PaymentAmountTests(unittest.TestCase):
    def test_to_kobo(self):
        self.assertEqual(to_kobo("10000.00"), 1_000_000)
        self.assertEqual(to_kobo(10000), 1_000_000)

    def test_to_ngn_requires_whole_naira(self):
        self.assertEqual(to_ngn(1_000_000), 10000)
        with self.assertRaises(AmountError):
            to_ngn(1_000_050)

    def test_to_ngn_rejects_non_positive(self):
        with self.assertRaises(AmountError):
            to_ngn(0)

    def test_commission_is_whole_naira(self):
        self.assertEqual(commission_kobo(1_000_000, 500), 50_000)
        self.assertEqual(commission_kobo(1_001_000, 500), 50_000)


if __name__ == "__main__":
    unittest.main()
