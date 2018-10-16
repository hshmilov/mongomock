import os
from pymongo import MongoClient

from qcore_adapter.protocol.consts import PUMP_SERIAL

DB_NAME = 'QCORE_DB'


class QcoreMongo(object):

    def __init__(self, connection):
        self._table = connection[DB_NAME]['PUMPS']

    @property
    def table(self):
        return self._table

    @property
    def all_pumps(self):
        return self.table.find({})

    def pump_by_serial(self, pump_serial):
        return self.table.find({PUMP_SERIAL: pump_serial}).next()
