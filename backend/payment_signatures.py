import hashlib
import hmac
import json


def extract_raw_data(raw_body: bytes) -> bytes | None:
    """Return the exact raw JSON value of the top-level `data` field.

    FossaPay signs JSON.stringify(body.data), so the bytes must come from the
    received body rather than a Python re-serialization.
    """
    try:
        body = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        return None

    decoder = json.JSONDecoder()

    def skip_ws(index: int) -> int:
        while index < len(body) and body[index] in " \t\r\n":
            index += 1
        return index

    index = skip_ws(0)
    if index >= len(body) or body[index] != "{":
        return None
    index += 1

    while True:
        index = skip_ws(index)
        if index >= len(body) or body[index] == "}":
            return None

        try:
            key, index = decoder.raw_decode(body, index)
        except json.JSONDecodeError:
            return None

        index = skip_ws(index)
        if index >= len(body) or body[index] != ":":
            return None

        index = skip_ws(index + 1)
        start = index

        try:
            _, index = decoder.raw_decode(body, index)
        except json.JSONDecodeError:
            return None

        if key == "data":
            return body[start:index].encode("utf-8")

        index = skip_ws(index)
        if index < len(body) and body[index] == ",":
            index += 1
            continue

        return None


def verify_signature(raw_data: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_data,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_body_signature(raw_body: bytes, signature: str, secret: str) -> bool:
    """Verify a signature computed over the whole request body."""
    expected = hmac.new(
        secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def verify_fossapay_event(
    raw_body: bytes,
    headers: dict,
    secret: str,
) -> tuple[bool, str | None]:
    """Verify a FossaPay webhook.

    FossaPay ships two signature headers and its public example signs
    `JSON.stringify(body.data)`, while the Checkout SDK verifies the v2
    signature against the raw request body. Until a real event has been
    captured we accept any of the documented combinations, and report which
    one matched so the correct scheme can be pinned down.

    Returns `(is_valid, matched_scheme)`.
    """
    lowered = {str(key).lower(): value for key, value in headers.items()}

    v2 = lowered.get("x-fossapay-signature-v2")
    if v2 and verify_body_signature(raw_body, v2, secret):
        return True, "v2-body"

    v1 = lowered.get("x-fossapay-signature")
    if v1:
        raw_data = extract_raw_data(raw_body)
        if raw_data is not None and verify_signature(raw_data, v1, secret):
            return True, "v1-data"
        if verify_body_signature(raw_body, v1, secret):
            return True, "v1-body"

    return False, None
