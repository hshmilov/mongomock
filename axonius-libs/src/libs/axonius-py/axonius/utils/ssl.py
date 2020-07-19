import logging
import os
import pem

import OpenSSL
from OpenSSL import crypto

SSL_CERT_PATH = '/etc/ssl/certs/nginx-selfsigned.crt'
SSL_KEY_PATH = '/etc/ssl/private/nginx-selfsigned.key'
SSL_CERT_PATH_LIBS = '/home/axonius/keys/nginx-selfsigned.crt'
SSL_KEY_PATH_LIBS = '/home/axonius/keys/nginx-selfsigned.key'
SSL_ECDH_CERT_PATH_LIBS = '/home/axonius/keys/nginx-selfsigned-ecdh.crt'
SSL_ECDH_KEY_PATH_LIBS = '/home/axonius/keys/nginx-selfsigned-ecdh.key'
MUTUAL_TLS_CA_PATH = '/home/axonius/mutual_tls_ca.crt'
MUTUAL_TLS_CONFIG_FILE = '/home/axonius/config/gui_external_configs/mtls.conf'
SSL_CIPHERS_CONFIG_FILE = '/home/axonius/config/nginx_conf.d/ciphers.conf'
CA_CERT_PATH = '/usr/local/share/ca-certificates/'
CA_BUNDLE_ENV_NAME = 'REQUESTS_CA_BUNDLE'

logger = logging.getLogger(f'axonius.{__name__}')


def get_ca_bundle() -> str:
    """
    Getting trusted ca bundle file using requests environment data
    :return: ca bundle binary data
    """
    ca_file_data = None
    filename = None
    try:
        filename = os.getenv(CA_BUNDLE_ENV_NAME)
        if filename:
            with open(filename, 'r') as f:
                ca_file_data = f.read()
    except Exception:
        logger.exception(f'Error getting ca file {filename}')
    return ca_file_data


def get_private_key_without_passphrase(private_key, passphrase=b''):
    if not passphrase:
        passphrase = b''
    if isinstance(passphrase, str):
        passphrase = passphrase.encode('utf-8')

    key = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key, passphrase)
    return crypto.dump_privatekey(crypto.FILETYPE_PEM, key)


def validate_cert_with_ca(cert_binary: bytes, ca_binary: bytes) -> bool:
    """
    :param cert_binary: Binary data of client certificate
    :param ca_binary: Binary data of CA
    :return:
    """

    try:
        certificate = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_binary)
    except OpenSSL.crypto.Error as e:
        logger.exception(f'Error parsing certificate')
        raise Exception(f'Certificate is invalid: {str(e)}')

    try:
        store = OpenSSL.crypto.X509Store()
        for _ca in pem.parse(ca_binary):
            store.add_cert(OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, str(_ca)))
    except OpenSSL.crypto.Error as e:
        logger.exception(f'Error parsing CA')
        raise Exception(f'CA is invalid: {str(e)}')

    store_ctx = OpenSSL.crypto.X509StoreContext(store, certificate)
    # Verify the certificate, returns None if it can validate the certificate
    return store_ctx.verify_certificate() is None


def check_associate_cert_with_private_key(cert: str, private_key: str, passphrase: bytes = '') -> bool:
    """
    :type cert: binary data of public key certificate
    :type private_key: binary data of private key pem
    :type passphrase: optional passphrase
    :raise: Exception if any key is invalid
    :return: if the keys are associated
    """
    try:
        private_key_no_pass = get_private_key_without_passphrase(private_key, passphrase)
        private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key_no_pass)
    except OpenSSL.crypto.Error as e:
        logger.exception(f'private key parsing error')
        if 'bad decrypt' in str(e).lower():
            raise Exception(f'Error: Invalid password for private key')
        raise Exception(f'Error: private key is invalid: {str(e)}')

    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    except OpenSSL.crypto.Error as e:
        logger.exception(f'public key parsing error')
        raise Exception(f'Error: Public certificate is invalid: {str(e)}')

    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    context.use_privatekey(private_key_obj)
    context.use_certificate(cert_obj)
    try:
        context.check_privatekey()
        return True
    except OpenSSL.SSL.Error:
        logger.exception(f'Error assoicating private and public key')
        return False
