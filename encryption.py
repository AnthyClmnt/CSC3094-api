from cryptography.fernet import Fernet
import os


def encryptToken(token: str):
    key = os.getenv('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.encrypt(token.encode())


def decrypt_token(token: str):
    key = os.getenv('ENCRYPTION_KEY')
    f = Fernet(key)
    return f.decrypt(token).decode()

