#!/home/ubuntu/cortex/venv/bin/python
"""
Decrypt file and RSA Verify against a public key
"""
import os
import argparse
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES


def main():
    # define buffer 1Mb
    buffer_size = 1024000

    parser = argparse.ArgumentParser(
        description='Verify and decrypt executable configuration script\nreturn an executable script')
    parser.add_argument('--file', type=str, default=False, help='Encrypted executable script', required=True)
    parser.add_argument('--signature', type=str, default=False, help='Signature file for validation', required=True)

    args = parser.parse_args()

    configuration_script_file = args.file
    signature_file = args.signature

    output_file_name = 'axonius_configuration'
    # get public key from file
    public_key_file = os.path.join(os.path.dirname(__file__), 'configuration-script-public.pem')
    public_key = RSA.import_key(open(public_key_file).read())
    # get encryption key from file
    decrypt_key_file = os.path.join(os.path.dirname(__file__), 'configuration.key')
    valid = False
    try:
        with open(decrypt_key_file, 'rb') as decrypt_file:
            decrypt_key = decrypt_file.read()
        # open the file to decrypt and output file
        with open(configuration_script_file, 'rb') as input_file:
            with open(output_file_name, 'wb') as output_file:
                # get the iv from file
                iv = input_file.read(16)
                # create the cipher
                cipher_encrypt = AES.new(decrypt_key, AES.MODE_CFB, iv=iv)
                # decrypt the file and save to output file
                buffer = input_file.read(buffer_size)
                pre_hashed_content = SHA256.new()
                while len(buffer) > 0:
                    decrypted_bytes = cipher_encrypt.decrypt(buffer)
                    pre_hashed_content.update(decrypted_bytes)
                    output_file.write(decrypted_bytes)
                    buffer = input_file.read(buffer_size)

        with open(signature_file, 'rb') as sig_file:
            signature = sig_file.read()

        try:
            pkcs1_15.new(public_key).verify(pre_hashed_content, signature)
            valid = True
        except ValueError:
            valid = False

    finally:
        print(f'file validation {"pass" if valid else "failed"}')
        if os.path.exists(configuration_script_file):
            os.remove(configuration_script_file)
        if os.path.exists(signature_file):
            os.remove(signature_file)
        if valid:
            exit(0)
        else:
            if os.path.exists(output_file_name):
                os.remove(output_file_name)
            exit(1)


if __name__ == '__main__':
    main()
