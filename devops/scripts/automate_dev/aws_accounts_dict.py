# IMPORTANT - do not export cortex related stuff here. This file should be importable in chef-repo as well


import redis


class AwsAccountsStore:
    def __init__(self):
        self.redis = redis.Redis(host='services.axonius.lan', db=1)

    def set_data_for_account(self, account_id, data):
        self.redis.set(account_id, data)

    def get_data_for_account(self, account_id):
        return self.redis.get(account_id)
