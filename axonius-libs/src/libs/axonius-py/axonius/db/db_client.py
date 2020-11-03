"""
Leave this file simple. It is imported by different processes and so it must be lightweight and independent
of any context variables
"""
import os

from pymongo import MongoClient, monitoring

DB_HOST = 'mongo.axonius.local'
DB_USER = 'ax_user'
DB_PASSWORD = 'ax_pass'
DB_URL = f'mongodb://{DB_HOST}:27017'


class CommandLogger(monitoring.CommandListener):

    def started(self, event):
        print('Command {0.command_name} with request id '
              '{0.request_id} started on server '
              '{0.connection_id} - {0.command}'.format(event))

    def succeeded(self, event):
        print('Command {0.command_name} with request id '
              '{0.request_id} on server {0.connection_id} '
              'succeeded in {0.duration_micros} '
              'microseconds - {0.command}'.format(event))

    def failed(self, event):
        print('Command {0.command_name} with request id '
              '{0.request_id} on server {0.connection_id} '
              'failed in {0.duration_micros} '
              'microseconds - {0.command}'.format(event))


def get_db_client(get_unique=False) -> MongoClient:
    if not get_unique and hasattr(get_db_client, 'db_instance'):
        return get_db_client.db_instance

    # https://jira.mongodb.org/browse/PYTHON-986
    max_pool_size = 100
    if os.getenv('MONGO_MAXPOOLSIZE'):
        max_pool_size = int(os.getenv('MONGO_MAXPOOLSIZE'))
    if os.getenv('MONGO_DEBUG') == '1':
        client = MongoClient(
            DB_URL, replicaSet='axon-cluster', retryWrites=True,
            username=DB_USER, password=DB_PASSWORD,
            localthresholdms=1000, connect=False, maxPoolSize=max_pool_size,
            event_listeners=[CommandLogger()])
    else:
        client = MongoClient(
            DB_URL, replicaSet='axon-cluster', retryWrites=True,
            username=DB_USER, password=DB_PASSWORD, maxPoolSize=max_pool_size,
            localthresholdms=1000, connect=False
        )

    if not get_unique:
        get_db_client.db_instance = client

    return client
