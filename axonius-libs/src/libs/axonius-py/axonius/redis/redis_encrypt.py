
import os
from axonius.consts.plugin_consts import REDIS_PASSWORD_VAR_NAME, AXONIUS_SETTINGS_PATH

REDIS_PASSWORD_SIZE = 14


class RedisEncrypt:

    @staticmethod
    def get_redis_password(axonius_settings_path=AXONIUS_SETTINGS_PATH):
        """
        :param axonius_settings_path either settings path inside axonius-manager or regular docker
        container.
        Get redis password from environment or REDIS_KEY_PATH file
        :return: password
        """
        redis_password = os.environ.get(REDIS_PASSWORD_VAR_NAME, '')
        if not redis_password:
            redis_password_file = axonius_settings_path / 'redis/.redis_password'
            if redis_password_file.is_file():
                redis_password = redis_password_file.read_text().strip()
        return redis_password
