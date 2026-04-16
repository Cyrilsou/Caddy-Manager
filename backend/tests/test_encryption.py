from app.security.encryption import TokenEncryptor


class TestEncryption:
    def test_encrypt_and_decrypt(self):
        encryptor = TokenEncryptor("test-secret-key-minimum-32-chars!")
        plaintext = "cf-api-token-12345"
        ciphertext = encryptor.encrypt(plaintext)
        assert ciphertext != plaintext
        assert encryptor.decrypt(ciphertext) == plaintext

    def test_different_ciphertexts(self):
        encryptor = TokenEncryptor("test-secret-key-minimum-32-chars!")
        c1 = encryptor.encrypt("same-text")
        c2 = encryptor.encrypt("same-text")
        assert c1 != c2  # Fernet uses random IV

    def test_wrong_key_fails(self):
        enc1 = TokenEncryptor("key-one-minimum-32-characters!!!")
        enc2 = TokenEncryptor("key-two-minimum-32-characters!!!")
        ciphertext = enc1.encrypt("secret")
        try:
            enc2.decrypt(ciphertext)
            assert False, "Should have raised"
        except Exception:
            pass
