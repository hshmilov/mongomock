import os
from pymongo import MongoClient

from qcore_adapter.protocol.consts import PUMP_SERIAL

DB_NAME = 'QCORE_DB'


class QcoreMongo(object):

    def __init__(self):

        # hack that allows me to deal with proper mongo creds propagation later
        if os.environ.get('DOCKER') == 'true':
            host = 'mongo'
        else:
            host = 'localhost'

        self.connection = MongoClient(host=host, username='ax_user', password='ax_pass')
        self._table = self.connection[DB_NAME]['PUMPS']

    @property
    def table(self):
        return self._table

    @property
    def all_pumps(self):
        return self.table.find({})

    def pump_by_serial(self, pump_serial):
        return self.table.find({PUMP_SERIAL: pump_serial}).next()
