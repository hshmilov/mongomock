from pymongo import MongoClient


class MockManager:
    def __init__(self, db_server):
        self.db = MongoClient(db_server).db

    def get_devices(self, plugin_name, client_id, offset, limit):
        print(f'Should use {self.db}')
        return {
            'total_count': 1,
            'data': [
                {
                    'id': f'{plugin_name}_{client_id}_0',
                    'name': f'device_{plugin_name}_{client_id}_0',
                    'hostname': f'PC-{plugin_name}-{client_id}'
                }
            ]
        }

    def get_users(self, plugin_name, client_id, offset, limit):
        print(f'Should use {self.db}')
        return {
            'total_count': 1,
            'data': [
                {
                    'id': f'{plugin_name}_{client_id}_0',
                    'username': f'user_{plugin_name}_{client_id}_0',
                    'first_name': 'john',
                    'last_name': 'doe'
                }
            ]
        }
