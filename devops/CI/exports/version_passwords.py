# IMPORTANT - do not export cortex related stuff here. This file should be importable in chef-repo as well

import redis
import base64
import hashlib


class VersionPasswords:
    def __init__(self):
        self.redis = redis.Redis(host='services.axonius.lan')
        self.version_prefix = f'version_password_'
        self.latest_version_key = self.version_prefix + 'latest'
        self.decrypt_version_salt_key = 'decrypt_version_salt'

    def _get_latest_version_password(self):
        return self.redis.get(self.latest_version_key) or b''

    def get_password_for_version(self, version):
        '''
        :param version:
        :return: password string
        If no password was ever set for this version - lets use the password for latest. Also lets create and entry
        to save for this password for future reference.
        '''
        if version == 'latest':
            password = self._get_latest_version_password()
        else:
            salt = self.get_decrypt_version_salt()
            password = base64.b64encode(hashlib.md5(version.encode() + salt).digest())[0:16]
        return password.decode()

    def get_decrypt_version_salt(self) -> bytes:
        return self.redis.get(self.decrypt_version_salt_key)
