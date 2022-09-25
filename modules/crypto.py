from cryptography.fernet import Fernet
import hashlib
import base64

def encrypt_user_string(user_id: int, ekey: str, string: str) -> bytes:
    """Encrypts an user string.
    Used for credentials and data in general

    Args:
        user_id (int): discord user id
        ekey (str): global ekey
        string (str): string to encrypt

    Returns:
        bytes: Encrypted data
    """

    user_sha224 = sha224(str(user_id + ekey))[0:32] # get first 32 characters of user_id in sha224
    encryption_key = b64_encode(user_sha224, urlsafe = True) # base64 of user_id in sha224
    return encrypt_string(string = string, key = encryption_key) # encrypted data

def decrypt_user_string(user_id: int, ekey: str, string: bytes) -> str:
    """Decrypts an user string.
    Used to access user encrypted data

    Args:
        user_id (int): discord user id
        ekey (str): global ekey
        string (bytes): data to decrypt

    Returns:
        bytes: Encrypted data
    """

    user_sha224 = sha224(str(user_id) + ekey)[0:32] # get first 32 characters of user_id in sha224
    encryption_key = b64_encode(user_sha224, urlsafe = True) # base64 of user_id in sha224
    return decrypt_string(data = string, key = encryption_key) # decrypted data

## Hashes
def sha1(string: str) -> str:
    """Returns the SHA1 of passed string
    """
    hash_object = hashlib.sha1(string.encode())
    return hash_object.hexdigest()

def sha224(string: str) -> str:
    """Returns the SHA244 of passed string
    """
    hash_object = hashlib.sha224(string.encode())
    return hash_object.hexdigest()


## AES
def encrypt_string(string: str, key: bytes) -> bytes:
    """Encrypts the passed string
    """
    fernet = Fernet(key)
    return fernet.encrypt(string.encode())

def decrypt_string(data: bytes, key: bytes) -> bytes:
    """Decrypts the passed data (string)
    """
    fernet = Fernet(key)
    return fernet.decrypt(data)


## Base64
def b64_encode(string: str, urlsafe: bool = False) -> bytes:
    """Encodes a string to base64
    """
    string_bytes = string.encode()
    if urlsafe:
        return base64.urlsafe_b64encode(string_bytes)
    else:
        return base64.b64decode(string_bytes)

def b64_decode(string: bytes, urlsafe: bool = False) -> str:
    """Decodes a base64 string
    """
    if urlsafe:
        return base64.urlsafe_b64decode(string).decode()
    else:
        return base64.b64decode(string).decode()