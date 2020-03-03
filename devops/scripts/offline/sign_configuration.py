"""
Encrypt file and RSA Sign using a private key
"""
import os
import tarfile
import argparse
from pathlib import Path
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES


def main():
    # define buffer 1Mb
    buffer_size = 1024000

    parser = argparse.ArgumentParser(description='Sign and encrypt executable configuration script')
    parser.add_argument('--key', type=str, default=False,
                        help='Private key file for encrypting the executable configuration script', required=True)
    parser.add_argument('--file', type=str, default=False,
                        help='Executable script to sign and encrypt', required=True)

    args = parser.parse_args()

    private_key_file = args.key
    configuration_script_file = args.file

    configuration_script_file_name = Path(configuration_script_file).name
    output_file_name = 'aaas_job.axonius'
    signature_file_name = 'axonius.sig'
    tar_file_name = f'{configuration_script_file_name}.tar'

    # get private key from file
    private_key = RSA.import_key(open(private_key_file).read(), 'axonius')
    # get encryption key from file
    encrypt_key_file = os.path.join(os.path.dirname(__file__), 'configuration.key')
    try:
        with open(encrypt_key_file, 'rb') as encrypt_file:
            encrypt_key = encrypt_file.read()
        # open the file to decrypt and output file
        with open(configuration_script_file, 'rb') as input_file:
            with open(output_file_name, 'wb') as output_file:
                # create the cipher
                cipher_encrypt = AES.new(encrypt_key, AES.MODE_CFB)
                # write the iv to the file
                output_file.write(cipher_encrypt.iv)
                # encrypt the file and save to output file
                buffer = input_file.read(buffer_size)
                content_hash = SHA256.new(buffer)
                while len(buffer) > 0:
                    ciphered_bytes = cipher_encrypt.encrypt(buffer)
                    output_file.write(ciphered_bytes)
                    buffer = input_file.read(buffer_size)
                    content_hash.update(buffer)

        signature = pkcs1_15.new(private_key).sign(content_hash)

        with open(signature_file_name, 'wb') as sig_file:
            sig_file.write(signature)

        with tarfile.open(tar_file_name, 'w') as tar:
            tar.add(signature_file_name)
            tar.add(output_file_name)

    finally:
        if os.path.exists(signature_file_name):
            os.remove(signature_file_name)
        if os.path.exists(output_file_name):
            os.remove(output_file_name)


if __name__ == '__main__':
    main()
