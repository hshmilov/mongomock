import logging
from collections import Iterable
from enum import Enum

from flask import current_app
from flask.json import JSONEncoder, dumps

from bson import ObjectId

logger = logging.getLogger(f'axonius.{__name__}')


class IteratorJSONEncoder(JSONEncoder):
    def default(self, o):
        if isinstance(o, ObjectId):
            return str(o.generation_time)
        if isinstance(o, Enum):
            return o.name
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        return JSONEncoder.default(self, o)


class IgnoreErrorJSONEncoder(JSONEncoder):
    def default(self, obj):
        try:
            return JSONEncoder.default(self, obj)
        except Exception:
            pass


def iterator_jsonify(iterable: Iterable, buffersize: int = 30 * 1024):
    """
    An iterable version of 'flask.jsonify'
    :param iterable: The iterator to JSONify
    :param buffersize: The buffer size for the chunks to be sent to the client
    :return:
    """
    indent = None
    separators = (',', ':')

    def res():
        buffer = '['
        try:
            first = True
            for item in iterable:
                if not first:
                    buffer += ','
                first = False
                try:
                    buffer += dumps(item, indent=indent, separators=separators, cls=IteratorJSONEncoder)
                except Exception:
                    logger.exception(f'Exception in dumps in {item}')
                    raise
                if len(buffer) >= buffersize:
                    yield buffer
                    buffer = ''

            yield buffer
            yield ']\n'
        except Exception:
            logger.exception(f'Exception in iterator_jsonify, buffer is {buffer}')
            raise

    return current_app.response_class(
        res(),
        mimetype=current_app.config['JSONIFY_MIMETYPE']
    )
