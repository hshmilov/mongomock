import logging
import os

import OpenSSL

SSL_CERT_PATH = '/etc/ssl/certs/nginx-selfsigned.crt'
SSL_KEY_PATH = '/etc/ssl/private/nginx-selfsigned.key'
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


def check_associate_cert_with_private_key(cert: str, private_key: str) -> bool:
    """
    :type cert: binary data of public key certificate
    :type private_key: binary data of private key pem
    :raise: Exception if any key is invalid
    :return: if the keys are associated
    """
    try:
        private_key_obj = OpenSSL.crypto.load_privatekey(OpenSSL.crypto.FILETYPE_PEM, private_key)
    except OpenSSL.crypto.Error:
        raise Exception('Error: private key is invalid. Expected pem format')

    try:
        cert_obj = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert)
    except OpenSSL.crypto.Error:
        raise Exception('Error: Public certificate is invalid. Expected pem format')

    context = OpenSSL.SSL.Context(OpenSSL.SSL.TLSv1_METHOD)
    context.use_privatekey(private_key_obj)
    context.use_certificate(cert_obj)
    try:
        context.check_privatekey()
        return True
    except OpenSSL.SSL.Error:
        return False
