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
