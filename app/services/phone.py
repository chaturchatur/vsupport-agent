import phonenumbers


def normalize_phone(raw: str, default_region: str = "US") -> tuple[str, bool]:
    """Normalize a phone number to E.164 format.

    Returns (normalized_number, is_valid). If parsing fails, returns (raw, False).
    """
    try:
        parsed = phonenumbers.parse(raw, default_region)
        valid = phonenumbers.is_valid_number(parsed)
        normalized = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return normalized, valid
    except phonenumbers.NumberParseException:
        return raw, False
