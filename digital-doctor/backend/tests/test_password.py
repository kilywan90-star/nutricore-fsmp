from src.security.password import hash_password, verify_password


def test_hash_and_verify():
    plain = "secure_password123"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password():
    hashed = hash_password("correct_password")
    assert not verify_password("wrong_password", hashed)
