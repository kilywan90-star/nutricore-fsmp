from src.security.phi_encrypt import encrypt_phi, decrypt_phi


def test_roundtrip_encrypt_decrypt():
    plaintext = "患者张三，身份证号110101199001011234，电话13812345678"
    ciphertext = encrypt_phi(plaintext)
    assert ciphertext != plaintext
    decrypted = decrypt_phi(ciphertext)
    assert decrypted == plaintext


def test_different_plaintexts_produce_different_ciphertexts():
    text1 = "患者张三"
    text2 = "患者李四"
    c1 = encrypt_phi(text1)
    c2 = encrypt_phi(text2)
    assert c1 != c2
