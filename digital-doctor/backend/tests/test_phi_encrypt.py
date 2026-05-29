from src.security.phi_encrypt import encrypt_phi, decrypt_phi


def test_encrypt_decrypt_roundtrip():
    plaintext = "张三 110101199001011234"
    ciphertext = encrypt_phi(plaintext)
    assert ciphertext != plaintext
    assert decrypt_phi(ciphertext) == plaintext


def test_encrypt_produces_different_output():
    text = "test_data"
    c1 = encrypt_phi(text)
    c2 = encrypt_phi(text)
    # Fernet uses random IV, so same plaintext produces different ciphertext
    assert c1 != c2
    # But both decrypt to the same plaintext
    assert decrypt_phi(c1) == text
    assert decrypt_phi(c2) == text
