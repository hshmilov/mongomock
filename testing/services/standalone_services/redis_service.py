import os

from services.weave_service import WeaveService
from services.ports import DOCKER_PORTS
from axonius.consts.plugin_consts import AXONIUS_SETTINGS_DIR_NAME, AXONIUS_SETTINGS_PATH
from axonius.redis.redis_client import get_db_client


class RedisService(WeaveService):

    def __init__(self):
        super().__init__('redis', '../infrastructures/redis')

    @property
    def _additional_parameters(self):
        return []

    def get_dockerfile(self, *args, **kwargs):
        redis_conf_path = f'{AXONIUS_SETTINGS_PATH}/redis/redis.conf'
        return f'''
            FROM redis:6.0.8
            CMD ["redis-server", "{redis_conf_path}"]
        '''[1:] if not kwargs or kwargs.get('image_tag', '') != 'fed' else f'''
            FROM axonius/redis_fed:latest
            CMD ["redis-server", "{redis_conf_path}"]
        '''

    @property
    def volumes_override(self):
        settings_path = os.path.abspath(os.path.join(self.cortex_root_dir, AXONIUS_SETTINGS_DIR_NAME, 'redis'))
        os.makedirs(settings_path, exist_ok=True)
        container_settings_dir_path = os.path.join(AXONIUS_SETTINGS_PATH, 'redis')
        volumes = [f'{settings_path}:{container_settings_dir_path}']

        return volumes

    @staticmethod
    def get_conf_file(redis_password):
        redis_key = f'{AXONIUS_SETTINGS_PATH}/redis/redis.key'
        redis_crt = f'{AXONIUS_SETTINGS_PATH}/redis/redis.crt'
        redis_ca_crt = f'{AXONIUS_SETTINGS_PATH}/redis/ca.crt'
        return f'''
port        0
tls-port    6379
requirepass {redis_password}
tls-cert-file {redis_crt}
tls-key-file {redis_key}
tls-ca-cert-file {redis_ca_crt}
'''[1:]

    @property
    def is_unique_image(self):
        return True

    def remove_image(self):
        pass  # We never want to remove this static image...

    def is_up(self, *args, **kwargs):
        return self.get_is_container_up()

    @staticmethod
    def get_client(db, axonius_settings_path=None):
        return get_db_client(host='redis', db=db, axonius_settings_path=axonius_settings_path)

    @property
    def exposed_ports(self):
        return [(DOCKER_PORTS['redis'], DOCKER_PORTS['redis'])] if os.getenv('PROD') != 'True' else []
