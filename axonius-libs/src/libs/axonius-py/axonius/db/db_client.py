"""
Leave this file simple. It is imported by different processes and so it must be lightweight and independent
of any context variables
"""
from pymongo import MongoClient

DB_HOST = 'mongodb://mongo.axonius.local:27017'
DB_USER = 'ax_user'
DB_PASSWORD = 'ax_pass'


def get_db_client() -> MongoClient:
    # https://jira.mongodb.org/browse/PYTHON-986
    return MongoClient(
        DB_HOST, replicaSet='axon-cluster', retryWrites=True,
        username=DB_USER, password=DB_PASSWORD,
        localthresholdms=1000, connect=False
    )
