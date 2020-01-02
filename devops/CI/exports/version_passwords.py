# IMPORTANT - do not export cortex related stuff here. This file should be importable in chef-repo as well

import redis


class VersionPasswords:
    def __init__(self):
        self.redis = redis.Redis(host='services.axonius.lan')
        self.version_prefix = f'version_password_'
        self.latest_version_key = self.version_prefix + 'latest'

    def get_latest_version_password(self):
        return (self.redis.get(self.latest_version_key) or b'').decode()

    def get_password_for_version(self, version):
        '''
        :param version:
        :return: password string
        If no password was ever set for this version - lets use the password for latest. Also lets create and entry
        to save for this password for future reference.
        '''
        password = (self.redis.get(self.version_prefix + version) or b'').decode()
        if not password:
            password = self.get_latest_version_password()
            self.redis.set(self.version_prefix + version, password)
        return password
