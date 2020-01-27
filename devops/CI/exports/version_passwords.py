# IMPORTANT - do not export cortex related stuff here. This file should be importable in chef-repo as well

import base64
import hashlib
import re

import redis


class VersionPasswords:
    def __init__(self):
        self.redis = redis.Redis(host='services.axonius.lan')
        self.version_prefix = f'version_password_'
        self.decrypt_version_salt_key = 'decrypt_version_salt'

    @staticmethod
    def extract_version_from_string(version_string):
        pattern = r'(\d+_\d+).*'
        match = re.match(pattern, version_string)
        if match:
            return match[1]
        return version_string

    def get_password_for_version(self, version):
        version = self.extract_version_from_string(version)
        salt = self.get_decrypt_version_salt()
        password = base64.b64encode(hashlib.md5(version.encode() + salt).digest())[0:16]

        return password.decode()

    def get_decrypt_version_salt(self) -> bytes:
        return self.redis.get(self.decrypt_version_salt_key)
