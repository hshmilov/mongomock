import logging
from threading import Lock
from typing import Any


from bson import Binary
from bson.codec_options import CodecOptions
from cryptography.exceptions import InternalError
from cryptography.hazmat.backends.openssl import backend
from cryptography.hazmat.bindings.openssl import binding
import pymongo
from pymongo.encryption import Algorithm, ClientEncryption
from pymongo.errors import EncryptionError

logger = logging.getLogger(f'axonius.{__name__}')

MONGO_MASTER_KEY_SIZE = 96

'''
This module should handle data encryption for Mongo
Using client side fields level encryption
https://docs.mongodb.com/manual/core/security-client-side-encryption/
'''

# pylint: disable=W0212


class MongoEncrypt:
    _fips_lock = Lock()
    _is_fips_enabled = False

    @staticmethod
    def get_db_encryption(db_connection: pymongo.MongoClient, collection: str, key: bytes) -> ClientEncryption:
        """
        Get mongo ClientEncryption object
        :param db_connection: MongoClient connection
        :param collection: keys collection
        :param key: encryption Masterkey data
        :return: ClientEncryption object
        """
        if not isinstance(key, bytes):
            logger.exception(f'Wrong encryption key: {key}')
            return None
        codec_options = CodecOptions()
        enc = ClientEncryption({
            'local': {
                'key': key
            }
        }, collection, db_connection, codec_options)
        return enc

    @classmethod
    def enable_fips(cls):
        cls._is_fips_enabled = True

    @classmethod
    def disable_fips(cls):
        cls._is_fips_enabled = False

    @classmethod
    def set_fips(cls, mode: bool) -> int:
        """
        Enable or disable fips mode
        :param mode: True/False
        :return: 1 on success
        """
        if not cls._is_fips_enabled:
            return 1
        try:
            lib = backend._lib
            with cls._fips_lock:
                status = lib.FIPS_mode_set(mode) if lib.FIPS_mode() != mode else 1
            binding._openssl_assert(lib, status == 1)
            return status
        except InternalError as e:
            logger.warning(e)
        except Exception:
            logger.exception('Error changing fips mode')
        return -1

    @staticmethod
    def db_encrypt(client_encrypt: ClientEncryption, key_alt_name: str, data: Any) -> Any:
        """
        Encrypt data using mongo client encryption by key alt name
        :param client_encrypt: ClientEncryption Instance
        :param key_alt_name: key alt name for encrypting the data
        :param data: data to encrypt
        :return: encrypted data
        """
        encrypted = None
        try:
            MongoEncrypt.set_fips(True)
            # There is no option to get key by alt_name right now on Pymongo
            # So we try to encrypt, if key_alt_name does not exist, we create a new key
            encrypted = client_encrypt.encrypt(data, key_alt_name=key_alt_name,
                                               algorithm=Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random)
        except EncryptionError as e:
            if 'did not provide all keys' in str(e):
                logger.info(f'Creating a new encryption key, alt name: {key_alt_name}')
                client_encrypt.create_data_key('local', key_alt_names=[key_alt_name])
            encrypted = client_encrypt.encrypt(data, key_alt_name=key_alt_name,
                                               algorithm=Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random)
        MongoEncrypt.set_fips(False)
        return encrypted

    @staticmethod
    def db_decrypt(client_encrypt: ClientEncryption, data: Binary) -> Any:
        """
        Decrypt data using mongo client encryption
        :param client_encrypt: ClientEncryption Instance
        :param data: data to decrypt
        :return: decrypted data
        """
        MongoEncrypt.set_fips(True)
        decrypted_data = client_encrypt.decrypt(data)
        MongoEncrypt.set_fips(False)
        return decrypted_data
