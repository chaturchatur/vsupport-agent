from app.services.phone import normalize_phone


def test_us_number_with_country_code():
    normalized, valid = normalize_phone("+14155551234")
    assert normalized == "+14155551234"
    assert valid is True


def test_us_number_without_country_code():
    normalized, valid = normalize_phone("(415) 555-1234")
    assert normalized == "+14155551234"
    assert valid is True


def test_us_number_digits_only():
    normalized, valid = normalize_phone("4155551234")
    assert normalized == "+14155551234"
    assert valid is True


def test_invalid_number():
    normalized, valid = normalize_phone("not-a-number")
    assert valid is False


def test_empty_string():
    normalized, valid = normalize_phone("")
    assert valid is False


def test_custom_region():
    normalized, valid = normalize_phone("020 7946 0958", default_region="GB")
    assert normalized == "+442079460958"
    assert valid is True
