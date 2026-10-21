import hashlib
import hmac
import unittest

from payment_signatures import extract_raw_data, verify_signature


class PaymentSignatureTests(unittest.TestCase):
    def _sign(self, data: bytes, secret: str) -> str:
        return hmac.new(secret.encode(), data, hashlib.sha256).hexdigest()

    def test_uses_exact_raw_data_not_reserialized_floats(self):
        raw_body = (
            b'{"eventId":"evt_1","eventType":"checkout.completed",'
            b'"data":{"amount":5000.00,"reference":"job-1"}}'
        )
        raw_data = extract_raw_data(raw_body)
        secret = "test-secret"

        self.assertEqual(
            raw_data,
            b'{"amount":5000.00,"reference":"job-1"}',
        )
        self.assertTrue(
            verify_signature(raw_data, self._sign(raw_data, secret), secret)
        )

    def test_extracts_data_with_whitespace_and_nested_objects(self):
        raw_body = b'{\n "eventType": "checkout.completed",\n "data": {"a": {"b": 1}, "c": [1, 2]}\n}'
        self.assertEqual(
            extract_raw_data(raw_body),
            b'{"a": {"b": 1}, "c": [1, 2]}',
        )

    def test_missing_data(self):
        self.assertIsNone(extract_raw_data(b'{"eventType":"checkout.completed"}'))

    def test_invalid_signature(self):
        self.assertFalse(verify_signature(b'{"a":1}', "bad", "test-secret"))


if __name__ == "__main__":
    unittest.main()
