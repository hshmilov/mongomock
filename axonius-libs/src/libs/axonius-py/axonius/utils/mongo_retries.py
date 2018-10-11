import logging

from pymongo.errors import ConnectionFailure, OperationFailure
from retrying import retry

logger = logging.getLogger(f'axonius.{__name__}')


def retry_if_mongo_error(exception):
    """
    Return whether or not the exception originates from Mongo
    """
    return isinstance(exception, (OperationFailure, ConnectionFailure))


def mongo_retry():
    """
    Sometimes mongo operations can fail, especially transactions.
    Use this decorator to retry a couple of times for those cases.
    This is the recommended uses according to specs

    https://docs.mongodb.com/manual/core/transactions/

    > In addition to the single retry behavior provided by the MongoDB drivers,
    > applications should take measures to handle "UnknownTransactionCommitResult" errors during transaction commits.
    """
    return retry(wait_fixed=10,
                 stop_max_delay=1000,
                 retry_on_exception=retry_if_mongo_error)
