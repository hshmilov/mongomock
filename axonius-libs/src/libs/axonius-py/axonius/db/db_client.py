"""
Leave this file simple. It is imported by different processes and so it must be lightweight and independent
of any context variables
"""
import os

from pymongo import MongoClient, monitoring

DB_HOST = 'mongodb://mongo.axonius.local:27017'
DB_USER = 'ax_user'
DB_PASSWORD = 'ax_pass'


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


def get_db_client() -> MongoClient:
    # https://jira.mongodb.org/browse/PYTHON-986
    max_pool_size = 100
    if os.getenv('MONGO_MAXPOOLSIZE'):
        max_pool_size = int(os.getenv('MONGO_MAXPOOLSIZE'))
    if os.getenv('MONGO_DEBUG') == '1':
        return MongoClient(
            DB_HOST, replicaSet='axon-cluster', retryWrites=True,
            username=DB_USER, password=DB_PASSWORD,
            localthresholdms=1000, connect=False, maxPoolSize=max_pool_size,
            event_listeners=[CommandLogger()])

    return MongoClient(
        DB_HOST, replicaSet='axon-cluster', retryWrites=True,
        username=DB_USER, password=DB_PASSWORD, maxPoolSize=max_pool_size,
        localthresholdms=1000, connect=False
    )
