import logging
from typing import Any

import pymongo
from pymongo.encryption import Algorithm, ClientEncryption
from pymongo.errors import EncryptionError
from bson import Binary
from bson.codec_options import CodecOptions

logger = logging.getLogger(f'axonius.{__name__}')

MONGO_MASTER_KEY_SIZE = 96

'''
This module should handle data encryption for Mongo
Using client side fields level encryption
https://docs.mongodb.com/manual/core/security-client-side-encryption/
'''


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


def db_encrypt(client_encrypt: ClientEncryption, key_alt_name: str, data: Any) -> Any:
    """
    Encrypt data using mongo client encryption by key alt name
    :param client_encrypt: ClientEncryption Instance
    :param key_alt_name: key alt name for encrypting the data
    :param data: data to encrypt
    :return: encrypted data
    """
    try:
        # There is no option to get key by alt_name right now on Pymongo
        # So we try to encrypt, if key_alt_name does not exist, we create a new key
        return client_encrypt.encrypt(data, key_alt_name=key_alt_name,
                                      algorithm=Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random)
    except EncryptionError as e:
        if 'did not provide all keys' in str(e):
            logger.info(f'Creating a new encryption key, alt name: {key_alt_name}')
            client_encrypt.create_data_key('local', key_alt_names=[key_alt_name])
        return client_encrypt.encrypt(data, key_alt_name=key_alt_name,
                                      algorithm=Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random)


def db_decrypt(client_encrypt: ClientEncryption, data: Binary) -> Any:
    """
    Decrypt data using mongo client encryption
    :param client_encrypt: ClientEncryption Instance
    :param data: data to decrypt
    :return: decrypted data
    """
    return client_encrypt.decrypt(data)
