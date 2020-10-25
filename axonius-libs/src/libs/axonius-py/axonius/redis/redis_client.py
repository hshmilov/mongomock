"""
Leave this file simple. It is imported by different processes and so it must be lightweight and independent
of any context variables
"""
import redis
from axonius.redis.redis_encrypt import RedisEncrypt
from axonius.consts.plugin_consts import AXONIUS_SETTINGS_PATH

DB_HOST = 'redis.axonius.local'
PORT = '6379'


def get_db_client(host=DB_HOST, password=None, port=PORT, db=0, axonius_settings_path=AXONIUS_SETTINGS_PATH):
    return redis.Redis(host=host,
                       port=port,
                       db=db,
                       password=password or RedisEncrypt.get_redis_password(axonius_settings_path),
                       ssl=True,
                       ssl_ca_certs=f'{axonius_settings_path}/redis/ca.crt',
                       ssl_keyfile=f'{axonius_settings_path}/redis/redis.key',
                       ssl_certfile=f'{axonius_settings_path}/redis/redis.crt')
